---
title: "A Course in Arithmetic"
description: "Working through Serre's book with a friend, one chapter at a time."
# Drop a figure in this directory and uncomment to give the series card an
# image. Without it the card is text-only: theme.scss hides Quarto's empty
# grey placeholder rather than reserving dead space.
# image: thumb.png
listing:
  # Must be a glob, not the bare directory `../../posts`. Each post lives in
  # its own directory as index.md/index.qmd, and from a page two levels down
  # the bare-directory form silently matches nothing at all -- it renders a
  # perfectly valid empty listing rather than raising an error.
  contents: ../../posts/*/index.*
  # Filters on the custom `series` key in each post's front matter, so this
  # page keeps no list of its own parts and needs no edit when one is added.
  include:
    series: arithmetic
  sort: "date asc"
  type: grid
  fields: [image, date, title, description]
  feed: false
---

::: {.accent-rule}
:::

I'm reading Jean-Pierre Serre's *A Course in Arithmetic* with a friend, and
writing up what I learn as I go. The posts assume a little abstract algebra
but try to build up the rest from scratch.
