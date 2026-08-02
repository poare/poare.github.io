# Notes Shortcode and Manifest-Driven Ingest — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-copied notes stub workflow with a Lua shortcode that owns all shared presentation markup, plus a manifest recording which notes are approved for publication and a sync script that copies PDFs and scaffolds stubs without ever overwriting hand-written prose.

**Architecture:** Four pieces with one responsibility each. `notes/notes.yml` records whether a note is published and where its source lives. `scripts/sync_notes.py` puts bytes on disk (PDF copy, thumbnail, first-time stub scaffold) and never touches an existing stub. `_extensions/pdf-note/` is a Lua shortcode owning how every note page looks. The stub `.md` owns what a note says. Spec: [docs/specs/2026-08-02-notes-shortcode-design.md](../specs/2026-08-02-notes-shortcode-design.md).

**Tech Stack:** Quarto 1.10.18 (pinned in CI), Lua shortcode extension, Python 3 (PyMuPDF for thumbnails, PyYAML for the manifest), pytest.

## Global Constraints

- **CI runs no Python.** PDFs, thumbnails and stubs are all committed. `sync_notes.py` is a local authoring tool only. Do not add a Python step to `.github/workflows/publish.yml`.
- **Quarto is pinned to 1.10.18.** Do not upgrade it. If a shortcode API differs from what this plan assumes, adapt the plan, not the pin.
- **The repo is public.** Never commit a PDF not listed in `notes/notes.yml`. Never write a machine-specific absolute path into a tracked file.
- **Slugs are kebab-case**, matching `^[a-z0-9]+(-[a-z0-9]+)*$`. Source filenames are snake_case; the rename happens at ingest.
- **Colours live in `theme.scss` only.** Do not introduce a colour literal anywhere; `test_colours_are_variables_not_literals` enforces this.
- **Prose files are `.md`, never `.qmd`.** `test_tracked_qmd_files_execute_code` enforces this — a `.qmd` that executes no code fails the suite.
- **`sync_notes.py` must never overwrite an existing stub.** This is the property the whole design rests on.
- Run the full suite with `pytest tests/ -v` from the repo root. It renders the site once per session and takes ~10s.

---

### Task 1: The `pdf-note` shortcode extension

Establishes the shortcode and proves it against the page that already renders correctly. Existing tests must keep passing unchanged — that is the evidence the shortcode reproduces the old markup exactly.

**Files:**
- Create: `_extensions/pdf-note/_extension.yml`
- Create: `_extensions/pdf-note/pdf-note.lua`
- Modify: `notes/lattice-qcd/example-note.md` (body replaced with the shortcode)
- Modify: `tests/test_site.py` (add one test at the end of the notes section, after `test_all_notes_stub_pdf_links_resolve`)

**Interfaces:**
- Consumes: nothing.
- Produces: the shortcode `{{< pdf-note >}}`, callable from any file under `notes/<topic>/`. If the slug cannot be derived from the input filename it accepts one positional argument: `{{< pdf-note some-slug >}}`. Emits, in order: a `<div class="accent-rule">`, the document's `description` metadata as a paragraph, a `Download PDF` link with classes `btn btn-primary` pointing at `../pdf/<slug>.pdf`, and an `<object>` viewer for the same path.

- [ ] **Step 1: Spike — determine whether a shortcode can read the input filename**

Create `_extensions/pdf-note/_extension.yml`:

```yaml
title: PDF note
author: Patrick Oare
version: 1.0.0
quarto-required: ">=1.4.0"
contributes:
  shortcodes:
    - pdf-note.lua
```

Create `_extensions/pdf-note/pdf-note.lua` with a temporary probe body:

```lua
return {
  ["pdf-note"] = function(args, kwargs, meta)
    local input = tostring(quarto.doc.input_file)
    return pandoc.Para(pandoc.Str("PROBE input_file=" .. input))
  end
}
```

Replace the body of `notes/lattice-qcd/example-note.md` (everything after the closing `---` of the front matter) with:

```markdown
{{< pdf-note >}}
```

- [ ] **Step 2: Run the probe**

Run: `quarto render notes/lattice-qcd/example-note.md --to html && grep -o 'PROBE input_file=[^<]*' _site/notes/lattice-qcd/example-note.html`

Expected: a line like `PROBE input_file=/Users/patrickoare/website/notes/lattice-qcd/example-note.md`.

