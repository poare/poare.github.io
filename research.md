---
# Full-width layout, so this page's left gutter matches every other tab.
# See index.md for the rationale.
page-layout: full
title: "Research"
---

::: {.accent-rule}
:::

<!-- Intro and QCD -->
I'm a particle physicist interested in understanding the strong nuclear force from a theoretical perspective. The strong force is what binds together the atomic nucleus. The nucleus is made of protons (positive charge) and neutrons (neutral charge): how does it stick together if positive charges can only repel one another? The answer is that there is a close-range force that is much stronger than electromagnetism at close ranges, which we (creatively) call the **strong force**. 

<!-- From an electromagnetic standpoint, the atomic nucleus is made of positively-charged and neutral-charged components -->

<!-- QCD -->
The mathematical theory that describes the strong force is called Quantum Chromodynamics (QCD). QCD describes the proton and neutron as made of constituent particles called **quarks** and **gluons**. The quarks make up matter, and they interact with one another via exchanging gluons, which are the force carriers of QCD. Quarks and gluons have "color" charge, which comes in red, green, and blue (and superpositions of these), which is why it's called chromodynamics: this means "color force". That the strong force is so strong at short distances makes it difficult to study from first principles. We can write the theory down exactly, but computing observables directly from the theory is difficult. 
<!-- Formally, QCD is an $SU(3)$ gauge theory coupled to six flavors of quark in the fundamental representation. -->

<!-- The strength of the strong force makes it difficult to study ("non-perturbative").  -->

My specific research field is called **lattice QCD**. We study QCD computationally by discretizing spacetime and evaluating the path integral numerically with statistical methods. Calculations require an extraordinary amount of compute and are typically done on supercomputing clusters. We use Markov Chain Monte Carlo to sample a high-dimensional probability distribution and determine estimators for objects called **correlation functions**, which can then be used to compute observables of interest like bound-state masses or energy levels. Lattice QCD is the only *ab initio* method that can compute QCD observables at all energy scales. 

<!-- of interest using resampling methods like the bootstrap or jackknife.  -->

Below I have a discussion of some of my current research areas in lattice QCD. This is a work in progress: I'll continue to update this page. 

<!-- Lattice QCD -->

# Non-Hermitian Solvers 
One of the most important equations in lattice QCD is the discrete Dirac equation,
$$
	D\psi = b.
