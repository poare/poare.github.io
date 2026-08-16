# Blog Series Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a blog post declare membership in an ordered series, so readers get a "Part 3 of …" banner, prev/next navigation, and a per-series landing page — with several series running in parallel.

**Architecture:** A series is a directory under `blog/series/` whose `index.md` is hand-written and never overwritten. A post joins one by adding `series: <slug>` to its frontmatter and two `{{< include >}}` lines to its body. `scripts/sync_series.py` derives part order from post dates and writes the two included partials into each post's directory. Those partials are COMMITTED, and the script is run by hand: Quarto expands includes while scanning the project, before pre-render scripts run, so a generated-at-build-time partial does not exist when its include is resolved and a fresh clone cannot render. `test_series_partials_are_up_to_date` fails if the script was not re-run. The series landing page and the Blog page's Series row are plain Quarto listings with no generated backing.

**Tech Stack:** Quarto 1.10.18, Python 3.12 + PyYAML (already in `requirements.txt`), pytest, SCSS.

**Spec:** `_docs/specs/2026-08-16-blog-series-design.md`

## Global Constraints

- Commands assume `$WEBSITE` points at this repo. **No tracked file may contain
  a machine-specific absolute path** — an absolute home-directory path on
  either macOS or Linux. This repo is public, and
  `test_no_local_filesystem_paths_leak_into_tracked_sources` scans every
  tracked file for exactly that. Use `$WEBSITE` or a repo-relative path.
- Part order is **publication date ascending, ties broken by directory name**. Part numbers are the 1-based position and are never stored anywhere.
- `scripts/sync_series.py` writes **only** `_series-banner.md` and `_series-nav.md` inside post directories. It must never write to a file containing prose.
- Series landing pages follow the stub convention of `scripts/sync_notes.py`: created once if absent, **never overwritten**, removed by `git rm`.
- Slugs are kebab-case, matching the existing `SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")` in `scripts/sync_notes.py`.
- A post naming a series with no landing page is a **hard error** (non-zero exit). A series with no posts is a **warning**.
- Generated links point at *source* paths (`/blog/series/arithmetic/index.md`), not `.html`. Quarto rewrites both the extension and the root-relative prefix per page depth, and resolving against source means Quarto validates the target exists. **If Task 3's rendered-HTML tests show the `.md` extension surviving into the output, switch the generator to emit `.html` and re-run** — that is the known fallback, not a surprise.
- Repo convention (enforced by `test_tracked_qmd_files_execute_code`): `.md` for prose, `.qmd` only for pages that execute code. Every file this plan creates is `.md`.
- Existing uncommitted work is present in `blog/`. Do not revert or "clean up" those files; only make the changes each task names.

---

### Task 1: Read post and series metadata

Pure functions that gather frontmatter and order each series' parts. No files are written in this task.

**Files:**
- Create: `scripts/sync_series.py`
- Create: `tests/test_series.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `SeriesError(Exception)` — raised for every author-facing misconfiguration.
  - `read_frontmatter(path: Path) -> dict` — YAML frontmatter of a file, `{}` if it has none.
  - `collect_posts(posts_dir: Path) -> list[dict]` — one dict per post directory, keys `slug` (directory name), `title` (str), `date` (`datetime.date` or `None`), `series` (str or `None`), `source` (str, e.g. `index.qmd`).
  - `load_series(series_dir: Path) -> dict[str, dict]` — slug → `{"title": str}`.
  - `group_parts(posts: list[dict], series_meta: dict) -> dict[str, list[dict]]` — series slug → parts in order.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_series.py`:

