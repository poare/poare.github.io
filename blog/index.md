---
title: "Blog"
listing:
  id: posts
  contents: posts
  type: grid
  sort: "date desc"
  categories: true
  # Posts that have an image (e.g. a figure from an executed notebook) show it.
  # Posts without one get a text-only card: theme.scss hides Quarto's empty
  # grey `.listing-item-img-placeholder` rather than reserving dead space.
  fields: [image, date, title, categories, description]
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
