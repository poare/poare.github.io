# Contact Page and Professional Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Contact tab carrying an email address, a postal address, and four named links to the author's professional profiles.

**Architecture:** One new markdown page at the repo root, one new navbar entry, and extensions to three existing test structures so the new page inherits the navbar, generation and layout guards that already cover every other tab. No new dependencies, no icon font, no third-party services. Spec: [../specs/2026-08-02-contact-and-profile-links-design.md](../specs/2026-08-02-contact-and-profile-links-design.md).

**Tech Stack:** Quarto 1.10.18 (pinned in CI), Markdown, pytest.

## Global Constraints

- **Quarto is pinned to 1.10.18** in `.github/workflows/publish.yml`. Do not change the pin.
- **CI runs no Python.** Do not add a Python step to any workflow file.
- **Colours live in `theme.scss` only.** Do not introduce a colour literal anywhere else; `test_colours_are_variables_not_literals` enforces this.
- **Prose files are `.md`, never `.qmd`.** `test_tracked_qmd_files_execute_code` fails any tracked `.qmd` that executes no code.
- **Every top-level page declares `page-layout: full`** so left gutters match site-wide. Two existing tests enforce this.
- **No machine-specific absolute path in any tracked file.** `test_no_local_filesystem_paths_leak_into_site` enforces this over tracked sources and rendered output.
- **No icon font, no external form service, no email obfuscation** — all three are explicit non-goals in the spec.
- Run the suite with `pytest tests/ -v` from the repo root, after `source .venv/bin/activate`. The default `python3` on PATH lacks `fitz`. The suite currently has 56 tests, all passing.

---

### Task 1: Contact page, navbar entry, and tests

**Files:**
- Create: `contact.md`
- Modify: `_quarto.yml` (the `navbar: left:` list)
- Modify: `tests/test_site.py` (`TABS` at line 144; the list in `test_tab_pages_are_generated` at line 156; `TOP_LEVEL_PAGES` at line ~162; one new test)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the page `contact.html` at the site root, reachable from the navbar of every page.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_site.py`, immediately after `test_tab_pages_are_generated`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

```bash
source .venv/bin/activate && pytest tests/test_site.py::test_contact_page_publishes_email_and_profiles -v
```

Expected: FAIL. The `read_html` helper asserts the file exists, so the failure is `expected generated file contact.html to exist`.

- [ ] **Step 3: Create `contact.md`**

Write exactly this file at the repo root:

```markdown
---
# Full-width layout, so this page's left gutter matches every other tab.
# See index.md for the rationale.
page-layout: full
title: "Contact"
---

::: {.accent-rule}
:::

## Email

[poare@bnl.gov](mailto:poare@bnl.gov)

## Address

Physics Department, Building 510\
Brookhaven National Laboratory\
P.O. Box 5000\
Upton, NY 11973-5000

## Elsewhere

- [INSPIRE-HEP](https://inspirehep.net/authors/2134227)
- [ORCID](https://orcid.org/0000-0002-8244-6158)
- [GitHub](https://github.com/poare)
- [LinkedIn](https://www.linkedin.com/in/patrick-oare-50a750125/)
```

Note the trailing backslashes in the Address block. They are Pandoc's hard line
break. Without them the four lines collapse into one wrapped paragraph, because
Markdown treats consecutive lines as the same paragraph.

- [ ] **Step 4: Add the navbar entry**

In `_quarto.yml`, append to the `navbar: left:` list, after the Blog entry:

```yaml
      - text: "Contact"
        href: contact.md
```

- [ ] **Step 5: Extend the three existing test structures**

In `tests/test_site.py`, change `TABS` (line 144) to:

```python
TABS = ["About", "CV", "Notes", "Blog", "Contact"]
```

Change the docstring of `test_all_tabs_present_in_navbar` — it currently says
"All four tabs", which is now wrong:

```python
    """Every tab appears *inside the navbar* — not merely somewhere on the page."""
```

Change the list in `test_tab_pages_are_generated` to:

```python
    for relpath in ["about.html", "cv/index.html", "notes/index.html",
                    "blog/index.html", "contact.html"]:
```

Add `contact.md` to `TOP_LEVEL_PAGES`:

```python
TOP_LEVEL_PAGES = {
    "index.md": "index.html",
    "about.md": "about.html",
    "cv/index.md": "cv/index.html",
    "notes/index.md": "notes/index.html",
    "blog/index.md": "blog/index.html",
    "contact.md": "contact.html",
}
```

Also update that dict's comment, which says "the five top-level pages":

```python
# Source file -> generated page, for the top-level pages that must share one
# layout. Kept together so a new tab is added to both halves at once.
```

- [ ] **Step 6: Run the full suite**

```bash
source .venv/bin/activate && pytest tests/ -v
```

Expected: 57 passed. The new test passes, and the two layout guards now also
cover `contact.md` — proving the new page's gutters match the other tabs.

If `test_every_top_level_page_declares_the_full_layout` fails, the
`page-layout: full` line is missing from `contact.md`'s front matter.

- [ ] **Step 7: Prove the new test discriminates**

Temporarily change the GitHub link in `contact.md` from
`https://github.com/poare` to `github.com/poare` (dropping the scheme — the
exact mistake the spec calls out), then run:

```bash
source .venv/bin/activate && pytest tests/test_site.py::test_contact_page_publishes_email_and_profiles -v
```

Expected: FAIL with "contact page is missing a link to https://github.com/poare".

Restore the scheme and confirm it passes again. Report both observations.

- [ ] **Step 8: Verify the address renders as four lines**

```bash
source .venv/bin/activate && quarto render >/dev/null 2>&1 && grep -c "<br>" _site/contact.html
```

Expected: `3` or more — three hard breaks between the four address lines. If it
prints `0`, the trailing backslashes were lost and the address rendered as one
run-on paragraph.

- [ ] **Step 9: Commit**

```bash
git add contact.md _quarto.yml tests/test_site.py
git commit -m "feat: add a Contact page with email, address and profile links"
```

---

## Notes for the implementer

- **Do not add an icon font, a contact form, or email obfuscation.** All three are explicit non-goals in the spec, decided deliberately.
- **Do not commit `index.md`.** It carries an unrelated uncommitted edit belonging to the author.
- **Do not push.** The author pushes.
- The `.accent-rule` div is the thin red rule under the page title, used on every other top-level page. It is styled in `theme.scss`; do not add styling for it here.
