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
  then create a stub `.md` in the matching topic folder.
- **Tab** — add two lines to the `navbar:` list in `_quarto.yml`.
- **Colours** — edit the variables at the top of `theme.scss`. Nothing further
  down hard-codes a colour.

## Conventions worth knowing

- **Use `.md` for prose, `.qmd` only for pages that execute code.** Markdown
  editors such as Obsidian only index `.md`.
- **`_freeze/` is committed on purpose.** It caches notebook outputs so CI needs
  no Python environment and the other machine does not re-run notebooks. If you
  edit a `.qmd`, run `quarto render` locally and commit the updated cache.
- **CI pins Quarto to 1.10.18** in `.github/workflows/publish.yml` (the
  `Install Quarto` step's `version:`). That is the version that produced the
  committed `_freeze/` cache; freeze semantics and render output aren't
  guaranteed stable across Quarto releases. If you upgrade Quarto locally, bump
  the pin in the workflow to match — the local version is what generates the
  cache CI later relies on.
- **Never commit unsubsetted `.ttf` files** to `assets/fonts/`. Run
  `python scripts/subset_fonts.py` instead; it produces WOFF2 files around
  100 KB each.
- **A `_freeze/` merge conflict** is not worth resolving by hand. Delete the
  affected entry, re-render, and commit.
- **Dark mode is deliberately not implemented.** See the comment at the top of
  `theme.scss` for the reasoning.

## First-time setup on a new machine

Install the Quarto CLI first — `quarto preview` and `quarto render` need it.
Match the version pinned in `.github/workflows/publish.yml` (currently 1.10.18):

- **macOS** — download the `.pkg` for that version from
  <https://github.com/quarto-dev/quarto-cli/releases> and install it, or
  `brew install quarto` for the latest release.
- **Ubuntu** — download the matching `.deb` from the same releases page and
  install with `sudo dpkg -i quarto-*.deb`.

Then set up the Python side:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python scripts/subset_fonts.py    # needs CMU fonts installed locally
