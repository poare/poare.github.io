import re

from conftest import extract_element, read_html, REPO_ROOT


def test_homepage_is_generated(site):
    html = read_html(site, "index.html")
    assert "Patrick Oare" in html


FONT_FACES = ["cmunrm", "cmunbx", "cmunti", "cmunbi", "cmunss", "cmuntt"]
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


def compiled_css(site):
    """Concatenate every generated stylesheet — Quarto's output path varies."""
    return "\n".join(
        p.read_text(encoding="utf-8")
        for p in site.rglob("*.css")
    )


def test_accent_colour_reaches_compiled_css(site):
    css = compiled_css(site).lower()
    assert "#750014" in css, "MIT red is missing from the compiled stylesheet"


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
        r"|pink|brown|navy|teal|olive|maroon|silver|aqua|fuchsia|lime)\b"
    )

    offenders = []
    for line in rules_section.splitlines():
        code = line.split("//")[0]          # strip trailing comments
        if not code.strip():
            continue
        if hex_literal.search(code) or colour_func.search(code) or colour_word.search(code):
            offenders.append(line.strip())

    assert offenders == [], f"hard-coded colours found in rules: {offenders}"


TABS = ["About", "CV", "Notes", "Blog"]


def test_all_tabs_present_in_navbar(site):
    """All four tabs appear *inside the navbar* — not merely somewhere on the page."""
    navbar = extract_element(read_html(site, "index.html"), "navbar")
    assert navbar, "no element with class 'navbar' found on index.html"
    for tab in TABS:
        assert f">{tab}<" in navbar, f"navbar is missing the {tab} tab"


def test_tab_pages_are_generated(site):
    for relpath in ["about.html", "cv/index.html",
                    "notes/index.html", "blog/index.html"]:
        assert (site / relpath).is_file(), f"{relpath} was not generated"


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
# rendering was verified by hand in a browser (see task-5-report.md) rather
# than by this suite, since a permanent headless-browser test rig was judged
# disproportionate for this site.

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
    """
    html = read_html(site, "blog/index.html")
    assert '<h3 class="anchored" data-anchor-id="currently-reading">Currently reading</h3>' in html, (
        "'Currently reading' is not rendered as a heading"
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


NOTE = "notes/lattice-qcd/example-note.html"


def test_note_stub_is_generated(site):
    html = read_html(site, NOTE)
    assert "Download PDF" in html, "stub is missing a download link"
    assert "<object" in html or "<iframe" in html, "stub has no embedded viewer"


def test_note_stub_has_indexable_description(site):
    html = read_html(site, NOTE)
    assert "condition number" in html.lower(), (
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
    meta tag is rendered); restored, it passes. See task-7-report.md.
    """
    html = read_html(site, NOTE)
    match = re.search(r'<meta name="description" content="([^"]*)">', html)
    assert match, "no <meta name=\"description\"> tag rendered on the stub page"
    assert "condition number" in match.group(1).lower(), (
        "meta description tag does not contain the front-matter description text"
    )


def test_notes_index_groups_by_topic(site):
    html = read_html(site, "notes/index.html")
    assert "Lattice QCD" in html, "topic heading is missing"
    assert "An example note" in html, "note is missing from its topic listing"


def test_pdf_is_copied_to_output(site):
    """`notes/pdf/orphan-fixture.pdf` is deliberately unreferenced by any
    stub page. Quarto's dependency scanner copies a PDF into _site whenever
    some rendered page links to it (e.g. example-note.pdf, via the stub's
    <object data=...>) — that would make this test pass even with the
    `resources:` key removed from _quarto.yml entirely. The whole point of
    `resources:` is to copy files that *nothing links to yet* (e.g. a PDF
    just dropped into notes/pdf/ before its stub page exists), so only an
    orphan file actually exercises that key. Verified: with `resources:`
    removed, this test fails (orphan-fixture.pdf is absent from _site);
    restored, it passes. See task-7-report.md for the captured output.
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
    thumb = REPO_ROOT / "notes" / "thumbs" / "example-note.png"
    assert thumb.is_file(), "make_thumbs.py did not produce example-note.png"

    html = read_html(site, "notes/index.html")
    listing = extract_element(html, "quarto-listing")
    assert listing, "no element with class 'quarto-listing' rendered"
    assert "thumbs/example-note.png" in listing, (
        "the listing card does not reference the generated thumbnail"
    )


def test_notes_topic_listing_scoped_to_its_own_section(site):
    """The 'Lattice QCD' listing must render as a child of its own heading's
    <section> — and the intro prose above the heading must NOT be swallowed
    into that same section. notes/index.md has the same shape that bit the
    blog page in an earlier task (prose, then a heading, then a generated
    listing div): Pandoc wraps everything after a heading into that
    heading's <section> until a heading of equal-or-higher level closes it.
    This page is designed to grow to many topics, each its own '## Heading'
    followed by its own listing div, so a section that fails to close would
    silently swallow every topic added after it.

    extract_element also raises directly if the id="lattice-qcd" element's
    markup never closes at all (unbalanced depth), which would itself mean
    the section swallowed the rest of the document.
    """
    html = read_html(site, "notes/index.html")
    section = extract_element(html, "lattice-qcd", by="id")
    assert section, "no element with id 'lattice-qcd' found"
    assert 'id="listing-lattice-qcd"' in section, (
        "the topic listing is not nested inside its own topic's <section>"
    )
    assert "Write-ups, derivations" not in section, (
        "the intro prose leaked into the topic section — the heading's "
        "<section> did not close where expected, which would reparent any "
        "topic added after this one"
    )
