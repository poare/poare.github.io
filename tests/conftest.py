import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def site():
    """Render the site once per test session and return the _site directory."""
    result = subprocess.run(
        ["quarto", "render"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"quarto render failed:\n{result.stdout}\n{result.stderr}")
    out = REPO_ROOT / "_site"
    assert out.is_dir(), "quarto render did not produce _site/"
    return out


def read_html(site, relpath):
    """Read a generated HTML file as text."""
    path = site / relpath
    assert path.is_file(), f"expected generated file {relpath} to exist"
    return path.read_text(encoding="utf-8")


from html.parser import HTMLParser

# HTML void elements never have a closing tag, so they must not affect depth
# tracking when we walk a subtree.
_VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class _SubtreeExtractor(HTMLParser):
    """Capture the raw HTML of the first element matching a given class or id."""

    def __init__(self, wanted_value, by="class"):
        super().__init__(convert_charrefs=False)
        self.wanted_value = wanted_value
        self.by = by
        self.depth = 0
        self.capturing = False
        self.finished = False
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        if self.finished:
            return
        if self.capturing:
            self.chunks.append(self.get_starttag_text())
            if tag not in _VOID_ELEMENTS:
                self.depth += 1
            return
        attrs_dict = dict(attrs)
        if self.by == "class":
            classes = (attrs_dict.get("class") or "").split()
            matched = self.wanted_value in classes
        else:
            matched = attrs_dict.get(self.by) == self.wanted_value
        if matched:
            self.capturing = True
            self.depth = 1
            self.chunks.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if self.capturing and not self.finished:
            self.chunks.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if not self.capturing or self.finished:
            return
        if tag in _VOID_ELEMENTS:
            return
        self.depth -= 1
        self.chunks.append(f"</{tag}>")
        if self.depth == 0:
            self.capturing = False
            self.finished = True

    def handle_data(self, data):
        if self.capturing and not self.finished:
            self.chunks.append(data)


def extract_element(html, value, by="class"):
    """Return the raw HTML of the first element matching `value`, or "" if
    no such element exists.

    By default matches an element whose class list contains `value`. Pass
    by="id" to match on an exact id attribute instead — useful when the
    class you'd otherwise key on is itself part of what a test is trying to
    prove exists (e.g. asserting a wrapper div's class was applied), since
    an id anchor from a heading is present regardless of that outcome.

    Tests use this to scope assertions to a specific region of the page.
    Matching against the whole document lets a test pass because the right
    markup exists *somewhere*, which is not the same as it existing in the
    right place.
    """
    parser = _SubtreeExtractor(value, by=by)
    parser.feed(html)
    if parser.capturing and not parser.finished:
        raise AssertionError(
            f"extract_element: found an element with {by} {value!r} but "
            "its markup never closed (depth never returned to zero) before the "
            "input ended. The captured fragment would have been silently "
            "widened to include unrelated trailing content. Fix the unclosed "
            "tag in the source HTML rather than trusting this fragment."
        )
    return "".join(parser.chunks)
