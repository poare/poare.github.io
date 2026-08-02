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
    offenders = [
        line for line in rules_section.splitlines()
        if not line.strip().startswith("//")
        and ("rgb" in line or "#" in line.split("//")[0])
    ]
    assert offenders == [], f"hard-coded colours found in rules: {offenders}"
