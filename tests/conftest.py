import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

ORPHAN_FIXTURE_PDF = REPO_ROOT / "notes" / "pdf" / "orphan-fixture.pdf"
ORPHAN_FIXTURE_THUMB = REPO_ROOT / "notes" / "thumbs" / "orphan-fixture.png"

# A minimal, well-formed one-page PDF — just enough structure (catalog,
# pages tree, one page) that anything which actually opens the file (not
# just checks it exists) still sees a valid document.
_MINIMAL_PDF_BYTES = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj
xref
0 4
0000000000 65535 f
trailer<</Size 4/Root 1 0 R>>
startxref
0
%%EOF
"""


@pytest.fixture(scope="session")
def _orphan_fixture_pdf():
    """Create the ephemeral, deliberately-unreferenced PDF that
    test_pdf_is_copied_to_output needs to exercise the `resources:` key in
    _quarto.yml (see that test's docstring for why an orphan file, one that
    no stub page links to, is required to actually test that key).

    This used to be a file tracked in git. That shipped it straight to the
    live public site (notes/pdf/orphan-fixture.pdf returned HTTP 200 there
    even though it is only test scaffolding) and caused
    scripts/make_thumbs.py to generate a matching thumbnail on the user's
    first real run and print "skip orphan-fixture.png" on every run after
    that, forever. Creating and deleting it here means it exists only for
    the duration of the test session and never touches a real deploy.
    """
    ORPHAN_FIXTURE_PDF.parent.mkdir(parents=True, exist_ok=True)
    ORPHAN_FIXTURE_PDF.write_bytes(_MINIMAL_PDF_BYTES)
    try:
        yield ORPHAN_FIXTURE_PDF
    finally:
        ORPHAN_FIXTURE_PDF.unlink(missing_ok=True)
        ORPHAN_FIXTURE_THUMB.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def site(_orphan_fixture_pdf):
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


def assert_local_links_resolve(site, page_relpath, suffix=".pdf"):
    """Assert every same-origin link with the given suffix on a page resolves
    to a file that exists in the built output.

    Off-site links (http://, https://, //) are skipped — there is nothing
    local to check. Root-relative hrefs (leading "/") resolve against the
    site root; plain relative hrefs resolve against the page's OWN
    directory, not a hard-coded location — this is what lets the same
    helper validate a nested notes stub (e.g. notes/lattice-qcd/foo.html
    linking to ../pdf/foo.pdf) as well as cv/index.html.
    """
    html = read_html(site, page_relpath)
    links = re.findall(rf'href="([^"]*{re.escape(suffix)})"', html)
    assert links, f"no {suffix} link found on {page_relpath}"

    off_site_pattern = re.compile(r"^(?:https?://|//)")
    found_local_link = False
    page_dir = (site / page_relpath).parent

    for href in links:
        # Skip off-site links; there is nothing local to verify.
        if off_site_pattern.match(href):
            continue

        found_local_link = True

        # Resolve the href: root-relative paths go to the site root,
        # relative paths go to the page's own directory.
        if href.startswith("/"):
            target = (site / href.lstrip("/")).resolve()
        else:
            target = (page_dir / href).resolve()

        assert target.is_file(), (
            f"{page_relpath} links to {href}, which resolves to {target} — "
            "not found in built output"
        )

    assert found_local_link, (
        f"no local {suffix} links found on {page_relpath} (only off-site URLs)"
    )


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
            # A void element (e.g. <img>, <input>) never gets a matching
            # end tag, so it must be considered complete immediately —
            # otherwise it would be flagged below as "never closed".
            if tag in _VOID_ELEMENTS:
                self.capturing = False
                self.finished = True

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
