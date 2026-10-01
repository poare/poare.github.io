---
# Full-width layout, so this page's left gutter matches every other tab.
# See index.md for the rationale. The category filter still occupies the
# right margin column here — the full layout preserves it.
page-layout: full
title: "Blog"
listing:
  # The Series row: one card per directory under blog/series/. Title, blurb
  # and figure all come from that series' own landing page front matter, so
  # a series is described in exactly one place and this row never needs
  # editing when one is added.
  - id: series
    contents: series/*/index.md
    type: grid
    sort: "title"
    fields: [image, title, description]
    feed: false
  - id: posts
    contents: posts
    type: grid
    sort: "date desc"
    categories: true
    # Posts that have an image (e.g. a figure from an executed notebook) show it.
    # Posts without one get a text-only card: theme.scss hides Quarto's empty
    # grey `.listing-item-img-placeholder` rather than reserving dead space.
    fields: [image, date, title, categories, description]
    feed: false
format:
  html:
    # Scroll arrows for the Series row. Page-level rather than site-wide:
    # this is the only page with a Series row. Quarto merges this with the
    # project-level format block, so the theme and favicon still apply --
    # test_blog_page_keeps_project_format_settings guards that.
    include-after-body: ../assets/series-row.html
---

::: {.accent-rule}
:::

One of the things I love to do in my free time is read math and physics textbooks. I find that whenever I read a textbook, the only way for me to truly understand what I'm reading is to take the time to write about it and think through the logical arguments myself. As such, I'll be documenting the books I'm reading here, although these will be quite technical. I also hope to write some less technical "series" posts about subjects I am an expert on which I find interesting. 

::: {.currently-reading}
### Currently reading

- *A Course in Arithmetic* — Jean Pierre Serre
- *A Course in Functional Analysis* — John B. Conway
:::

## Series

Multi-part writing, in order.

:::{#series}
:::

## All posts

:::{#posts}
:::
