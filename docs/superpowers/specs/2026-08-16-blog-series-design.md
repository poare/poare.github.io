# Blog series — design

**Date:** 2026-08-16
**Status:** approved, not yet implemented

## Problem

Blog posts are currently flat and independent: a directory per post under
`blog/posts/YYYY-MM-DD-slug/`, surfaced only through a single
reverse-chronological listing on `blog/index.md`. Two multi-part series are
about to run in parallel — *A Course in Arithmetic* (a book-club series) and
*The History of the Standard Model* — and nothing in the site expresses that a
post is part of an ordered sequence.

A reader landing mid-series has no way to find the previous part, the next
part, or the series as a whole. The author has no place to describe a series.

## Goals

1. A post can declare membership in a series.
2. Several series run in parallel without interfering with each other or with
   standalone posts.
3. A reader on any part can move to the adjacent parts, or to an index of the
   whole series.
4. Each series has a landing page the author writes freely, with its own
   figure.
5. Adding a part requires no renumbering and no manual bookkeeping.

## Non-goals

- A persistent series sidebar on post pages. Considered and rejected: it
  changes the page layout site-wide for a navigation need that prev/next
  already covers.
- Per-part figures on the series landing page beyond what posts already
  produce. Posts keep their existing image behaviour on listings.
- Replacing categories. `categories:` continues to drive the filter chips on
  the blog index; `series:` drives ordering and navigation. They overlap and
  that is fine.

## Data model

A series **is** a directory under `blog/series/`. There is no central
manifest. Rejected alternative: a `blog/series.yml` holding titles and blurbs —
once the landing page exists and carries a title, description, and image, a
manifest would duplicate that data and drift from it.

```
blog/series/arithmetic/
    index.md      committed, hand-written, never overwritten by any script
    thumb.png     the figure shown on the series card
blog/posts/2026-08-18-arithmetic/
    index.md      committed, hand-written; declares `series: arithmetic`
    _series-banner.md   generated, gitignored
    _series-nav.md      generated, gitignored
```

### Series landing page

```markdown
---
title: "A Course in Arithmetic"
description: "Working through Serre's book with a friend, one chapter at a time."
image: thumb.png
listing:
  contents: ../../posts
  include:
    series: arithmetic
  sort: "date asc"
  type: grid
---

Free prose: why the series exists, where it is going, what it assumes.
```

The listing block is Quarto's native filtering on a custom frontmatter field.
If `include:` proves not to filter on custom fields, the fallback is
`sync_series.py` emitting an explicit `contents:` list of post paths into a
generated partial. The landing-page test below distinguishes these cases
immediately, so the fallback is a known, tested branch rather than a surprise.

The page is created by hand and **never written to by any script**, following
the spirit of the stub convention in `scripts/sync_notes.py`: it holds
hand-written prose, and a config-driven overwrite is how a typo'd slug silently
destroys it. Taking a series down is a `git rm`.

Nothing scaffolds it. A post naming a series with no landing page is an error
(below), and a script that answered the same situation by silently creating a
page would defeat that check: a typo'd slug would produce a plausible-looking
empty series rather than a message naming the mistake.

### Post frontmatter

```yaml
---
title: "A Course in Arithmetic: Prerequisites"
date: 2026-08-18
categories: [math, arithmetic, technical, book-club]
series: arithmetic
---

{{< include _series-banner.md >}}

... prose ...

{{< include _series-nav.md >}}
```

A post with no `series:` key is an ordinary standalone post and carries neither
include. The two include directives are the only authoring boilerplate.

### Ordering

Part order is publication date ascending, ties broken by directory name. Part
numbers are the 1-based position in that order and are never written down
anywhere. Publishing a post makes it the next part; back-dating one inserts it
mid-series and renumbers everything downstream automatically.

## Components

### `scripts/sync_series.py`

Sole responsibility: given the posts and series that exist, write each series
post's banner and nav partials.

- **Input:** frontmatter of every `blog/posts/*/index.{md,qmd}` and every
  `blog/series/*/index.md`.
- **Output:** `_series-banner.md` and `_series-nav.md` in each series post's
  directory. Nothing else is written.
- **Validation:** exits non-zero with a clear message if a post names a series
  with no landing page. A silent broken link is the failure mode worth
  spending an error on. A series with no posts is a warning, not an error —
  that is the normal state of a series the author has just started.
- **Safety:** never writes to a file that holds prose. Idempotent; re-running
  changes nothing.
- Registered as a Quarto `pre-render` script in `_quarto.yml`, so it runs at
  the start of every `quarto render` and the navigation cannot go stale.

Depends on PyYAML, matching `sync_notes.py`. Rejected alternative: hand-parsing
frontmatter with the standard library to avoid a CI dependency — a bespoke YAML
parser diverging from the rest of `scripts/` is not worth ten seconds of CI.

### Generated markup

Banner, at the top of a post:

```markdown
::: {.series-banner}
Part 3 of [A Course in Arithmetic](/blog/series/arithmetic/)
:::
```

Nav, at the foot of a post:

```markdown
::: {.series-nav}
[← Part 2: Prerequisites](/blog/posts/2026-08-18-arithmetic/) ·
[All parts](/blog/series/arithmetic/) ·
[Part 4: Quadratic forms →](/blog/posts/2026-09-02-quadratic-forms/)
:::
```

The prev link is omitted on the first part and the next link on the last.
Hrefs are root-relative: `_quarto.yml` documents that Quarto rewrites those
per page depth on the way out, which plain relative links in included partials
would not survive.

### `blog/index.md`

Gains a Series row above the existing post grid:

```yaml
listing:
  - id: series
    contents: series/*/index.md
    type: grid
    fields: [image, title, description]
  - id: posts
    # unchanged
```

The main post grid is left exactly as it is: every part of every series
continues to appear there, newest first, interleaved with standalone posts. A
reader reaches a post either directly from that grid or via the series card and
its landing page.

### `theme.scss`

Two additions, sized off the existing `$accent`: `.series-banner` (small,
above the prose) and `.series-nav` (a rule with prev left, index centre, next
right).

### `.gitignore`

```
blog/posts/**/_series-*.md
```

### `.github/workflows` deploy

Add a `setup-python` step and `pip install pyyaml` before `quarto render`, so
the pre-render script runs in CI.

This does not weaken the workflow's deliberate exclusion of Python: that
comment is about notebook execution, and without Jupyter installed the freeze
cache still governs all code execution. Update the comment to say so, since it
currently reads as an absolute prohibition.

## Testing

Assertions run against rendered HTML in `_site`, in the style of
`tests/test_site.py`, not against the script's intentions.

1. A series post's banner names the correct series and links to a landing page
   that exists in the built output.
2. Prev/next links on a middle part resolve to files that exist. The first
   part has no prev link; the last has no next link.
3. The series landing page lists exactly the posts tagged with that series —
   no more, no fewer. This is what catches the `include:` filter silently
   matching nothing or everything.
4. The Blog page's Series row contains one card per directory under
   `blog/series/`.
5. A post naming a nonexistent series makes `sync_series.py` exit non-zero
   (unit test against a temporary tree).
6. The `.qmd` post in a series has correct navigation despite its execution
   being frozen. The freeze cache holds computed output; this proves it does
   not also hold stale navigation.

## Documentation

`README.md` gains a Series section: starting a series, adding a part, taking a
series down.

## Migration

The three existing posts are retrofitted: `series: arithmetic` on the
arithmetic post, `series: standard-model` on the two Standard Model posts, plus
the include lines and two landing pages with figures.
