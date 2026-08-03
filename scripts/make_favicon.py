"""Generate the site favicon from the vector source artwork.

`assets/lqcd_icon.pdf` is the master: a square, pure-vector drawing with no
embedded raster images. Two outputs come from it:

  assets/favicon.svg  the primary icon. Vector, so it stays crisp at any
                      size and on hi-DPI screens.
  assets/favicon.png  a fallback for browsers that do not take SVG favicons
                      (Safari before 16.4) and for bookmark tiles.

Both outputs are committed, so CI needs no Python and a fresh checkout needs
nothing run. Only re-run this if the source artwork changes.

Usage:  python scripts/make_favicon.py
"""

import sys
from pathlib import Path

# Prefer `pymupdf` over its legacy `fitz` alias: an unrelated PyPI package
# squats the name fitz. See the longer note in scripts/make_thumbs.py.
_PYMUPDF_HELP = (
    "PyMuPDF is required but was not found.\n"
    "\n"
    "    pip install pymupdf\n"
    "\n"
    "Do NOT run `pip install fitz` — that is a different package entirely."
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
SOURCE = REPO_ROOT / "assets" / "lqcd_icon.pdf"
SVG_OUT = REPO_ROOT / "assets" / "favicon.svg"
PNG_OUT = REPO_ROOT / "assets" / "favicon.png"

# 48px is the largest size browsers routinely ask a PNG favicon for. The tab
# itself renders at 16px; going much above 48 only grows the file.
PNG_SIZE = 48


def main():
    if not SOURCE.is_file():
        print(f"ERROR  source artwork not found: {SOURCE}")
        sys.exit(1)

    with fitz.open(SOURCE) as doc:
        if doc.page_count == 0:
            print(f"ERROR  {SOURCE.name} has no pages")
            sys.exit(1)
        page = doc.load_page(0)
        rect = page.rect

        # A non-square source would be letterboxed or stretched by the
        # browser, differently in each context it appears. Better to fail
        # loudly here than to ship an icon that is subtly wrong everywhere.
        if abs(rect.width - rect.height) > 0.5:
            print(
                f"ERROR  {SOURCE.name} is {rect.width:.1f}x{rect.height:.1f}pt, "
                "not square. Favicons must be square."
            )
            sys.exit(1)

        SVG_OUT.write_text(page.get_svg_image(), encoding="utf-8")

        zoom = PNG_SIZE / rect.width
        # alpha=True keeps the background transparent so the icon sits on the
        # browser's own tab colour rather than a white square.
        page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True).save(PNG_OUT)

    for out in (SVG_OUT, PNG_OUT):
        print(f"wrote  {out.relative_to(REPO_ROOT)}  ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
