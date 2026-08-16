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


BANNER_NAME = "_series-banner.md"
NAV_NAME = "_series-nav.md"


# Links point at SOURCE paths, not .html. Quarto rewrites the extension and
# the leading slash per page depth on the way out, and resolving against
# the source file means Quarto itself errors on a link to a post that does
# not exist -- an .html link would silently 404 in production instead.
def _post_href(post):
    return f"/blog/posts/{post['slug']}/{post['source']}"


def _series_href(series_slug):
    return f"/blog/series/{series_slug}/index.md"


def banner_markdown(part_number, series_slug, series_title):
    """The 'Part N of <series>' line that opens a post in a series."""
    return (
        "::: {.series-banner}\n"
        f"Part {part_number} of [{series_title}]({_series_href(series_slug)})\n"
        ":::\n"
    )


def nav_markdown(parts, index, series_slug):
    """The prev / index / next footer for the part at `index`.

    The prev link is omitted on the first part and the next on the last:
    a link reading "Part 0" is worse than no link at all.
    """
    links = []
    if index > 0:
        previous = parts[index - 1]
        links.append(
            f"[← Part {index}: {previous['title']}]({_post_href(previous)})"
        )
    links.append(f"[All parts]({_series_href(series_slug)})")
    if index < len(parts) - 1:
        following = parts[index + 1]
        links.append(
            f"[Part {index + 2}: {following['title']} →]({_post_href(following)})"
        )
    return "::: {.series-nav}\n" + " · ".join(links) + "\n:::\n"


def _write_if_changed(path, text):
    """Write only when the content differs.

    Rewriting an unchanged file bumps its mtime, and Quarto keys some of
    its caching on mtimes -- so an unconditional write would make every
    render look like every post had changed.
    """
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def write_partials(grouped, series_meta, posts):
    """Write each series post's partials and delete any stale ones.

    Returns human-readable lines describing what changed.
    """
    lines = []
    in_a_series = set()

    for series_slug, parts in grouped.items():
        if not parts:
            lines.append(f"warning: series {series_slug!r} has no posts yet")
            continue
        title = series_meta[series_slug]["title"]
        for index, post in enumerate(parts):
            in_a_series.add(post["slug"])
            directory = post["path"].parent
            banner = banner_markdown(index + 1, series_slug, title)
            nav = nav_markdown(parts, index, series_slug)
            if _write_if_changed(directory / BANNER_NAME, banner):
                lines.append(f"wrote {post['slug']}/{BANNER_NAME}")
            if _write_if_changed(directory / NAV_NAME, nav):
                lines.append(f"wrote {post['slug']}/{NAV_NAME}")

    # A post that drops its `series:` key keeps its include directives
    # until they are removed by hand. Leaving the partials behind would
    # render last render's navigation indefinitely, and since they are
    # gitignored, no diff would ever show it.
    for post in posts:
        if post["slug"] in in_a_series:
            continue
        for name in (BANNER_NAME, NAV_NAME):
            stale = post["path"].parent / name
            if stale.is_file():
                stale.unlink()
                lines.append(f"removed stale {post['slug']}/{name}")

    return lines


def main(argv=None):
    try:
        posts = collect_posts(POSTS_DIR)
        series_meta = load_series(SERIES_DIR)
        grouped = group_parts(posts, series_meta)
    except SeriesError as exc:
        print(f"sync_series: {exc}", file=sys.stderr)
        return 1

    for line in write_partials(grouped, series_meta, posts):
        print(f"sync_series: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
