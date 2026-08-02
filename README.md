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
- **Tab** — add three lines to the `navbar:` list in `_quarto.yml`.
- **Colours** — edit the variables at the top of `theme.scss`. Nothing further
  down hard-codes a colour.

## Conventions worth knowing

- **Use `.md` for prose, `.qmd` only for pages that execute code.** Markdown
  editors such as Obsidian only index `.md`.
- **`_freeze/` is committed on purpose.** It caches notebook outputs so CI needs
  no Python environment and the other machine does not re-run notebooks. If you
  edit a `.qmd`, run `quarto render` locally and commit the updated cache.
- **Never commit unsubsetted `.ttf` files** to `assets/fonts/`. Run
  `python scripts/subset_fonts.py` instead; it produces WOFF2 files around
  100 KB each.
- **A `_freeze/` merge conflict** is not worth resolving by hand. Delete the
  affected entry, re-render, and commit.
- **Dark mode is deliberately not implemented.** See `website_setup.md`.

## First-time setup on a new machine

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python scripts/subset_fonts.py    # needs CMU fonts installed locally
