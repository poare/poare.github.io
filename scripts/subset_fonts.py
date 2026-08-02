"""Subset the CMU Unicode fonts to WOFF2 for web delivery.

The full TTFs are ~600 KB each because they carry the entire Unicode range.
The site needs Latin, Greek (for kappa, lambda and friends in prose), common
punctuation and a handful of maths operators. Subsetting to those ranges takes
each face to roughly 100 KB.

Source fonts are read from the system font directory; they are NOT committed.
Run this once per machine after installing the CMU fonts.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "assets" / "fonts"

# macOS and Ubuntu keep user fonts in different places.
SOURCE_DIRS = [
    Path.home() / "Library" / "Fonts",     # macOS
    Path.home() / ".local" / "share" / "fonts",  # Ubuntu
    Path.home() / ".fonts",                 # older Ubuntu
    Path("/usr/share/fonts/truetype/cmu"),  # Ubuntu package
]

FACES = ["cmunrm", "cmunbx", "cmunti", "cmunbi", "cmunss", "cmuntt"]

# Latin, Latin-1, Latin Extended-A, Greek, general punctuation,
# super/subscripts, currency, letterlike symbols, arrows, maths operators,
# geometric shapes.
UNICODES = ",".join([
    "U+0020-007E",
    "U+00A0-00FF",
    "U+0100-017F",
    "U+0370-03FF",
    "U+2000-206F",
    "U+2070-209F",
    "U+20A0-20BF",
    "U+2100-214F",
    "U+2190-21FF",
    "U+2200-22FF",
    "U+25A0-25FF",
])


def find_source(face):
    for directory in SOURCE_DIRS:
        candidate = directory / f"{face}.ttf"
        if candidate.is_file():
            return candidate
    return None


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    missing = []
    failed = []
    for face in FACES:
        source = find_source(face)
        if source is None:
            missing.append(face)
            continue
        target = OUT_DIR / f"{face}.woff2"

        # A single bad face (e.g. a corrupt TTF, or one fontTools chokes on
        # for some unicode range it doesn't like) must not abort the whole
        # run -- this regenerates all six committed WOFF2 files in one go,
        # so an uncaught exception here would silently leave every face
        # after the bad one un-subsetted.
        try:
            subprocess.run(
                [
                    sys.executable, "-m", "fontTools.subset", str(source),
                    f"--output-file={target}",
                    "--flavor=woff2",
                    "--layout-features=*",
                    f"--unicodes={UNICODES}",
                ],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            print(f"ERROR  {face}: {type(exc).__name__}: {exc}")
            failed.append(face)
            continue

        kb = target.stat().st_size / 1024
        print(f"{face}.woff2  {kb:6.1f} KB")

    if missing:
        print(
            "\nERROR: could not find these faces in any known font directory:\n  "
            + "\n  ".join(missing)
            + "\nInstall the CMU Unicode fonts, then re-run.",
            file=sys.stderr,
        )

    if failed:
        print(f"\n{len(failed)} of {len(FACES)} face(s) failed to subset:")
        for face in failed:
            print(f"  - {face}")

    if missing or failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
