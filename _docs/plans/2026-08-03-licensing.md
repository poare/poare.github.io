# Licensing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** License the site's prose under CC BY 4.0 and its code under MIT, satisfy the SIL Open Font License obligations for the Computer Modern Unicode fonts the repo redistributes, and surface all three in a footer on every page.

**Architecture:** Four new files carrying licence texts and attribution, then a `page-footer` in `_quarto.yml` pointing at them. Licence texts are downloaded from canonical sources rather than transcribed, because they are legal documents where a dropped clause matters. Spec: [../specs/2026-08-03-licensing-design.md](../specs/2026-08-03-licensing-design.md).

**Tech Stack:** Quarto 1.10.18 (pinned in CI), Markdown, pytest, curl.

## Global Constraints

- **Quarto is pinned to 1.10.18** in `.github/workflows/publish.yml`. Do not change the pin.
- **CI runs no Python.** Do not add a Python step to any workflow file.
- **Colours live in `theme.scss` only.** `test_colours_are_variables_not_literals` enforces this.
- **Every top-level page declares `page-layout: full`.** Two existing tests enforce this.
- **No machine-specific absolute path in any tracked file.** `test_no_local_filesystem_paths_leak_into_site` enforces this over tracked sources *and* rendered output.
- **The font family names `CMU Serif` and `CMU Typewriter` are NOT to be renamed.** Subsetting is a modification under the OFL, but the Reserved Font Name is "Computer Modern Unicode fonts", which those names do not contain. This was decided deliberately; renaming is out of scope.
- **Licence texts must be fetched, never typed from memory.** A transcription error in a legal document is a real defect.
- Run the suite with `pytest tests/ -v` from the repo root after `source .venv/bin/activate`. The default `python3` on PATH lacks `fitz`. The suite currently has 57 tests, all passing.
- Copyright holder is **Patrick Oare**; the year is **2026**.

---

### Task 1: Licence files and font attribution

**Files:**
- Create: `LICENSE`, `LICENSE-CONTENT`, `assets/fonts/OFL.txt`, `assets/fonts/NOTICE`
- Modify: `tests/test_site.py` (add tests at the end of the file)
- Modify: `README.md` (add a Licensing section)

**Interfaces:**
- Consumes: nothing.
- Produces: the four files above, at those exact paths. Task 2's footer links to `LICENSE`, `LICENSE-CONTENT` and `assets/fonts/OFL.txt`.

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/test_site.py`:

```python
LICENCE_FILES = ["LICENSE", "LICENSE-CONTENT", "assets/fonts/OFL.txt",
                 "assets/fonts/NOTICE"]


def test_licence_files_exist_and_are_not_empty():
    """Every licence the footer points at must actually be in the repo.

    A footer promising CC BY with no licence file behind it is worse than
    no notice at all: it tells people they may reuse the work while giving
    them nothing to rely on.
    """
    for relpath in LICENCE_FILES:
        path = REPO_ROOT / relpath
        assert path.is_file(), f"{relpath} is missing"
        assert path.stat().st_size > 200, (
            f"{relpath} is {path.stat().st_size} bytes — suspiciously small "
            "for a licence file; check the download did not truncate"
        )


def test_licence_texts_contain_their_operative_clauses():
    """The licence texts are downloaded over a network, so the failure to
    guard against is a truncated or error-page response committed silently.
    Checking for clauses unique to each licence proves the real text landed,
    where a size check alone would pass on an HTML error page.
    """
    ofl = (REPO_ROOT / "assets" / "fonts" / "OFL.txt").read_text(encoding="utf-8")
    assert "Reserved Font Name" in ofl, "OFL.txt lacks the Reserved Font Name clause"
    assert "SIL OPEN FONT LICENSE" in ofl.upper(), "OFL.txt is not the SIL OFL"

    content = (REPO_ROOT / "LICENSE-CONTENT").read_text(encoding="utf-8")
    assert "Attribution 4.0 International" in content, (
        "LICENSE-CONTENT is not the CC BY 4.0 legal code"
    )
    assert "ShareAlike" not in content, (
        "LICENSE-CONTENT looks like a ShareAlike licence, not plain CC BY"
    )

    mit = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in mit, "LICENSE is not the MIT licence"
    assert "Patrick Oare" in mit, "LICENSE has no copyright holder"
    assert "<year>" not in mit and "[year]" not in mit, (
        "LICENSE still contains an unfilled template placeholder"
    )


def test_font_notice_credits_upstream():
    """The OFL requires the copyright notice to travel with the fonts. The
    faces here are subsetted copies of someone else's work; the NOTICE is
    what says so.
    """
    notice = (REPO_ROOT / "assets" / "fonts" / "NOTICE").read_text(encoding="utf-8")
    assert "Panov" in notice, "NOTICE does not credit the font's author"
    assert "cm-unicode.sourceforge.io" in notice, "NOTICE has no upstream URL"
    assert "subset" in notice.lower(), (
        "NOTICE does not record that these are subsetted, i.e. modified, copies"
    )
