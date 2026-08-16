import datetime

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
