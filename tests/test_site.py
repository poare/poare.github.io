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
