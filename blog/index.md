---
title: "Blog"
listing:
  id: posts
  contents: posts
  type: grid
  sort: "date desc"
  categories: true
  # No `image` field: posts rarely have a natural thumbnail, and requesting one
  # makes Quarto reserve an empty grey block on every card that lacks it. The
  # Notes listing DOES request images, because those get real thumbnails
  # generated from each PDF's first page (scripts/make_thumbs.py).
  fields: [date, title, categories, description]
  feed: false
---

::: {.accent-rule}
:::

Notes on whatever I am thinking about — usually numerical linear algebra,
sometimes lattice field theory, sometimes a textbook I am working through.

::: {.currently-reading}
### Currently reading

Edit this list by hand as books come and go.

- *Modern Quantum Mechanics* — Sakurai & Napolitano
- *Iterative Methods for Sparse Linear Systems* — Saad
:::

:::{#posts}
:::
