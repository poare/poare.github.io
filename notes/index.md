---
# Full-width layout, so this page's left gutter matches every other tab.
# See index.md for the rationale.
page-layout: full
title: "Notes"
listing:
  - id: physics
    contents: physics
    type: grid
    sort: "title"
    fields: [image, title, description, categories]
    feed: false
  - id: math
    contents: math
    type: grid
    sort: "title"
    fields: [image, title, description, categories]
    feed: false
  # Sorted by the `order` field rather than by title: these are a numbered
  # series, and an alphabetical title sort puts "Recitation 10" between 1
  # and 2. sync_notes.py writes `order` into each stub from the manifest.
  - id: qft-i
    contents: qft-i
    type: grid
    sort: "order"
    fields: [image, title, description, categories]
    feed: false
---

::: {.accent-rule}
:::

Notes I've accumulated throughout my time in academia. Some are complete, others are remarkably less so. I plan to come back and finish most of these notes eventually: if there's a particular topic you'd like to hear about that I haven't finished writing up, let me know!

## Physics

Notes about physics, primarily particle physics. Anything labeled "part3" was constructed when I was studying for the MIT Physics Part III exam, which is an oral qualifying exam that you must pass to enter the second stage of your doctorate. When I took the exam, any question related to quantum field theory or the Standard Model was fair game... it was quite a stressful semester!

:::{#physics}
:::

## Math

:::{#math}
:::

## QFT I (8.323) Recitation Notes

When I was a graduate student at MIT, I TA'd for Relativistic Quantum Field Theory I (8.323) two years in a row. I got a lot of freedom in shaping the recitations how I wanted to, and doing it two years in a row let me iterate on my recitations and improve them. QFT requires an immense about of mathematical machinery; so much so that the first semester's course is usually just raw calculation and hard to remember that you're in a physics class. I tried to make the recitations complement the lectures and also give the students a taste of the physics to come in QFT II and III. It was a lot of fun, and definitely one of the most rewarding experiences of my graduate school career. 

:::{#qft-i}
:::
