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

    failed = []

    for pdf_path in pdfs:
        target = THUMB_DIR / f"{pdf_path.stem}.png"
        if target.exists() and not force:
            print(f"skip   {target.name}")
            continue

        # A single encrypted/corrupt PDF must not abort the whole batch —
        # this runs over dozens of real files, and pdfs is sorted, so an
        # uncaught exception here would silently skip every file that
        # sorts after the bad one.
        try:
            with fitz.open(pdf_path) as doc:
                if doc.page_count == 0:
                    print(f"WARN   {pdf_path.name} has no pages, skipping")
                    continue
                page = doc.load_page(0)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
                pixmap.save(target)
        except Exception as exc:
            print(f"ERROR  {pdf_path.name}: {exc}")
            failed.append(pdf_path.name)
            continue

        kb = target.stat().st_size / 1024
        print(f"wrote  {target.name}  ({kb:.0f} KB)")

    if failed:
        print(f"\n{len(failed)} of {len(pdfs)} PDF(s) failed:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