**If instead you get an empty result, a Lua error, or the literal text `nil`:** `quarto.doc.input_file` is unavailable in shortcodes at this Quarto version. Take the documented fallback — the shortcode requires an explicit slug argument, `{{< pdf-note example-note >}}` — and in every later step of this plan replace bare `{{< pdf-note >}}` with the slug-argument form. Record which branch you took in the commit message. Everything else in the plan is unaffected.

- [ ] **Step 3: Write the real shortcode**

Replace the whole of `_extensions/pdf-note/pdf-note.lua`:

```lua
-- Shared presentation markup for every notes stub page.
--
-- Each note page is otherwise identical: an accent rule, the front-matter
-- description repeated as body prose, a download button, and an inline PDF
-- viewer. Hand-copying that into 20-30 files meant the slug was typed four
-- times per note and changing the presentation was a 30-file edit. This
-- shortcode owns all of it; a stub's body is one line.
--
-- Usage:  {{< pdf-note >}}              slug derived from the filename
--         {{< pdf-note explicit-slug >}} slug given explicitly

-- notes/<topic>/<slug>.md -> "<slug>". Handles both path separators so the
-- extension is not silently macOS/Linux-only.
local function slug_from_input_file()
  local input = quarto.doc.input_file
  if input == nil then
    return nil
  end
  return tostring(input):match("([^/\\]+)%.[^.]+$")
end

return {
  ["pdf-note"] = function(args, kwargs, meta)
    local slug
    if #args > 0 then
      slug = pandoc.utils.stringify(args[1])
    else
      slug = slug_from_input_file()
    end

    -- Failing loudly matters more than usual here: a nil slug would
    -- otherwise produce "../pdf/nil.pdf" on a page that still looks
    -- plausible, and the broken download would only be found by clicking.
    if slug == nil or slug == "" then
      error(
        "pdf-note: could not determine the note slug from the input " ..
        "filename. Pass it explicitly: {{< pdf-note my-note-slug >}}"
      )
    end

    local pdf_path = "../pdf/" .. slug .. ".pdf"

    -- Reuse the description's inlines rather than flattening to a string,
    -- so markup in the front matter (maths, emphasis) survives.
    local description_inlines = pandoc.Inlines({})
    if meta ~= nil and meta.description ~= nil then
      if type(meta.description) == "table" then
        description_inlines = pandoc.Inlines(meta.description)
      else
        description_inlines = pandoc.Inlines(
          {pandoc.Str(pandoc.utils.stringify(meta.description))}
        )
      end
    end

    local accent_rule = pandoc.Div(
      pandoc.Blocks({}),
      pandoc.Attr("", {"accent-rule"}, {})
    )

    local download_button = pandoc.Para(pandoc.Inlines({
      pandoc.Link(
        pandoc.Inlines({pandoc.Str("Download"), pandoc.Space(), pandoc.Str("PDF")}),
        pdf_path,
        "",
        pandoc.Attr("", {"btn", "btn-primary"}, {})
      )
    }))

    local viewer = pandoc.RawBlock("html", table.concat({
      '<object data="' .. pdf_path .. '" type="application/pdf" ',
      'width="100%" height="800">\n',
      '  <p>Your browser cannot display PDFs inline.\n',
      '     <a href="' .. pdf_path .. '">Download it instead</a>.</p>\n',
      '</object>'
    }))

    return pandoc.Blocks({
      accent_rule,
      pandoc.Para(description_inlines),
      download_button,
      viewer,
    })
  end
}
```

- [ ] **Step 4: Confirm `notes/lattice-qcd/example-note.md` is the one-line form**

The whole file should now read:

```markdown
---
title: "An example note"
description: "Why the condition number of the Dirac operator is governed by its smallest eigenvalues, and what deflation does about it."
categories: [lattice-qcd, solvers]
image: ../thumbs/example-note.png
---

{{< pdf-note >}}
```

- [ ] **Step 5: Run the existing suite — it must pass unchanged**

Run: `pytest tests/ -v`

Expected: 34 passed. In particular `test_note_stub_is_generated`, `test_note_stub_has_indexable_description`, `test_note_stub_meta_description_tag_is_populated` and `test_all_notes_stub_pdf_links_resolve` all still pass. Those tests were written against the hand-copied markup, so their passing is the proof that the shortcode reproduces it.

If `test_note_stub_has_indexable_description` fails, the description is not reaching the body — check the `meta.description` branch in the Lua.

- [ ] **Step 6: Write the failing regression test**

Add to the end of the notes section of `tests/test_site.py`:

