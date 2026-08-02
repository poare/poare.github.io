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
- **Note** — put the PDF in `notes/pdf/`, run `python scripts/make_thumbs.py`,
  then copy `notes/_note-template.md` into the matching topic folder and
  replace the `TITLE` / `SLUG` / `DESCRIPTION` / `TOPIC` placeholders (the
  leading underscore keeps the template itself out of the rendered site).
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
  a font update or a change to the Unicode ranges); it overwrites all six
  committed WOFF2 files, so check the resulting diff before committing.
- **A `_freeze/` merge conflict** is not worth resolving by hand. Delete the
  affected entry, re-render, and commit.
- **Dark mode is deliberately not implemented.** See the comment at the top of
  `theme.scss` for the reasoning.

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
