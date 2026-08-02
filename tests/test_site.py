import re

from conftest import read_html, REPO_ROOT


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
    html = read_html(site, "index.html")
    for tab in TABS:
        assert f">{tab}<" in html, f"navbar is missing the {tab} tab"


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

    Task 3 styles `.navbar .nav-link.active`, but its test could only grep the
    compiled CSS text — which proves the rule was authored, not that it matches
    anything. Now that real nav items exist, assert an element actually carries
    both classes. Without this, the underline could be entirely non-functional
    and every other test would still pass.
    """
    html = read_html(site, "about.html")
    both_classes = re.compile(
        r'class="[^"]*(?:\bnav-link\b[^"]*\bactive\b|\bactive\b[^"]*\bnav-link\b)[^"]*"'
    )
    assert both_classes.search(html), (
        "no element carries both 'nav-link' and 'active' classes on about.html — "
        "the theme's underline selector does not match Quarto's markup. "
        "Inspect with: grep -o 'class=\"[^\"]*nav-link[^\"]*\"' _site/about.html "
        "and correct the selector in theme.scss."
    )
