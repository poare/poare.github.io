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
    """Capture the raw HTML of the first element carrying a given class."""

    def __init__(self, wanted_class):
        super().__init__(convert_charrefs=False)
        self.wanted_class = wanted_class
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
        classes = (dict(attrs).get("class") or "").split()
        if self.wanted_class in classes:
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


def extract_element(html, class_name):
    """Return the raw HTML of the first element whose class list contains
    class_name, or "" if no such element exists.

    Tests use this to scope assertions to a specific region of the page.
    Matching against the whole document lets a test pass because the right
    markup exists *somewhere*, which is not the same as it existing in the
    right place.
    """
    parser = _SubtreeExtractor(class_name)
    parser.feed(html)
    return "".join(parser.chunks)