```python
def test_no_stub_hand_copies_the_viewer_markup():
    """Every notes stub must get its viewer from the pdf-note shortcode.

    The shortcode exists so that changing how PDFs are presented is a
    one-file edit rather than a 20-30 file edit. That property only holds
    while no stub has quietly reverted to pasting the markup in directly —
    which is exactly what someone does when they copy an older note as a
    starting point. Checks source .md files, not rendered HTML: the
    rendered page is *supposed* to contain <object>.
    """
    notes_dir = REPO_ROOT / "notes"
    stubs = sorted(
        p for p in notes_dir.glob("*/*.md")
        if not p.name.startswith("_")
    )
    assert stubs, "no notes stubs found under notes/<topic>/"
    for stub in stubs:
        text = stub.read_text(encoding="utf-8")
        assert "<object" not in text, (
            f"{stub.relative_to(REPO_ROOT)} hand-copies the <object> viewer "
            "instead of calling {{< pdf-note >}}"
        )
        assert "{{< pdf-note" in text, (
            f"{stub.relative_to(REPO_ROOT)} does not call the pdf-note "
            "shortcode"
        )
```

- [ ] **Step 7: Write the shortcode output test**

The existing `test_note_stub_is_generated` only checks that the strings `Download PDF` and `<object` appear *somewhere* on the page. It would still pass if the shortcode emitted the viewer but dropped the accent rule, or pointed every note at the same wrong PDF. Add, immediately after the test from Step 6:

```python
def test_note_page_renders_the_shortcode_output(site):
    """The shortcode must emit all of its parts, pointing at THIS note's PDF.

    The slug is derived, not typed, so the failure to guard against is a
    page that renders perfectly while referencing another note's PDF —
    which test_all_notes_stub_pdf_links_resolve would happily pass, since
    that file does exist. Deriving the expected slug from the page path is
    what makes this test check identity rather than mere existence.

    Body prose from the front-matter `description` is covered by
    test_note_stub_has_indexable_description just above.
    """
    html = read_html(site, NOTE)
    slug = Path(NOTE).stem

    assert extract_element(html, "accent-rule"), (
        "the shortcode did not emit the accent rule"
    )
    assert f'href="../pdf/{slug}.pdf"' in html, (
        f"no download button pointing at ../pdf/{slug}.pdf — the shortcode "
        "derived the wrong slug, or emitted no button"
    )
    assert f'data="../pdf/{slug}.pdf"' in html, (
        f"no <object> viewer pointing at ../pdf/{slug}.pdf"
    )
```

- [ ] **Step 8: Run both new tests**

Run: `pytest tests/test_site.py -k "hand_copies or shortcode_output" -v`

Expected: 2 passed (Step 4 already converted the only stub).

To prove they discriminate, do both mutations and undo each afterwards:
1. Paste `<object data="x">` into `notes/lattice-qcd/example-note.md` → `test_no_stub_hand_copies_the_viewer_markup` FAILS.
2. Change the stub's body to `{{< pdf-note some-other-slug >}}` → `test_note_page_renders_the_shortcode_output` FAILS.

- [ ] **Step 9: Run the full suite**

Run: `pytest tests/ -v`

Expected: 36 passed.

- [ ] **Step 10: Commit**

```bash
git add _extensions/pdf-note/_extension.yml _extensions/pdf-note/pdf-note.lua notes/lattice-qcd/example-note.md tests/test_site.py
git commit -m "feat: add pdf-note shortcode owning the shared stub markup"
```

---

### Task 2: Expose a reusable thumbnail function

`sync_notes.py` needs to render one thumbnail for one PDF. `make_thumbs.py` currently has only `main()`, which globs the whole directory. Extract the per-file logic so there is exactly one thumbnailing code path, rather than a second one that drifts.

