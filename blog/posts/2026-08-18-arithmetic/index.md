---
title: "A Course in Arithmetic: Prerequesites"
date: 2026-08-18
categories: [math, arithmetic, technical, book-club]
series: arithmetic
---

{{< include _series-banner.md >}}

This is my first book club post! I'm reading through Jean-Pierre Serre's [A Course in Arithmetic](https://link.springer.com/book/10.1007/978-1-4684-9884-4) with a friend and want to write some technical blog posts to go along with what I learn as I write the book.

I'll be starting Chapter 1 soon, but I thought I'd begin by dredging up my memory of Math 250A at Berkeley, which was the graduate abstract algebra course. The book begins with an introduction to field theory. It's not what I would think of now as field theory (as a physicist), but *real* field theory: the study of the algebraic object called a field.

A **field** is an algebraic object that generalizes structures like $\mathbb Q, \mathbb R$, or $\mathbb C$: it's a set that you can add or multiply on, and all non-zero elements have multiplicative inverses. Formally, a field is a triple $(F, +, *)$ that is a commutative division ring with identity. I like to think of a field as two groups: 

1. An additive abelian group $(F, +)$ with identity $0$ and additive inverse $-x$, and
2. A multiplicative abelian group $(F^*, \cdot)$ where $F^* = \{x\in F : x\neq 0\}$ is the group of non-zero elements, with identity $1\neq 0$ and inverse $x^{-1}$ (this is $1/x$ in the usual number fields we're used to).

I could write out these axioms explicitly, but there's like 8 of them and it's kind of a pain: they tell you the same information, which is that you have addition and multiplication which work nicely with one another (distribute), are commutative, and have inverses. 

Infinite fields are well and good, but finite fields are where things get strange. 

{{< include _series-nav.md >}}
