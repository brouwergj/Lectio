#!/usr/bin/env python
import argparse
import subprocess
from pathlib import Path

import fitz  # pymupdf
from ebooklib import epub
from bs4 import BeautifulSoup


def extract_pdf(path: Path) -> str:
    doc = fitz.open(path)
    chunks = []
    for page in doc:
        # "text" gives a layout-ish text; "blocks" or "dict" are alternatives
        chunks.append(page.get_text("text"))
    return "\n\n".join(chunks)


def extract_epub(path: Path) -> str:
    book = epub.read_epub(str(path))
    chunks = []
    for item in book.get_items():
        if item.get_type() == epub.EpubHtml:
            html = item.get_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            if text:
                chunks.append(text)
    return "\n\n".join(chunks)


def convert_mobi_to_epub(mobi_path: Path, tmp_dir: Path) -> Path:
    """
    Use Calibre's ebook-convert to turn MOBI into EPUB.
    Requires `ebook-convert` to be installed and on PATH.
    """
    epub_path = tmp_dir / (mobi_path.stem + ".epub")
    epub_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["ebook-convert", str(mobi_path), str(epub_path)]
    subprocess.run(cmd, check=True)
    return epub_path


def extract_mobi(path: Path, tmp_dir: Path) -> str:
    """
    Simplest: MOBI -> EPUB -> text.
    """
    epub_path = convert_mobi_to_epub(path, tmp_dir)
    return extract_epub(epub_path)


def main():
    parser = argparse.ArgumentParser(description="Extract text from PDF/EPUB/MOBI into .txt files.")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("../corpus/source"),
        help="Directory containing original documents."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("../corpus/text"),
        help="Directory to write extracted .txt files."
    )
    parser.add_argument(
        "--tmp-dir",
        type=Path,
        default=Path("../corpus/tmp"),
        help="Temporary directory for conversions (e.g. MOBI->EPUB)."
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.tmp_dir.mkdir(parents=True, exist_ok=True)

    supported_exts = {".pdf", ".epub", ".mobi"}

    for path in args.raw_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in supported_exts:
            continue

        rel = path.relative_to(args.raw_dir)
        out_path = args.out_dir / rel.with_suffix(".txt")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[*] Extracting {path} -> {out_path}")

        try:
            if path.suffix.lower() == ".pdf":
                text = extract_pdf(path)
            elif path.suffix.lower() == ".epub":
                text = extract_epub(path)
            elif path.suffix.lower() == ".mobi":
                text = extract_mobi(path, args.tmp_dir)
            else:
                continue

            # Basic cleanup
            text = text.replace("\r\n", "\n").replace("\r", "\n")

            out_path.write_text(text, encoding="utf-8")
        except Exception as e:
            print(f"[!] Failed on {path}: {e}")


if __name__ == "__main__":
    main()