**Files:**
- Modify: `scripts/make_thumbs.py`
- Modify: `tests/test_site.py` (add tests at the end of the file)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `scripts.make_thumbs.render_thumbnail(pdf_path: Path, force: bool = False) -> Path | None` — renders page 1 of `pdf_path` to `notes/thumbs/<stem>.png` and returns the written path, or `None` if the thumbnail already existed and `force` is False. Raises `EmptyPdfError` (a `ValueError` subclass) if the PDF has no pages; propagates PyMuPDF exceptions for unreadable files. Also produces `scripts.make_thumbs.THUMB_DIR` and `PDF_DIR` (unchanged).

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/test_site.py`:

```python
def test_render_thumbnail_writes_a_png(tmp_path, monkeypatch):
    """sync_notes.py renders one thumbnail at a time, so the per-file logic
    has to be callable on its own rather than only via a directory scan.
    """
    import fitz

    from scripts import make_thumbs

    thumb_dir = tmp_path / "thumbs"
    monkeypatch.setattr(make_thumbs, "THUMB_DIR", thumb_dir)

    pdf_path = tmp_path / "sample-note.pdf"
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.save(pdf_path)
    doc.close()

    written = make_thumbs.render_thumbnail(pdf_path)
    assert written == thumb_dir / "sample-note.png"
    assert written.is_file(), "render_thumbnail did not write the PNG"


def test_render_thumbnail_skips_an_existing_thumbnail(tmp_path, monkeypatch):
    """Re-running the sync over a manifest of 30 notes must not re-render
    every thumbnail each time.
    """
    import fitz

    from scripts import make_thumbs

    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    monkeypatch.setattr(make_thumbs, "THUMB_DIR", thumb_dir)

    pdf_path = tmp_path / "sample-note.pdf"
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.save(pdf_path)
    doc.close()

    existing = thumb_dir / "sample-note.png"
    existing.write_bytes(b"sentinel")

    assert make_thumbs.render_thumbnail(pdf_path) is None
    assert existing.read_bytes() == b"sentinel", "an existing thumbnail was overwritten"
    assert make_thumbs.render_thumbnail(pdf_path, force=True) is not None
    assert existing.read_bytes() != b"sentinel", "--force did not re-render"


def test_render_thumbnail_rejects_an_empty_pdf(tmp_path, monkeypatch):
    """A zero-page PDF is a real thing PyMuPDF will hand back. Rendering
    page 0 of it raises deep inside fitz; catching it here keeps the batch
    loop's warn-and-continue behaviour meaningful.
    """
    import fitz

    from scripts import make_thumbs

    monkeypatch.setattr(make_thumbs, "THUMB_DIR", tmp_path / "thumbs")

    pdf_path = tmp_path / "empty-note.pdf"
    doc = fitz.open()
    doc.save(pdf_path)
    doc.close()

    with pytest.raises(make_thumbs.EmptyPdfError):
        make_thumbs.render_thumbnail(pdf_path)
```

Add `import pytest` to the imports at the top of `tests/test_site.py` if it is not already there.

- [ ] **Step 2: Make `scripts/` importable**

Create the empty file `scripts/__init__.py` so `from scripts import make_thumbs` resolves:

```bash
touch scripts/__init__.py
```

Add a `pytest.ini`-equivalent so the repo root is on `sys.path`. Append to `tests/conftest.py`, just below the `REPO_ROOT` assignment:

```python
# Make the repo root importable so tests can `from scripts import ...`.
# scripts/ holds local authoring tools; they are not a package on the path
# by default, and pytest's rootdir insertion only covers tests/.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
```

and add `import sys` to that file's imports.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pytest tests/test_site.py -k render_thumbnail -v`

Expected: 3 failed with `AttributeError: module 'scripts.make_thumbs' has no attribute 'render_thumbnail'`.

- [ ] **Step 4: Refactor `make_thumbs.py`**

Replace everything from the `ZOOM` constant to the end of `main()` with:

```python
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
```

Note the deliberate preservation of behaviour: a zero-page PDF still warns and continues *without* counting as a failure, so the script's exit code means the same thing it did before.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_site.py -k render_thumbnail -v`

Expected: 3 passed.

- [ ] **Step 6: Verify the script itself still behaves**

Run: `python scripts/make_thumbs.py`

Expected: `skip   example-note.png` and exit 0. The refactor must not change what the CLI does.

- [ ] **Step 7: Run the full suite**

Run: `pytest tests/ -v`

Expected: 39 passed.

- [ ] **Step 8: Commit**

```bash
git add scripts/make_thumbs.py scripts/__init__.py tests/conftest.py tests/test_site.py
git commit -m "refactor: expose render_thumbnail so sync_notes can reuse it"
```

---

### Task 3: The manifest and `sync_notes.py`

**Files:**
- Create: `notes/notes.yml`
- Create: `scripts/sync_notes.py`
- Modify: `requirements.txt`
- Modify: `tests/test_site.py`

