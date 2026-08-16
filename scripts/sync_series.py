"""Generate the series banner and prev/next navigation for blog posts.

A series is a directory under blog/series/ whose index.md is written by
hand. A post joins one by declaring `series: <slug>` in its front matter.
Part order is publication date ascending, so nothing has to be renumbered
when a post is added or back-dated.

Runs as a Quarto pre-render script, so the navigation is rebuilt on every
`quarto render` and cannot go stale.

Usage:  python scripts/sync_series.py
"""

import datetime
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# Running this as `python scripts/sync_series.py` puts scripts/ on
# sys.path, not the repo root, so `from scripts...` imports would fail even
# though they resolve fine under pytest. Mirrors sync_notes.py.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

POSTS_DIR = REPO_ROOT / "blog" / "posts"
SERIES_DIR = REPO_ROOT / "blog" / "series"

# A front matter block is a YAML document fenced by --- at the very start
# of the file. Non-greedy so a horizontal rule later in the prose cannot
# swallow the whole document.
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


class SeriesError(Exception):
    """A post or series is misconfigured. Raised with the offender named."""


def read_frontmatter(path):
    """Return a file's YAML front matter as a dict, or {} if it has none."""
    match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    if not match:
        return {}
    data = yaml.safe_load(match.group(1))
    return data if isinstance(data, dict) else {}


def _as_date(value):
    """Coerce a front matter date to datetime.date, or None.

    PyYAML already parses an unquoted `date: 2026-08-18` into a date, but a
    quoted one stays a string, and Quarto accepts both. Sorting a mix of
    the two raises TypeError deep inside sorted(), which names neither the
    post nor the problem -- so both forms are normalised here instead.
    """
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def collect_posts(posts_dir):
    """Return one dict per post directory containing an index.md/.qmd."""
    posts = []
    if not posts_dir.is_dir():
        return posts
    for directory in sorted(p for p in posts_dir.iterdir() if p.is_dir()):
        for name in ("index.md", "index.qmd"):
            source = directory / name
            if source.is_file():
                break
        else:
            continue
        meta = read_frontmatter(source)
        posts.append({
            "slug": directory.name,
            "title": str(meta.get("title", directory.name)),
            "date": _as_date(meta.get("date")),
            "series": meta.get("series"),
            "source": source.name,
            "path": source,
        })
    return posts


def load_series(series_dir):
    """Return slug -> metadata for every series landing page that exists."""
    series = {}
    if not series_dir.is_dir():
        return series
    for directory in sorted(p for p in series_dir.iterdir() if p.is_dir()):
        index = directory / "index.md"
        if not index.is_file():
            continue
        meta = read_frontmatter(index)
        series[directory.name] = {"title": str(meta.get("title", directory.name))}
    return series


def group_parts(posts, series_meta):
    """Return series slug -> parts in publication order.

    Every declared series gets a key, including ones with no posts yet:
    that is the normal state of a series the moment its landing page is
    written, and erroring on it would make starting a series impossible.
    """
    grouped = {slug: [] for slug in series_meta}
    for post in posts:
        slug = post["series"]
        if slug is None:
            continue
        if slug not in series_meta:
            raise SeriesError(
                f"{post['slug']}: series {slug!r} has no landing page. "
                f"Create blog/series/{slug}/index.md, or fix the typo."
            )
        if post["date"] is None:
            raise SeriesError(
                f"{post['slug']}: a post in a series needs a `date` in its "
                "front matter -- part order is derived from it."
            )
        grouped[slug].append(post)

    # Ties broken by directory name so two posts sharing a date order the
    # same way on every machine; a bare date sort would leave them at the
    # mercy of directory iteration order.
    for parts in grouped.values():
        parts.sort(key=lambda post: (post["date"], post["slug"]))
    return grouped
