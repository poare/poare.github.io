# Notes: shared shortcode and manifest-driven ingest

Status: approved 2026-08-02. Supersedes the hand-copied stub workflow described
in the README's "Adding content" section.

## Problem

Every note page is a near-identical stub created by copying
`notes/_note-template.md` and replacing placeholders by hand. Per note the slug
is typed four times (`image:`, the download link, and twice in the `<object>`
viewer) and the description twice (front matter and body prose). The `<object>`
block is four lines of raw HTML repeated verbatim in every file.

At the current single example note this costs nothing. At the intended 20-30
notes it means changing how PDFs are presented is a 30-file edit, and a
mistyped slug produces a broken download link on one page while every other
page still looks fine.

A second, separate problem: nothing records *which* notes are approved for
publication. The source PDFs live in a working notes tree containing unfinished
material, and the boundary between "drafted" and "published" currently exists
only in the author's head at the moment of copying.

## Non-goals

- **Deleting or unpublishing notes.** The sync step only adds and refreshes.
  Removing a manifest entry leaves the PDF, thumbnail and stub in place;
  unpublishing is a manual `git rm`. Config-driven deletion is how a typo'd
  slug silently destroys hand-written prose.
- **Bulk ingest.** Publishing is deliberately one explicit manifest entry at a
  time. The repo is public and every committed PDF is permanent in git history.
- **Rebuilding PDFs from LaTeX.** The sync step consumes finished PDFs. It
  never invokes a TeX toolchain.
- **Putting notes under version control.** Whether the source notes tree
  becomes its own git repository is an independent decision on its own
  timeline. Nothing here is wasted work if that happens later; only the value
  of `NOTES_ROOT` changes.

## Architecture

Four pieces with one responsibility each.

| Piece | Owns | Does not own |
|---|---|---|
| `notes/notes.yml` | Whether a note is published, and where its source lives | Any displayed content |
| `scripts/sync_notes.py` | Bytes on disk: PDF copies, thumbnails, first-time stub scaffold | Anything already written |
| `_extensions/pdf-note/` | How every note page looks | What any individual note says |
| The stub `.md` | Title, description, categories, prose | Presentation markup |

The division to keep in mind: the manifest owns *whether and from where*, the
script owns *bytes on disk*, the shortcode owns *how it looks*, the stub owns
*what it says*.

### `notes/notes.yml`

```yaml
- slug: lorentz-poincare-groups
  source: physics/lorentz_poincare_groups/lorentz_poincare_groups.pdf
  topic: physics
```

Three keys, all required. `source` is relative to the `NOTES_ROOT` environment
variable, which defaults to `~/Dropbox (Personal)/notes`. Paths are stored
relative so that no machine-specific location is committed to a public repo,
and so a second machine with a different layout needs only a different
`NOTES_ROOT`.

`slug` is kebab-case and is the note's identity everywhere: page URL, stub
filename, PDF filename, thumbnail filename. Source filenames are snake_case;
the snake-to-kebab rename happens here, once, and doubles as a deliberate act
signalling that a note is finished enough to have a public URL.

`topic` names the subdirectory under `notes/` and must correspond to a listing
in `notes/index.md`.

### `scripts/sync_notes.py`

For each manifest entry:

1. Resolve `NOTES_ROOT` / `source`; error clearly if the file is absent.
2. Copy to `notes/pdf/<slug>.pdf`, overwriting. The PDF is a build input, never
   hand-edited, so refreshing it after a recompile is safe.
3. Generate `notes/thumbs/<slug>.png` by calling into `scripts/make_thumbs.py`
   rather than reimplementing thumbnailing. That code path already handles
   corrupt and encrypted PDFs per-file without aborting the batch.
4. If `notes/<topic>/<slug>.md` does **not** exist, scaffold it with `title` and
   `description` as obvious placeholders and a body of `{{< pdf-note >}}`.
   If it **does** exist, leave it completely untouched.

Step 4's no-overwrite rule is the property the whole design rests on: re-running
after recompiling a PDF must refresh the binary and thumbnail while preserving
every word written by hand. It is tested, not merely documented.

Failures are per-entry: one missing source or corrupt PDF warns, continues, and
the run exits non-zero with a summary. This matches the behaviour already
established in `make_thumbs.py` and `subset_fonts.py`.

The script is a local authoring tool. CI never runs it. PDFs, thumbnails and
stubs are all committed, so the no-Python-in-CI invariant established in Task 9
is unaffected.