**Interfaces:**
- Consumes: `scripts.make_thumbs.render_thumbnail(pdf_path, force=False)` from Task 2.
- Produces:
  - `scripts.sync_notes.MANIFEST: Path` — `notes/notes.yml`.
  - `scripts.sync_notes.SLUG_RE: re.Pattern` — `^[a-z0-9]+(-[a-z0-9]+)*$`.
  - `scripts.sync_notes.notes_root() -> Path` — `NOTES_ROOT` env var, else `~/Dropbox (Personal)/notes`, expanded.
  - `scripts.sync_notes.load_manifest(path: Path) -> list[dict]` — parses and validates; raises `ManifestError` on a missing key, unknown key, bad slug, or duplicate slug.
  - `scripts.sync_notes.scaffold_stub(stub_path: Path, slug: str, topic: str) -> bool` — writes the stub only if absent; returns True if it wrote one, False if the file already existed.
  - `scripts.sync_notes.ManifestError(Exception)`.

- [ ] **Step 1: Add the YAML dependency**

Append to `requirements.txt`:

```
pyyaml
```

Install it: `pip install -r requirements.txt`

- [ ] **Step 2: Write the failing tests**

Add to the end of `tests/test_site.py`:

```python
def test_manifest_slugs_are_kebab_case():
    """A slug becomes a public URL. snake_case or capitals reaching it is
    both ugly and, for search engines, a single unreadable token — and it
    is not fixable later without breaking a published link.
    """
    from scripts import sync_notes

    entries = sync_notes.load_manifest(sync_notes.MANIFEST)
    assert entries, "notes.yml lists no notes"
    for entry in entries:
        assert sync_notes.SLUG_RE.match(entry["slug"]), (
            f"slug {entry['slug']!r} is not kebab-case"
        )


def test_every_manifest_entry_has_its_files():
    """Catches the 'added an entry, forgot to run the sync' failure, which
    otherwise surfaces as a 404 on the live site rather than a test failure.
    """
    from scripts import sync_notes

    for entry in sync_notes.load_manifest(sync_notes.MANIFEST):
        slug, topic = entry["slug"], entry["topic"]
        for expected in (
            REPO_ROOT / "notes" / "pdf" / f"{slug}.pdf",
            REPO_ROOT / "notes" / "thumbs" / f"{slug}.png",
            REPO_ROOT / "notes" / topic / f"{slug}.md",
        ):
            assert expected.is_file(), (
                f"{expected.relative_to(REPO_ROOT)} is missing — run "
                "python scripts/sync_notes.py"
            )


def test_manifest_rejects_a_bad_entry(tmp_path):
    """load_manifest is the only thing standing between a typo and a
    half-published note, so its validation is tested directly rather than
    trusted.
    """
    from scripts import sync_notes

    def write(text):
        path = tmp_path / "notes.yml"
        path.write_text(text, encoding="utf-8")
        return path

    with pytest.raises(sync_notes.ManifestError, match="missing"):
        write("- slug: a-note\n  topic: physics\n")  # no source

    with pytest.raises(sync_notes.ManifestError, match="kebab-case"):
        write("- slug: A_Note\n  source: x.pdf\n  topic: physics\n")

    with pytest.raises(sync_notes.ManifestError, match="unknown"):
        write("- slug: a-note\n  source: x.pdf\n  topic: physics\n  title: nope\n")

    with pytest.raises(sync_notes.ManifestError, match="duplicate"):
        write(
            "- slug: a-note\n  source: x.pdf\n  topic: physics\n"
            "- slug: a-note\n  source: y.pdf\n  topic: math\n"
        )


def test_sync_never_overwrites_an_existing_stub(tmp_path):
    """The property the whole design rests on. A stub holds hand-written
    prose — errata, 'supersedes the 2024 version', links to related notes.
    Re-running the sync after recompiling a PDF must refresh the binary and
    the thumbnail and leave every word of that prose alone.
    """
    from scripts import sync_notes

    stub = tmp_path / "lorentz-poincare-groups.md"

    assert sync_notes.scaffold_stub(stub, "lorentz-poincare-groups", "physics") is True
    scaffolded = stub.read_text(encoding="utf-8")
    assert "{{< pdf-note" in scaffolded
    assert "../thumbs/lorentz-poincare-groups.png" in scaffolded

    hand_written = scaffolded + "\n\nSupersedes the 2024 version.\n"
    stub.write_text(hand_written, encoding="utf-8")

    assert sync_notes.scaffold_stub(stub, "lorentz-poincare-groups", "physics") is False
    assert stub.read_text(encoding="utf-8") == hand_written, (
        "scaffold_stub overwrote an existing stub and destroyed hand-written prose"
    )


def test_notes_root_is_overridable(monkeypatch, tmp_path):
    """The Ubuntu machine's notes tree is not at the macOS default. The env
    var is the only thing that makes the committed manifest portable, so a
    regression here would break the second machine silently.
    """
    from scripts import sync_notes

    monkeypatch.setenv("NOTES_ROOT", str(tmp_path))
    assert sync_notes.notes_root() == tmp_path

    monkeypatch.delenv("NOTES_ROOT", raising=False)
    assert sync_notes.notes_root() == Path("~/Dropbox (Personal)/notes").expanduser()
```