```python
import datetime
from pathlib import Path

import pytest

from scripts.sync_series import (
    SeriesError,
    collect_posts,
    group_parts,
    load_series,
    read_frontmatter,
)


def write(path, text):
    """Create a file and every parent directory it needs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def tree(tmp_path):
    """A miniature blog: two series, three posts, one standalone post.

    Dates are deliberately out of directory order for `late`, so a test that
    passes only because the parts happen to be alphabetical will fail here.
    """
    posts = tmp_path / "blog" / "posts"
    series = tmp_path / "blog" / "series"
    write(posts / "2026-08-18-a" / "index.md",
          '---\ntitle: "First"\ndate: 2026-08-18\nseries: arithmetic\n---\n\nbody\n')
    write(posts / "2026-08-20-late" / "index.md",
          '---\ntitle: "Third"\ndate: 2026-09-05\nseries: arithmetic\n---\n\nbody\n')
    write(posts / "2026-08-19-b" / "index.md",
          '---\ntitle: "Second"\ndate: 2026-08-19\nseries: arithmetic\n---\n\nbody\n')
    write(posts / "2026-08-21-solo" / "index.md",
          '---\ntitle: "Standalone"\ndate: 2026-08-21\n---\n\nbody\n')
    write(series / "arithmetic" / "index.md",
          '---\ntitle: "A Course in Arithmetic"\n---\n\nblurb\n')
    return tmp_path


def test_read_frontmatter_parses_yaml_block(tmp_path):
    path = write(tmp_path / "index.md", '---\ntitle: "T"\ndate: 2026-08-18\n---\n\nbody\n')
    data = read_frontmatter(path)
    assert data["title"] == "T"
    assert data["date"] == datetime.date(2026, 8, 18)


def test_read_frontmatter_returns_empty_dict_without_a_block(tmp_path):
    path = write(tmp_path / "index.md", "no frontmatter here\n")
    assert read_frontmatter(path) == {}


def test_collect_posts_records_series_and_source_filename(tree):
    posts = {p["slug"]: p for p in collect_posts(tree / "blog" / "posts")}
    assert posts["2026-08-18-a"]["series"] == "arithmetic"
    assert posts["2026-08-18-a"]["source"] == "index.md"
    assert posts["2026-08-21-solo"]["series"] is None


def test_group_parts_orders_by_date_not_directory_name(tree):
    parts = group_parts(collect_posts(tree / "blog" / "posts"),
                        load_series(tree / "blog" / "series"))
    assert [p["title"] for p in parts["arithmetic"]] == ["First", "Second", "Third"]


def test_group_parts_excludes_standalone_posts(tree):
    parts = group_parts(collect_posts(tree / "blog" / "posts"),
                        load_series(tree / "blog" / "series"))
    assert all(p["slug"] != "2026-08-21-solo" for p in parts["arithmetic"])


def test_unknown_series_is_a_hard_error(tree):
    write(tree / "blog" / "posts" / "2026-08-22-typo" / "index.md",
          '---\ntitle: "Typo"\ndate: 2026-08-22\nseries: arithmatic\n---\n\nbody\n')
    with pytest.raises(SeriesError, match="arithmatic"):
        group_parts(collect_posts(tree / "blog" / "posts"),
                    load_series(tree / "blog" / "series"))


def test_series_post_without_a_date_is_an_error(tree):
    write(tree / "blog" / "posts" / "2026-08-23-undated" / "index.md",
          '---\ntitle: "Undated"\nseries: arithmetic\n---\n\nbody\n')
    with pytest.raises(SeriesError, match="date"):
        group_parts(collect_posts(tree / "blog" / "posts"),
                    load_series(tree / "blog" / "series"))


def test_empty_series_appears_with_no_parts(tree):
    write(tree / "blog" / "series" / "standard-model" / "index.md",
          '---\ntitle: "The Standard Model"\n---\n\nblurb\n')
    parts = group_parts(collect_posts(tree / "blog" / "posts"),
                        load_series(tree / "blog" / "series"))
    assert parts["standard-model"] == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_series.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.sync_series'`

- [ ] **Step 3: Write the implementation**

Create `scripts/sync_series.py`. Match the docstring-heavy style of `scripts/sync_notes.py`: explain *why* a check exists, not what it does.

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_series.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commit**

```bash
git add scripts/sync_series.py tests/test_series.py
git commit -m "feat: read blog series metadata and order parts by date"
```

---

### Task 2: Generate the banner and nav partials

Turns the ordered parts into the two files each post includes, and wires the script into `quarto render`.

**Files:**
- Modify: `scripts/sync_series.py` (append to it)
- Modify: `tests/test_series.py` (append to it)
- Modify: `_quarto.yml` (the `project:` block at the top)
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `SeriesError`, `collect_posts`, `load_series`, `group_parts` from Task 1.
- Produces:
  - `banner_markdown(part_number: int, series_slug: str, series_title: str) -> str`
  - `nav_markdown(parts: list[dict], index: int, series_slug: str) -> str`
  - `write_partials(grouped: dict, series_meta: dict, posts: list[dict]) -> list[str]` — writes the partials, deletes stale ones, returns human-readable lines describing what changed.
  - `main(argv=None) -> int` — 0 on success, 1 on `SeriesError`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_series.py`:

```python
from scripts.sync_series import (
    banner_markdown,
    main,
    nav_markdown,
    write_partials,
)


def test_banner_names_the_part_and_links_to_the_series(tmp_path):
    text = banner_markdown(3, "arithmetic", "A Course in Arithmetic")
    assert "Part 3 of" in text
    assert "[A Course in Arithmetic](/blog/series/arithmetic/index.md)" in text
    assert ".series-banner" in text


def test_nav_on_a_middle_part_links_both_ways(tree):
    parts = group_parts(collect_posts(tree / "blog" / "posts"),
                        load_series(tree / "blog" / "series"))["arithmetic"]
    text = nav_markdown(parts, 1, "arithmetic")
    assert "Part 1: First" in text
    assert "Part 3: Third" in text
    assert "[All parts](/blog/series/arithmetic/index.md)" in text


def test_nav_omits_prev_on_the_first_part(tree):
    parts = group_parts(collect_posts(tree / "blog" / "posts"),
                        load_series(tree / "blog" / "series"))["arithmetic"]
    text = nav_markdown(parts, 0, "arithmetic")
    assert "Part 1:" not in text
    assert "Part 2: Second" in text


