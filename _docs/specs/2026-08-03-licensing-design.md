# Licensing the site: content, code, and redistributed fonts

Status: approved 2026-08-03.

## Problem

The repository has no licence file of any kind. Default copyright therefore
applies: everything is "all rights reserved". The notes are readable but nobody
may legally redistribute or adapt them, and nobody may reuse the build scripts,
the theme, or the Quarto shortcode. That is not the intended state for an
academic site whose purpose is to make notes useful to other people.

Separately, and more pressingly, **the repository redistributes third-party
fonts without shipping their licence.** `assets/fonts/` contains five subsetted
Computer Modern Unicode faces. Redistribution — which committing them and
serving them to every visitor plainly is — carries obligations set by the
upstream licence, not by preference.

## Findings

The font files' own `name` table records:

> Converted by Andrey V. Panov from TeX fonts. Some glyphs are copied from Blue
> Sky fonts released by AMS.

version 0.7.0. They carry no licence field. The upstream project (CTAN package
`cm-unicode`, <https://cm-unicode.sourceforge.io/>) licenses the fonts under the
**SIL Open Font License, Version 1.1**, copyright Andrey V. Panov 2003–2009,
with the Reserved Font Name "Computer Modern Unicode fonts".

## Decisions

**Prose and notes: CC BY 4.0.** Attribution is what academics actually want,
and CC BY delivers exactly that while permitting the reuse that makes notes
useful — translation, adaptation into course material, inclusion in open
educational resources.

CC BY-NC was considered and rejected. "Non-commercial" is undefined in
practice — a blog carrying ads, a paid course, a company reading group — so it
deters good-faith reuse while doing nothing against bad-faith use. It also makes
the notes ineligible for OER collections and incompatible with Wikipedia, which
requires BY-SA or freer.

CC BY-SA was considered and rejected: share-alike would keep derivatives open,
but it cannot be mixed into differently-licensed work, so someone folding a
section into their own CC BY course notes could not.

**Code: MIT.** Short, universally recognised, and compatible with essentially
everything.

Licensing the code under CC BY was rejected. Creative Commons recommends
against CC licences for software: they do not address patents, say nothing
about source versus binary distribution, and are incompatible with common
open-source licences, so nobody could safely mix the code into an existing
project. Apache 2.0 was rejected as disproportionate — its patent grant and
change-notice requirements serve projects with patent exposure or corporate
contributors, neither of which applies to a personal site's build scripts.

**Fonts: comply with the OFL.** This is an obligation, not a choice. Ship the
licence text and the upstream copyright notice alongside the fonts.

**Font family names are left unchanged.** The OFL forbids a *modified* version
from using the Reserved Font Name, and subsetting is modification. The reserved
name is "Computer Modern Unicode fonts"; the CSS declares `CMU Serif` and
`CMU Typewriter`, which do not contain that string. Shipping subsetted OFL
fonts under their original family names is common and widely tolerated.
Renaming would touch `theme.scss`, `scripts/subset_fonts.py` and the tests for
no practical benefit. Recorded here so the reasoning is visible if it is ever
revisited.

## Non-goals

- **No relicensing of third-party material inside the notes.** CC BY asserts
  rights the author holds. A figure reproduced from a textbook or paper stays
  under its own terms and cannot be sublicensed. `LICENSE-CONTENT` says so
  explicitly rather than leaving a false implication.
- **No per-file licence headers.** Two licence files and a footer cover it; a
  header in every script would be noise on a project this size.
- **No CLA, no contribution policy.** Nobody else contributes.

## Design

### Files

| Path | Contents |
|---|---|
| `LICENSE` | MIT, copyright Patrick Oare, covering all code |
| `LICENSE-CONTENT` | CC BY 4.0 legal code, plus a preamble stating scope and the third-party caveat |
| `assets/fonts/OFL.txt` | SIL OFL 1.1, verbatim, with Panov's copyright and the Reserved Font Name filled into its header |
| `assets/fonts/NOTICE` | Where the fonts came from, that they are subsetted, and a pointer to `OFL.txt` |

Two existing files are modified: `_quarto.yml` gains the `page-footer` and an
`assets/fonts/OFL.txt` entry under `resources:` so the licence is served, and
`README.md` gains the Licensing section.

`LICENSE` holds MIT because GitHub's licence detector reads that exact filename;
the repository will show "MIT" in its sidebar, which is correct for the part a
passer-by might reuse. The README gains a Licensing section explaining the split
so nobody assumes MIT covers the notes.

**Licence texts are fetched from canonical sources, not transcribed.** These
are legal documents where a typo matters, and both are verified reachable:

- OFL 1.1 — <https://openfontlicense.org/documents/OFL.txt>
- CC BY 4.0 — <https://creativecommons.org/licenses/by/4.0/legalcode.txt>

### Site-visible notice

A licence nobody can find protects nothing. Quarto's `page-footer` puts one
line on every page:

> © 2026 Patrick Oare. Prose and notes under CC BY 4.0; code under MIT.
> Typeset in Computer Modern Unicode (OFL).

with CC BY 4.0, MIT and OFL linked — the first two to their canonical URLs, the
OFL to the copy served from this site.

## Testing

| Test | Failure it catches |
|---|---|
| All four licence files exist and are non-empty | A licence referenced by the footer but absent from the repo |
| `OFL.txt` contains its operative clauses (the "Reserved Font Name" condition and the permission grant), and `LICENSE-CONTENT` contains CC BY 4.0's | A truncated or placeholder download silently committed — the failure mode of fetching a legal text over the network |
| `LICENSE` names MIT and carries a copyright line | An empty template committed by accident |
| The footer renders on a top-level page and on a nested notes page | A footer configured but not reaching every page depth |
| `assets/fonts/OFL.txt` is present in the built output | The licence not travelling with the fonts it covers — the fonts are served to every visitor, so the licence must be reachable too |

The footer's external links are deliberately not fetched, for the reason
established when the Contact page was built: a suite that makes network calls
fails for reasons unrelated to this site.

## Maintenance

The footer's copyright year is written once in `_quarto.yml`. It is static; no
mechanism updates it, and nothing breaks if it lags. A stale year is a
cosmetic wart, not a legal defect.