- [ ] **Step 3: Run them to verify they fail**

Run: `pytest tests/test_site.py -k "manifest or sync_never or notes_root" -v`

Expected: 5 failed with `ModuleNotFoundError: No module named 'scripts.sync_notes'`.

- [ ] **Step 4: Write `scripts/sync_notes.py`**

```python
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
```

- [ ] **Step 5: Create the manifest with the existing note**

Create `notes/notes.yml`. The example note has no source in the working notes tree, so the manifest starts empty with an explanatory comment; Task 4 adds the first real entry.

```yaml
# Which notes are published, and where each one's source PDF lives.
#
# Being listed here is what makes a note public. `source` is relative to
# the NOTES_ROOT environment variable (default: ~/Dropbox (Personal)/notes)
# so that no machine-specific path is committed to this public repo.
#
# After editing, run: python scripts/sync_notes.py
#
# Removing an entry does NOT unpublish the note — see "Unpublishing a note"
# in the README.
[]
```

- [ ] **Step 6: Run the tests**

Run: `pytest tests/test_site.py -k "manifest or sync_never or notes_root" -v`

Expected: 4 passed, 1 failed — `test_manifest_slugs_are_kebab_case` fails on `assert entries, "notes.yml lists no notes"`, because the manifest is deliberately empty until Task 4. That is the correct state; Task 4 turns it green. Do not weaken the assertion to accommodate an empty manifest — an empty manifest on the finished site would mean nothing is published.

- [ ] **Step 7: Commit**

```bash
git add notes/notes.yml scripts/sync_notes.py requirements.txt tests/test_site.py
git commit -m "feat: add the notes manifest and sync_notes.py"
```

---

### Task 4: Ingest the first real note

**Files:**
- Modify: `notes/notes.yml`
- Create: `notes/physics/lorentz-poincare-groups.md` (scaffolded by the script, then filled in by hand)
- Create: `notes/pdf/lorentz-poincare-groups.pdf` (copied by the script)
- Create: `notes/thumbs/lorentz-poincare-groups.png` (rendered by the script)
- Modify: `notes/index.md`

**Interfaces:**
- Consumes: `sync_notes.main()` via the CLI, and the `{{< pdf-note >}}` shortcode from Task 1.
- Produces: the `physics` topic and a note page at `notes/physics/lorentz-poincare-groups.html`.

- [ ] **Step 1: Add the manifest entry**

Replace the `[]` at the end of `notes/notes.yml` with:

```yaml
- slug: lorentz-poincare-groups
  source: physics/lorentz_poincare_groups/lorentz_poincare_groups.pdf
  topic: physics
```

- [ ] **Step 2: Run the sync**

Run: `python scripts/sync_notes.py`

Expected output:

```
NOTES_ROOT = /Users/patrickoare/Dropbox (Personal)/notes
  pdf    lorentz-poincare-groups.pdf
  thumb  lorentz-poincare-groups.png
  stub   notes/physics/lorentz-poincare-groups.md  <- fill in TITLE and DESCRIPTION
```

Then confirm all three files exist:

Run: `ls -la notes/pdf/lorentz-poincare-groups.pdf notes/thumbs/lorentz-poincare-groups.png notes/physics/lorentz-poincare-groups.md`

- [ ] **Step 3: Fill in the stub**

Replace the scaffolded front matter in `notes/physics/lorentz-poincare-groups.md` so the whole file reads:

```markdown
---
title: "The Lorentz and Poincaré Groups"
description: "The Lorentz algebra and its finite-dimensional representations, Dirac and Majorana spinors, spinor index conventions, discrete symmetries, and the little-group classification of Poincaré representations."
categories: [physics, group-theory]
image: ../thumbs/lorentz-poincare-groups.png
---

{{< pdf-note >}}
```