```

- [ ] **Step 2: Run them to verify they fail**

```bash
source .venv/bin/activate && pytest tests/test_site.py -k "licence or font_notice" -v
```

Expected: 3 failed, the first with `LICENSE is missing`.

- [ ] **Step 3: Download the two licence texts**

```bash
curl -sL https://creativecommons.org/licenses/by/4.0/legalcode.txt -o LICENSE-CONTENT
curl -sL https://openfontlicense.org/documents/OFL.txt -o assets/fonts/OFL.txt
wc -c LICENSE-CONTENT assets/fonts/OFL.txt
```

Expected: `LICENSE-CONTENT` around 18,657 bytes, `OFL.txt` several thousand. If
either is under 1,000 bytes you have fetched an error page — stop and report
rather than committing it.

- [ ] **Step 4: Add the scope preamble to `LICENSE-CONTENT`**

Prepend these lines to the file, above the downloaded legal code, leaving the
legal code itself untouched:

```
The prose on this site — page text, blog posts, the notes and their PDFs,
and the thumbnails generated from them — is licensed under the Creative
Commons Attribution 4.0 International licence, reproduced in full below.

Code is NOT covered by this licence. See LICENSE for the MIT terms that
apply to the scripts, tests, theme and Quarto extension.

Some notes may reproduce figures, tables or quotations from textbooks and
papers. That third-party material remains under its own terms and is not
sublicensed here; this licence covers only the author's own expression.

The fonts distributed under assets/fonts/ are third-party works under the
SIL Open Font License. See assets/fonts/OFL.txt and assets/fonts/NOTICE.

----------------------------------------------------------------------
```

- [ ] **Step 5: Fill in the OFL header**

The downloaded `assets/fonts/OFL.txt` opens with a template header containing
`<dates>`, `<Copyright Holder>` and `<Reserved Font Name>` placeholders, plus
extra example lines for additional copyright holders. Replace that whole
placeholder block — every line from the first `Copyright (c)` through the last
placeholder line before the blank line preceding `This Font Software is
licensed under the SIL Open Font License, Version 1.1.` — with exactly:

```
Copyright (c) 2003-2009, Andrey V. Panov (panov@canopus.iacp.dvo.ru),
with Reserved Font Name "Computer Modern Unicode fonts".
```

Leave everything from `This Font Software is licensed under...` onward exactly
as downloaded. Verify no placeholder survives:

```bash
grep -c "<Copyright Holder>\|<dates>\|<Reserved Font Name>" assets/fonts/OFL.txt
```

Expected: `0`.

- [ ] **Step 6: Write `LICENSE` (MIT)**

```
MIT License

Copyright (c) 2026 Patrick Oare

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 7: Write `assets/fonts/NOTICE`**

```
Computer Modern Unicode fonts
=============================

The .woff2 files in this directory are SUBSETTED COPIES of the Computer
Modern Unicode fonts by Andrey V. Panov — that is, modified versions. They
were produced by scripts/subset_fonts.py, which strips glyphs outside the
Unicode ranges this site needs in order to cut download size.

  Upstream:  https://cm-unicode.sourceforge.io/
  CTAN:      https://ctan.org/pkg/cm-unicode
  Copyright: (c) 2003-2009 Andrey V. Panov
  Licence:   SIL Open Font License, Version 1.1 — see OFL.txt in this
             directory for the full text.

The fonts' own metadata records: "Converted by Andrey V. Panov from TeX
fonts. Some glyphs are copied from Blue Sky fonts released by AMS."

The CSS declares these faces as "CMU Serif" and "CMU Typewriter". The
licence's Reserved Font Name is "Computer Modern Unicode fonts", which
those names do not contain, so the subsetted copies keep their original
family names deliberately.
```

- [ ] **Step 8: Run the tests**

```bash
source .venv/bin/activate && pytest tests/test_site.py -k "licence or font_notice" -v
```

Expected: 3 passed.

- [ ] **Step 9: Add the README section**

Insert immediately before the `## First-time setup on a new machine` heading:

```markdown
## Licensing

Two licences, because prose and code want different terms:

- **Prose, notes and their PDFs** — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Reuse and adapt freely with attribution. See `LICENSE-CONTENT`.
- **Code** — MIT. Scripts, tests, `theme.scss`, the Quarto extension. See `LICENSE`.

`LICENSE` holds the MIT text because GitHub's licence detector reads that
filename; it does not mean MIT covers the writing.

The fonts under `assets/fonts/` are third-party work under the SIL Open Font
License — subsetted copies of Computer Modern Unicode by Andrey V. Panov. That
licence obliges us to ship its text and copyright notice, which is what
`assets/fonts/OFL.txt` and `assets/fonts/NOTICE` are for. **Do not delete them,
and do not rename the font families.**
```

- [ ] **Step 10: Run the full suite**

```bash
source .venv/bin/activate && pytest tests/ -v
```

Expected: 60 passed.

- [ ] **Step 11: Commit**

```bash
git add LICENSE LICENSE-CONTENT assets/fonts/OFL.txt assets/fonts/NOTICE tests/test_site.py README.md
git commit -m "docs: license content CC BY 4.0, code MIT, and comply with the font OFL"
```

