# PULSEJET polynomial phase metric: conventions and derivation

## 1. Timing model of the implemented GPU resampler

The present polynomial CUDA kernel uses a length-`N_fft` input array.
For sample index `i` and sampling time `dt`, define

```
tau = (i - N_fft/2) * dt.
t_arr = tau + [ a_mid*tau^2/2 + j_mid*tau^3/6 ] / c.
```

The observed time-series is read at `t_arr` for uniformly sampled
emission-time output. This matches the source file
`PULSEJET_beta/include/transforms/polynomial_timing.hpp`.
At the midpoint, the instantaneous acceleration is `a_mid` and its
time derivative is `j_mid`. At the **start**,

```
a_start = a_mid - j_mid*T/2,   T = N_fft * dt.
```

Thus parameters from a start-referenced bank must not be fed directly
into a midpoint-referenced PULSEJET search.

To first order in the small delay, the observed pulse phase is

```
phi(tau) = 2*pi*f * [tau - a_mid*tau^2/(2*c) - j_mid*tau^3/(6*c)].
```

The minus sign in phase corresponds to inverting a **positive** arrival
delay; it is not an arbitrary change in the sign of acceleration.
The standalone metric derives from this phase model, not from a
Keplerian orbit or a Taylor-expanded change in intrinsic spin.

The resampler maps sample positions with nearest-neighbour rounding and
zeroes out-of-bounds reads. The metric does not model those finite
sampling/edge artefacts.

## 2. Small offsets and phase derivatives

Consider a signal offset `(Delta a, Delta j)` relative to a template
with the same phase reference. Its leading-order phase residual is

```
delta_phi(tau) =
  -pi*f/c * Delta a * tau^2
  -pi*f/(3*c) * Delta j * tau^3.
```

On the symmetric interval `tau in [-T/2,T/2]`, the derivatives are

```
q_a = -pi*f*tau^2/c
q_j = -pi*f*tau^3/(3*c)
q_f ~= 2*pi*tau .
```

Here `q_f` neglects corrections to the spin-frequency derivative of
relative order `a*T/c` and `j*T^2/c`, consistent with the
leading-order metric. The search optimizes spin frequency; the metric
must therefore remove the best-fitting linear phase.

A coherent complex signal's fractional **power** loss is approximately
its residual phase variance for small phase errors. Subtracting the
mean of each derivative projects out arbitrary constant phase:

```
G_xy = <q_x q_y> - <q_x><q_y>.
```

Projecting out frequency by a Schur complement gives

```
g_ij = G_ij - G_if * G_fj / G_ff,  i,j in {a,j}.
```

Useful symmetric time moments are

```
<tau^2> = T^2/12
<tau^4> = T^4/80
<tau^6> = T^6/448.
```

For acceleration, `Var(tau^2)=T^4/180`.
For jerk, subtract the part of cubic phase fitted by a frequency shift:

```
<tau^6> - <tau^4>^2/<tau^2> = T^6/2800.
```

Because the acceleration derivative is even and the jerk derivative
odd, their projected cross-covariance is zero at midpoint to this
order. The resulting local metric is

```
g_aa = pi^2 * f^2 * T^4/(180*c^2)
g_aj = 0
g_jj = pi^2 * f^2 * T^6/(25200*c^2)
mu ~ g_aa*(Delta a)^2 + g_jj*(Delta j)^2.
```

Metric coordinates `x=sqrt(g_aa)*a`, `y=sqrt(g_jj)*j` yield
`mu ~= Delta x^2 + Delta y^2`. Their metric density
`sqrt(det(g))` is **constant** over the box in this approximation.
Therefore, uniform IID samples in (a,j) already sample metric volume
uniformly. MH/emcee do not improve metric-volume sampling for a flat
metric merely by virtue of being MCMC methods.

## 3. What "mismatch = 0.3" really means

`mu=0.3` corresponds to a target **30% leading-order loss in
coherent power** due to the nearest template. It is *not* a promised
30% reduction in final harmonic-summed search S/N. The quadratic
approximation is accurate for small offsets; for larger phase mismatch
the actual complex-signal coherence must be evaluated independently.

The design frequency `f` should be the **highest fundamental spin
frequency relevant to the bank**, making the quadratic metric
conservative for lower fundamental frequencies at the same duration.
Harmonics multiply phase residuals; the fundamental's metric bound
does not necessarily bound higher harmonic contributions.

Metric requirements strengthen sharply with duration:
`g_aa proportional to f^2*T^4`,
`g_jj proportional to f^2*T^6`. Do not reuse a 505-second bank
at 893 seconds without a new coverage calculation.

## 4. Deterministic metric grid (reference implementation)

Given physical bounds `[a_min,a_max]` and `[j_min,j_max]`,
take maximum width in whitened metric coordinates

```
h = sqrt(2*mu)
n_a = max(1,ceil((a_max-a_min)*sqrt(g_aa)/h))
n_j = max(1,ceil((j_max-j_min)*sqrt(g_jj)/h)).
```

Place cell centers at

```
a_i = a_min + (i + 1/2)*(a_max-a_min)/n_a
j_k = j_min + (k + 1/2)*(j_max-j_min)/n_j.
```

The farthest point from a cell center is at most half a cell width
away on each axis; that includes the **outer box corners**:

```
mu_worst <= g_aa*[ (a_max-a_min)/(2*n_a) ]^2
          + g_jj*[ (j_max-j_min)/(2*n_j) ]^2
         <= mu.
```

This is a global bound for the **quadratic midpoint metric**, not a
proof about nonlinear coherent overlap or harmonic search S/N.
The square rectangular covering is deliberately a conservative
reference; later versions may compare hexagonal/A2 coverings.

## 5. Stochastic generator

The independent uniform sampler draws `N` a/j pairs over the box
using a fixed random seed. It is not an MCMC chain. The optional
budget estimate is the interior Poisson approximation:

```
V = (a_max-a_min)*(j_max-j_min)*sqrt(g_aa*g_jj)
N ~= ceil( -ln(1-p)*V / (pi*mu) ).
```

It neglects boundary effects and finite-bank correlations; *p is a
design heuristic*, **not an achieved coverage guarantee**. The CLI
evaluates independent random challenge points and box corners; these
are empirical diagnostics, not a mathematical bound for stochastic
placements. Compare equal-template-count grid and stochastic banks,
not just their default budgets.

## 6. Independent validation strategy

1. Evaluate phase-derivative covariance and the frequency Schur
   complement by **independent midpoint numerical quadrature**.
2. Evaluate complex phase coherence after best-fit linear phase
   subtraction and compare `1-|<exp(i delta_phi)>|^2` with the
   quadratic prediction at small offsets.
3. Test acceleration/jerk signs, frequency scaling and T scaling.
4. Test deterministic edge/corner coverage and stochastic seed
   reproducibility, without using the design metric to generate
   numerical phase samples.
5. On the cluster, compare actual per-template search S/N versus
   predicted mismatch and fold candidates independently.

The numerical coherence routine uses a **least-squares** linear phase
subtraction. At larger mismatch it need not coincide with a direct
maximum-likelihood frequency scan, so it is intentionally used to
validate the local regime rather than claim all-offset exactness.