- [ ] **Step 4: Add the topic listing**

In `notes/index.md`, add a second listing to the `listing:` block in the front matter, after the existing `lattice-qcd` entry:

```yaml
  - id: physics
    contents: physics
    type: grid
    sort: "title"
    fields: [image, title, description, categories]
    feed: false
```

and append to the end of the file:

```markdown
## Physics

:::{#physics}
:::
```

- [ ] **Step 5: Verify the sync is idempotent against real files**

Run: `python scripts/sync_notes.py`

Expected:

```
  pdf    lorentz-poincare-groups.pdf
  skip   lorentz-poincare-groups.png (exists)
  keep   notes/physics/lorentz-poincare-groups.md (already written)
```

Then confirm the hand-written front matter survived:

Run: `grep -c "Lorentz and Poincaré" notes/physics/lorentz-poincare-groups.md`

Expected: `1`. If this prints `0`, `scaffold_stub` overwrote the file — stop and fix Task 3 before going further.

- [ ] **Step 6: Run the full suite**

Run: `pytest tests/ -v`

Expected: 44 passed. `test_manifest_slugs_are_kebab_case` now passes because the manifest is no longer empty.

- [ ] **Step 7: Check the rendered page in a browser**

Run: `quarto preview` and open `notes/physics/lorentz-poincare-groups.html`.

Confirm by eye: the accent rule renders, the description appears as body prose, the Download PDF button is dark red (not Bootstrap blue), and the embedded viewer shows page 1 of the note. Confirm the Notes index shows a Physics section with a thumbnail card. Stop the preview when done.

- [ ] **Step 8: Commit**

```bash
git add notes/notes.yml notes/physics/lorentz-poincare-groups.md notes/pdf/lorentz-poincare-groups.pdf notes/thumbs/lorentz-poincare-groups.png notes/index.md
git commit -m "content: publish the Lorentz and Poincare groups note"
```

---

### Task 5: Retire the example note and the template

The example note and `_note-template.md` both exist only because there was no real note and no shortcode. Both are now placeholder content on a live public site.

Seven existing tests hard-code `example-note`, `lattice-qcd` or the string `condition number`. They must be repointed at the real note, not deleted — each still guards something real.

**Files:**
- Delete: `notes/lattice-qcd/example-note.md`, `notes/pdf/example-note.pdf`, `notes/thumbs/example-note.png`, `notes/_note-template.md`, and the now-empty `notes/lattice-qcd/` directory
- Modify: `notes/index.md`
- Modify: `tests/test_site.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: the note published in Task 4.
- Produces: no new interfaces.

- [ ] **Step 1: Repoint the hard-coded tests**

In `tests/test_site.py`, change the `NOTE` constant:

```python
NOTE = "notes/physics/lorentz-poincare-groups.html"
```

In `test_note_stub_has_indexable_description`, change the asserted substring and its message:

```python
    assert "little-group" in html.lower(), (
        "the description text search engines rely on is missing"
    )
```

In `test_note_stub_meta_description_tag_is_populated`, change the asserted substring:

```python
    assert "little-group" in match.group(1).lower(), (
        "meta description tag does not contain the front-matter description text"
    )
```

In `test_notes_index_groups_by_topic`:

```python
def test_notes_index_groups_by_topic(site):
    html = read_html(site, "notes/index.html")
    assert "Physics" in html, "topic heading is missing"
    assert "The Lorentz and Poincaré Groups" in html, (
        "note is missing from its topic listing"
    )
```

In `test_note_thumbnail_is_generated_and_referenced`, change both references:

```python
    thumb = REPO_ROOT / "notes" / "thumbs" / "lorentz-poincare-groups.png"
    assert thumb.is_file(), "sync_notes.py did not produce lorentz-poincare-groups.png"

    html = read_html(site, "notes/index.html")
    listing = extract_element(html, "quarto-listing")
    assert listing, "no element with class 'quarto-listing' rendered"
    assert "thumbs/lorentz-poincare-groups.png" in listing, (
        "the listing card does not reference the generated thumbnail"
    )
```

In `test_notes_topic_listing_scoped_to_its_own_section`, change the id and the nested-listing assertion:

```python
    section = extract_element(html, "physics", by="id")
    assert section, "no element with id 'physics' found"
    assert 'id="listing-physics"' in section, (
        "the topic listing is not nested inside its own topic's <section>"
    )