def test_nav_omits_next_on_the_last_part(tree):
    parts = group_parts(collect_posts(tree / "blog" / "posts"),
                        load_series(tree / "blog" / "series"))["arithmetic"]
    text = nav_markdown(parts, 2, "arithmetic")
    assert "Part 2: Second" in text
    assert "Part 4" not in text
    assert "Third" not in text.split("[All parts]")[1]


def test_nav_links_to_the_actual_source_filename(tmp_path):
    parts = [
        {"slug": "p1", "title": "One", "source": "index.md"},
        {"slug": "p2", "title": "Two", "source": "index.qmd"},
    ]
    text = nav_markdown(parts, 0, "s")
    assert "/blog/posts/p2/index.qmd" in text


def test_write_partials_creates_both_files(tree):
    posts = collect_posts(tree / "blog" / "posts")
    meta = load_series(tree / "blog" / "series")
    write_partials(group_parts(posts, meta), meta, posts)
    post_dir = tree / "blog" / "posts" / "2026-08-19-b"
    assert (post_dir / "_series-banner.md").is_file()
    assert (post_dir / "_series-nav.md").is_file()
    assert "Part 2 of" in (post_dir / "_series-banner.md").read_text(encoding="utf-8")


def test_write_partials_removes_stale_files_from_a_post_that_left_its_series(tree):
    """A post dropping its `series:` key must lose its partials, or the
    include directives it still carries would render last render's
    navigation forever -- and being gitignored, nothing else would notice.
    """
    solo = tree / "blog" / "posts" / "2026-08-21-solo"
    (solo / "_series-nav.md").write_text("stale\n", encoding="utf-8")
    posts = collect_posts(tree / "blog" / "posts")
    meta = load_series(tree / "blog" / "series")
    write_partials(group_parts(posts, meta), meta, posts)
    assert not (solo / "_series-nav.md").exists()


def test_write_partials_is_idempotent(tree):
    posts = collect_posts(tree / "blog" / "posts")
    meta = load_series(tree / "blog" / "series")
    write_partials(group_parts(posts, meta), meta, posts)
    first = (tree / "blog" / "posts" / "2026-08-19-b" / "_series-nav.md").read_text(
        encoding="utf-8")
    write_partials(group_parts(posts, meta), meta, posts)
    second = (tree / "blog" / "posts" / "2026-08-19-b" / "_series-nav.md").read_text(
        encoding="utf-8")
    assert first == second


def test_main_exits_non_zero_on_an_unknown_series(tree, monkeypatch, capsys):
    write(tree / "blog" / "posts" / "2026-08-22-typo" / "index.md",
          '---\ntitle: "Typo"\ndate: 2026-08-22\nseries: nope\n---\n\nbody\n')
    monkeypatch.setattr("scripts.sync_series.POSTS_DIR", tree / "blog" / "posts")
    monkeypatch.setattr("scripts.sync_series.SERIES_DIR", tree / "blog" / "series")
    assert main([]) == 1
    assert "nope" in capsys.readouterr().err


def test_main_exits_zero_on_a_healthy_tree(tree, monkeypatch):
    monkeypatch.setattr("scripts.sync_series.POSTS_DIR", tree / "blog" / "posts")
    monkeypatch.setattr("scripts.sync_series.SERIES_DIR", tree / "blog" / "series")
    assert main([]) == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_series.py -v`
Expected: FAIL — `ImportError: cannot import name 'banner_markdown'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/sync_series.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_series.py -v`
Expected: PASS, 18 tests

- [ ] **Step 5: Register the pre-render script**

In `_quarto.yml`, add `pre-render` to the existing `project:` block, with a comment explaining why it is there:

```yaml
project:
  type: website
  output-dir: _site
  # Regenerates each series post's banner and prev/next partials before
  # every render, so navigation cannot go stale. The partials are
  # gitignored: they are derived entirely from post front matter, and a
  # committed copy would just be a second source of truth to drift.
  pre-render: scripts/sync_series.py
  resources:
```

- [ ] **Step 6: Ignore the generated partials**

Append to `.gitignore`, below the existing `blog/posts/**/index_files/` entry:

```
# Series banner and prev/next navigation, regenerated from post front
# matter by scripts/sync_series.py on every render.
blog/posts/**/_series-*.md
```

- [ ] **Step 7: Verify the pre-render hook actually runs**

Run: `cd "$WEBSITE" && quarto render 2>&1 | grep sync_series`
Expected: no error output, and the render completes. With no series declared yet, the script has nothing to write and prints nothing — an empty grep result with exit status 0 from `quarto render` is a pass. Confirm the render itself succeeded:

Run: `cd "$WEBSITE" && quarto render >/dev/null && echo RENDER_OK`
Expected: `RENDER_OK`

- [ ] **Step 8: Commit**

```bash
git add scripts/sync_series.py tests/test_series.py _quarto.yml .gitignore
git commit -m "feat: generate series banner and prev/next partials at pre-render"
```

---

### Task 3: Series landing pages and post migration

Makes the feature visible: two real series, three real posts, verified against rendered HTML.

**Files:**
- Create: `blog/series/arithmetic/index.md`
- Create: `blog/series/standard-model/index.md`
- Modify: `blog/posts/2026-08-18-arithmetic/index.md`
- Modify: `blog/posts/2026-08-17-standard-model-history/index.md`
- Modify: `blog/posts/2026-08-18-uv-catastrophe/index.qmd`
- Modify: `tests/test_site.py` (append)

**Interfaces:**
- Consumes: the partials written by Task 2.
- Produces: `blog/series/<slug>/index.md` pages that later tasks link to and list.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_site.py`. These render the real site via the existing session-scoped `site` fixture.

