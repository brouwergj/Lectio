#!/usr/bin/env python
"""
Index extracted corpus text into a Qdrant vector database using Ollama embeddings.

Assumptions:
- Text files already exist under ../corpus/text (or a custom --text-dir).
- An Ollama server is reachable (local or remote) and has an embedding model pulled.
- A Qdrant instance is reachable (local or remote).

Example:
    python index_corpus_qdrant.py \
        --text-dir ../corpus/text \
        --collection lectio_corpus \
        --ollama-url http://192.168.1.50:11434 \
        --ollama-model nomic-embed-text \
        --qdrant-url http://192.168.1.50:6333
"""

import argparse
import itertools
import os
from pathlib import Path
from typing import Iterable, List, Tuple

import requests
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from tqdm import tqdm


def iter_paragraphs(text_root: Path) -> Iterable[Tuple[Path, int, str]]:
    """
    Yield (file_path, paragraph_index, paragraph_text) for all .txt files.
    A simple paragraph split on double newlines; very short chunks are skipped.
    """
    for txt_path in text_root.rglob("*.txt"):
        if not txt_path.is_file():
            continue
        try:
            text = txt_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            print(f"[!] Failed to read {txt_path}: {exc}")
            continue

        raw_paragraphs = [p.strip() for p in text.split("\n\n")]
        paragraphs = [p for p in raw_paragraphs if len(p) > 40]

        for idx, para in enumerate(paragraphs):
            yield txt_path, idx, para


def get_embedding(
    session: requests.Session,
    ollama_url: str,
    model: str,
    text: str,
) -> List[float]:
    """
    Call Ollama's /api/embeddings endpoint for a single piece of text.
    """
    url = ollama_url.rstrip("/") + "/api/embeddings"
    resp = session.post(url, json={"model": model, "prompt": text})
    resp.raise_for_status()
    data = resp.json()
    return data["embedding"]


def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    dim: int,
    distance: Distance = Distance.COSINE,
) -> None:
    """
    Create or recreate the collection with the given dimensionality.
    If the collection exists with a different dimension, it will be recreated.
    """
    existing = client.get_collection(collection_name=collection_name)
    existing_dim = existing.vectors_count or existing.config.params.vectors.size  # type: ignore[attr-defined]

    if existing_dim == dim:
        print(f"[*] Reusing existing collection '{collection_name}' with dim={dim}")
        return

    print(f"[*] Recreating collection '{collection_name}' with dim={dim}")
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dim, distance=distance),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Index corpus paragraphs into Qdrant using Ollama embeddings.")
    parser.add_argument(
        "--text-dir",
        type=Path,
        default=Path("../corpus/text"),
        help="Root directory containing extracted .txt files.",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="lectio_corpus",
        help="Qdrant collection name.",
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        help="Base URL for the Ollama server.",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default=os.environ.get("OLLAMA_MODEL", "nomic-embed-text"),
        help="Ollama embedding model name (must be pulled on the server).",
    )
    parser.add_argument(
        "--qdrant-url",
        type=str,
        default=os.environ.get("QDRANT_URL", "http://localhost:6333"),
        help="Base URL for the Qdrant service.",
    )
    parser.add_argument(
        "--qdrant-api-key",
        type=str,
        default=os.environ.get("QDRANT_API_KEY", ""),
        help="Qdrant API key, if authentication is enabled.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Number of points per Qdrant upsert batch.",
    )
    args = parser.parse_args()

    if not args.text_dir.exists():
        raise SystemExit(f"Text directory not found: {args.text_dir}")

    # Count paragraphs for progress reporting.
    total_paragraphs = sum(1 for _ in iter_paragraphs(args.text_dir))
    if total_paragraphs == 0:
        print("[!] No paragraphs found in text directory.")
        return

    print(f"[*] Found {total_paragraphs} paragraphs to index.")

    # Qdrant client: can point to local or remote host.
    client = QdrantClient(
        url=args.qdrant_url,
        api_key=args.qdrant_api_key or None,
    )

    session = requests.Session()

    paragraphs = iter_paragraphs(args.text_dir)

    # Peek the first paragraph to determine embedding dimension and ensure collection.
    try:
        first_path, first_idx, first_text = next(paragraphs)
    except StopIteration:
        print("[!] No paragraphs found in text directory.")
        return

    print(f"[*] Getting embedding dimension from first paragraph in {first_path}")
    first_embedding = get_embedding(session, args.ollama_url, args.ollama_model, first_text)
    dim = len(first_embedding)
    print(f"[*] Embedding dimension: {dim}")

    # Create or check collection.
    try:
        ensure_collection(client, args.collection, dim)
    except Exception:
        # If collection does not exist yet, create it.
        print(f"[*] Creating collection '{args.collection}' with dim={dim}")
        client.recreate_collection(
            collection_name=args.collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    # Helper to stream paragraphs including the first one we already embedded.
    def all_paragraphs():
        yield first_path, first_idx, first_text, first_embedding
        for path, idx, para in paragraphs:
            yield path, idx, para, None

    point_id_counter = itertools.count()
    buffer: List[PointStruct] = []

    for path, idx, para, maybe_emb in tqdm(
        all_paragraphs(),
        total=total_paragraphs,
        desc="Indexing paragraphs",
    ):
        if maybe_emb is None:
            emb = get_embedding(session, args.ollama_url, args.ollama_model, para)
        else:
            emb = maybe_emb

        pid = next(point_id_counter)
        payload = {
            "file": str(path),
            "paragraph_index": idx,
            "text": para,
        }
        buffer.append(PointStruct(id=pid, vector=emb, payload=payload))

        if len(buffer) >= args.batch_size:
            client.upsert(collection_name=args.collection, points=buffer)
            print(f"[*] Upserted {len(buffer)} points (last file: {path})")
            buffer.clear()

    if buffer:
        client.upsert(collection_name=args.collection, points=buffer)
        print(f"[*] Upserted final {len(buffer)} points.")

    print("[*] Indexing complete.")


if __name__ == "__main__":
    main()
