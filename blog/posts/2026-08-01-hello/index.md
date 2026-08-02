---
title: "Deflation and the low modes of the Dirac operator"
date: 2026-08-01
categories: [solvers, lattice]
---

The condition number of the Dirac operator $D$ is governed by the ratio of its
extreme eigenvalues, $\kappa(D) = \lambda_{\max} / \lambda_{\min}$. Because the
smallest eigenvalues sit near zero, the condition number is large and Krylov
solvers converge slowly.

Deflation removes the $k$ smallest modes from the operator that the solver sees:

$$
D_{\text{defl}} = D \left( I - \sum_{i=1}^{k} v_i v_i^{\dagger} \right)
$$

The effective condition number becomes $\lambda_{\max} / \lambda_{k+1}$, which
is dramatically smaller.
