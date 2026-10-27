# Scientific validation and development log

**Policy:** append dated entries. Keep measurements, test inputs, source
revisions, defects, interpretation and pending work. Do not retroactively
replace failed runs. Retain linked CI logs and uploaded artifacts with
search-container/injection provenance for publication.

## 2026-10-27 — Legacy-generator intake and design audit

**Source:** original `main` at `5a2792be0ed1197598c0ae0c091427295b75ee11`,
one `Acc_and_Jerk_Random_template_bank_generator` prototype and README.

Findings:

1. It uses a phase model with elapsed time integrated from `0` to
   `T`; parameters written that way are **start-referenced**, while
   current PULSEJET polynomial kernel uses the midpoint of `N_fft`.
   Coordinates must be transformed, not directly reinterpreted.
2. Metric obtained by numerical symbolic covariance with f included
   is sensible in principle; the prototype has no tests comparing
   it to the actual GPU midpoint convention.
3. Original README defaults: `f=230 Hz`, `T=600s`,
   `a_max=150 m/s²`, `j_max=30 m/s³`, `coverage=0.90`,
   `mismatch=0.30`. These are placeholders, not validated
   observational search limits. Especially `j_max=30` is much wider
   than the injection-test jerk range (~0.3 m/s³).
4. The independence-MH routine counts only accepted **moves** and
   discards rejected-state repetitions; that does not constitute a
   tested standard MH chain. The emcee path likewise lacks independent
   mixing/coverage tests. Neither method is assumed science-ready.
5. Output prototype has a text `a j` header, and was written for
   Colab with bare separator lines; headerless two numeric columns
   are simpler and accepted by PULSEJET's current reader.

**Action:** preserve the legacy prototype and untouched main branch;
create `dev/midpoint-metric-bank` and a standalone Python 3.10+
standard-library generator.

## 2026-10-27 — Independent metric derivation

Target phase model for midpoint-relative time `tau`:
`phi=2*pi*f*[tau-a*tau²/(2c)-j*tau³/(6c)]`.
PULSEJET GPU timing:
`input_sample_index = i + [a*tau²/2+j*tau³/6]/(c*dt)`,
where `tau=(i-N_fft/2)*dt`; with rounding and bounds checks.
The phase formula is its small-delay inverse.

At leading order, after marginalizing over the spin-frequency linear
phase and arbitrary constant phase:

```text
g_aa = pi² f² T⁴ / (180 c²)
g_aj = 0
g_jj = pi² f² T⁶ / (25200 c²)
```

Derived from symmetric time moments and independent covariance/Schur
numerical quadrature. The metric predicts **local coherent power**
loss, not harmonic summed spectral search S/N.

Fixed independent reference example:
`f=383 Hz`, `dt=6.02352941176e-5 s`,
`N_fft=8388608`, `T=505.2902701172523 s`,
`a in [-255,-215] m/s²`, `j in [-0.4,0.25] m/s³`,
requested `mu=0.30`, `c=299792458 m/s`.

Analytical reference results (not PULSEJET GPU measurements):

| Metric/reference | Value |
|---|---:|
| T (s) | 505.2902701172523 |
| g_aa | approximately 0.00583374073955646 |
| g_aj | exactly 0 (leading order) |
| g_jj | approximately 10.63900369894246 |
| Metric grid shape | 4 accelerations × 3 jerks |
| Number of grid templates | 12 |
| Global worst-case quadratic-metric bound | approximately 0.2707040480112222 |
| Stochastic interior-Poisson N estimate at p=0.90 | 16 |

The grid bound holds over the entire specified rectangle including
corners, but only **within the quadratic metric approximation**.
The stochastic estimated count does not guarantee 90% coverage,
especially at edges.

## 2026-10-27 — Initial CI test pass (before documentation)

**Run:** https://github.com/Rouhin1997/Template_bank_generator_codes_for_PULSEJET_beta/actions/runs/40497173874
**Commit:** `0c7f02329edc6f3440968afeb8797e522b0b7748`
**Result:** GitHub Actions `Validate metric bank` completed `success`.

The CPU suite covered:

- four phase/convention tests (midpoint conversion, arrival delay,
  phase signs, invalid inputs);
- five metric tests (independent quadrature, frequency/T scaling,
  local numerical coherent power vs predicted, parity, validation);
- five bank tests (whole-domain grid bound, degenerate dimensions,
  random reproducibility, exact two-column roundtrip/SHA,
  invalid inputs);
- three CLI tests (bank/report creation, overwrite protection,
  exact stochastic bank count, invalid option combination);
- a command-line smoke test producing an actual bank and JSON report
  with the reference benchmark arguments.

**Scope:** numerical CPU and format validation, **not yet direct
PULSEJET C++ reader execution** or GPU injection recovery with banks.
The original search container and third-party distillers were untouched.

## 2026-10-27 — Reproducible experiment artifacts added

`scripts/reference_coherence_validation.py` generates twelve
(reference frequency and duration fixed) coherent-power-loss comparisons:
mismatch targets 0.01, 0.03, 0.10 and 0.30 × acceleration-only,
jerk-only, equally mixed offsets. It records numerical loss after
least-squares linear frequency projection alongside metric predictions.

`.github/workflows/validate-bank.yml` now runs it in CI, generates
`test_bank_aj.txt` and `test_bank_report.json`, and stores all three
files as a 90-day `midpoint-bank-reference` artifact. The repository
includes the generator and deterministic case definitions for
regeneration after artifact retention expires. The numerical report
distinguishes small-mismatch agreement from breakdown of the quadratic
approximation at larger offsets.

**Pending check:** confirm first updated CI run passes and inspect
the saved numerical report. Do not mark as tested before checking.

## Outstanding blockers before science-grade multi-injection inference

- [ ] Inspect regenerated coherence benchmark numbers, particularly
      systematic deviations near `mu=0.3`.
- [ ] Execute a generated bank directly through PULSEJET's actual
      `Polynomial_TemplateBank_Reader` and GPU search.
- [ ] Repeat generator checks for conservative design frequencies and
      actual segment lengths across M62 W1–W4.
- [ ] Compare grid versus stochastic coverage at **equal** template
      budgets and multiple seeds, including edge losses.
- [ ] Resolve existing PULSEJET PeakFinder minimum-frequency bug with
      approved regression tests and a fresh versioned GPU image before
      broad-frequency recovery/completeness studies.
- [ ] Shared DM/a/j searches and actual recovered-S/N mismatch
      experiments, with independent folding and uninjected data controls.

**Do not conflate:** metric coverage, returned candidate fraction,
pipeline search S/N, folded significance, and astrophysical
flux-density completeness.
