# poare.github.io

Source for <https://www.patrickoare.phd>, built with [Quarto](https://quarto.org)
and deployed to GitHub Pages.

## Working on it

    quarto preview          # live preview at localhost, reloads on save
    pytest tests/ -v        # verify the built output
    git push                # GitHub renders and republishes automatically

## Adding content

- **Blog post** — create `blog/posts/YYYY-MM-DD-slug/index.md` with `title`,
  `date` and `categories` in the front matter. It appears in the listing
  automatically.
- **Note** — add an entry to `notes/notes.yml` (`slug` in kebab-case,
  `source` relative to `NOTES_ROOT`, `topic`), run
  `python scripts/sync_notes.py`, then fill in the `TITLE` and
  `DESCRIPTION` placeholders in the stub it scaffolds. The stub's body is
  just `{{< pdf-note >}}`; the shortcode in `_extensions/pdf-note/` renders
  the accent rule, download button and inline viewer. Write any extra prose
  (errata, "supersedes the 2024 version") after the shortcode — re-running
  the sync never touches an existing stub. `topic` must correspond to an
  `id:` in the `listing:` block of `notes/index.md` — if this is the first
  note for a new topic, add a listing section for it there too (copy the
  `## Physics` / `:::{#physics}:::` pattern), or the note renders but never
  appears on `/notes`.
- **Tab** — add two lines to the `navbar:` list in `_quarto.yml`.
- **Colours** — edit the variables at the top of `theme.scss`. Nothing further
  down hard-codes a colour.

## Unpublishing a note

**Taking a note off the site is always a manual `git rm`.** Nothing automates
it, on purpose. Remove all three files:

    git rm notes/<topic>/<slug>.md notes/pdf/<slug>.pdf notes/thumbs/<slug>.png

Deleting only the stub leaves the PDF reachable at its direct URL — the page
disappears, the download does not.

Note that `git rm` removes the file from the *current* site, not from history:
the PDF stays in every earlier commit, and this repo is public. Treat
publishing as irreversible and decide before committing, not after.

Also remove the note's entry from `notes/notes.yml`. Removing the entry on
its own does not unpublish anything — the files stay until they are
`git rm`'d — but leaving the entry behind after deleting the files fails
`test_every_manifest_entry_has_its_files`.

## Conventions worth knowing

- **Use `.md` for prose, `.qmd` only for pages that execute code.** Markdown
  editors such as Obsidian only index `.md`.
- **`_freeze/` is committed on purpose.** It caches notebook outputs so CI needs
  no Python environment and the other machine does not re-run notebooks. If you
  edit a `.qmd`, run `quarto render` locally and commit the updated cache.
  Doing that requires Jupyter and matplotlib — both are in `requirements.txt`
  purely for this; CI itself installs no Python at all.
- **CI pins Quarto to 1.10.18** in `.github/workflows/publish.yml` (the
  `Install Quarto` step's `version:`). That is the version that produced the
  committed `_freeze/` cache; freeze semantics and render output aren't
  guaranteed stable across Quarto releases. If you upgrade Quarto locally, bump
  the pin in the workflow to match — the local version is what generates the
  cache CI later relies on.
- **Never commit unsubsetted `.ttf` files** to `assets/fonts/`. The subsetted
  WOFF2 outputs are already committed under `assets/fonts/` — you do not need
  to regenerate them on a new machine. Only run
  `python scripts/subset_fonts.py` if you are deliberately re-subsetting (e.g.
  a font update or a change to the Unicode ranges); it overwrites all five
  committed WOFF2 files, so check the resulting diff before committing.
- **A `_freeze/` merge conflict** is not worth resolving by hand. Delete the
  affected entry, re-render, and commit.
- **Dark mode is deliberately not implemented.** See the comment at the top of
  `theme.scss` for the reasoning.
- **The favicon is generated, not hand-drawn.** `assets/lqcd_icon.pdf` is the
  master artwork; `python scripts/make_favicon.py` renders it to
  `assets/favicon.svg` (primary) and `assets/favicon.png` (fallback for
  browsers without SVG favicon support). Both outputs are committed, so a
  fresh checkout needs nothing run — only re-run it if the artwork changes.
  The script refuses to build a non-square icon, since that would be
  letterboxed or stretched differently in every place it appears.
- **`NOTES_ROOT` points at the working notes tree**, defaulting to
  `~/Dropbox (Personal)/notes`. The manifest stores source paths relative to
  it so no machine-specific path is committed to this public repo. Set the
  env var on any machine whose notes live elsewhere.
- **Presentation markup belongs in the shortcode, not in a stub.** If you
  find yourself pasting an `<object>` tag into a note, change
  `_extensions/pdf-note/pdf-note.lua` instead — that is the whole point of
  it, and `test_no_stub_hand_copies_the_viewer_markup` will fail otherwise.

## First-time setup on a new machine

Install the Quarto CLI first — `quarto preview` and `quarto render` need it.
Match the version pinned in `.github/workflows/publish.yml` (currently 1.10.18):

- **macOS** — download the `.pkg` for that version from
  <https://github.com/quarto-dev/quarto-cli/releases> and install it.
  (`brew install quarto` installs whatever is newest, which will usually *not*
  match the pin — use the `.pkg` if you want the versions to agree.)
- **Ubuntu** — download the matching `.deb` from the same releases page and
  install with `sudo dpkg -i quarto-*.deb`.

Then set up the Python side:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

That's it — the subsetted WOFF2 fonts and the notebook `_freeze/` cache are
already committed, so nothing further needs to run on a fresh checkout.
`scripts/subset_fonts.py` is only for deliberately regenerating the fonts
(see the "Conventions worth knowing" note above); it needs the CMU fonts
installed locally and is not a setup step.
