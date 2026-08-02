"""Sync approved notes from the working notes tree into the site.

notes/notes.yml is the record of which notes are published and where their
sources live. For each entry this copies the PDF in, renders its thumbnail,
and — only if one does not exist yet — scaffolds a stub page.

An existing stub is NEVER overwritten. It holds hand-written prose, and a
config-driven overwrite is how a typo'd slug silently destroys it. Taking a
note off the site is a manual `git rm`; see the README.

Usage:  python scripts/sync_notes.py [--force-thumbs]
Env:    NOTES_ROOT   root of the working notes tree
                     (default: ~/Dropbox (Personal)/notes)
"""

import os
import re
import shutil
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# Running this as `python scripts/sync_notes.py` puts scripts/ on sys.path,
# not the repo root, so `from scripts.make_thumbs import ...` would fail —
# even though it resolves fine under pytest, which imports this as
# scripts.sync_notes. Inserting the repo root makes both entry points work.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.make_thumbs import EmptyPdfError, render_thumbnail  # noqa: E402

MANIFEST = REPO_ROOT / "notes" / "notes.yml"
PDF_DIR = REPO_ROOT / "notes" / "pdf"

DEFAULT_NOTES_ROOT = "~/Dropbox (Personal)/notes"

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

REQUIRED_KEYS = {"slug", "source", "topic"}

STUB_TEMPLATE = """---
title: "TITLE"
description: "DESCRIPTION"
categories: [{topic}]
image: ../thumbs/{slug}.png
---

{{{{< pdf-note >}}}}
"""


class ManifestError(Exception):
    """notes.yml is malformed. Raised with the offending entry named."""


def notes_root():
    """Root of the working notes tree.

    Read from NOTES_ROOT so the committed manifest holds only relative
    paths: nothing machine-specific lands in this public repo, and a second
    machine with a different layout needs only a different env var.
    """
    return Path(os.environ.get("NOTES_ROOT", DEFAULT_NOTES_ROOT)).expanduser()


def load_manifest(path):
    """Parse and validate notes.yml, returning a list of entry dicts.

    Validation is strict — an unknown key is an error rather than being
    ignored — because the likeliest cause is a misremembered schema, and
    silently dropping it would publish a note with the wrong metadata.
    """
    if not path.is_file():
        raise ManifestError(f"{path} does not exist")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ManifestError(f"{path} must contain a YAML list of entries")

    entries = []
    seen = set()
    for index, entry in enumerate(raw):
        where = f"entry {index + 1}"
        if not isinstance(entry, dict):
            raise ManifestError(f"{where}: expected a mapping, got {type(entry).__name__}")

        keys = set(entry)
        missing = REQUIRED_KEYS - keys
        if missing:
            raise ManifestError(f"{where}: missing required key(s): {', '.join(sorted(missing))}")
        unknown = keys - REQUIRED_KEYS
        if unknown:
            raise ManifestError(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")

        slug = entry["slug"]
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            raise ManifestError(
                f"{where}: slug {slug!r} is not kebab-case "
                "(lowercase letters, digits and single hyphens)"
            )
        if slug in seen:
            raise ManifestError(f"{where}: duplicate slug {slug!r}")
        seen.add(slug)

        entries.append(entry)

    return entries


def scaffold_stub(stub_path, slug, topic):
    """Write a placeholder stub if none exists. Returns True if it wrote one.

    Never overwrites: an existing stub holds hand-written prose.
    """
    if stub_path.exists():
        return False
    stub_path.parent.mkdir(parents=True, exist_ok=True)
    stub_path.write_text(STUB_TEMPLATE.format(slug=slug, topic=topic), encoding="utf-8")
    return True


def sync_entry(entry, root, force_thumbs=False):
    """Copy one note's PDF, render its thumbnail, scaffold its stub.

    Returns a list of human-readable lines describing what changed.
    """
    slug, topic = entry["slug"], entry["topic"]
    source = root / entry["source"]
    if not source.is_file():
        raise FileNotFoundError(f"source PDF not found: {source}")

    lines = []

    # The PDF is a build input, never hand-edited, so overwriting it is how
    # a recompiled note gets picked up.
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    target_pdf = PDF_DIR / f"{slug}.pdf"
    shutil.copy2(source, target_pdf)
    lines.append(f"pdf    {target_pdf.name}")

    thumb = render_thumbnail(target_pdf, force=force_thumbs)
    lines.append(f"thumb  {slug}.png" if thumb else f"skip   {slug}.png (exists)")

    stub_path = REPO_ROOT / "notes" / topic / f"{slug}.md"
    if scaffold_stub(stub_path, slug, topic):
        lines.append(f"stub   {stub_path.relative_to(REPO_ROOT)}  <- fill in TITLE and DESCRIPTION")
    else:
        lines.append(f"keep   {stub_path.relative_to(REPO_ROOT)} (already written)")

    return lines


def main():
    force_thumbs = "--force-thumbs" in sys.argv
    root = notes_root()

    try:
        entries = load_manifest(MANIFEST)
    except ManifestError as exc:
        print(f"ERROR  {exc}")
        sys.exit(1)

    if not entries:
        print(f"No notes listed in {MANIFEST}")
        return

    print(f"NOTES_ROOT = {root}")

    failed = []
    for entry in entries:
        # One unreadable source must not stop the rest: this runs over the
        # whole manifest, and a mid-list abort would leave the site in a
        # half-synced state that no test distinguishes from a full one.
        try:
            for line in sync_entry(entry, root, force_thumbs=force_thumbs):
                print(f"  {line}")
        except (OSError, EmptyPdfError) as exc:
            print(f"ERROR  {entry['slug']}: {type(exc).__name__}: {exc}")
            failed.append(entry["slug"])

    if failed:
        print(f"\n{len(failed)} of {len(entries)} note(s) failed:")
        for slug in failed:
            print(f"  - {slug}")
        sys.exit(1)


if __name__ == "__main__":
    main()