```python
# Every post that declares a series, and the series it belongs to. Kept
# explicit rather than derived from the front matter, so a test failure
# means the site is wrong -- a test that reads the same source the
# generator reads would agree with any mistake the generator made.
SERIES_POSTS = {
    "2026-08-17-standard-model-history": ("standard-model", 1),
    "2026-08-18-uv-catastrophe": ("standard-model", 2),
    "2026-08-18-arithmetic": ("arithmetic", 1),
}


def _post_html(site, slug):
    return read_html(site, f"blog/posts/{slug}/index.html")


@pytest.mark.parametrize("slug,expected", sorted(SERIES_POSTS.items()))
def test_series_post_shows_its_banner(site, slug, expected):
    series_slug, part = expected
    banner = extract_element(_post_html(site, slug), "series-banner")
    assert banner, f"{slug} has no .series-banner block"
    assert f"Part {part} of" in banner
    assert f"series/{series_slug}/" in banner


@pytest.mark.parametrize("slug", sorted(SERIES_POSTS))
def test_series_nav_links_resolve(site, slug):
    """Every link in the nav must point at a file that exists in _site.

    This is also what catches the source-path convention failing: if
    Quarto stops rewriting `/blog/.../index.md` to a relative `.html`, the
    hrefs here still say `.md` and resolve to nothing.
    """
    nav = extract_element(_post_html(site, slug), "series-nav")
    assert nav, f"{slug} has no .series-nav block"
    hrefs = re.findall(r'href="([^"]+)"', nav)
    assert hrefs, f"{slug} nav contains no links"
    page_dir = (site / "blog" / "posts" / slug)
    for href in hrefs:
        target = (page_dir / href).resolve()
        if target.is_dir():
            target = target / "index.html"
        assert target.is_file(), f"{slug} nav links to {href}, which does not exist"


def test_first_part_has_no_previous_link(site):
    nav = extract_element(_post_html(site, "2026-08-17-standard-model-history"),
                          "series-nav")
    assert "←" not in nav
    assert "→" in nav


def test_last_part_has_no_next_link(site):
    nav = extract_element(_post_html(site, "2026-08-18-uv-catastrophe"), "series-nav")
    assert "→" not in nav
    assert "←" in nav


def test_frozen_qmd_post_still_gets_current_navigation(site):
    """The .qmd post's execution is cached in _freeze/. That cache holds
    computed output; this proves it does not also serve stale navigation,
    which would leave the post's part number frozen at whatever it was the
    last time its Python ran.
    """
    banner = extract_element(_post_html(site, "2026-08-18-uv-catastrophe"),
                             "series-banner")
    assert "Part 2 of" in banner


@pytest.mark.parametrize("series_slug", ["arithmetic", "standard-model"])
def test_series_page_lists_exactly_its_own_posts(site, series_slug):
    """The listing must match the posts tagged with this series -- no more,
    no fewer. A filter that silently matches nothing, or everything, still
    renders a perfectly valid page, so only an exact comparison catches it.
    """
    html_text = read_html(site, f"blog/series/{series_slug}/index.html")
    linked = set(re.findall(r'href="[^"]*posts/([^/"]+)/', html_text))
    expected = {slug for slug, (series, _) in SERIES_POSTS.items()
                if series == series_slug}
    assert linked == expected
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_site.py -k series -v`
Expected: FAIL — the `.series-banner` blocks do not exist and `blog/series/…/index.html` is missing.

- [ ] **Step 3: Create the two series landing pages**

Create `blog/series/arithmetic/index.md`:

```markdown
---
title: "A Course in Arithmetic"
description: "Working through Serre's book with a friend, one chapter at a time."
# Drop a figure in this directory and uncomment to give the series card an
# image. Without it the card is text-only: theme.scss hides Quarto's empty
# grey placeholder rather than reserving dead space.
# image: thumb.png
listing:
  contents: ../../posts
  include:
    series: arithmetic
  sort: "date asc"
  type: grid
  fields: [image, date, title, description]
  feed: false
---

::: {.accent-rule}
:::

I'm reading Jean-Pierre Serre's *A Course in Arithmetic* with a friend, and
writing up what I learn as I go. The posts assume a little abstract algebra
but try to build up the rest from scratch.
```

