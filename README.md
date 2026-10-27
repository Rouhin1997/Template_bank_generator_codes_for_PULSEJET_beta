# PULSEJET_beta acceleration–jerk template-bank generator

**Status:** research development, **v0.1.0**, validated on CPU for the
leading-order midpoint metric and bank-file format. **Not yet validated
end-to-end against PULSEJET's GPU reader or search sensitivity.**

This project generates *two-column polynomial motion banks* for the
[`PULSEJET_beta`](https://github.com/Rouhin1997/PULSEJET_beta)
GPU acceleration-and-jerk search:

```text
-235 -0.25
-235 0
-215 0.15
```

Each line contains **acceleration in m/s²**, followed by **jerk in m/s³**,
both referenced to the **midpoint of the actual FFT search segment**.
There is **no header**. The file is consumed by PULSEJET's
`Polynomial_TemplateBank_Reader`, via its `-P` polynomial-bank option.
It is a *search-template file*, **not** the source-truth JSON used by
the INCEPTION pulsar injector.

The original October 2025 Colab-style prototype,
[`Acc_and_Jerk_Random_template_bank_generator`](Acc_and_Jerk_Random_template_bank_generator),
is retained **unchanged for provenance**, not recommended for current
science use. It was an untested exploration using a start-referenced
phase convention and MCMC samplers. The new tested implementation lives
under `pulsejet_bank/` on branch `dev/midpoint-metric-bank`.
The repository's `main` branch has not been changed.

## Contents

- [1. Development philosophy and status](#1-development-philosophy-and-status)
- [2. Polynomial timing model](#2-polynomial-timing-model)
- [3. Projected acceleration–jerk metric](#3-projected-accelerationjerk-metric)
- [4. How templates are placed](#4-how-templates-are-placed)
- [5. Install and generate a bank](#5-install-and-generate-a-bank)
- [6. Interpret the report](#6-interpret-the-report)
- [7. Reproducibility and scientific tests](#7-reproducibility-and-scientific-tests)
- [8. Integration with PULSEJET and injection experiments](#8-integration-with-pulsejet-and-injection-experiments)
- [9. Limitations and next steps](#9-limitations-and-next-steps)

## 1. Development philosophy and status

The bank should not secretly contain the true acceleration and jerk of
every injected pulsar. Instead it should **span a chosen physical range**
and provide measured or mathematically documented coverage. By
comparing the closest template to an independent injection manifest, we
can test whether theoretical mismatch predicts search-S/N loss.

Two bank builders are provided:

| Method | Purpose | Coverage assertion |
|---|---|---|
| `grid` (default) | Transparent, deterministic **reference bank** | Every point in the rectangular box has a nearest template within the specified **quadratic metric** bound |
| `stochastic` | Seeded IID uniform metric-volume sampling for comparison | No hard guarantee; independent empirical coverage is measured |

The grid is not presented as the optimal possible lattice. A later
triangular/A2 packing and more advanced stochastic placement can be
compared with it fairly. The original MH/emcee options are deliberately
not silently reused: for the midpoint *leading-order* metric,
`sqrt(det(g))` is constant, so a random **uniform** point already has
the correct metric-volume sampling distribution.

## 2. Polynomial timing model

Our current GPU resampler uses an arrival-time warp. Let `N_fft` be the
number of FFT samples, `dt` the original sampling interval, and
`tau = (i - N_fft/2)*dt` the time offset from the FFT midpoint.
With midpoint acceleration `a`, midpoint jerk `j`, and speed of
light `c = 299792458 m/s`:

```text
t_arr = tau + [a*tau²/2 + j*tau³/6] / c.
```

A pulsar with fundamental frequency `f` then has the leading-order
observed phase model:

```text
phi(tau) = 2*pi*f*[tau - a*tau²/(2*c) - j*tau³/(6*c)].
```

The plus sign in the **arrival delay** and minus sign in the **observed
phase** are compatible: the latter follows by inverting arrival time
to first order in the small propagation delay.

**Crucially, `a` and `j` are midpoint coordinates**, unlike a
start-referenced model. For constant jerk:

```text
a_start = a_mid - j_mid*T/2,   T = N_fft*dt.
```

For the M62 experiments this detail matters. Searching a physically
centered subsegment avoids an unwanted midpoint shift from padding a
shorter observation up to a longer FFT. A bank constructed for 505 s
does not automatically cover an 893 s search with the same mismatch
criterion.

Full derivation: [`docs/METRIC_DERIVATION.md`](docs/METRIC_DERIVATION.md).

## 3. Projected acceleration–jerk metric

We need templates dense enough that an injected signal is not overly
dephased after correction. Search frequency is **unknown and searched**
by PULSEJET, so its best-fitting value must be projected out instead of
incorrectly treating frequency as fixed.

On a symmetric `[-T/2,T/2]` time interval, start from the covariance
of the phase derivatives, subtract the arbitrary constant phase,
and then take the Schur complement of the frequency dimension.
At leading order in velocity/c:

```text
g_aa = pi²*f²*T⁴/(180*c²)
g_aj = 0
g_jj = pi²*f²*T⁶/(25200*c²).
```

For template offset `(Delta a, Delta j)` relative to a signal:

```text
mu_pred ~= g_aa*(Delta a)² + g_jj*(Delta j)².
```

`mu_pred` approximates the **fractional coherent POWER loss**, not
fractional amplitude loss and not the exact reduction of PULSEJET's
harmonic-summed detection S/N.

The metric is diagonal in midpoint coordinates because acceleration
perturbations have an even time dependence, jerk perturbations have an
odd one, and spin-frequency fitting removes the jerk's linear-phase
component. The higher-order dependence on a and j and
nearest-neighbour GPU sampling are not included in this analytical
metric.

The metric scales strongly with time: `g_aa ~ T⁴`, `g_jj ~ T⁶`;
both scale as `f²`. Use a **design spin frequency at least as high as
the largest fundamental pulsar frequency** targeted in the search.
The harmonic-summed detection statistic can suffer additional
dephasing at higher harmonics; do not claim this fundamental-frequency
metric is an absolute harmonic sensitivity bound.

For the detailed moments, projection and restrictions, read
[`docs/METRIC_DERIVATION.md`](docs/METRIC_DERIVATION.md).

## 4. How templates are placed

### Deterministic grid (recommended first)

Transform to whitened coordinates:

```text
x = sqrt(g_aa)*a
y = sqrt(g_jj)*j.
```

Then the predicted mismatch is Euclidean squared distance,
`mu ~= (Delta x)² + (Delta y)²`.

The generator divides each physical interval into equally sized cells.
It chooses the numbers of cells so that the maximum cell-centre
separation in whitened space yields mismatch no greater than the
requested `mu`. Each template sits in the center of a cell, including
those adjacent to the edges of the requested acceleration–jerk box.

If `L_a=a_max-a_min`, `L_j=j_max-j_min`, `h=sqrt(2*mu)`:

```text
n_a = max(1, ceil(L_a*sqrt(g_aa)/h))
n_j = max(1, ceil(L_j*sqrt(g_jj)/h))
N_grid = n_a*n_j.

mu_worst = g_aa*(L_a/(2*n_a))² + g_jj*(L_j/(2*n_j))² <= mu.
```

This is a worst-case bound on the **quadratic midpoint metric** across
the entire **specified rectangle**, even at its corners. It does not
prove the *actual* Fourier/harmonic S/N loss is below `mu`.
The grid is intentionally easy to audit and serves as an independent
reference for more efficient bank-placement methods.

### Stochastic IID bank (research comparison)

At leading order the projected metric is constant across (a,j), so
the right metric-volume density is uniform. The random generator
draws independent uniform points from the requested box with a fixed
seed. Unlike the original MCMC concept, it does not introduce Markov
chain autocorrelation or require convergence tuning.

Unless an exact `--templates` count is supplied, its initial count
comes from an **interior** Poisson approximation:

```text
V = (a_max-a_min)*(j_max-j_min)*sqrt(g_aa*g_jj)
N ~= ceil(-ln(1-p)*V / (pi*mu)).
```

Here `p` is a nominal *interior* coverage target, **not a validated
global coverage guarantee**. The approximation neglects edges and
discrete bank effects; empirical coverage can be substantially lower
at boundaries. Compare stochastic and grid constructions with the
same template count when evaluating efficiency.

Every generated bank is evaluated against independent random challenge
points and all four corners; results are written in the JSON report.

## 5. Install and generate a bank

Requirements: **Python 3.10+**, standard library only. No NumPy,
SymPy, Matplotlib, or emcee is required for this validated baseline.

Clone and check out the development branch:

```bash
git clone https://github.com/Rouhin1997/Template_bank_generator_codes_for_PULSEJET_beta.git
cd Template_bank_generator_codes_for_PULSEJET_beta
git switch dev/midpoint-metric-bank

python3 -m unittest discover -s tests -v
```

You can optionally `python3 -m pip install -e .` and use the
`pulsejet-bank` shell command; the examples use `python3 -m pulsejet_bank`
to avoid altering a machine's environment.

**Example: a controlled W3/I15 neighbourhood bank**, f=383 Hz,
T=8,388,608 samples × 60.2352941176 µs = **505.2902701172523 s**:

```bash
mkdir -p outputs

python3 -m pulsejet_bank \
  --frequency-hz 383 \
  --duration-s 505.2902701172523 \
  --a-min -255 --a-max -215 \
  --j-min -0.4 --j-max 0.25 \
  --mismatch 0.30 \
  --method grid \
  --validation-points 1000 \
  --output outputs/w3_i15_grid.txt \
  --report outputs/w3_i15_grid.json
```

These bounds are **illustrative, deliberately centred near one known
source** for generator testing. They are **not** the common wide bank
that will ultimately search all injected pulsars.

For this example, the analytical coefficients are about
`g_aa=0.00583374` (m/s²)⁻² and `g_jj=10.6390` (m/s³)⁻².
The deterministic grid has `4 × 3 = 12` templates and a maximum
quadratic-metric mismatch bound of approximately **0.270704**,
below the requested 0.30. The grid's observed sample coverage must
also be measured and stored in the report. We intentionally do not
equate this numerical metric bound with measured PULSEJET S/N loss.

You may alternatively generate a seeded stochastic bank:

```bash
python3 -m pulsejet_bank \
  --frequency-hz 383 --duration-s 505.2902701172523 \
  --a-min -255 --a-max -215 --j-min -0.4 --j-max 0.25 \
  --mismatch 0.30 --method stochastic \
  --coverage 0.90 --seed 7 \
  --output outputs/w3_i15_random.txt \
  --report outputs/w3_i15_random.json
```

To set an exact stochastic budget, add e.g. `--templates 100`.
Choose `--method grid` for a bound; `--coverage` is only used to
estimate template count for the stochastic generator.

**Output safety:** existing files cannot be overwritten unless you
explicitly pass `--overwrite`. Parent output directories must exist.
The bank content is plain text:

```text
-250 -0.29166666666666669
-250 -0.075000000000000011
-250 0.14166666666666666
```

(Those rows are illustrative of the grid's first acceleration cell;
always rely on the generated file for exact values.)
Each row contains precisely two finite numeric values; it has no
metadata header, extra column or source-specific injection truth.

## 6. Interpret the report

The optional `--report` JSON records:

- `design`: duration, design fundamental frequency, box edges and
  target local coherent-power mismatch;
- `metric`: all analytical matrix elements;
- `method`, `template_count` and `construction`: how/why the
  bank was placed and the deterministic bound (when applicable);
- `validation`: random challenge seed/size, empirical fraction within
  mismatch tolerance, median, p90, p99, maximum sampled mismatch and
  maximum mismatch among the **four box corners**;
- `bank_sha256`: exact checksum of the two-column file, enabling
  cross-run science provenance;
- `limitations`: scientific caveats attached to every report.

A stochastic empirical coverage of e.g. 0.88 is an *estimated*
fraction for its particular challenge sample; it is not a proven
population completeness of 88%. Similarly, `grid` provides a bound
within the model, **not** a bound on the hardware pipeline.

## 7. Reproducibility and scientific tests

Run:

```bash
python3 -m compileall -q pulsejet_bank tests
python3 -m unittest discover -s tests -v
```

The `.github/workflows/validate-bank.yml` CI runs those commands and
a full command-line bank export on every development-branch push.

The suite checks:

1. Midpoint/start acceleration conversion, delay sign and phase sign.
2. Independent numerical phase-derivative covariance and frequency
   projection versus analytical `g_aa`, `g_aj`, `g_jj`.
3. Numerical coherent-power loss versus local quadratic mismatch for
   small injected offsets and multiple frequencies/durations.
4. Expected metric scaling in spin frequency and duration.
5. Grid edge/corner bounds, seeded stochastic reproducibility,
   invalid-parameter rejection.
6. Headerless two-column export, double-precision roundtrip,
   SHA-256 correctness, no-overwrite protection and CLI report output.

Records are **append-only** in
[`docs/VALIDATION_LOG.md`](docs/VALIDATION_LOG.md).
The forward development gates live in
[`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md).

## 8. Integration with PULSEJET and injection experiments

The proposed M62 experiment is:

1. Use the original INCEPTION JSON manifest as **independent truth**;
   do not inject bank grid points as if they were new truth parameters.
2. Choose a common acceleration–jerk rectangle enveloping all
   five signals in each window and a suitable shared additional-DM grid.
3. Record the exact search **FFT duration** and highest fundamental
   frequency for the metric.
4. Generate a bank with a specified mismatch and record its SHA-256.
5. Supply the bank to PULSEJET using `-P path/to/bank.txt` and the
   DM trial file; search the full chosen frequency interval.
6. Parse recovered candidates without preassigning their injected
   spin frequencies, match them to the injection manifest afterward,
   and compute their nearest-template metric mismatch.
7. Compare loss of spectral S/N to controlled matched-motion templates,
   perform uninjected observational controls, and independently fold
   recovered candidates with PulsarX.

**Important existing PULSEJET bug:** the current old pinned GPU image's
PeakFinder effectively starts searching near **twice** the requested
minimum frequency. Our prior fixed-template recovery tests used
narrow-band workarounds. Before making broad recovery/completeness
claims, separately fix that source bug, add regression tests, and build
a **versioned new image**. The generator does **not** modify PeakFinder.

Another limitation: the GPU polynomial kernel defines its midpoint
from **FFT array length**. When `nsamples` and `fft_size` differ,
ensure padding has not silently shifted the polynomial time reference
from the injection reference.

## 9. Limitations and next steps

**Validated so far:** the leading-order phase metric, deterministic
model-space placement, stochastic comparison sampler, two-column format,
and numerical/CLI CPU tests.

**Not yet established:** GPU-bank integration, coverage of a realistic
shared DM/a/j search, optimal packing efficiency, actual measured
harmonic-summed S/N mismatch, statistical completeness or flux
sensitivity. The numerical phase-coherence test projects frequency by
least-squares linear phase detrending; that coincides with optimal
frequency projection locally but need not maximize power for large
offsets.

The original MCMC sampler is **not claimed defective for all uses**.
It simply has not been validated or shown necessary here. A corrected,
benchmarked MH or `emcee` method may be added after the metric reference
and stochastic IID baseline are demonstrably reliable.

Any science result must store the branch/commit, bank SHA-256,
`f_design`, `N_fft`, `dt`, bank parameter range, mismatch,
construction method and validation seed, search GPU container revision,
injection-truth manifest, recovered candidates and relevant logs.