---

### Task 2: Site footer

**Files:**
- Modify: `_quarto.yml` (the `website:` block, and `resources:`)
- Modify: `tests/test_site.py` (add tests at the end of the file)

**Interfaces:**
- Consumes: `LICENSE`, `LICENSE-CONTENT` and `assets/fonts/OFL.txt` from Task 1.
- Produces: a footer on every rendered page.

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/test_site.py`:

```python
def test_licence_footer_renders_on_every_page_depth(site):
    """The footer must reach nested pages, not just the root.

    Quarto rewrites relative hrefs by page depth, so a footer that works on
    the homepage can still 404 from inside notes/physics/. Both depths are
    checked for that reason.
    """
    for relpath in ["index.html", "notes/physics/lorentz-poincare-groups.html"]:
        html = read_html(site, relpath)
        footer = extract_element(html, "nav-footer")
        assert footer, f"no element with class 'nav-footer' on {relpath}"
        assert "Patrick Oare" in footer, f"no copyright holder in the footer on {relpath}"
        assert "CC BY 4.0" in footer, f"no content licence named in the footer on {relpath}"
        assert "MIT" in footer, f"no code licence named in the footer on {relpath}"


def test_font_licence_is_served_with_the_fonts(site):
    """The OFL wants its text to travel with the fonts it covers, and the
    fonts are served to every visitor. Committing OFL.txt to the repo covers
    source redistribution; this covers the built site.
    """
    served = site / "assets" / "fonts" / "OFL.txt"
    assert served.is_file(), (
        "assets/fonts/OFL.txt was not copied into _site — check the "
        "resources entry in _quarto.yml"
    )
    assert "Reserved Font Name" in served.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run them to verify they fail**

```bash
source .venv/bin/activate && pytest tests/test_site.py -k "footer or font_licence_is_served" -v
```

Expected: 2 failed — no `nav-footer` element exists, and `OFL.txt` is not in the output.

- [ ] **Step 3: Add the footer and the resources entry**

In `_quarto.yml`, inside the `website:` block, after the `navbar:` section, add:

```yaml
  # A licence nobody can find protects nothing, so the terms go on every page.
  # Quarto rewrites these relative hrefs per page depth, so they resolve from
  # nested pages too.
  page-footer:
    center: |
      &copy; 2026 Patrick Oare &middot;
      prose and notes under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) &middot;
      code under [MIT](LICENSE) &middot;
      typeset in Computer Modern Unicode ([OFL](assets/fonts/OFL.txt))
```

Then add to the `resources:` list under `project:`:

```yaml
    # The footer links to both of these, and neither is a Quarto page, so
    # they must be copied explicitly or the links 404. The OFL entry is also
    # an obligation in its own right: the licence has to ship with the fonts,
    # which are served to every visitor.
    - LICENSE
    - assets/fonts/OFL.txt
```

- [ ] **Step 4: Run the tests**

```bash
source .venv/bin/activate && pytest tests/test_site.py -k "footer or font_licence_is_served" -v
```

Expected: 2 passed.

If `test_licence_footer_renders_on_every_page_depth` fails on the class name,
inspect what Quarto actually emitted and match it:

```bash
grep -o 'class="[^"]*footer[^"]*"' _site/index.html
```

Use the real class in the test rather than forcing the markup to match a guess.

- [ ] **Step 5: Verify the footer's own links resolve**

The footer links to two files that are not Quarto pages. Confirm they reached
the output and that the hrefs point at them from a nested page:

```bash
source .venv/bin/activate && quarto render >/dev/null 2>&1
ls -la _site/LICENSE _site/assets/fonts/OFL.txt
grep -o 'href="[^"]*OFL.txt"' _site/notes/physics/lorentz-poincare-groups.html
```

Expected: both files listed, and the href resolving upward (e.g.
`../../assets/fonts/OFL.txt`).

Note that `LICENSE` has no file extension, so a browser may download it rather
than display it inline. That is acceptable — GitHub's licence detector requires
this exact filename, and being downloaded is a small cost against being
detected. Do not rename it to `LICENSE.txt` to make the browser happier.

- [ ] **Step 6: Run the full suite**

```bash
source .venv/bin/activate && pytest tests/ -v
```

Expected: 62 passed.

- [ ] **Step 7: Commit**

```bash
git add _quarto.yml tests/test_site.py
git commit -m "feat: show the licence terms in a footer on every page"
```

---

## Notes for the implementer

- **Do not rename the font families.** `CMU Serif` and `CMU Typewriter` stay as they are; this was decided deliberately and is recorded in the spec.
- **Do not transcribe a licence text by hand.** Both are downloaded in Task 1 Step 3. If a download fails, stop and report rather than typing from memory.
- **Do not commit `index.md`.** It carries an unrelated uncommitted edit belonging to the author.
- **Do not push.** The author pushes.
- If `curl` has no network access in your environment, report BLOCKED. Do not substitute a summary or a link in place of the licence text.
