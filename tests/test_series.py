import datetime

import pytest

from scripts.sync_series import (
    SeriesError,
    banner_markdown,
    collect_posts,
    group_parts,
    load_series,
    main,
    nav_markdown,
    read_frontmatter,
    write_partials,
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


def arithmetic_parts(tree):
    """The ordered parts of the fixture tree's only populated series."""
    return group_parts(collect_posts(tree / "blog" / "posts"),
                       load_series(tree / "blog" / "series"))["arithmetic"]


def test_banner_names_the_part_and_links_to_the_series():
    text = banner_markdown(3, "arithmetic", "A Course in Arithmetic")
    assert "Part 3 of" in text
    assert "[A Course in Arithmetic](/blog/series/arithmetic/index.md)" in text
    assert ".series-banner" in text


def test_nav_on_a_middle_part_links_both_ways(tree):
    text = nav_markdown(arithmetic_parts(tree), 1, "arithmetic")
    assert "Part 1: First" in text
    assert "Part 3: Third" in text
    assert "[All parts](/blog/series/arithmetic/index.md)" in text


def test_nav_omits_prev_on_the_first_part(tree):
    text = nav_markdown(arithmetic_parts(tree), 0, "arithmetic")
    assert "Part 1:" not in text
    assert "Part 2: Second" in text


def test_nav_omits_next_on_the_last_part(tree):
    text = nav_markdown(arithmetic_parts(tree), 2, "arithmetic")
    assert "Part 2: Second" in text
    assert "Part 4" not in text
    assert "Third" not in text.split("[All parts]")[1]


def test_nav_links_to_the_actual_source_filename():
    """A .qmd post is served from index.html like any other, but the link
    has to name the source file that exists -- Quarto resolves it against
    the source tree, and a link to a nonexistent index.md is a build error.
    """
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
    navigation forever.
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
    nav = tree / "blog" / "posts" / "2026-08-19-b" / "_series-nav.md"
    write_partials(group_parts(posts, meta), meta, posts)
    first = nav.read_text(encoding="utf-8")
    write_partials(group_parts(posts, meta), meta, posts)
    assert nav.read_text(encoding="utf-8") == first


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


def test_series_partials_are_up_to_date():
    """The committed partials must match what the generator would write now.

    They have to be committed rather than generated at build time: Quarto
    expands {{< include >}} while scanning the project, before pre-render
    scripts run, so a partial that does not already exist on disk fails the
    render outright. Committing them buys a working fresh clone at the cost
    of a file that can fall out of date -- adding a post shifts the part
    numbers of everything after it, and nothing else in the suite would
    notice the neighbouring posts still claiming the old ones.

    So this is the guard that makes the manual step safe: it recomputes
    every partial in memory (writing nothing) and compares. If it fails,
    run `python scripts/sync_series.py` and commit the result.
    """
    from scripts.sync_series import (
        BANNER_NAME,
        NAV_NAME,
        POSTS_DIR,
        SERIES_DIR,
    )

    posts = collect_posts(POSTS_DIR)
    series_meta = load_series(SERIES_DIR)
    grouped = group_parts(posts, series_meta)

    in_a_series = set()
    for series_slug, parts in grouped.items():
        for index, post in enumerate(parts):
            in_a_series.add(post["slug"])
            directory = post["path"].parent
            expected = {
                BANNER_NAME: banner_markdown(
                    index + 1, series_slug, series_meta[series_slug]["title"]
                ),
                NAV_NAME: nav_markdown(parts, index, series_slug),
            }
            for name, want in expected.items():
                path = directory / name
                assert path.is_file(), (
                    f"{post['slug']}/{name} is missing -- "
                    "run `python scripts/sync_series.py` and commit the result"
                )
                assert path.read_text(encoding="utf-8") == want, (
                    f"{post['slug']}/{name} is out of date -- "
                    "run `python scripts/sync_series.py` and commit the result"
                )

    for post in posts:
        if post["slug"] in in_a_series:
            continue
        for name in (BANNER_NAME, NAV_NAME):
            stale = post["path"].parent / name
            assert not stale.is_file(), (
                f"{post['slug']} is not in a series but still has {name} -- "
                "run `python scripts/sync_series.py` and commit the result"
            )
