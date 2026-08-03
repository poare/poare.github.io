# Contact page and professional links

Status: approved 2026-08-02.

## Problem

The site has no way to reach its author and no links to his professional
profiles. Both were listed as open items in the setup doc. They are treated as
one piece of work because they share a page and would otherwise force the same
placement decision twice.

## Decisions taken, and why

**A plain email address, no contact form.** GitHub Pages serves static files
and cannot process a form POST, so a working form means a third-party endpoint
(Formspree, Web3Forms and similar): an external dependency that can break,
start charging, or inject its own branding, and which sits between a
correspondent and the author. The people who contact an academic site are
mostly colleagues, students and collaborators who will send email regardless,
and the address is already discoverable from published papers and INSPIRE, so a
form would add friction while protecting little. If spam later becomes a real
problem, obfuscating the address is a small change on top of this.

**Named text links, not an icon row.** Two reasons beyond taste. INSPIRE-HEP
has no widely recognised icon — unlike GitHub and LinkedIn — so in an icon row
it becomes an unlabelled glyph, and it is the most important of the four in
this field. And the site currently loads no icon font: Quarto's navbar icons
pull in Bootstrap Icons, a real download for four links, on a site that is
deliberately typographic (self-hosted Computer Modern, text underlines rather
than borders).

**Links live on the Contact page, not the CV or the navbar.** One place, where
a visitor looking for them will go.

## Non-goals

- **No contact form**, per the reasoning above.
- **No email obfuscation.** The address is published plainly. This is a
  deliberate trade, not an oversight.
- **No shared metadata value for the email.** It appears on exactly one page,
  so a single-source-of-truth mechanism would be machinery without a purpose.
  The affiliation will also appear on the homepage; the author has explicitly
  decided that duplication needs no special treatment.
- **No liveness checking of external URLs.** See Testing.

## Design

### New file: `contact.md`

At the repo root, beside `about.md`. Front matter follows every other
top-level page:

```yaml
---
# Full-width layout, so this page's left gutter matches every other tab.
# See index.md for the rationale.
page-layout: full
title: "Contact"
---
```

Body: an `.accent-rule` div, then three `##` sections.

**Email** — `poare@bnl.gov`, rendered as a `mailto:` link.

**Address**

```
Physics Department, Building 510
Brookhaven National Laboratory
P.O. Box 5000
Upton, NY 11973-5000
```

**Elsewhere** — four named links as a bullet list, one per line. A list rather
than an inline run separated by punctuation: screen readers announce a list and
its length, and adding a fifth profile later is one more line rather than a
re-flowed sentence. The visible text is the service name, never the raw URL, so
the page reads as prose:

| Text | URL |
|---|---|
| INSPIRE-HEP | `https://inspirehep.net/authors/2134227` |
| ORCID | `https://orcid.org/0000-0002-8244-6158` |
| GitHub | `https://github.com/poare` |
| LinkedIn | `https://www.linkedin.com/in/patrick-oare-50a750125/` |

The GitHub URL is stored with its `https://` scheme. Written as `github.com/poare`
it would be treated as a relative path and resolve to a 404 on this site.

### Modified: `_quarto.yml`

A fifth navbar entry after Blog:

```yaml
      - text: "Contact"
        href: contact.md
```

### Modified: `tests/test_site.py`

Three existing structures gain the new page, so most coverage comes for free:

- `TABS` — the navbar test then asserts Contact appears in the navbar itself
- the list in `test_tab_pages_are_generated`
- `TOP_LEVEL_PAGES` — which makes both layout guards enforce that Contact's
  gutters match the other tabs, and that the rendering followed

## Testing

One new test beyond the three extensions above: assert the page contains a
`mailto:` link whose address matches exactly, and that all four profile URLs
appear as absolute `https://` hrefs. A typo in a profile URL is otherwise
invisible until a visitor clicks it and lands on a 404, and a relative-looking
GitHub href would break silently in the same way.

**External URLs are deliberately not fetched.** A suite that makes network
calls fails when LinkedIn is slow, when a runner has no egress, or when a
service rate-limits — none of which mean the site is broken. A green suite that
depends on a third party being up is worse than no test at all. The test
verifies what this repo controls: that the links are well-formed and present.

## Maintenance

Changing jobs means editing the Email and Address sections of `contact.md` —
plain prose in one file, nothing generated, nothing to regenerate.

The homepage does not currently state an affiliation. When it gains one during
the planned research-interests rewrite, it becomes a second place to update.
The author has decided that duplication is acceptable and needs no shared
metadata value; this note exists so the second location is not forgotten.