Create `blog/series/standard-model/index.md`:

```markdown
---
title: "The History of the Standard Model"
description: "A deep pass through the timeline behind my Lectures on Tap talk."
# image: thumb.png
listing:
  contents: ../../posts
  include:
    series: standard-model
  sort: "date asc"
  type: grid
  fields: [image, date, title, description]
  feed: false
---

::: {.accent-rule}
:::

The timeline behind my Lectures on Tap talk, followed much further than
forty-five minutes allowed — one episode of the story at a time.
```

- [ ] **Step 4: Migrate the three existing posts**

In each post, add the `series:` key as the last line of the frontmatter, a `{{< include _series-banner.md >}}` line immediately after the closing `---` (separated by a blank line), and a `{{< include _series-nav.md >}}` line at the very end of the file.

`blog/posts/2026-08-18-arithmetic/index.md` — add `series: arithmetic`.
`blog/posts/2026-08-17-standard-model-history/index.md` — add `series: standard-model`.
`blog/posts/2026-08-18-uv-catastrophe/index.qmd` — add `series: standard-model`.

For example, the head of `blog/posts/2026-08-18-arithmetic/index.md` becomes:

```markdown
---
title: "A Course in Arithmetic: Prerequesites"
date: 2026-08-18
categories: [math, arithmetic, technical, book-club]
series: arithmetic
---

{{< include _series-banner.md >}}

This is my first book club post! I'm reading through Jean-Pierre Serre's
```

and its final line becomes:

```markdown
{{< include _series-nav.md >}}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_site.py -k series -v`
Expected: PASS, 10 tests

If `test_series_page_lists_exactly_its_own_posts` fails with an empty `linked` set, Quarto's listing `include:` filter is not matching the custom `series` field. Fallback: replace the `contents:` and `include:` keys on both landing pages with an explicit list of post paths, e.g.

```yaml
listing:
  contents:
    - ../../posts/2026-08-17-standard-model-history/index.md
    - ../../posts/2026-08-18-uv-catastrophe/index.qmd
```

and note in the landing page comment that the list is maintained by hand. Re-run the test.

- [ ] **Step 6: Run the whole suite for regressions**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest -v`
Expected: PASS, all tests

- [ ] **Step 7: Commit**

```bash
git add blog/series tests/test_site.py blog/posts
git commit -m "feat: add series landing pages and put existing posts in series"
```

---

### Task 4: Series row on the Blog page

**Files:**
- Modify: `blog/index.md`
- Modify: `tests/test_site.py` (append)

**Interfaces:**
- Consumes: `blog/series/<slug>/index.md` from Task 3.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_site.py`:

```python
def test_blog_page_shows_one_card_per_series(site):
    html_text = read_html(site, "blog/index.html")
    row = extract_element(html_text, "series", by="id")
    assert row, "blog page has no #series listing block"
    linked = set(re.findall(r'href="[^"]*series/([^/"]+)/', row))
    assert linked == {"arithmetic", "standard-model"}


def test_blog_page_still_lists_every_post(site):
    """Series parts stay in the main grid. The Series row is an index, not
    a replacement -- a new part must still surface on the blog front page
    when it is published.
    """
    posts_grid = extract_element(read_html(site, "blog/index.html"), "posts", by="id")
    linked = set(re.findall(r'href="[^"]*posts/([^/"]+)/', posts_grid))
    assert set(SERIES_POSTS) <= linked
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_site.py -k blog_page -v`
Expected: FAIL — no `#series` element on the page.

- [ ] **Step 3: Add the Series listing to `blog/index.md`**

Change the single `listing:` mapping in the frontmatter into a list of two listings, keeping the existing post listing's options exactly as they are:

```yaml
listing:
  # The Series row: one card per directory under blog/series/. Each card's
  # title, blurb and image come from that series' landing page front
  # matter, so a series is described in exactly one place.
  - id: series
    contents: series/*/index.md
    type: grid
    fields: [image, title, description]
    feed: false
  - id: posts
    contents: posts
    type: grid
    sort: "date desc"
    categories: true
    # Posts that have an image (e.g. a figure from an executed notebook) show it.
    # Posts without one get a text-only card: theme.scss hides Quarto's empty
    # grey `.listing-item-img-placeholder` rather than reserving dead space.
    fields: [image, date, title, categories, description]
    feed: false
```

Then add the Series section to the body, above the existing `:::{#posts}` block:

```markdown
## Series

Multi-part writing, in order.

:::{#series}
:::

## All posts

:::{#posts}
:::
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_site.py -k blog_page -v`
Expected: PASS, 2 tests

- [ ] **Step 5: Commit**

```bash
git add blog/index.md tests/test_site.py
git commit -m "feat: show a series row on the blog page"
```

---

### Task 5: Style the banner and navigation

**Files:**
- Modify: `theme.scss` (append, after the `.quarto-grid-item` block)
- Modify: `tests/test_site.py` (append)