### `_extensions/pdf-note/`

A Lua shortcode invoked as `{{< pdf-note >}}`, emitting in order:

1. The `.accent-rule` div
2. `[Download PDF](../pdf/<slug>.pdf){.btn .btn-primary}`
3. The `<object>` viewer with its non-supporting-browser fallback link

Quarto's own page template already renders the front-matter `description:`
under the title, so the shortcode does not emit it a second time — an earlier
version did, which put the same sentence on the page twice.

Content authored after the shortcode in the stub renders after the viewer, so a
note can carry errata, "supersedes the 2024 version", or links to related notes.

**Open implementation question, to be resolved first:** whether a shortcode can
read `quarto.doc.input_file` to derive the slug. If it can, the body names the
slug zero times. If it cannot, the fallback is an explicit argument,
`{{< pdf-note lorentz-poincare-groups >}}` — one repeated token per stub instead
of four. This is the only part of the design resting on unverified Quarto
behaviour and must be settled before the rest is built.

Either way the slug still appears once in the stub's `image:` front matter. A
body shortcode cannot populate front matter, and the listing reads `image:` as
metadata, so this occurrence cannot be eliminated. It is written by
`sync_notes.py` at scaffold time and so is never typed by hand.

## Content flow

```
notes tree (working, private)
    |  manual: finish the note, decide it is publishable
    v
notes/notes.yml           <- the approval boundary; one explicit entry
    |  sync_notes.py
    v
notes/pdf/<slug>.pdf      (overwritten each run)
notes/thumbs/<slug>.png   (overwritten each run)
notes/<topic>/<slug>.md   (created once, never overwritten)
    |  quarto render, shortcode expands {{< pdf-note >}}
    v
_site/notes/<topic>/<slug>.html
```

## Testing

The existing conftest helper that globs every notes stub and resolves its PDF
link covers new notes on creation and continues to apply unchanged. Added on
top of it:

| Test | Failure it catches |
|---|---|
| Rendered note page contains the accent rule, and a button href and `<object>` data attribute pointing at *that page's own* slug | Shortcode expanding to nothing, or deriving another note's slug — which a mere link-resolution check would pass, since the other file exists |
| Every manifest slug has a committed PDF, thumbnail and stub | Manifest entry added, sync never run |
| Every manifest slug matches `^[a-z0-9]+(-[a-z0-9]+)*$` | snake_case or capitals reaching a public URL |
| No stub contains a literal `<object` | Quiet regression to hand-copied boilerplate |
| Running sync twice leaves an existing stub byte-identical | The clobber-your-prose failure |

Assertions against rendered HTML use the existing `extract_element()` helper in
`tests/conftest.py` so they stay scoped to the element under test.

## Migration

1. Verify the `input_file` question; settle the shortcode's calling convention.
2. Build the extension and convert `notes/lattice-qcd/example-note.md` to use
   it, proving the shortcode against a page that already renders correctly.
3. Add the manifest and `sync_notes.py`; ingest
   `physics/lorentz_poincare_groups/lorentz_poincare_groups.pdf` as
   `lorentz-poincare-groups`, creating the `physics` topic and its listing in
   `notes/index.md`.
4. Remove `example-note` (stub, PDF, thumbnail) and `notes/_note-template.md`,
   which the shortcode makes obsolete. The site should not ship placeholder
   content once a real note exists. This empties the `lattice-qcd` topic, so
   its `##` heading and listing block come out of `notes/index.md` at the same
   time — an empty listing renders as a bare heading with nothing under it.
5. Update the README's "Adding content" section to describe the manifest
   workflow, and extend its "Unpublishing a note" section to add removing the
   `notes.yml` entry. Removing that entry alone does not unpublish — the files
   stay until they are `git rm`'d, and the entry must go too or the
   manifest-consistency test will fail on a missing PDF.

## Confirmed and outstanding

- `NOTES_ROOT` default `~/Dropbox (Personal)/notes` is correct on the macOS
  machine. **Unconfirmed on the Ubuntu machine** — to be checked; if it
  differs, only the env var changes, not the manifest.
- The `[physics, group-theory]` categories on the first note are provisional.
  Category taxonomy gets revisited once enough notes exist to see it whole.

Topic groupings beyond `physics` are deferred until more notes are assembled.
The source tree's existing `math` / `physics` split is the natural starting
point.
