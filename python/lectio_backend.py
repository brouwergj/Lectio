#!/usr/bin/env python
from pathlib import Path
import os
from typing import List

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.models import ScoredPoint


BASE_DIR = Path(__file__).resolve().parent.parent
ADDIN_DIR = BASE_DIR / "word-addin"


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://192.168.178.237:11434")
OLLAMA_EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://192.168.178.237:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY") or None
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "lectio_corpus")


app = FastAPI(title="Lectio Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if ADDIN_DIR.exists():
    app.mount("/addin", StaticFiles(directory=str(ADDIN_DIR), html=True), name="addin")


client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
session = requests.Session()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    score: float
    file: str
    paragraph_index: int
    text: str


class SearchResponse(BaseModel):
    results: List[SearchResult]


def get_embedding(text: str) -> List[float]:
    url = OLLAMA_URL.rstrip("/") + "/api/embeddings"
    resp = session.post(url, json={"model": OLLAMA_EMBED_MODEL, "prompt": text})
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}") from exc
    data = resp.json()
    return data["embedding"]


def point_to_result(point: ScoredPoint) -> SearchResult:
    payload = point.payload or {}
    return SearchResult(
        score=float(point.score or 0.0),
        file=str(payload.get("file", "")),
        paragraph_index=int(payload.get("paragraph_index", 0)),
        text=str(payload.get("text", "")),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query text is empty.")

    try:
        embedding = get_embedding(query)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to get embedding: {exc}") from exc

    try:
        points = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=embedding,
            limit=req.top_k,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Qdrant search failed: {exc}") from exc

    results = [point_to_result(p) for p in points]
    return SearchResponse(results=results)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "lectio_backend:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=True,
    )