**Interfaces:**
- Consumes: the `.series-banner` and `.series-nav` classes emitted in Task 2.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_site.py`:

```python
def _all_css(site):
    """Every stylesheet in the built site, concatenated.

    theme.scss is compiled into a hashed bootstrap bundle whose filename
    changes whenever the theme does, so a test cannot name the file it
    needs to read.
    """
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore")
                     for path in sorted(site.rglob("*.css")))


def test_series_classes_are_styled(site):
    """An unstyled .series-nav still renders -- as an undifferentiated line
    of links with no rule above it -- so nothing else in the suite would
    notice the styles being dropped from theme.scss.
    """
    combined = _all_css(site)
    assert ".series-banner" in combined
    assert ".series-nav" in combined
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_site.py -k series_classes -v`
Expected: FAIL — neither class appears in the compiled CSS.

- [ ] **Step 3: Add the styles**

Append to `theme.scss`:

```scss
// Series banner: the "Part 3 of ..." line above a post's prose. Small and
// quiet -- it is orientation, not content, and must not compete with the
// post title directly above it.
.series-banner {
  font-size: 0.85rem;
  color: rgba(0, 0, 0, 0.6);
  margin-bottom: 1.5rem;
}

// Series navigation: the prev / index / next footer. The rule above it
// separates navigation from prose; without one the links read as a final
// sentence of the post.
.series-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
  justify-content: space-between;
  border-top: 1px solid $rule;
  margin-top: 3rem;
  padding-top: 1rem;
  font-size: 0.9rem;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_site.py -k series_classes -v`
Expected: PASS

- [ ] **Step 5: Look at the result**

Run: `cd "$WEBSITE" && quarto preview` and open `blog/posts/2026-08-18-arithmetic/`. Confirm the banner sits above the prose and the nav sits below a hairline rule with prev on the left and next on the right. Stop the preview with Ctrl-C.

- [ ] **Step 6: Commit**

```bash
git add theme.scss tests/test_site.py
git commit -m "style: series banner and prev/next navigation"
```

---

### Task 6: CI and documentation

**Files:**
- Modify: `.github/workflows/publish.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: `scripts/sync_series.py` from Task 2.
- Produces: nothing.

- [ ] **Step 1: Add Python to the deploy workflow**

The workflow currently has a comment stating no Python is installed on purpose. That comment becomes false once a Python pre-render script exists, so replace both the comment and the step. Insert before the "Render the site" step:

```yaml
      # Python is installed for scripts/sync_series.py, which Quarto runs as
      # a pre-render script to rebuild each series post's navigation.
      #
      # Jupyter is deliberately NOT installed. Notebook outputs still come
      # from the committed _freeze/ cache, and without Jupyter here a .qmd
      # that was changed and committed without being re-rendered locally
      # fails the build loudly instead of silently executing in CI.
      - name: Install Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install the pre-render script's dependencies
        run: pip install pyyaml
```

Delete the old "No Python is installed here on purpose…" comment block above the "Render the site" step, leaving that step itself unchanged.

- [ ] **Step 2: Verify the workflow file parses**

Run: `cd "$WEBSITE" && .venv/bin/python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/publish.yml')); print('YAML_OK')"`
Expected: `YAML_OK`

- [ ] **Step 3: Document the feature**

Add a `## Blog series` section to `README.md`, after the existing `## Adding content` section:

````markdown
## Blog series

A series is a directory under `blog/series/`. Its `index.md` is written by
hand and is never overwritten by any script — taking a series down is a
`git rm`, exactly like a note.

**Starting one:** create `blog/series/<slug>/index.md` with a title,
description, and a listing filtered on the slug:

```yaml
---
title: "A Course in Arithmetic"
description: "One-line blurb, shown on the series card."
image: thumb.png        # optional; drop the figure in the same directory
listing:
  contents: ../../posts
  include:
    series: arithmetic
  sort: "date asc"
  type: grid
  fields: [image, date, title, description]
  feed: false
---
```

Everything below the front matter is yours. The card on the Blog page takes
its title, blurb, and figure from here, so a series is described in exactly
one place.

**Adding a part:** in the post's front matter add `series: <slug>`, then put

```
{{< include _series-banner.md >}}
```

directly below the front matter and

```
{{< include _series-nav.md >}}
```

at the end of the file. Nothing else. Part order is publication date
ascending, so the new post becomes the next part automatically, and
back-dating one inserts it mid-series and renumbers the rest.

Both included files are generated by `scripts/sync_series.py`, which Quarto
runs before every render. They are gitignored — never edit them, and never
commit them. Naming a series with no landing page fails the render with a
message naming the post.
````

- [ ] **Step 4: Run the whole suite**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest -v`
Expected: PASS, all tests

- [ ] **Step 5: Commit**

```bash
git add .github/workflows README.md
git commit -m "ci: install python for the series pre-render script; document series"
```

---

### Task 7: Keep the Series row to exactly one row

Quarto renders a grid listing as `#listing-series > .list.grid > .g-col-1`,
where `.list.grid` is a CSS grid that wraps onto further rows as cards
accumulate — which would push the post grid down the page as series build up.
This overrides it to a single horizontal strip that scrolls, with arrows that
appear only when it actually overflows.

