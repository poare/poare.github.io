"""Render the first page of each note PDF to a PNG thumbnail.

The Notes listings show a card grid; without thumbnails the cards are just
filenames. Existing thumbnails are skipped, so this is cheap to re-run after
adding a single PDF.

Usage:  python scripts/make_thumbs.py [--force]
"""

import sys
from pathlib import Path

# PyMuPDF ships two module names for itself: the modern `pymupdf` and the
# legacy `fitz`. Prefer `pymupdf` -- an UNRELATED package squats the name
# `fitz` on PyPI, so `pip install fitz` succeeds and then fails at import
# with a Starlette error about a missing 'static/' directory, which points
# nowhere near PDFs. The hasattr check catches the case where that squatter
# is installed and importable.
_PYMUPDF_HELP = (
    "PyMuPDF is required but was not found.\n"
    "\n"
    "    pip install pymupdf\n"
    "\n"
    "Do NOT run `pip install fitz`. PyMuPDF's legacy module is named fitz,\n"
    "but the name fitz on PyPI belongs to an unrelated package; installing\n"
    "it shadows PyMuPDF and fails with a confusing error about 'static/'."
)

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24.3
except ImportError:
    try:
        import fitz  # older PyMuPDF, which provides only this name
    except Exception as exc:  # the squatter raises RuntimeError, not ImportError
        raise SystemExit(_PYMUPDF_HELP) from exc

if not hasattr(fitz, "Matrix"):
    raise SystemExit(_PYMUPDF_HELP)

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = REPO_ROOT / "notes" / "pdf"
THUMB_DIR = REPO_ROOT / "notes" / "thumbs"

# 2x scale gives a sharp image on high-DPI screens without bloating the repo.
ZOOM = 2.0


class EmptyPdfError(ValueError):
    """A PDF with zero pages — there is no page 1 to render."""


def render_thumbnail(pdf_path, force=False):
    """Render page 1 of `pdf_path` to THUMB_DIR/<stem>.png.

    Returns the written Path, or None if the thumbnail already existed and
    `force` is False. Raises EmptyPdfError for a zero-page PDF and lets
    PyMuPDF's own exceptions propagate for unreadable ones — callers decide
    whether one bad file should stop them. main() warns and continues;
    sync_notes.py does the same.
    """
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    target = THUMB_DIR / f"{pdf_path.stem}.png"
    if target.exists() and not force:
        return None

    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            raise EmptyPdfError(f"{pdf_path.name} has no pages")
        page = doc.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
        pixmap.save(target)

    return target


def main():
    force = "--force" in sys.argv

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {PDF_DIR}")
        return

    failed = []

    for pdf_path in pdfs:
        # A single encrypted/corrupt PDF must not abort the whole batch —
        # this runs over dozens of real files, and pdfs is sorted, so an
        # uncaught exception here would silently skip every file that
        # sorts after the bad one.
        try:
            target = render_thumbnail(pdf_path, force=force)
        except EmptyPdfError as exc:
            print(f"WARN   {exc}, skipping")
            continue
        except Exception as exc:
            print(f"ERROR  {pdf_path.name}: {type(exc).__name__}: {exc}")
            failed.append(pdf_path.name)
            continue

        if target is None:
            print(f"skip   {pdf_path.stem}.png")
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
