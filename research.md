---
# Full-width layout, so this page's left gutter matches every other tab.
# See index.md for the rationale.
page-layout: full
title: "Research"
---

::: {.accent-rule}
:::

<!-- Intro -->
I'm a particle physicist interested in understanding the strong nuclear force from a theoretical perspective. My specific 

<!-- QCD -->

<!-- Lattice QCD -->

# Non-Hermitian Solvers 
One of the most important equations in lattice QCD is the discrete Dirac equation,
$$
	D\psi = b.
$$ {#eq-dirac}
The discrete Dirac equation is used to construct **propagators**, which are the central objects that we use to compute correlation functions. Here, $\psi$ is the fermion field we solve for, $b$ is the source, and $D$ is a high-dimensional matrix called the **Dirac operator**. The specific form of the Dirac operator depends on the QCD discretization that you use; for example, one of the most common Dirac operators is the Wilson operator with mass $m$, 
$$
	D_W(x, y) = (4 + m) - \frac{1}{2} \sum_{\mu = 1}^4 (1 - \gamma_\mu) U_\mu(x) \delta_{x + \hat\mu, y} + (1 + \gamma_\mu) U_\mu^\dagger(y) \delta_{x, y + \hat\mu},
$$
constructed from the Dirac $\gamma$-matrices and the gauge links $U_\mu(x)$. 

The Dirac operator $D$ is extremely high-dimensional (for a $48^3\times 96$ dimensional lattice,  $\dim D \approx 10^9 \times 10^9$), so $\psi = D^{-1} b$ cannot be evaluated directly. Instead, one typically solves the Dirac equation (@eq-dirac) with Krylov solvers. Krylov solvers are iterative linear solvers which start with an initial vector $r_0$ and find the best solution to $D\psi = b$ in the dimension-$N$ subspace $\{r_0, D r_0, D^2 r_0, ..., D^{N-1} r_0\}$ (the **Krylov space**). The exact definition of "best" depends on the Krylov solver at hand: examples are Conjugate Gradient (CG) and Generalized Minimum Residual (GMRES). These are iterative solvers: each iteration increases the dimension of the Krylov space $N\mapsto N+1$. As $N$ gets larger, the Krylov space better approximates the full space, and one gets a better approximation to the solution. Because solving the Dirac equation bottlenecks LQCD simulations, it is important to improve our solver algorithms so they converge as fast as possible. 

The convergence of Krylov solvers depends on the Dirac operator and its eigenvalue spectrum. 

# Spectral Function Reconstruction
The energy spectra of a system, $\rho(\omega)$, describes the system's state. You can read off

<!-- Add R-ratio plot -->

#### Papers
1. Bergamischi, Jay, Oare
2. Abbott, Jay, Oare
3. ...
4. ...

# Confinement and Adjoint $\mathrm{QCD}_2$



# Neutrinoless Double Beta Decay
The nature of the neutrino mass is unknown. Experimental observation of neutrino oscillations show that at least 2 of the 3 known neutrinos must have mass, but this mass must enter through Beyond the Standard Model physics. The mechanism responsible for the neutrino mass is unknown at this time. There are two possible types of neutrino mass: Dirac and Majorana. A Dirac mass would imply that neutrinos have distinct antiparticles, while a Majorana mass would imply that they are their own antiparticles. 

Neutrinoless double beta ($0\nu\beta\beta$) decay is one of the most well-studied candidates for physics beyond the Standard Model: if observed, it would immediately imply that the neutrino is a Majorana particle. It is the hypothetical decay of two down quarks into two up quarks and two electrons,
$$
	2d\rightarrow 2u + 2e^-.
$$
The Standard Model admits a similar cousin to this decay, neutrino-*full* double beta decay, $2d\rightarrow 2u + 2e^- + 2\overline{\nu}_e$. (the rarest observed Standard Model decay). The lack of neutrinos in the final state is 

<!-- TODO add classic LD diagram -->

#### Papers
1. a
2. b
# Renormalization of the QCD Energy-Momentum Tensor


#### Papers
1. a
2. b