Depends on Task 4 (the Series row must exist). Nothing depends on this task.

**Files:**
- Create: `assets/series-row.html`
- Modify: `theme.scss` (append)
- Modify: `blog/index.md` (frontmatter)
- Modify: `tests/test_site.py` (append)
- Modify: `README.md` (the Blog series section from Task 6)

**Interfaces:**
- Consumes: the `#listing-series` element rendered by Task 4, and `_all_css(site)` from Task 5.
- Produces: nothing.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_site.py`:

```python
def test_series_row_never_wraps(site):
    """The Series row is an index above the real content. If it wrapped, it
    would grow downward and push the post grid off the screen as series
    accumulate -- which is exactly what Quarto's grid listing does by
    default, so this override has to be asserted rather than assumed.
    """
    rules = re.findall(r"#listing-series[^{}]*\{[^{}]*\}", _all_css(site))
    assert rules, "no #listing-series rule in the compiled CSS"
    joined = " ".join(rules)
    assert "nowrap" in joined
    assert "overflow-x" in joined


def test_scroll_arrows_are_styled(site):
    assert ".series-scroll" in _all_css(site)


def test_scroller_script_is_scoped_to_the_blog_page(site):
    """The script belongs to the one page with a Series row. Loading it
    site-wide would be harmless -- it no-ops without #listing-series -- but
    page-level inclusion is the claim being made here, and a site-wide
    include would quietly ship dead code on every page.
    """
    assert "seriesScroller" in read_html(site, "blog/index.html")
    assert "seriesScroller" not in _post_html(site, "2026-08-18-arithmetic")


