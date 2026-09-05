# patrickoare.phd

Quarto website. `README.md` is the full reference and is unusually detailed — read the relevant section there before changing anything structural. This file is only the operating rules that are easy to get wrong.

## How the site is built and deployed

GitHub Pages, via `.github/workflows/publish.yml`, on push to `main` only. Any other branch pushes without deploying.

**CI installs no Python.** It renders from the committed `_freeze/` cache and installs only `pyyaml` for the series script. So notebook cells execute on a developer machine and never in CI. If a deploy ever fails asking for Jupyter, it means a `.qmd` changed and was committed without being re-rendered locally first.

## Commands

```bash
quarto render                       # whole site
quarto preview blog/posts/<slug>/index.qmd
.venv/bin/python -m pytest tests -q  # 110 tests; runs quarto render itself
python scripts/sync_series.py       # after adding or re-dating a post
```

`_environment` pins `QUARTO_PYTHON=.venv/bin/python`. Do not drop it: Quarto otherwise runs whatever `python3` is on `PATH`, which on these machines is Anaconda, and the render dies with a `ModuleNotFoundError` that reads like a broken path rather than the wrong interpreter.

## The freeze cache

`_freeze/` is committed on purpose and is the reason CI needs no Python.

**Its cache key covers only the `.qmd` source.** Editing anything the cell *imports* — `plotstyle.py`, or `plottools.py`/`formattools.py` over in the `lqcd` repo — does not invalidate it, so the page goes on serving a figure from whenever the code last ran while displaying your current source next to it. Clear the entry explicitly:

```bash
rm -rf _freeze/blog/posts/<slug> && quarto render
```

The same staleness applies to `{{< include >}}` partials, which is why `sync_series.py` has a CI gate.

**Never hand-resolve a `_freeze/` merge conflict.** Delete the affected entry, re-render, commit.

## Plotting in posts

Posts plot through `plotstyle.py` at the repo root:

```python
import plotstyle as pt
```

It re-exports the `plottools` API and selects the `blog_post` style. `plottools` lives in the separate `lqcd` repository and stays the single copy — never vendor it here. What belongs in this repo is only the choice of style.

The style switch must happen after `plottools` is imported and by mutating `formattools.default_style` in place. `plottools` takes `default_style` as a default argument value in ~15 signatures, and Python evaluates those once at import, so rebinding the name afterwards is a silent no-op.

Two per-machine setup steps are needed before any of this imports — three pip installs and a `.pth` file. See `README.md`, "Making `plottools` importable". A `.pth` line is taken verbatim, so a `~` in it silently adds no path at all.

## Layout invariants

Every page sets `page-layout: full` so the left gutter matches site-wide; posts inherit it from `blog/posts/_metadata.yml`, which also sets the `blog-post` body class.

Three rules at the end of `theme.scss` carry measured numbers in their comments. They look over-specified and are not — each records a failure that a "simplification" would reintroduce:

- The post measure cap is `min(965px, 100%)`. A bare `max-width` caps a grid item but never shrinks one, and overflowed by 617px at a 375px viewport.
- The minimum side gutters use a `clamp()` ramp. A flat value overflowed at 768px, where the grid's own minimum content width already needs the space.
- Executed-cell figures are capped at `max-width: 100%` with `height: auto`. Quarto writes an explicit pixel width onto a matplotlib `<img>` and nothing else caps it.

Verify layout changes by measuring the rendered DOM at several viewport widths, not by eye — every number in those comments came from a measurement, and the regressions above all looked fine at desktop width.

## Conventions

- `.md` for prose, `.qmd` only for pages that execute code. Markdown editors index only `.md`.
- Colours come from the five SCSS variables at the top of `theme.scss`. A hex literal anywhere else fails `test_colours_are_variables_not_literals`.
- Quarto is pinned to 1.10.18 in the workflow. Bump it there if you upgrade locally, since the local version generates the cache CI relies on.
- Dark mode is deliberately not implemented; see the comment at the top of `theme.scss`.
