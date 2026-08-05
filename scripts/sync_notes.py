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

# `order` is optional and exists for numbered series: a listing sorted by
# title puts "Recitation 10" between 1 and 2, because title sort is
# alphabetical. Entries carrying it get it written into the stub's front
# matter, and the topic's listing in notes/index.md sorts on it instead.
OPTIONAL_KEYS = {"order"}

STUB_TEMPLATE = """---
title: "TITLE"
description: "DESCRIPTION"
categories: [{topic}]
image: ../thumbs/{slug}.png
{order_line}---

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
        unknown = keys - REQUIRED_KEYS - OPTIONAL_KEYS
        if unknown:
            raise ManifestError(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")

        slug = entry["slug"]
        if not isinstance(slug, str) or not SLUG_RE.match(slug):
            raise ManifestError(
                f"{where}: slug {slug!r} is not kebab-case "
                "(lowercase letters, digits and single hyphens)"
            )
        order = entry.get("order")
        if order is not None and not isinstance(order, int):
            raise ManifestError(
                f"{where}: order {order!r} is not a whole number. It is used "
                "to sort a topic's listing numerically, so a string would sort "
                "alphabetically and defeat the point."
            )

        if slug in seen:
            raise ManifestError(f"{where}: duplicate slug {slug!r}")
        seen.add(slug)

        # An absolute source silently defeats NOTES_ROOT: Path(root) / "/abs"
        # discards `root` entirely and evaluates to the absolute path as-is,
        # so this would work on the author's machine, pass every other
        # check, and commit a machine-specific path straight into the
        # public manifest -- exactly what NOTES_ROOT exists to prevent, and
        # unfixable after the fact once it's in git history.
        source = entry["source"]
        if isinstance(source, str) and Path(source).is_absolute():
            raise ManifestError(
                f"{where}: source {source!r} must be relative to NOTES_ROOT, "
                "not an absolute path"
            )

        # topic is interpolated straight into a filesystem path
        # (REPO_ROOT / "notes" / topic / f"{slug}.md") and into a Quarto
        # category verbatim. slug gets the kebab-case check above; topic
        # must get the same one, or a value like "../../foo" writes a stub
        # outside the notes tree entirely.
        topic = entry["topic"]
        if not isinstance(topic, str) or not SLUG_RE.match(topic):
            raise ManifestError(
                f"{where}: topic {topic!r} is not kebab-case "
                "(lowercase letters, digits and single hyphens)"
            )

        entries.append(entry)

    return entries


def scaffold_stub(stub_path, slug, topic, order=None):
    """Write a placeholder stub if none exists. Returns True if it wrote one.

    Never overwrites: an existing stub holds hand-written prose.

    The existence check and the write must be one atomic operation, not
    two: `stub_path.exists()` returns False for a DANGLING SYMLINK (a
    symlink whose target does not exist), so a check-then-write would let
    `write_text` follow that link and write the stub outside the notes
    tree entirely -- reproduced by hand: a dangling symlink at the stub
    path caused the placeholder to be silently written to the link's
    target instead. The same two-step check also has a TOCTOU race between
    two concurrent runs, both of which could pass the `exists()` guard
    before either writes. Opening with the "x" (exclusive-create) mode
    closes both gaps: the OS creates and opens the file in one step and
    fails with FileExistsError if the path is already occupied by
    anything -- a real file, or a symlink, dangling or not -- since "x"
    refuses to follow a symlink whose target is absent rather than
    creating through it.
    """
    stub_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(stub_path, "x", encoding="utf-8") as handle:
            handle.write(STUB_TEMPLATE.format(
                slug=slug,
                topic=topic,
                order_line="" if order is None else f"order: {order}\n",
            ))
    except FileExistsError:
        return False
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

    # Slugs are only deduped WITHIN the manifest (see load_manifest). If an
    # entry's topic changes (or is typo'd) after its stub was already
    # scaffolded under the old topic, nothing above this point notices --
    # this would scaffold a second stub under the new topic and leave the
    # old one live, publishing the same PDF twice with no test failing.
    # Catch it here by checking the filesystem itself for any existing
    # `<slug>.md` under a DIFFERENT topic directory before writing anything.
    stub_path = REPO_ROOT / "notes" / topic / f"{slug}.md"
    for existing in (REPO_ROOT / "notes").glob(f"*/{slug}.md"):
        if existing != stub_path:
            raise FileExistsError(
                f"{slug!r} already has a stub at "
                f"{existing.relative_to(REPO_ROOT)}, but notes.yml now "
                f"declares topic {topic!r} (expecting "
                f"{stub_path.relative_to(REPO_ROOT)}). A slug must not be "
                "published under two topics at once -- `git rm "
                f"{existing.relative_to(REPO_ROOT)}` if the topic change is "
                "intentional, then re-run the sync."
            )

    # The PDF is a build input, never hand-edited, so overwriting it is how
    # a recompiled note gets picked up.
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    target_pdf = PDF_DIR / f"{slug}.pdf"
    shutil.copy2(source, target_pdf)
    lines.append(f"pdf    {target_pdf.name}")

    thumb = render_thumbnail(target_pdf, force=force_thumbs)
    lines.append(f"thumb  {slug}.png" if thumb else f"skip   {slug}.png (exists)")

    if scaffold_stub(stub_path, slug, topic, entry.get("order")):
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