def test_blog_page_keeps_project_format_settings(site):
    """blog/index.md now sets `format: html: include-after-body`. Quarto is
    expected to merge that with the project-level format block rather than
    replace it; if it replaced it, this one page would silently lose its
    theme and favicon while every other page kept them.
    """
    html_text = read_html(site, "blog/index.html")
    assert "favicon" in html_text
    assert re.search(r'<link[^>]+rel="stylesheet"', html_text), (
        "blog page has no stylesheet link -- project format settings were lost"
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_site.py -k "series_row or scroll or format_settings" -v`
Expected: FAIL — no `#listing-series` rule in the CSS and no script on the page. (`test_blog_page_keeps_project_format_settings` may already pass; that is fine, it is a regression guard for Step 4.)

- [ ] **Step 3: Create the scroller script**

Create `assets/series-row.html`:

```html
<script>
// Scroll arrows for the Series row on the blog page. That row is a single
// non-wrapping strip (see theme.scss) whose native scrollbar is hidden, so
// these buttons are how it gets moved.
//
// Inert unless #listing-series is on the page, so loading it anywhere else
// does nothing rather than throwing.
(function seriesScroller() {
  function init() {
    var listing = document.getElementById("listing-series");
    if (!listing) return;
    var strip = listing.querySelector(".list.grid");
    if (!strip) return;

    // Scrollable by keyboard, not only by clicking the arrows.
    strip.setAttribute("tabindex", "0");
    strip.setAttribute("role", "region");
    strip.setAttribute("aria-label", "Series");

    var buttons = {};
    ["left", "right"].forEach(function (side) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "series-scroll series-scroll-" + side;
      button.setAttribute("aria-label", "Scroll series " + side);
      button.innerHTML = side === "left" ? "&#8249;" : "&#8250;";
      button.addEventListener("click", function () {
        var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        strip.scrollBy({
          left: (side === "left" ? -1 : 1) * strip.clientWidth * 0.8,
          behavior: reduce ? "auto" : "smooth"
        });
      });
      listing.appendChild(button);
      buttons[side] = button;
    });

    function update() {
      // The 1px tolerance matters: fractional layout widths mean scrollLeft
      // rarely equals scrollWidth - clientWidth exactly, which would leave
      // the right arrow showing at the end of the strip forever.
      var maxScroll = strip.scrollWidth - strip.clientWidth;
      buttons.left.hidden = strip.scrollLeft <= 1;
      buttons.right.hidden = strip.scrollLeft >= maxScroll - 1;
    }

    strip.addEventListener("scroll", update);
    // The strip can start overflowing purely because the window narrowed,
    // so a scroll listener alone would leave the arrows in the wrong state.
    if (window.ResizeObserver) {
      new ResizeObserver(update).observe(strip);
    }
    window.addEventListener("resize", update);
    update();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
</script>
```

- [ ] **Step 4: Load it from the blog page only**

Add to the frontmatter of `blog/index.md`, below the `listing:` block:

```yaml
format:
  html:
    # Scroll arrows for the Series row. Page-level rather than site-wide:
    # this is the only page with a Series row. Quarto merges this with the
    # project-level format block, so the theme and favicon still apply --
    # test_blog_page_keeps_project_format_settings guards that.
    include-after-body: ../assets/series-row.html
```

- [ ] **Step 5: Add the styles**

Append to `theme.scss`:

```scss
// The Series row on the blog page is exactly one row, always. Quarto
// renders a grid listing as a CSS grid that wraps onto further rows as
// cards accumulate, which would push the post grid down the page as the
// number of series grows. This makes it a single strip that scrolls
// sideways instead; the arrows come from assets/series-row.html.
#listing-series {
  position: relative;

  .list.grid {
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    scroll-snap-type: x proximity;
    gap: 1rem;
    // The arrows are the affordance. A native horizontal scrollbar under
    // the cards is noise, and on macOS it is invisible until scrolled anyway.
    scrollbar-width: none;

    &::-webkit-scrollbar {
      display: none;
    }
  }

  // Quarto emits one .g-col-1 wrapper per card. Flex children shrink by
  // default, so without an explicit basis the cards would compress to fit
  // instead of overflowing -- and nothing would ever scroll.
  .g-col-1 {
    flex: 0 0 clamp(210px, 30%, 320px);
    scroll-snap-align: start;
  }
}

// Scroll arrows. Hidden by the script unless the strip actually overflows,
// so with only a couple of series the row is indistinguishable from a
// plain grid and no controls appear until they are needed.
.series-scroll {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: 1px solid $rule;
  border-radius: 50%;
  background: var(--bs-body-bg, #fff);
  color: $accent;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;

  &:focus-visible {
    box-shadow: 0 0 0 2px $accent-faded;
  }
}

.series-scroll-left {
  left: -0.75rem;
}

.series-scroll-right {
  right: -0.75rem;
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest tests/test_site.py -k "series_row or scroll or format_settings" -v`
Expected: PASS, 4 tests

- [ ] **Step 7: Verify overflow behaviour in a browser**

The feature is invisible with two series, so it must be checked against enough
cards to overflow. Create six throwaway series, look at the page, then delete
them — they are never committed.

```bash
cd "$WEBSITE"
for n in 1 2 3 4 5 6; do
  mkdir -p "blog/series/scratch-$n"
  printf -- '---\ntitle: "Scratch %s"\ndescription: "Throwaway card for checking the scroller."\n---\n\nscratch\n' "$n" > "blog/series/scratch-$n/index.md"
done
quarto preview
```

In the browser, on the blog page, confirm:

- the Series cards sit on **one** line, with the row scrolling sideways rather than wrapping;
- the right arrow is visible and the left arrow is not, until you scroll;
- clicking an arrow moves the strip and the arrows update at each end;
- narrowing the window makes the arrows appear on their own, without a reload;
- the post grid below is unaffected.

Then stop the preview and remove the scratch series:

```bash
rm -rf blog/series/scratch-*
```

Confirm they are gone before committing:

Run: `cd "$WEBSITE" && ls blog/series`
Expected: exactly `arithmetic` and `standard-model`

- [ ] **Step 8: Document it**

Append to the `## Blog series` section of `README.md`, after the "Adding a
part" paragraph:

```markdown
The Series row on the blog page is always exactly one row. Once there are
more cards than fit, it scrolls sideways and arrow buttons appear at its
ends; below that threshold it looks like an ordinary grid and no controls
are shown. The arrows come from `assets/series-row.html`, which
`blog/index.md` loads on its own — it is the only page that needs it.
```

- [ ] **Step 9: Run the whole suite**

Run: `cd "$WEBSITE" && .venv/bin/python -m pytest -v`
Expected: PASS, all tests

- [ ] **Step 10: Commit**

```bash
git add assets/series-row.html theme.scss blog/index.md tests/test_site.py README.md
git commit -m "feat: keep the series row to one scrollable row with arrows"
```

---

## Done when

- `pytest` passes in full.
- `quarto render` succeeds from a fresh `git clone`, which requires the
  `_series-*.md` partials to be **committed**. (This bullet originally said
  the opposite -- that the render must work with no partials present. That
  was written before the include-ordering constraint was discovered, and is
  exactly the thing Quarto cannot do.)
- The Blog page shows a Series row above the full post grid.
- The Series row occupies exactly one row at every window width, scrolling
  sideways with arrows once the cards overflow.
- Each series post shows its part number and links to its neighbours and its series page.

---

## Follow-ups

Not part of this plan; recorded here so they are not lost.

- [ ] **Give each series its own thumbnail.** Neither landing page sets
  `image:` yet -- the line is commented out pending artwork -- and the two
  cards consequently do not match. Arithmetic renders text-only, while
  Standard Model shows a figure Quarto scraped out of the rendered page:
  the residual-convergence plot belonging to the UV-catastrophe post's own
  listing card. Nothing is broken, but a plot from *inside* one part is
  standing in for the whole series, and it will change on its own if a post
  is added or re-dated ahead of that one. Fix by adding `thumb.png` to each
  directory under `blog/series/` and uncommenting `image:`, then pin each
  card to its own series' image with a test -- there is no point writing
  that test while the answer is "whatever Quarto found".