```

Leave that test's `"Write-ups, derivations" not in section` assertion and its docstring alone — the prose-leak check is unchanged by the topic rename.

- [ ] **Step 2: Delete the example note and the template**

```bash
git rm notes/lattice-qcd/example-note.md notes/pdf/example-note.pdf notes/thumbs/example-note.png notes/_note-template.md
```

- [ ] **Step 3: Remove the empty topic from the notes index**

In `notes/index.md`, delete the `lattice-qcd` entry from the `listing:` block:

```yaml
  - id: lattice-qcd
    contents: lattice-qcd
    type: grid
    sort: "title"
    fields: [image, title, description, categories]
    feed: false
```

and delete the heading and listing div:

```markdown
## Lattice QCD

:::{#lattice-qcd}
:::
```

An empty listing renders as a bare heading with nothing under it, so leaving either half behind is visible on the live site.

- [ ] **Step 4: Run the full suite**

Run: `pytest tests/ -v`

Expected: 44 passed.

If `test_notes_topic_listing_scoped_to_its_own_section` fails with "no element with id 'physics' found", the `## Physics` heading's generated id differs from the listing id — check the rendered `notes/index.html` for the actual `id=` on the section and match it.

- [ ] **Step 5: Update the README**

In `README.md`, replace the `**Note**` bullet under "Adding content" with:

```markdown
- **Note** — add an entry to `notes/notes.yml` (`slug` in kebab-case,
  `source` relative to `NOTES_ROOT`, `topic`), run
  `python scripts/sync_notes.py`, then fill in the `TITLE` and
  `DESCRIPTION` placeholders in the stub it scaffolds. The stub's body is
  just `{{< pdf-note >}}`; the shortcode in `_extensions/pdf-note/` renders
  the accent rule, description, download button and inline viewer. Write
  any extra prose (errata, "supersedes the 2024 version") after the
  shortcode — re-running the sync never touches an existing stub.
```

Add to "Conventions worth knowing":

```markdown
- **`NOTES_ROOT` points at the working notes tree**, defaulting to
  `~/Dropbox (Personal)/notes`. The manifest stores source paths relative to
  it so no machine-specific path is committed to this public repo. Set the
  env var on any machine whose notes live elsewhere.
- **Presentation markup belongs in the shortcode, not in a stub.** If you
  find yourself pasting an `<object>` tag into a note, change
  `_extensions/pdf-note/pdf-note.lua` instead — that is the whole point of
  it, and `test_no_stub_hand_copies_the_viewer_markup` will fail otherwise.
```

In the "Unpublishing a note" section, add after the `git rm` command block:

```markdown
Also remove the note's entry from `notes/notes.yml`. Removing the entry on
its own does not unpublish anything — the files stay until they are
`git rm`'d — but leaving the entry behind after deleting the files fails
`test_every_manifest_entry_has_its_files`.
```

- [ ] **Step 6: Verify the deleted PDF is gone from the built site**

Run: `pytest tests/ -v && test ! -e _site/notes/pdf/example-note.pdf && echo "example-note.pdf correctly absent"`

Expected: 44 passed, then `example-note.pdf correctly absent`.

- [ ] **Step 7: Commit**

```bash
git add -A notes README.md tests/test_site.py
git commit -m "content: retire the example note and stub template"
```

- [ ] **Step 8: Push and verify the deploy**

```bash
git push
```

Then wait for the workflow and check the live pages:

Run: `curl -s -o /dev/null -w "%{http_code}\n" https://www.patrickoare.phd/notes/physics/lorentz-poincare-groups.html https://www.patrickoare.phd/notes/pdf/lorentz-poincare-groups.pdf`

Expected: `200` twice. Also confirm `https://www.patrickoare.phd/notes/pdf/example-note.pdf` now returns 404.

---

## Notes for the implementer

- **The `_freeze/` cache is untouched by this work.** No `.qmd` changes here, so no re-render of the notebook post is needed.
- **If a `quarto render` leaves the tree dirty**, check `.gitignore` — an earlier fix normalised the `/.quarto/` entry specifically because Quarto re-appends its own. Do not let a stray edit to that line back in.
- **Do not add an orphan PDF fixture** to test the `resources:` key. One already exists, created ephemerally by the `_orphan_fixture_pdf` fixture in `tests/conftest.py`; a tracked one previously shipped to the live site.
- **Category taxonomy is provisional.** `[physics, group-theory]` on the first note is a starting guess, to be revisited once enough notes exist to see it whole. Do not build anything that depends on the current category names.
