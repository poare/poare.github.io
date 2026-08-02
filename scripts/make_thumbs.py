"""Render the first page of each note PDF to a PNG thumbnail.

The Notes listings show a card grid; without thumbnails the cards are just
filenames. Existing thumbnails are skipped, so this is cheap to re-run after
adding a single PDF.

Usage:  python scripts/make_thumbs.py [--force]
"""

import sys
from pathlib import Path

import fitz  # PyMuPDF

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = REPO_ROOT / "notes" / "pdf"
THUMB_DIR = REPO_ROOT / "notes" / "thumbs"

# 2x scale gives a sharp image on high-DPI screens without bloating the repo.
ZOOM = 2.0


def main():
    force = "--force" in sys.argv
    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {PDF_DIR}")
        return

    for pdf_path in pdfs:
        target = THUMB_DIR / f"{pdf_path.stem}.png"
        if target.exists() and not force:
            print(f"skip   {target.name}")
            continue

        with fitz.open(pdf_path) as doc:
            if doc.page_count == 0:
                print(f"WARN   {pdf_path.name} has no pages, skipping")
                continue
            page = doc.load_page(0)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
            pixmap.save(target)

        kb = target.stat().st_size / 1024
        print(f"wrote  {target.name}  ({kb:.0f} KB)")


if __name__ == "__main__":
    main()