$$ {#eq-dirac}
Here, $\psi$ is the fermion field we solve for, $b$ is the source, and $D$ is a high-dimensional matrix called the **Dirac operator**, which is a discretization of the elliptic differential operator $\gamma^\mu (\partial_\mu + i A_\mu) - m$. The discrete Dirac equation is used to construct **propagators**, which are the central objects that we use to compute correlation functions. The specific form of the Dirac operator is not unique and depends on the QCD discretization that you use; one of the most common Dirac operators is the Wilson operator with mass $m$, 
$$
	D_W(x, y) = (4 + m) \delta_{x, y} - \frac{1}{2} \sum_{\mu = 1}^4 \big[ (1 - \gamma_\mu) U_\mu(x) \delta_{x + \hat\mu, y} + (1 + \gamma_\mu) U_\mu^\dagger(y) \delta_{x, y + \hat\mu} \big],
$$
constructed from the Dirac $\gamma$-matrices and the gauge links $U_\mu(x)$. 

The Dirac operator $D$ is very high-dimensional (for a $48^3\times 96$ dimensional lattice,  $\dim D \approx 10^9 \times 10^9$), so $\psi = D^{-1} b$ cannot be evaluated directly. Instead, one typically solves the Dirac equation (@eq-dirac) with Krylov solvers. Krylov solvers are iterative linear solvers which start with an initial vector $r_0$ and find the best solution to $D\psi = b$ in the dimension-$N$ subspace $\{r_0, D r_0, D^2 r_0, ..., D^{N-1} r_0\}$ (the **Krylov space**). The exact definition of "best" depends on the Krylov solver at hand: examples we use frequently are Conjugate Gradient (CG) and Generalized Minimum Residual (GMRES). These are iterative solvers: each iteration increases the dimension of the Krylov space $N\mapsto N+1$. As $N$ gets larger, the Krylov space better approximates the full space, and one gets a better approximation to the solution. Because solving the Dirac equation bottlenecks lattice QCD simulations, it is important to improve our solver algorithms so they converge as fast as possible. 

The convergence of Krylov solvers depends on the Dirac operator and its eigenvalue spectrum. The modes responsible for slow convergence in Krylov solvers are the low eigenmodes. I'm currently studying how to accelerate these linear solvers in two ways. First, a more accurate computation of the Dirac operator's eigenspectrum. Interior eigenmodes are difficult to compute directly, and we can leverage ideas from applied math to better extract these eigenvalues. Second, I'm studying adaptive, algebraic multigrid methods to solve the Dirac equation. Multigrid methods furnish the near-null space of the Dirac operator in order to remove the slowly convergent degrees of freedom in a solve. They take longer to set up, but once set up can rapidly accelerate a solve.

# Spectral Function Reconstruction

Spectral functions describe the interacting states in a quantum field theory. From the spectral function, you can read off the bound states, resonances, and scattering thresholds in the theory: they're extremely valuable quantities to know. Unfortunately, spectral densities are very difficult to compute from lattice QCD. They're related to lattice correlation functions via an ill-posed inverse problem. One can formulate the relation between the correlation function $C(t)$ and the spectral density $\rho(\omega)$ at zero temperature as a Laplace transform,
$$
	C(t) = \int d\omega\, \rho(\omega)\, e^{-\omega t}.
$$
The spectral density is defined at an infinite number of points, $\omega\in\mathbb R$, and must be reconstructed from the correlation function at a finite number of points, $t\in \{1, 2, ..., T\}$. 

In 2023 Thomas Bergamaschi, Will Jay, and I developed a novel method for reconstructing spectral functions in lattice QCD based on Nevanlinna-Pick interpolation theory. Our method not only constructs a spectral density from the input data, but also the space of all possible spectral densities that are consistent with the input data. This is unique to the analytic structure of the problem: it's very well constrained, which allowed us to understand the space of possible solutions. We've since extended the formalism to matrix-valued correlation functions via applying mathematical solutions to the moment problem, and are now thinking about how to incorporate statistical errors into our method.

<!-- Add R-ratio plot -->

#### Publications
1. T. Bergamaschi, W. Jay, <u>P. Oare</u>, **Hadronic Structure, Conformal Maps, and Analytic Continuation**, [Phys. Rev. **D** 108 (2023) 7, 074516](https://journals.aps.org/prd/abstract/10.1103/PhysRevD.108.074516).
2. R. Abbott, W. Jay, <u>P. Oare</u>, **Moment problems and bounds for matrix-valued smeared spectral functions**, [arXiv:hep-lat/2508.01377](https://arxiv.org/abs/2508.01377) (in submission to Phys. Rev. **D**, September 2026).
3. R. Abbott, W. Jay, <u>P. Oare</u>, **Moment problems and spectral functions**, [PoS LATTICE2025 (2026) 146](https://arxiv.org/abs/2602.11260).
4. R. Abbott, S. Fields, W. Jay, <u>P. Oare</u>, M. Saccardi, **The Causal Bootstrap: Bounding Smeared Spectral Functions from Non-Perturbative Euclidean Data**, [arXiv:hep-lat/2605.20509](https://arxiv.org/abs/2605.20509) (accepted to Phys. Rev. **D**, September 2026).

<!-- # Confinement and Adjoint $\mathrm{QCD}_2$
Quarks in nature are never found alone: they're always found in quark-antiquark pairs (mesons), combinations of 3 quarks (baryons), or more exotic combinations of quarks and antiquarks. This property of QCD is called **color confinement**. Precisely stated, color confinement says that quarks are only found in color-neutral bound states. A lone quark is not color neutral: it must be paired up with some combination of quarks and antiquarks. 

Adjoint QCD is the theory of a Majorana fermion coupled to an $SU(N)$ gauge field in the adjoint representation in 2 spacetime dimensions. We are in the process of computing string tensions and the low-lying spectrum of $\mathrm{QCD}_2$ using rational Hybrid Monte Carlo. -->

# Neutrinoless Double Beta Decay
The nature of the neutrino mass is unknown. Experimental observation of neutrino oscillations shows that at least 2 of the 3 known neutrinos must have mass, but this mass must enter through Beyond the Standard Model physics. The mechanism responsible for the neutrino mass is unknown at this time. There are two possible types of neutrino mass: Dirac and Majorana. A Dirac mass would imply that neutrinos have distinct antiparticles, while a Majorana mass would imply that they are their own antiparticles. 

Neutrinoless double beta ($0\nu\beta\beta$) decay is one of the most well-studied candidates for physics beyond the Standard Model: if observed, it would immediately imply that the neutrino is a Majorana particle. It is the hypothetical decay of two down quarks into two up quarks and two electrons,
$$
	2d\rightarrow 2u + 2e^-.
$$
The Standard Model admits a similar cousin to this decay, neutrino-*full* double beta decay, $2d\rightarrow 2u + 2e^- + 2\overline{\nu}_e$ (the rarest observed Standard Model decay). The lack of neutrinos in the final state is important because it implies the neutrino is its own antiparticle. 

<!-- TODO add classic LD diagram -->

In order to properly understand experimental $0\nu\beta\beta$ decay data, one must understand the decay from a theoretical perspective. There are a large number of different mechanisms that physicists have proposed for $0\nu\beta\beta$ decay over the years, and input for these theoretical models must be supplied by lattice QCD. I've computed lattice QCD inputs for the $0\nu\beta\beta$ decay of the pion $\pi^-\rightarrow\pi^+ e^- e^-$ and the dinucleon $n^0 n^0 \rightarrow p^+ p^+ e^- e^-$ (a heavier cousin of the deuteron that only exists at artificially large quark mass).

#### Publications
1. W. Detmold, W. Jay, D. Murphy, <u>P. Oare</u>, P. Shanahan, **Neutrinoless Double Beta Decay from Lattice QCD: The Short-Distance $\pi^-\rightarrow\pi^+ e^- e^-$ Amplitude**, [Phys. Rev. **D** 107 (2023) 9, 094501](https://journals.aps.org/prd/abstract/10.1103/PhysRevD.107.094501).
2. W. Detmold, Z. Fu, A. Grebe, W. Jay, D. Murphy, <u>P. Oare</u>, P. Shanahan, **Long-distance nuclear matrix elements for neutrinoless double-beta decay from lattice QCD**, [Phys. Rev. **D** 109 (2024) 11, 114514](https://journals.aps.org/prd/abstract/10.1103/PhysRevD.109.114514).


<!-- # Renormalization of the QCD Energy-Momentum Tensor


#### Publications
1. a
2. b -->