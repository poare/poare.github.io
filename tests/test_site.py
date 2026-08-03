import html
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import assert_local_links_resolve, extract_element, read_html, REPO_ROOT


def test_homepage_is_generated(site):
    html = read_html(site, "index.html")
    assert "Patrick Oare" in html


FONT_FACES = ["cmunrm", "cmunbx", "cmunti", "cmunbi", "cmuntt"]
MAX_FONT_BYTES = 150 * 1024


def test_fonts_are_subsetted_woff2():
    for face in FONT_FACES:
        path = REPO_ROOT / "assets" / "fonts" / f"{face}.woff2"
        assert path.is_file(), f"missing subsetted font {face}.woff2"
        size = path.stat().st_size
        assert size < MAX_FONT_BYTES, (
            f"{face}.woff2 is {size / 1024:.0f} KB, over the 150 KB budget"
        )


def test_no_raw_ttf_committed():
    stray = list((REPO_ROOT / "assets" / "fonts").glob("*.ttf"))
    assert stray == [], f"unsubsetted TTFs must not be committed: {stray}"


def test_tracked_qmd_files_execute_code():
    """README states the convention: use `.md` for prose, `.qmd` only for
    pages that execute code (Obsidian and other plain-markdown editors don't
    index `.qmd`). Nothing previously enforced that split — a `.qmd` saved
    with a heading and some prose but no code cell would silently violate
    the convention and only cost the next editor Obsidian's indexing, a
    failure mode with no obvious symptom. This checks every git-tracked
    `.qmd` for at least one executable code fence (```` ```{...} ````).
    """
    result = subprocess.run(
        ["git", "ls-files", "*.qmd"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"git ls-files *.qmd failed:\n{result.stderr}"
    qmd_files = [line for line in result.stdout.splitlines() if line]
    assert qmd_files, "no .qmd files are tracked -- nothing to check"
    for relpath in qmd_files:
        text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
        assert "```{" in text, (
            f"{relpath} has a .qmd extension but contains no executable "
            "code fence ('```{...}') -- use .md instead if it is plain prose"
        )


def compiled_css(site):
    """Concatenate every generated stylesheet — Quarto's output path varies."""
    return "\n".join(
        p.read_text(encoding="utf-8")
        for p in site.rglob("*.css")
    )


def test_accent_colour_reaches_compiled_css(site):
    css = compiled_css(site).lower()
    assert "#750014" in css, "MIT red is missing from the compiled stylesheet"


def test_base_font_size_reaches_compiled_css(site):
    """theme.scss deliberately sets an 18px (not Bootstrap's default 16px)
    root font size — see the comment next to $font-size-root there: CMU's
    strokes are drawn for print and read too thin at 16px on screen.
    Nothing previously asserted on the compiled value, so silently editing
    theme.scss back down to 16px passed every test in the suite.
    """
    css = compiled_css(site)
    assert "--bs-root-font-size: 18px" in css, (
        "compiled CSS does not set the 18px root font size from theme.scss"
    )


def test_fonts_are_referenced_by_css(site):
    css = compiled_css(site)
    assert "cmunrm.woff2" in css, "body font is not referenced in the CSS"
    assert "@font-face" in css


def test_nav_underline_spec(site):
    css = compiled_css(site).replace(" ", "")
    assert "text-underline-offset:5px" in css
    assert "text-decoration-thickness:1px" in css
    assert "text-decoration-skip-ink:none" in css


def test_we_did_not_write_a_dark_theme():
    """Dark mode is out of scope for version one.

    This asserts against our own SCSS rather than the compiled output, because
    Bootstrap ships its own prefers-color-scheme rules that we do not control.
    """
    scss = (REPO_ROOT / "theme.scss").read_text()
    assert "prefers-color-scheme" not in scss
    assert not (REPO_ROOT / "theme-dark.scss").exists()


def test_colours_are_variables_not_literals():
    """Every hex value must live in the defaults block, never in a rule.

    This is what keeps a future dark mode to one new file instead of a hunt
    through every selector.
    """
    scss = (REPO_ROOT / "theme.scss").read_text()
    rules_section = scss.split("/*-- scss:rules --*/")[1]

    # Each pattern looks for a colour in *property-value* position (after a
    # colon), so an id selector like `#quarto-content` is not a false positive.
    hex_literal = re.compile(r":[^;]*#[0-9a-fA-F]{3,8}\b")
    colour_func = re.compile(r":[^;]*\b(?:rgb|rgba|hsl|hsla)\(")
    colour_word = re.compile(
        r":\s*(?:red|blue|green|black|white|gray|grey|orange|purple|yellow"
        r"|pink|brown|navy|teal|olive|maroon|silver|aqua|fuchsia|lime"
        r"|transparent|currentcolor|cyan|magenta)\b",
        re.IGNORECASE,
    )

    offenders = []
    for line in rules_section.splitlines():
        code = line.split("//")[0]          # strip trailing comments
        if not code.strip():
            continue
        if hex_literal.search(code) or colour_func.search(code) or colour_word.search(code):
            offenders.append(line.strip())

    assert offenders == [], f"hard-coded colours found in rules: {offenders}"


TABS = ["About", "CV", "Notes", "Blog", "Contact"]


def test_all_tabs_present_in_navbar(site):
    """Every tab appears *inside the navbar* — not merely somewhere on the page."""
    navbar = extract_element(read_html(site, "index.html"), "navbar")
    assert navbar, "no element with class 'navbar' found on index.html"
    for tab in TABS:
        assert f">{tab}<" in navbar, f"navbar is missing the {tab} tab"


def test_tab_pages_are_generated(site):
    for relpath in ["about.html", "cv/index.html", "notes/index.html",
                    "blog/index.html", "contact.html"]:
        assert (site / relpath).is_file(), f"{relpath} was not generated"


# The exact values published on the Contact page. Kept as constants so the
# test states the intended values rather than re-deriving them from the page
# it is checking — a test that reads the page for both sides of its own
# assertion cannot catch a typo.
CONTACT_EMAIL = "poare@bnl.gov"
CONTACT_PROFILE_URLS = [
    "https://inspirehep.net/authors/2134227",
    "https://orcid.org/0000-0002-8244-6158",
    "https://github.com/poare",
    "https://www.linkedin.com/in/patrick-oare-50a750125/",
]


def test_contact_page_publishes_email_and_profiles(site):
    """The email and all four profile links must be present and well-formed.

    A typo in a profile URL is invisible until a visitor clicks it and lands
    on someone else's page or a 404, and `github.com/poare` written without a
    scheme would be treated as a relative path and 404 on this site — which
    is why each URL is asserted in full rather than by substring.

    The external URLs are deliberately NOT fetched. A suite that makes network
    calls fails when a service is slow, rate-limits, or the runner has no
    egress, none of which mean this site is broken.
    """
    html = read_html(site, "contact.html")

    assert f'href="mailto:{CONTACT_EMAIL}"' in html, (
        f"no mailto: link for {CONTACT_EMAIL} on the contact page"
    )

    for url in CONTACT_PROFILE_URLS:
        assert f'href="{url}"' in html, f"contact page is missing a link to {url}"


# Source file -> generated page, for the top-level pages that must share one
# layout. Kept together so a new tab is added to both halves at once.
TOP_LEVEL_PAGES = {
    "index.md": "index.html",
    "about.md": "about.html",
    "cv/index.md": "cv/index.html",
    "notes/index.md": "notes/index.html",
    "blog/index.md": "blog/index.html",
    "contact.md": "contact.html",
}


def test_every_top_level_page_declares_the_full_layout():
    """All top-level pages use `page-layout: full` so their left gutters line up.

    Without this, a heading jumps horizontally as you move between tabs —
    the default article layout indents content roughly 240px at a 1280px
    viewport, the full layout roughly 73px. The pages were mixed before
    (Blog and the homepage on the default, the rest on full) and the
    mismatch was visible when clicking between them.

    Asserted on the front matter rather than the rendered output because
    that is the single knob that controls it; the companion test below
    checks the rendering actually followed.
    """
    for source in TOP_LEVEL_PAGES:
        text = (REPO_ROOT / source).read_text(encoding="utf-8")
        front_matter = text.split("---", 2)[1]
        assert "page-layout: full" in front_matter, (
            f"{source} does not declare `page-layout: full`, so its gutters "
            "will not match the other top-level pages"
        )


def test_top_level_pages_render_in_the_full_width_column(site):
    """The declared layout must actually reach the generated markup.

    Quarto puts the content in a `column-page*` class for the full layout
    and `column-body` for the default article layout. Blog legitimately
    renders `column-page-left` rather than `column-page`: its category
    filter occupies the right margin, so the content column is left-aligned
    within the same page column. Both share the same left edge, which is
    what this test is really about, so the assertion accepts the whole
    `column-page` family rather than pinning one exact class.
    """
    for source, relpath in TOP_LEVEL_PAGES.items():
        html = read_html(site, relpath)
        match = re.search(r'<main class="([^"]*)"', html)
        assert match, f"no <main> element found in {relpath}"
        classes = match.group(1)
        assert "column-page" in classes, (
            f"{relpath} rendered <main class=\"{classes}\"> — expected a "
            f"column-page* class. Check `page-layout: full` in {source}."
        )


def test_favicon_is_declared_and_shipped(site):
    """Both favicon files must be linked AND actually present in the output.

    Two separate failures are possible and only one is visible: a link with
    no file behind it looks fine in the markup and shows the browser's
    default globe to every visitor.

    The SVG is the one at risk. It is referenced only from a raw <link> in
    `include-in-header`, and it reaches _site because Quarto scans the
    generated HTML and copies what it finds — verified by removing the
    `resources:` entry that was originally added for it and confirming the
    file still shipped, which is why that entry is not there. That copying
    is incidental behaviour rather than something configured here, so this
    test is what would catch a Quarto version that stopped doing it.

    Checked on a nested page, not the homepage: Quarto rewrites the href per
    page depth, so a path that works at the root can still 404 two levels
    down.
    """
    for relpath in ["index.html", "notes/physics/lorentz-poincare-groups.html"]:
        html = read_html(site, relpath)
        links = re.findall(r'<link[^>]*rel="icon"[^>]*>', html)
        assert len(links) == 2, (
            f"{relpath} declares {len(links)} favicon link(s), expected 2 "
            "(a PNG fallback and an SVG)"
        )

        hrefs = [re.search(r'href="([^"]+)"', link).group(1) for link in links]
        assert any(h.endswith(".png") for h in hrefs), "no PNG favicon linked"
        assert any(h.endswith(".svg") for h in hrefs), "no SVG favicon linked"

        page_dir = (site / relpath).parent
        for href in hrefs:
            target = (page_dir / href).resolve()
            assert target.is_file(), (
                f"{relpath} links favicon {href}, which resolves to {target} "
                "— not present in the built output"
            )


def test_favicon_source_artwork_is_square():
    """A non-square favicon gets letterboxed or stretched, differently in
    each place it appears. scripts/make_favicon.py refuses to build one, but
    that script is only run by hand when the artwork changes; this asserts
    the committed source still satisfies the rule.
    """
    import fitz

    source = REPO_ROOT / "assets" / "lqcd_icon.pdf"
    assert source.is_file(), "favicon source artwork is missing"
    with fitz.open(source) as doc:
        rect = doc.load_page(0).rect
    assert abs(rect.width - rect.height) < 0.5, (
        f"favicon source is {rect.width:.1f}x{rect.height:.1f}pt, not square"
    )


def test_full_text_search_is_enabled(site):
    """Quarto's built-in search is included — it partly compensates for PDFs
    being poorly indexed by search engines."""
    assert (site / "search.json").is_file(), "search index was not generated"


def test_active_nav_link_markup_matches_theme_selector(site):
    """Prove the theme's underline selector matches real rendered markup.

    theme.scss styles `.navbar .nav-link.active` — a descendant combinator.
    Asserting the classes co-occur somewhere in the document would not
    establish that; the element must be inside the navbar. Without this, the
    underline could be entirely non-functional and every other test would
    still pass.
    """
    navbar = extract_element(read_html(site, "about.html"), "navbar")
    assert navbar, "no element with class 'navbar' found on about.html"
    both_classes = re.compile(
        r'class="[^"]*(?:\bnav-link\b[^"]*\bactive\b|\bactive\b[^"]*\bnav-link\b)[^"]*"'
    )
    assert both_classes.search(navbar), (
        "no element inside the navbar carries both 'nav-link' and 'active' — "
        "the theme's underline selector does not match Quarto's markup. "
        "Inspect with: grep -o 'class=\"[^\"]*nav-link[^\"]*\"' _site/about.html"
    )


POST = "blog/posts/2026-08-01-hello/index.html"

# Quarto/Pandoc's "katex" html-math-method renders client-side: the maths is
# actually typeset by KaTeX's JavaScript running in the reader's browser on
# page load, not by Quarto at build time. Confirmed against Quarto's own
# maintainers (github.com/quarto-dev/quarto-cli discussions #5227 and
# #10604): there is no built-in build-time/static KaTeX rendering. That means
# the static files under _site/ that these tests read can never contain
# class="katex" or class="katex-display" — those only exist in the live DOM
# after JavaScript has run. The tests below assert only what the static
# output can actually establish: that the KaTeX library is wired up and
# pinned to a fixed version, and that Pandoc recognised and consumed the
# $...$ / $$...$$ delimiters into maths nodes for KaTeX to target. Real
# rendering was verified by hand: opening the built post in an actual
# browser and confirming both the inline and display equations typeset
# correctly, rather than by this suite, since a permanent headless-browser
# test rig was judged disproportionate for this site.

KATEX_PINNED_VERSION = "0.18.1"


def test_katex_assets_are_loaded_and_pinned(site):
    """KaTeX renders client-side, so the static HTML cannot show rendered
    maths. What it can show is that the library is wired up and pinned to a
    fixed version rather than tracking @latest, which would let an upstream
    KaTeX release silently break every equation on the site.
    """
    html = read_html(site, POST)
    assert "katex.min.js" in html, "KaTeX script tag missing"
    assert f"katex@{KATEX_PINNED_VERSION}" in html, "KaTeX version is not pinned"
    assert "katex@latest" not in html, "KaTeX must not track @latest"


def test_inline_math_delimiters_were_consumed_by_pandoc(site):
    """Pandoc must parse inline `$...$` into a maths node at build time,
    leaving the raw LaTeX source inside a <span class="math inline"> for
    KaTeX to typeset client-side. Literal "$...$" text surviving into the
    prose means the maths was never recognised as maths at all.

    Verified this discriminates: re-running the post's source through pandoc
    with the tex_math_dollars extension disabled (simulating a markdown
    parser regression) reproduces exactly this failure mode — bare "$D$"
    survives as literal text instead of becoming <span class="math
    inline">D</span>, and the more complex \\kappa(D) expression is silently
    mangled rather than preserved for KaTeX.
    """
    html = read_html(site, POST)
    assert '<span class="math inline">D</span>' in html, (
        "the bare $D$ was not parsed into a maths span"
    )
    assert "\\kappa(D)" in html, "LaTeX source missing — nothing for KaTeX to render"
    assert "$D$" not in html, "delimiters survived around D; maths was not parsed"
    assert "$\\kappa(D)$" not in html, "delimiters survived; maths was not parsed"


def test_blog_lists_the_post(site):
    """The post title must appear *inside the rendered listing card* and
    link to the post's real page — not merely appear somewhere on the page
    (e.g. a <title> tag or a search-index leak), which would pass even if
    the `listing:` block were misconfigured and rendered nothing."""
    html = read_html(site, "blog/index.html")
    listing = extract_element(html, "quarto-listing")
    assert listing, "no element with class 'quarto-listing' rendered — the listing block did not run"
    assert "Deflation and the low modes" in listing, "post title missing from the rendered listing card"
    assert 'href="../blog/posts/2026-08-01-hello/index.html"' in listing, (
        "listing card does not link to the post's actual page"
    )


def test_blog_shows_category_tags(site):
    """Category tags must render as Quarto's clickable filter widget, not
    as plain text. This checks two independent things the `categories: true`
    listing option produces: (1) each post card carries its categories as
    `listing-category` elements wired to `quartoListingCategory()`, the JS
    click handler that filters the grid; and (2) the sidebar gets a
    `quarto-listing-category` filter panel with a real `data-category` value
    per tag. Plain-text tags, or omitting `categories: true`, would fail
    both checks.
    """
    html = read_html(site, "blog/index.html")

    listing = extract_element(html, "quarto-listing")
    assert listing, "no element with class 'quarto-listing' rendered — the listing block did not run"
    card_tags = re.findall(
        r'class="listing-category"\s+onclick="window\.quartoListingCategory\([^)]*\)[^>]*>\s*(solvers|lattice)\s*</div>',
        listing,
    )
    assert set(card_tags) == {"solvers", "lattice"}, (
        f"post card is missing clickable category tags for solvers/lattice, found: {card_tags}"
    )

    sidebar = extract_element(html, "quarto-listing-category")
    assert sidebar, "no category filter panel (class 'quarto-listing-category') rendered in the sidebar"
    sidebar_tags = re.findall(
        r'<div class="category" data-category="[^"]+">\s*(solvers|lattice)\b', sidebar
    )
    assert set(sidebar_tags) == {"solvers", "lattice"}, (
        f"sidebar filter panel is missing clickable entries for solvers/lattice, found: {sidebar_tags}"
    )


def test_blog_has_currently_reading_header(site):
    """'Currently reading' must render as a real heading, positioned above
    the generated listing, with the hand-written book list under it — this
    is the editable-prose header, not text that happens to appear anywhere
    on the page (e.g. leaking in from a post body). Checking heading markup
    and document order together rules out both a plain-text stand-in and a
    header accidentally placed below the `:::{#posts}:::` div.

    The heading match is a regex over the `<h3 ...>Currently reading</h3>`
    shape rather than the exact attribute string Quarto happens to emit
    today (`class="anchored" data-anchor-id="currently-reading"`) — the
    README explicitly invites local Quarto upgrades, and Pandoc's own
    heading-anchor markup is exactly the kind of incidental detail that
    changes across versions. What must hold is that it is an <h3>
    containing this text, not the precise attribute set Pandoc bolts on.
    """
    html = read_html(site, "blog/index.html")
    assert re.search(r"<h3[^>]*>Currently reading</h3>", html), (
        "'Currently reading' is not rendered as an <h3> heading"
    )
    header_pos = html.find("Currently reading")
    listing_pos = html.find('id="listing-posts"')
    assert listing_pos != -1, "generated listing container not found"
    assert header_pos < listing_pos, (
        "the 'currently reading' header must render above the generated listing"
    )
    for book in ("Modern Quantum Mechanics", "Iterative Methods for Sparse Linear Systems"):
        assert book in html, f"reading list is missing {book!r}"


def test_listing_is_not_nested_inside_the_editable_header(site):
    """The hand-edited header must be a SIBLING of the generated listing.

    Pandoc wraps everything after a heading into that heading's <section>. If
    the listing lands inside the "Currently reading" block, then adding any
    further heading to the book list silently reparents the generated grid.
    This page is hand-edited regularly, so that trap must stay closed.
    """
    html = read_html(site, "blog/index.html")
    # Match by id, not class: the id="currently-reading" anchor comes from
    # Pandoc's automatic heading slug and exists whether or not the fix
    # (which adds a wrapping div carrying a "currently-reading" class) is in
    # place. Keying on the class instead would make this test fail for the
    # wrong reason if the fix regressed — "no such element" rather than
    # actually showing the listing nested inside — so it would stop
    # discriminating the defect it exists to catch.
    header_block = extract_element(html, "currently-reading", by="id")
    assert header_block, "no element with id 'currently-reading' found"
    assert 'id="listing-posts"' not in header_block, (
        "the generated listing is nested inside the editable header block; "
        "adding a heading to the book list would silently reparent it"
    )


def test_display_math_delimiters_were_consumed_by_pandoc(site):
    """As above, for the $$...$$ display equation: Pandoc must recognise it
    and produce a <span class="math display"> node containing the raw LaTeX,
    which is exactly what the injected client-side render script (see
    test_katex_assets_are_loaded_and_pinned) looks for via
    `classList.contains('display')` to decide whether to call KaTeX in
    display mode.
    """
    html = read_html(site, POST)
    assert 'class="math display"' in html, (
        "display equation was not parsed into a maths node"
    )
    assert "D_{\\text{defl}}" in html, "LaTeX source for the display equation is missing"
    assert "$$" not in html, "display-math delimiters survived unprocessed"


NOTE = "notes/physics/lorentz-poincare-groups.html"


def _note_stub_path(note_html_relpath):
    """Map a rendered note page's site-relative path to its .md source stub.

    e.g. "notes/physics/lorentz-poincare-groups.html" ->
    <repo>/notes/physics/lorentz-poincare-groups.md
    """
    return REPO_ROOT / Path(note_html_relpath).with_suffix(".md")


def _note_stub_front_matter(note_html_relpath):
    """Parse the YAML front matter of the .md stub behind a rendered note page.

    Tests key on this instead of retyping the stub's prose as a literal
    string. The whole design premise of a stub is hand-written prose the
    author edits freely (title, description, errata) -- a test that
    retypes today's wording fails on a legitimate future edit as a false
    alarm, not because anything broke. Deriving the expected text from the
    stub's own front matter keeps the test meaningful across such edits.
    """
    import yaml

    stub_path = _note_stub_path(note_html_relpath)
    text = stub_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?\n)---\n", text, re.DOTALL)
    assert match, f"{stub_path} has no YAML front matter"
    return yaml.safe_load(match.group(1))


def _ascii_needle(text):
    """Pick a run of plain ASCII characters (20+ chars) out of `text`.

    Such a substring has no `&`, quotes, angle brackets or non-ASCII
    letters, so it renders identically whether or not the surrounding
    context HTML-escapes those characters -- see
    test_note_description_appears_exactly_once_in_body for the full
    rationale this is factored out of.
    """
    ascii_runs = re.findall(r"[A-Za-z0-9 ,.\-]{20,}", text)
    assert ascii_runs, (
        f"{text!r} has no plain-ASCII run of 20+ chars to key on; pick a "
        "different needle strategy if this text changes"
    )
    return max(ascii_runs, key=len).strip()


def test_note_stub_is_generated(site):
    html = read_html(site, NOTE)
    assert "Download PDF" in html, "stub is missing a download link"
    assert "<object" in html or "<iframe" in html, "stub has no embedded viewer"


def test_note_stub_has_indexable_description(site):
    """The description text search engines rely on must reach the body.

    The expected substring is derived from the stub's own front-matter
    `description:` field (via _note_stub_front_matter/_ascii_needle) rather
    than hard-coded as the literal "little-group" -- a legitimate rewrite
    of the description would otherwise fail this test as a false alarm.
    """
    html_text = read_html(site, NOTE)
    front_matter = _note_stub_front_matter(NOTE)
    needle = _ascii_needle(front_matter["description"])
    assert needle.lower() in html_text.lower(), (
        "the description text search engines rely on is missing"
    )


def test_note_stub_meta_description_tag_is_populated(site):
    """The body text alone (checked above) does not prove the front-matter
    `description:` reached the actual <meta name="description"> tag search
    engines read for the results-page snippet — a test on body text alone
    would still pass if that pipeline were broken. Verified against the real
    rendered output that Quarto emits the tag in this exact form:
    <meta name="description" content="...">. Verified this discriminates: with
    the front-matter `description:` line removed, this test fails (no such
    meta tag is rendered); restored, it passes.

    The expected substring is derived from the stub's own front matter
    (not the meta tag itself, which is exactly what is under test here, and
    not a hard-coded literal, which would false-alarm on a legitimate
    description edit).
    """
    html_text = read_html(site, NOTE)
    match = re.search(r'<meta name="description" content="([^"]*)">', html_text)
    assert match, "no <meta name=\"description\"> tag rendered on the stub page"
    meta_content = html.unescape(match.group(1))

    front_matter = _note_stub_front_matter(NOTE)
    needle = _ascii_needle(front_matter["description"])
    assert needle.lower() in meta_content.lower(), (
        "meta description tag does not contain the front-matter description text"
    )


def test_note_description_appears_exactly_once_in_body(site):
    """Regression guard: the `pdf-note` shortcode used to re-emit the
    front-matter `description` as a body paragraph even though Quarto's own
    page template already prints that same text under the title — so the
    description appeared twice inside <body> on every note page, and every
    existing test still passed because they only assert the text is
    *present*, never that it is present exactly once.

    The expected text is derived from the page's own
    <meta name="description" content="..."> tag rather than hard-coded, so
    this keeps working if the note's description is edited later. The meta
    attribute and the rendered body can HTML-escape the same characters
    differently (`&amp;`, `&#39;`, accented letters, etc.), so comparing the
    two verbatim would produce false mismatches unrelated to the bug this
    test targets. To avoid that, pick a run of plain ASCII characters from
    the (unescaped) meta content — a substring with no `&`, quotes, angle
    brackets or non-ASCII letters renders identically in both places
    regardless of escaping — and count occurrences of just that substring.
    """
    html_text = read_html(site, NOTE)
    match = re.search(r'<meta name="description" content="([^"]*)">', html_text)
    assert match, "no <meta name=\"description\"> tag rendered on the stub page"
    meta_content = html.unescape(match.group(1))

    ascii_runs = re.findall(r"[A-Za-z0-9 ,.\-]{20,}", meta_content)
    assert ascii_runs, (
        "meta description has no plain-ASCII run of 20+ chars to key on; "
        "pick a different needle strategy if the note's description changes"
    )
    needle = max(ascii_runs, key=len).strip()

    body_match = re.search(r"<body[^>]*>(.*)</body>", html_text, re.DOTALL)
    assert body_match, "no <body> element found on the stub page"
    body = body_match.group(1)

    count = body.count(needle)
    assert count == 1, (
        f"expected the description text {needle!r} to appear exactly once "
        f"in <body>, found {count} — the pdf-note shortcode is likely "
        "re-emitting the front-matter description that Quarto's page "
        "template already renders under the title"
    )


def test_notes_index_groups_by_topic(site):
    """The expected title is derived from the stub's own front matter
    rather than hard-coded as the literal "The Lorentz and Poincaré
    Groups" -- a legitimate title revision would otherwise fail this test
    as a false alarm, not because the listing broke.
    """
    html_text = read_html(site, "notes/index.html")
    assert "Physics" in html_text, "topic heading is missing"
    front_matter = _note_stub_front_matter(NOTE)
    assert front_matter["title"] in html_text, (
        "note is missing from its topic listing"
    )


def test_pdf_is_copied_to_output(site):
    """`notes/pdf/orphan-fixture.pdf` is deliberately unreferenced by any
    stub page. Quarto's dependency scanner copies a PDF into _site whenever
    some rendered page links to it (e.g. lorentz-poincare-groups.pdf, via
    the stub's <object data=...>) — that would make this test pass even with the
    `resources:` key removed from _quarto.yml entirely. The whole point of
    `resources:` is to copy files that *nothing links to yet* (e.g. a PDF
    just dropped into notes/pdf/ before its stub page exists), so only an
    orphan file actually exercises that key. Verified: with `resources:`
    removed, this test fails (orphan-fixture.pdf is absent from _site);
    restored, it passes.
    """
    orphan = site / "notes" / "pdf" / "orphan-fixture.pdf"
    assert orphan.is_file(), (
        "orphan-fixture.pdf (unreferenced by any stub) was not copied into "
        "_site — check the resources config in _quarto.yml"
    )


def test_note_thumbnail_is_generated_and_referenced(site):
    """The card grid's whole point is a visual thumbnail; without one the
    cards are bare text. None of the brief's four required tests check this,
    so it is checked here: both that scripts/make_thumbs.py actually wrote
    the PNG to disk, and that the rendered listing's <img> references it. A
    typo'd `image:` front-matter path would leave the PNG on disk but
    missing from the page; a broken make_thumbs.py would leave nothing on
    disk at all. Either failure mode is caught.
    """
    thumb = REPO_ROOT / "notes" / "thumbs" / "lorentz-poincare-groups.png"
    assert thumb.is_file(), "sync_notes.py did not produce lorentz-poincare-groups.png"

    html = read_html(site, "notes/index.html")
    listing = extract_element(html, "quarto-listing")
    assert listing, "no element with class 'quarto-listing' rendered"
    assert "thumbs/lorentz-poincare-groups.png" in listing, (
        "the listing card does not reference the generated thumbnail"
    )


def test_notes_topic_listing_scoped_to_its_own_section(site):
    """The 'Physics' listing must render as a child of its own heading's
    <section> — and the intro prose above the heading must NOT be swallowed
    into that same section. notes/index.md has the same shape that bit the
    blog page in an earlier task (prose, then a heading, then a generated
    listing div): Pandoc wraps everything after a heading into that
    heading's <section> until a heading of equal-or-higher level closes it.
    This page is designed to grow to many topics, each its own '## Heading'
    followed by its own listing div, so a section that fails to close would
    silently swallow every topic added after it.

    extract_element also raises directly if the id="physics" element's
    markup never closes at all (unbalanced depth), which would itself mean
    the section swallowed the rest of the document.
    """
    html = read_html(site, "notes/index.html")
    section = extract_element(html, "physics", by="id")
    assert section, "no element with id 'physics' found"
    assert 'id="listing-physics"' in section, (
        "the topic listing is not nested inside its own topic's <section>"
    )
    assert "Write-ups, derivations" not in section, (
        "the intro prose leaked into the topic section — the heading's "
        "<section> did not close where expected, which would reparent any "
        "topic added after this one"
    )


def test_cv_download_link_resolves_to_a_real_file(site):
    """Follow the actual href to verify both the link and the file exist.

    A rename of the PDF and its link together (the expected workflow when
    swapping in a real CV) is caught by this test, not the two redundant
    hard-coded tests that were removed. Logic lives in
    conftest.assert_local_links_resolve, shared with the notes-stub version
    of this check below, since both page types make the same promise: a
    same-origin .pdf href must resolve to a real file in the built output.
    """
    assert_local_links_resolve(site, "cv/index.html")


def test_all_notes_stub_pdf_links_resolve(site):
    """Every generated notes stub must link to a PDF that actually exists.

    Globs every stub under notes/ (excluding the topic-index page notes/
    index.html, which has no PDF of its own) rather than hard-coding
    "notes/physics/lorentz-poincare-groups.html" — the point is that a new
    stub added in a new topic folder is covered the day it is added, with
    no test to remember to write. A mutation test proved the gap this
    closes: pointing lorentz-poincare-groups.md's PDF path at a nonexistent
    file left all previously-existing tests passing (including test_note_stub_is_
    generated, which only checks for the presence of a "Download PDF"
    string and an <object> tag — never that either resolves) while the
    download button and <object> viewer both 404 in the browser.
    """
    stubs = sorted(
        p for p in site.glob("notes/**/*.html")
        if p.relative_to(site) != Path("notes/index.html")
    )
    assert stubs, "no notes stub pages were generated"
    for stub in stubs:
        assert_local_links_resolve(site, str(stub.relative_to(site)))


def test_no_stub_hand_copies_the_viewer_markup():
    """Every notes stub must get its viewer from the pdf-note shortcode.

    The shortcode exists so that changing how PDFs are presented is a
    one-file edit rather than a 20-30 file edit. That property only holds
    while no stub has quietly reverted to pasting the markup in directly —
    which is exactly what someone does when they copy an older note as a
    starting point. Checks source .md files, not rendered HTML: the
    rendered page is *supposed* to contain <object>.
    """
    notes_dir = REPO_ROOT / "notes"
    stubs = sorted(
        p for p in notes_dir.glob("*/*.md")
        if not p.name.startswith("_")
    )
    assert stubs, "no notes stubs found under notes/<topic>/"
    for stub in stubs:
        text = stub.read_text(encoding="utf-8")
        assert "<object" not in text, (
            f"{stub.relative_to(REPO_ROOT)} hand-copies the <object> viewer "
            "instead of calling {{< pdf-note >}}"
        )
        assert "{{< pdf-note" in text, (
            f"{stub.relative_to(REPO_ROOT)} does not call the pdf-note "
            "shortcode"
        )


def test_note_page_renders_the_shortcode_output(site):
    """The shortcode must emit all of its parts, pointing at THIS note's PDF.

    The slug is derived, not typed, so the failure to guard against is a
    page that renders perfectly while referencing another note's PDF —
    which test_all_notes_stub_pdf_links_resolve would happily pass, since
    that file does exist. Deriving the expected slug from the page path is
    what makes this test check identity rather than mere existence.

    Body prose from the front-matter `description` is covered by
    test_note_stub_has_indexable_description just above.
    """
    html = read_html(site, NOTE)
    slug = Path(NOTE).stem

    assert extract_element(html, "accent-rule"), (
        "the shortcode did not emit the accent rule"
    )
    assert f'href="../pdf/{slug}.pdf"' in html, (
        f"no download button pointing at ../pdf/{slug}.pdf — the shortcode "
        "derived the wrong slug, or emitted no button"
    )
    assert f'data="../pdf/{slug}.pdf"' in html, (
        f"no <object> viewer pointing at ../pdf/{slug}.pdf"
    )


NOTEBOOK_POST = "blog/posts/2026-08-02-notebook-demo/index.html"


def test_notebook_post_rendered_a_figure(site):
    html = read_html(site, NOTEBOOK_POST)
    assert "<img" in html or "data:image/png" in html, (
        "the notebook produced no figure"
    )


def test_freeze_cache_is_committed():
    """_freeze/ must be *git-tracked*, not merely present on disk.

    Checking only for the directory's existence (and a *.json somewhere
    inside it) would also pass for a cache that was generated locally and
    never `git add`-ed -- exactly the state that makes Task 10's CI fail
    demanding Jupyter, since CI clones the repo and gets only tracked
    files, not whatever a contributor happens to have sitting in their
    working tree. So we ask git itself what is tracked, rather than the
    filesystem.
    """
    freeze = REPO_ROOT / "_freeze"
    assert freeze.is_dir(), (
        "_freeze/ must exist and be committed so CI needs no Python"
    )

    result = subprocess.run(
        ["git", "ls-files", "_freeze/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"git ls-files _freeze/ failed:\n{result.stderr}"

    tracked = [line for line in result.stdout.splitlines() if line]
    assert tracked, (
        "_freeze/ exists on disk but git tracks nothing inside it -- "
        "run `git add _freeze/` and commit"
    )
    assert any(
        "execute-results" in path and path.endswith(".json") for path in tracked
    ), (
        "_freeze/ is tracked by git but none of the tracked paths look like "
        f"an execute-results/*.json cache: {tracked}"
    )


def test_freeze_cache_is_reused_without_a_working_python(site, tmp_path):
    """Render the whole project again with every python3/python/jupyter
    lookup on PATH shadowed by a shim that fails loudly. If quarto still
    produces the figure, and the shim never fires, the figure can only have
    come from the committed _freeze/ cache, not from re-executing the
    notebook -- this is exactly the guarantee Task 10's CI depends on, since
    its workflow installs no Python at all.

    We use shims rather than a stripped-down PATH. An earlier version of
    this test built a "hostile" PATH by symlinking every entry of /usr/bin
    except python3/pip3, plus a few hard-coded system directories, into a
    staging directory. That approach silently depends on the filesystem
    layout of one specific machine: on this project's other development
    machine (an Ubuntu desktop, vs. the macOS laptop this was written on) a
    versioned `python3.12` binary can live somewhere that scheme doesn't
    strip, defeating the isolation, or a tool quarto's own launcher needs
    can live outside those four directories, breaking the render for
    reasons that have nothing to do with Python. A test that fails for the
    wrong reason on a second platform is worse than no test -- this project
    has already deleted a test for exactly that fault.

    Shims sidestep the whole problem, because they depend on no directory
    layout at all: we prepend one directory containing executable
    stand-ins named python3, python and jupyter to PATH, ahead of
    everything already there. PATH shadowing works identically on macOS
    and Linux, so the shim directory hides real Python entry points
    without removing or symlinking a single thing from the rest of PATH --
    coreutils and quarto's own launcher are untouched on any platform.

    Note this deliberately runs a *project* render (`quarto render`, no
    target), matching what CI does. Targeting the single .qmd file directly
    (`quarto render path/to/index.qmd`) always re-executes the code cell
    regardless of the freeze cache -- freeze is a project-level render
    optimization, not a per-file one -- so that form would not exercise the
    thing this test is trying to prove. Do not "optimise" this into a
    single-file render.

    This reuses the already-rendered `site` fixture only to force it to run
    first (so the freeze cache reflects the current source before we probe
    it) and to know where quarto lives; it then does a second, independent
    project render subprocess with the shimmed PATH, writing into a
    temporary output directory (via --output-dir) so the repo's real
    _site/ is left untouched.
    """
    quarto_bin = shutil.which("quarto")
    assert quarto_bin, "quarto not found on PATH"

    marker = "FREEZE-SHIM-INVOKED"
    shim_dir = tmp_path / "python-shim"
    shim_dir.mkdir()
    for name in ("python3", "python", "jupyter"):
        shim = shim_dir / name
        shim.write_text(
            "#!/bin/sh\n"
            f'echo "{marker}: {name}" >&2\n'
            "exit 1\n"
        )
        shim.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = f"{shim_dir}{os.pathsep}{env['PATH']}"

    out_dir = tmp_path / "shim-render-out"

    # --output-dir redirects quarto's final HTML output, but NOT its
    # freeze-thaw staging step: when a render actually re-executes a
    # notebook (the failure mode this test exists to catch), quarto writes
    # execute-results/figure staging files into an `index_files/` directory
    # next to the source .qmd, regardless of --output-dir. That directory
    # is untracked and not gitignored, and its name is confusingly similar
    # to the legitimate, committed `_freeze/.../index/` cache -- so on the
    # one run where this test's failure signal fires for real, it would
    # otherwise also leave debris in the source tree. Clean it up
    # unconditionally, whether the render/assertions below pass or fail.
    staging_dir = REPO_ROOT / "blog/posts/2026-08-02-notebook-demo/index_files"
    try:
        result = subprocess.run(
            [quarto_bin, "render", "--output-dir", str(out_dir)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, (
            "quarto render failed with a shimmed Python on PATH -- the freeze "
            f"cache was not reused:\n{result.stdout}\n{result.stderr}"
        )
        assert marker not in result.stdout and marker not in result.stderr, (
            "quarto invoked a python3/python/jupyter shim -- it re-executed the "
            f"notebook instead of reusing the freeze cache:\n"
            f"{result.stdout}\n{result.stderr}"
        )

        rendered = out_dir / NOTEBOOK_POST
        assert rendered.is_file(), (
            f"expected rendered notebook page at {rendered}, not found"
        )
        html = rendered.read_text(encoding="utf-8")
        assert "<img" in html or "data:image/png" in html, (
            "figure missing after a Python-free render"
        )
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


def test_cname_is_copied_to_output(site):
    """The `CNAME` file at the repo root tells GitHub Pages which custom
    domain to serve the site under. Because Actions-based deployment
    rebuilds the published artifact on every run, the domain has to live in
    the repository (via `resources:` in _quarto.yml) rather than only in
    the repo's GitHub Pages settings -- otherwise a redeploy silently drops
    the custom domain and the site reverts to the default github.io URL
    with no error anywhere.

    This test is deliberately strict about content, not just presence: a
    CNAME file that exists but is empty, or that names the wrong domain,
    would still "detach" the real custom domain just as silently as a
    missing file, so both failure modes must be caught here.
    """
    cname = site / "CNAME"
    assert cname.is_file(), (
        "CNAME was not copied into _site -- check the resources config in "
        "_quarto.yml"
    )
    assert cname.read_text(encoding="utf-8") == "www.patrickoare.phd\n", (
        "CNAME in _site does not contain exactly 'www.patrickoare.phd' -- "
        "a missing, empty, or wrong-domain CNAME silently detaches the "
        "custom domain on the next deploy"
    )


def test_render_thumbnail_writes_a_png(tmp_path, monkeypatch):
    """sync_notes.py renders one thumbnail at a time, so the per-file logic
    has to be callable on its own rather than only via a directory scan.
    """
    import fitz

    from scripts import make_thumbs

    thumb_dir = tmp_path / "thumbs"
    monkeypatch.setattr(make_thumbs, "THUMB_DIR", thumb_dir)

    pdf_path = tmp_path / "sample-note.pdf"
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.save(pdf_path)
    doc.close()

    written = make_thumbs.render_thumbnail(pdf_path)
    assert written == thumb_dir / "sample-note.png"
    assert written.is_file(), "render_thumbnail did not write the PNG"


def test_render_thumbnail_skips_an_existing_thumbnail(tmp_path, monkeypatch):
    """Re-running the sync over a manifest of 30 notes must not re-render
    every thumbnail each time.
    """
    import fitz

    from scripts import make_thumbs

    thumb_dir = tmp_path / "thumbs"
    thumb_dir.mkdir()
    monkeypatch.setattr(make_thumbs, "THUMB_DIR", thumb_dir)

    pdf_path = tmp_path / "sample-note.pdf"
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.save(pdf_path)
    doc.close()

    existing = thumb_dir / "sample-note.png"
    existing.write_bytes(b"sentinel")

    assert make_thumbs.render_thumbnail(pdf_path) is None
    assert existing.read_bytes() == b"sentinel", "an existing thumbnail was overwritten"
    assert make_thumbs.render_thumbnail(pdf_path, force=True) is not None
    assert existing.read_bytes() != b"sentinel", "--force did not re-render"


def test_render_thumbnail_rejects_an_empty_pdf(tmp_path, monkeypatch):
    """A zero-page PDF is a real thing PyMuPDF will hand back. Rendering
    page 0 of it raises deep inside fitz; catching it here keeps the batch
    loop's warn-and-continue behaviour meaningful.

    The installed PyMuPDF (1.28.0) refuses to *save* an in-memory,
    zero-page fitz.Document -- fitz.open() with no new_page() call, and a
    page added then deleted, both raise "cannot save with zero pages" from
    Document.save() itself, before render_thumbnail is ever reached. A
    zero-page PDF is still a real file PyMuPDF will happily *open* (that is
    the whole premise of this test), so the fixture is hand-crafted as raw
    bytes -- the same technique conftest.py's _MINIMAL_PDF_BYTES uses, but
    with an empty Kids array and Count 0 -- rather than produced via fitz.
    """
    from scripts import make_thumbs

    monkeypatch.setattr(make_thumbs, "THUMB_DIR", tmp_path / "thumbs")

    pdf_path = tmp_path / "empty-note.pdf"
    pdf_path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"xref\n"
        b"0 3\n"
        b"0000000000 65535 f\n"
        b"trailer<</Size 3/Root 1 0 R>>\n"
        b"startxref\n"
        b"0\n"
        b"%%EOF\n"
    )

    with pytest.raises(make_thumbs.EmptyPdfError):
        make_thumbs.render_thumbnail(pdf_path)


def test_manifest_is_not_empty():
    """load_manifest itself raises ManifestError on anything actually
    malformed (missing keys, bad slugs, duplicates, absolute paths -- see
    test_manifest_rejects_a_bad_entry), so a loop reasserting SLUG_RE.match
    on entries it already returned could never fail: load_manifest would
    have raised first. That made the old version of this test tautological.
    The kebab-case rule itself is genuinely covered -- by
    test_manifest_rejects_a_bad_entry's "kebab-case" cases, which drive it
    through the rejection path directly. What is NOT covered elsewhere is
    the possibility of an empty-but-well-formed manifest (`notes.yml`
    truncated to nothing, or every entry deleted), which load_manifest
    would happily accept as a valid empty list -- so that is what this
    keeps checking.
    """
    from scripts import sync_notes

    entries = sync_notes.load_manifest(sync_notes.MANIFEST)
    assert entries, "notes.yml lists no notes"


def test_manifest_topics_have_a_matching_notes_index_listing():
    """The spec requires a manifest entry's `topic` to correspond to a
    listing in notes/index.md, but nothing previously checked that. Adding
    an entry with e.g. `topic: math` (no "math" listing section) still
    scaffolds a stub, passes every other test, and renders a publicly
    reachable page at notes/math/<slug>.html -- one that appears nowhere on
    /notes, since no listing block ever points at notes/math/.

    This parses the YAML front matter of notes/index.md, collects every
    `id:` under its `listing:` block, and asserts every distinct topic in
    notes.yml has a matching id.
    """
    import yaml

    from scripts import sync_notes

    entries = sync_notes.load_manifest(sync_notes.MANIFEST)
    manifest_topics = {entry["topic"] for entry in entries}

    index_text = (REPO_ROOT / "notes" / "index.md").read_text(encoding="utf-8")
    front_matter_match = re.match(r"^---\n(.*?\n)---\n", index_text, re.DOTALL)
    assert front_matter_match, "notes/index.md has no YAML front matter"
    front_matter = yaml.safe_load(front_matter_match.group(1))

    listings = front_matter.get("listing") or []
    listed_ids = {item["id"] for item in listings if isinstance(item, dict) and "id" in item}

    missing = manifest_topics - listed_ids
    assert not missing, (
        f"notes.yml has topic(s) {sorted(missing)} with no matching `id:` "
        "under notes/index.md's `listing:` block -- add a listing section "
        "for the new topic (see the README's 'Adding content -- Note' "
        f"bullet). Listed ids: {sorted(listed_ids)}"
    )


def test_every_manifest_entry_has_its_files():
    """Catches the 'added an entry, forgot to run the sync' failure, which
    otherwise surfaces as a 404 on the live site rather than a test failure.
    """
    from scripts import sync_notes

    for entry in sync_notes.load_manifest(sync_notes.MANIFEST):
        slug, topic = entry["slug"], entry["topic"]
        for expected in (
            REPO_ROOT / "notes" / "pdf" / f"{slug}.pdf",
            REPO_ROOT / "notes" / "thumbs" / f"{slug}.png",
            REPO_ROOT / "notes" / topic / f"{slug}.md",
        ):
            assert expected.is_file(), (
                f"{expected.relative_to(REPO_ROOT)} is missing — run "
                "python scripts/sync_notes.py"
            )


def test_manifest_rejects_a_bad_entry(tmp_path):
    """load_manifest is the only thing standing between a typo and a
    half-published note, so its validation is tested directly rather than
    trusted.
    """
    from scripts import sync_notes

    def write(text):
        path = tmp_path / "notes.yml"
        path.write_text(text, encoding="utf-8")
        return path

    with pytest.raises(sync_notes.ManifestError, match="missing"):
        sync_notes.load_manifest(write("- slug: a-note\n  topic: physics\n"))  # no source

    with pytest.raises(sync_notes.ManifestError, match="kebab-case"):
        sync_notes.load_manifest(write("- slug: A_Note\n  source: x.pdf\n  topic: physics\n"))

    with pytest.raises(sync_notes.ManifestError, match="unknown"):
        sync_notes.load_manifest(
            write("- slug: a-note\n  source: x.pdf\n  topic: physics\n  title: nope\n")
        )

    with pytest.raises(sync_notes.ManifestError, match="duplicate"):
        sync_notes.load_manifest(
            write(
                "- slug: a-note\n  source: x.pdf\n  topic: physics\n"
                "- slug: a-note\n  source: y.pdf\n  topic: math\n"
            )
        )

    with pytest.raises(sync_notes.ManifestError, match="absolute"):
        sync_notes.load_manifest(
            write("- slug: a-note\n  source: /Users/someone/x.pdf\n  topic: physics\n")
        )

    with pytest.raises(sync_notes.ManifestError, match="kebab-case"):
        sync_notes.load_manifest(
            write("- slug: a-note\n  source: x.pdf\n  topic: Not_Kebab\n")
        )


def test_sync_never_overwrites_an_existing_stub(tmp_path):
    """The property the whole design rests on. A stub holds hand-written
    prose — errata, 'supersedes the 2024 version', links to related notes.
    Re-running the sync after recompiling a PDF must refresh the binary and
    the thumbnail and leave every word of that prose alone.
    """
    from scripts import sync_notes

    stub = tmp_path / "lorentz-poincare-groups.md"

    assert sync_notes.scaffold_stub(stub, "lorentz-poincare-groups", "physics") is True
    scaffolded = stub.read_text(encoding="utf-8")
    assert "{{< pdf-note" in scaffolded
    assert "../thumbs/lorentz-poincare-groups.png" in scaffolded

    hand_written = scaffolded + "\n\nSupersedes the 2024 version.\n"
    stub.write_text(hand_written, encoding="utf-8")

    assert sync_notes.scaffold_stub(stub, "lorentz-poincare-groups", "physics") is False
    assert stub.read_text(encoding="utf-8") == hand_written, (
        "scaffold_stub overwrote an existing stub and destroyed hand-written prose"
    )


def test_scaffold_stub_does_not_follow_a_dangling_symlink(tmp_path):
    """`stub_path.exists()` returns False for a DANGLING symlink (one whose
    target does not exist) -- a check-then-write guard built on `.exists()`
    would therefore treat the path as free, and `write_text` would follow
    the link and write the placeholder to wherever it points, potentially
    outside the notes tree entirely. Reproduced by hand before this fix:
    pointing a dangling symlink at a file outside a scratch notes tree and
    calling scaffold_stub silently created that outside file.

    The fix opens with "x" (exclusive create), which POSIX defines as
    failing on a symlink -- dangling or not -- without following it, so
    this asserts scaffold_stub now returns False (preserving the
    already-written-so-don't-touch-it contract) and never creates anything
    at the link's target.
    """
    from scripts import sync_notes

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_target = outside_dir / "escaped.md"

    notes_dir = tmp_path / "notes_tree"
    notes_dir.mkdir()
    stub = notes_dir / "a-note.md"
    stub.symlink_to(outside_target)  # target does not exist -- dangling

    assert not stub.exists(), "fixture is not actually a dangling symlink"

    result = sync_notes.scaffold_stub(stub, "a-note", "physics")

    assert result is False, (
        "scaffold_stub must treat an occupied (even dangling-symlink) path "
        "as already having a stub, not as free to write"
    )
    assert not outside_target.exists(), (
        "scaffold_stub followed the dangling symlink and wrote outside the "
        "notes tree"
    )
    assert stub.is_symlink(), "scaffold_stub must not remove the existing symlink"


def test_sync_entry_never_overwrites_an_existing_stub(tmp_path, monkeypatch):
    """test_sync_never_overwrites_an_existing_stub (above) proves scaffold_stub's
    own guard works, but scaffold_stub is a private helper and sync_entry is
    its only real caller. A mutation that inlines the write directly into
    sync_entry -- bypassing the guard entirely -- left that test, and the
    whole rest of the suite, green: nothing previously drove the
    never-overwrite property through sync_entry itself. This does, using a
    small real PDF under a temporary NOTES_ROOT, with the module's own path
    constants monkeypatched to tmp_path so nothing touches the real
    notes/pdf/ or notes/<topic>/ trees (and nothing is left behind after the
    test).
    """
    import fitz

    from scripts import make_thumbs, sync_notes

    repo_root = tmp_path / "repo"
    (repo_root / "notes").mkdir(parents=True)
    monkeypatch.setattr(sync_notes, "REPO_ROOT", repo_root)
    monkeypatch.setattr(sync_notes, "PDF_DIR", repo_root / "notes" / "pdf")
    monkeypatch.setattr(make_thumbs, "THUMB_DIR", repo_root / "notes" / "thumbs")

    notes_root = tmp_path / "notes-root"
    notes_root.mkdir()
    source = notes_root / "note.pdf"
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.save(source)
    doc.close()

    entry = {"slug": "test-note", "source": "note.pdf", "topic": "physics"}

    sync_notes.sync_entry(entry, notes_root)

    stub_path = repo_root / "notes" / "physics" / "test-note.md"
    assert stub_path.is_file(), "sync_entry did not scaffold a stub"
    scaffolded = stub_path.read_text(encoding="utf-8")

    hand_written = scaffolded + "\n\nSupersedes the 2024 version.\n"
    stub_path.write_text(hand_written, encoding="utf-8")

    sync_notes.sync_entry(entry, notes_root)

    assert stub_path.read_text(encoding="utf-8") == hand_written, (
        "sync_entry overwrote an existing stub and destroyed hand-written prose"
    )


def test_sync_entry_rejects_a_slug_republished_under_a_different_topic(tmp_path, monkeypatch):
    """slug de-duplication only happens WITHIN the manifest (load_manifest's
    `seen` set) -- nothing previously checked whether `<slug>.md` already
    existed under a DIFFERENT topic directory on disk. Reproduced by hand
    before this fix: with notes/physics/a-note.md already published,
    syncing {slug: a-note, topic: math} (e.g. after a typo'd or
    since-changed `topic:` in notes.yml) happily scaffolded
    notes/math/a-note.md too, leaving BOTH pages live for one PDF, with no
    test failing.

    This drives that exact scenario through sync_entry with the module's
    path constants monkeypatched to tmp_path (as in the never-overwrites
    test above), and asserts it now raises before writing anything under
    the new topic -- and that the original stub is left untouched.
    """
    import fitz

    from scripts import make_thumbs, sync_notes

    repo_root = tmp_path / "repo"
    (repo_root / "notes" / "physics").mkdir(parents=True)
    monkeypatch.setattr(sync_notes, "REPO_ROOT", repo_root)
    monkeypatch.setattr(sync_notes, "PDF_DIR", repo_root / "notes" / "pdf")
    monkeypatch.setattr(make_thumbs, "THUMB_DIR", repo_root / "notes" / "thumbs")

    existing_stub = repo_root / "notes" / "physics" / "a-note.md"
    existing_stub.write_text(
        '---\ntitle: "A Note"\ndescription: "desc"\ncategories: [physics]\n'
        "image: ../thumbs/a-note.png\n---\n\n{{< pdf-note >}}\n",
        encoding="utf-8",
    )

    notes_root = tmp_path / "notes-root"
    notes_root.mkdir()
    source = notes_root / "a-note.pdf"
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.save(source)
    doc.close()

    entry = {"slug": "a-note", "source": "a-note.pdf", "topic": "math"}

    with pytest.raises(FileExistsError, match="a-note"):
        sync_notes.sync_entry(entry, notes_root)

    assert existing_stub.is_file(), "the original stub must be left untouched"
    assert not (repo_root / "notes" / "math" / "a-note.md").exists(), (
        "sync_entry must not scaffold a second stub for the same slug "
        "under a different topic"
    )
    assert not (repo_root / "notes" / "pdf" / "a-note.pdf").exists(), (
        "sync_entry must raise before copying the PDF, not just before "
        "scaffolding the stub"
    )


def test_notes_root_is_overridable(monkeypatch, tmp_path):
    """The Ubuntu machine's notes tree is not at the macOS default. The env
    var is the only thing that makes the committed manifest portable, so a
    regression here would break the second machine silently.
    """
    from scripts import sync_notes

    monkeypatch.setenv("NOTES_ROOT", str(tmp_path))
    assert sync_notes.notes_root() == tmp_path

    monkeypatch.delenv("NOTES_ROOT", raising=False)
    assert sync_notes.notes_root() == Path(sync_notes.DEFAULT_NOTES_ROOT).expanduser()


def test_internal_planning_docs_are_not_published(site):
    """`_docs/` holds internal design specs and implementation plans — notes
    for whoever is building a feature, not content for site visitors. Quarto
    renders every markdown file in the project by default, so before this
    directory was underscore-prefixed it was silently built into the public
    site as ordinary pages (e.g. _site/docs/plans/...html), leaking
    developer-only planning documents (and the local absolute paths inside
    them, see test_no_local_filesystem_paths_leak_into_site below) to anyone
    who found the URL.

    If this test fails, a directory holding internal-only docs has
    reappeared without a leading underscore (or _quarto.yml's `render:`
    list stopped excluding it). Rename it to start with `_` (Quarto's
    built-in "do not render" convention) rather than adding a page-by-page
    exclusion.
    """
    published_doc_pages = [
        p for p in site.rglob("*.html") if "docs" in p.relative_to(site).parts
    ]
    assert not published_doc_pages, (
        "internal docs were published to the site: "
        f"{[str(p.relative_to(site)) for p in published_doc_pages]} -- "
        "rename the source directory to start with '_' (e.g. docs/ -> "
        "_docs/) so Quarto stops rendering it"
    )


def test_no_local_filesystem_paths_leak_into_site(site):
    """General guard against the whole class of bug, not just one instance
    of it: this is a PUBLIC site, so no generated HTML should ever contain
    a developer's local absolute filesystem path (a macOS/Linux home
    directory such as /Users/patrickoare or /home/someone). Such a path can
    leak in from all sorts of places that have nothing to do with each
    other -- a stray docstring rendered as prose, an error message baked
    into a page at build time, a misconfigured resource path, a debug
    print left in a template -- and every one of those is a future variant
    of the exact defect that motivated this test (internal planning docs
    under docs/ that embedded /Users/patrickoare/... paths and got
    published). Asserting on the pattern directly, instead of only on the
    one directory that leaked this time, catches the next occurrence too.

    Scoped to *.html: notes/pdf/*.pdf and other binary resources are
    copied verbatim and are not expected to be free of such substrings.
    """
    offenders = []
    for path in site.rglob("*.html"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "/Users/" in text or "/home/" in text:
            offenders.append(str(path.relative_to(site)))
    assert not offenders, (
        "generated HTML contains a local absolute filesystem path "
        "('/Users/' or '/home/'), which leaks developer machine layout "
        f"to the public site: {offenders} -- find and remove the source "
        "of the absolute path (e.g. hard-coded paths in prose, docstrings, "
        "or error messages rendered into the page)"
    )


def test_no_local_filesystem_paths_leak_into_tracked_sources():
    """The rendered-output guard above (test_no_local_filesystem_paths_leak_
    into_site) only ever sees a leak *after* it has already reached a public
    page. A tracked planning doc under `_docs/` (excluded from rendering,
    see test_internal_planning_docs_are_not_published) can still hold a
    machine-specific absolute path and fail the project's own stated
    constraint -- "no machine-specific absolute path in any tracked file" --
    without ever tripping the HTML-only check, since it is never rendered at
    all. This scans every git-TRACKED file directly for the same pattern.

    Excludes this file (tests/test_site.py) by exact path, not by weakening
    the search pattern: it legitimately contains the literal strings
    "/Users/" and "/home/" as this test's own and the sibling test's search
    needles, and that is not the defect either test exists to catch.

    Restricted to text files: binary blobs (PDFs, PNGs, woff2 fonts) are not
    expected to be free of arbitrary byte sequences that happen to match,
    and are skipped by attempting a strict UTF-8 decode -- a failure there
    means the file is binary (or at least not the kind of hand-authored
    prose/config this check is for), so it is skipped rather than misread.
    """
    THIS_FILE = "tests/test_site.py"

    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"git ls-files failed:\n{result.stderr}"
    tracked = [line for line in result.stdout.splitlines() if line]
    assert tracked, "git ls-files returned no tracked files"

    offenders = []
    for relpath in tracked:
        if relpath == THIS_FILE:
            continue
        path = REPO_ROOT / relpath
        if not path.is_file():
            continue
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue  # binary file -- not in scope for this check
        if "/Users/" in text or "/home/" in text:
            offenders.append(relpath)

    assert not offenders, (
        "tracked source file(s) contain a local absolute filesystem path "
        f"('/Users/' or '/home/'): {offenders} -- this is a public repo, so "
        "no machine-specific absolute path may land in any tracked file "
        "(rewrite as a relative path, '<repo>/...', or an env var reference)"
    )
