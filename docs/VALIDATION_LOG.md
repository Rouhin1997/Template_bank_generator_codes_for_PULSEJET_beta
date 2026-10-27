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


## 2026-10-27 — Benchmark import failure, correction and final green CI

**Failure records (retained intentionally):**
- https://github.com/Rouhin1997/Template_bank_generator_codes_for_PULSEJET_beta/actions/runs/40497974934 (`5e6a0a3d12`)
- https://github.com/Rouhin1997/Template_bank_generator_codes_for_PULSEJET_beta/actions/runs/40498072537 (`c88f7d2514`)

Both failures occurred **after** analytical/numerical unittest and bank-export smoke tests passed. The new benchmark was invoked as
`python scripts/reference_coherence_validation.py` and Python resolved
`sys.path[0]` to `scripts/`, making the sibling `pulsejet_bank` package
unavailable. Actual failure: `ModuleNotFoundError: No module named 'pulsejet_bank'`.
No scientific metric assertion failed.

**Fix:** change CI to invoke the script as a package-root module:
`python -m scripts.reference_coherence_validation --output /tmp/reference_coherence.json`
(commit `9c2537f3ae2265fbf82966d1daa82550e5eaf05e`).

**Successful rerun:**
https://github.com/Rouhin1997/Template_bank_generator_codes_for_PULSEJET_beta/actions/runs/40498168746
- **Result:** `success`, all workflow steps passed.
- **17 / 17** CPU unit and numerical tests passed; Python compilation
  and CLI bank/export checks passed.
- Independently generated **12 phase-coherence comparison cases**:
  local predicted mismatch `mu in {0.01,0.03,0.10,0.30}`
  × {acceleration-only, jerk-only, mixed-equal-metric},
  `f=383 Hz`, `T=505.2902701172523 s`, 4,096 phase samples each.
- **Maximum absolute numeric-coherent-loss versus quadratic-metric
  difference for targets mu≤0.10:** `0.005533032382306`
  (reported by the actual CI benchmark).
- At `mu=0.30`, the quadratic approximation is visibly less exact.
  An independent local reference evaluation showed numerical
  coherent-power losses about `0.2639` (acceleration only),
  `0.2630` (jerk only), and `0.2538` (mixed) versus quadratic
  estimate 0.30; these illustrate a **local metric's breakdown
  at larger offsets**, not a bug or a PULSEJET measured S/N.
  Exact benchmark rows are in the archived JSON file.
- **Three saved CI artifacts**, uploaded as one
  `midpoint-bank-reference` archive:
  `test_bank_aj.txt`, `test_bank_report.json`,
  `reference_coherence.json`.
  [Artifact download](https://github.com/Rouhin1997/Template_bank_generator_codes_for_PULSEJET_beta/actions/runs/40498168746/artifacts/12730768307),
  artifact ID `12730768307`; retention through
  **2027-01-25**, after which the source + commands here regenerate it.

**Interpretation:** we now have repeatable CPU-level mathematical and
bank-file validation, including a numerical estimate of where the
small-mismatch approximation stops being quantitatively precise.
No template from this new generator has yet been fed into the actual
PULSEJET GPU binary. No model-space coverage test measures
observational detection completeness. No changes to PULSEJET source,
container, or third-party distillers occurred.


## 2026-10-27 — Off-grid W3/I15 coverage regression

The bank designed for `f=383Hz, T=505.2902701172523s`,
`a∈[-255,-215]`, `j∈[-0.4,0.25]`, `mu=0.30`,
has 12 centre-of-cell templates; the actual W3/I15 injected
`a=-235 m/s², j=-0.25 m/s³` is **not present** in the bank.

The two nearest reference templates are
`(-240,-0.2916666666666667)` and
`(-230,-0.2916666666666667)`, both at
`mu_pred=0.16431401102179768`. This number is a **computed local
quadratic coherent-power mismatch**, not a PULSEJET recovery statistic.
It demonstrates a quantitative *off-grid* reference case that can
later be searched on the GPU to test whether measured spectral-S/N loss
follows the metric prediction.

A new unit regression in `tests/test_bank.py` asserts that truth is
absent from the bank yet has predicted mismatch below the requested
bound. **CI run:** https://github.com/Rouhin1997/Template_bank_generator_codes_for_PULSEJET_beta/actions/runs/40498423240,
commit `f35e2d0cb7ad5cd71987496bf872fddf523e2343`, **success**
(18 mathematical, generator and interface tests). GPU search and
independent recovered-candidate folding remain pending.


## 2026-10-27 — Actual HPC Python 3.12 environment, bank export and 18-test PASS

The user installed/cloned branch `dev/midpoint-metric-bank` into
`/home/rnag/PULSEJET_validation/PULSEJET_templatebank_source` on
`node3`. The system default `python3` is **3.6.8**, which failed the
initial test import (`dataclasses` unavailable) and old subprocess
signature (`capture_output` unsupported). This was strictly an
interpreter-version incompatibility, not a metric-test failure. The
cluster provides module `python/3.12.4` (and an existing INCEPTION SIF
with Python 3.10.12); with the newer module, the user ran:

```bash
python3 -m unittest discover -s tests -v
# Ran 18 tests in 1.087s -- OK

mkdir -p outputs
python3 -m pulsejet_bank \
  --frequency-hz 383 \
  --duration-s 505.2902701172523 \
  --a-min -255 --a-max -215 \
  --j-min -0.4 --j-max 0.25 \
  --mismatch 0.30 --method grid \
  --output outputs/w3_i15_reference.txt \
  --report outputs/w3_i15_reference.json
```

**Actual node3 generated-bank report and checks:**
- `template_count=12`, grid `[4,3]`, `wc -l=12`.
- SHA256 of generated two-column file:
  `969af3da3f5a271d36af4ed98808a6d68337592eaa1d127a5159faf95a02a29f`.
- `g_aa=0.005833740739556459`, `g_aj=0.0`,
  `g_jj=10.639003698942455`.
- `proper_area=6.477350382016185`.
- Global maximum **quadratic metric** mismatch in this grid:
  `0.2707040480112222`, below design limit `0.30`.
- **1000/1000** random challenge points within metric tolerance;
  max sampled mismatch `0.2665962040237954`,
  median `0.08636815116489935`, p90 `0.16744257250259484`,
  p99 `0.22896659134821631`. Four corner worst metric
  mismatch `0.2707040480112222`.
- Exactly two header-free float columns: a={−250,−240,−230,−220}
  m/s² and j={−0.29166666666666669,−0.075000000000000011,
  +0.14166666666666672} m/s³, each combination.
- W3/I15 injection truth (a,j)=(−235,−0.25) is **off grid**;
  two closest cells a=−240 and −230 with j≈−0.2916667,
  each with predicted leading-order coherent-power metric mismatch
  `0.16431401102179768`.

**Conclusion:** validated source and full 12-row bank generation on the
target HPC node; the FFT-midpoint epoch convention is explicit and
compatible with PULSEJET's polynomial timing source. **Not yet** a
generated-bank GPU detection or measured search-S/N mismatch. Next
step: PULSEJET searches exact generated file using the prior centered
8,388,608-sample W3/I15 segment, DM8, old-image frequency-bound
workaround and previously measured matched-template S/N 36.15.
Do not overinterpret 1,000/1,000 metric challenge coverage as actual
astrophysical recovery completeness.


## 2026-10-27 — FIRST externally generated 12-template bank recovered W3/I15 on GPU (PASS)

On `node3`, user ran PULSEJET `scripts/run_m62_w3_i15_generated_bank_integration.sh` against the real MeerKAT W3 observational filterbank containing our existing injections, using the **actual generator output** SHA256 `969af3da3f5a271d36af4ed98808a6d68337592eaa1d127a5159faf95a02a29f` and no hardcoded replacement or injected truth row. All 12 bank rows passed strict SHA/JSON/format checks before passing to the pinned PULSEJET GPU SIF.

- Search: DM8 fixed; `start_sample=3216372`, `nsamples=fft_size=8388608`, duration `505.2902701172523 s`; W3/I15 truth f=383Hz, a=−235m/s², j=−0.25m/s³; old SIF PeakFinder workaround requested min187 max395Hz.
- **Execution: success/exit0, A40 GPUs recognized, all 12 polynomial templates resampled, 18s external wall**. Raw spectral detections **244 →47 after per-template harmonic distillation →4 after bank distillation/final**, 44 nested associations.
- **Top recovered candidate:** f=`383.000153 Hz`, DM8, `a=−230 m/s²`, `j≈−0.2916666567 m/s³` (XML float representation), **search S/N 25.15**, `nh=3`, 11 nested associations. Frequency error +0.000153Hz ≈0.077 Fourier bins. The truth `(-235,-0.25)` is absent from the bank; nearest metric-distance points are `(-230,-0.2916667)` and `(-240,-0.2916667)`, both with `mu_pred=0.164314011022`. Thus this **passes first off-grid bank-generation + PULSEJET C++ two-column reader + GPU full-pipeline injection recovery**.
- Single-template exact-motion control on the same W3 observation/segment/DM had search S/N **36.15**. Off-grid ratio **25.15/36.15 = 0.6956**, **observed spectral-S/N reduction 30.44%**. This is **not** a direct observation of 30.44% coherent power mismatch, nor a failure of the metric-predicted **16.43% fundamental quadratic coherent-power** mismatch. Candidate `nh=3` corresponds to an **8-harmonic summing stage** in `PULSEJET_beta/src/kernels.cu` (harmonic stages contain 2,4,8,16... harmonics). Higher harmonics experience much stronger residual phase distortion.

**Independent coherent-phase model check for the chosen off-grid offset** `Δa=5 m/s²`, `Δj=−1/24 m/s³`, f=383Hz, T=505.29027s: frequency-projected complex-coherence power losses about **0.1518 at fundamental**, **0.4836 at 2nd harmonic**, **0.7708 at 3rd**, **0.9155 at 4th**. This helps explain why the 8-harmonic spectral search statistic need not track fundamental quadratic `mu_pred=0.1643`. Phase models do not account for PULSEJET resampling, harmonic weighting, RFI, finite frequency binning or normalization. A physics-grounded **harmonic-aware mismatch objective** may be useful later, once controlled S/N-vs-mismatch experiments quantify sensitivity.

**Reproducibility:** source and results recorded also in `PULSEJET_beta/docs/paper/PULSEJET_VALIDATION_LOG.md` (commit `bf9276877d54440ea1f6d1c53be35b581c2ebfda`). GPU data at
`/home/rnag/PULSEJET_validation/stage8_m62_generated_bank/w3_i15_dm8_generated_grid12_center8m_v1/overview.xml`, corresponding `.log`, `_provenance.txt`. The existing W3 injected `.fil`, generated bank, original legacy generator, PULSEJET source/kernels, third-party distillers and pinned image were **not** edited for this experiment.

**Next:** isolate the two nearest templates with single-template GPU controls, check possible harmonic-level effects on template tolerance, and then expand to a common envelope/DM grid with injected truths deliberately off-grid. No broad completeness claim yet.


## 2026-10-27 — Two equal-distance off-grid nearest templates independently confirmed on A40

Paired GPU search source: `PULSEJET_beta/scripts/run_m62_w3_i15_generated_bank_nearest_controls.sh` on node3, same existing W3/I15 injected filterbank, pinned image, DM8, exactly centered 8,388,608-sample segment, unchanged workaround frequency range 187–395 Hz. Each control used one of the **actual** two nearest templates from externally generated `w3_i15_reference.txt` (SHA256 `969af3da3f5a271d36af4ed98808a6d68337592eaa1d127a5159faf95a02a29f`) chosen programmatically, with no injected truth row in either bank.

| Template | a (m/s²) | j (m/s³) | Local predicted μ (fundamental coherent power) | Recovered f (Hz) | PULSEJET search S/N | `nh` stage |
|---|---:|---:|---:|---:|---:|---:|
| One-row nearest A | −240 | −0.2916666666666667 | 0.164314 | 383.000153 | 24.98 | 3 (8 harmonics) |
| One-row nearest B | −230 | −0.2916666666666667 | 0.164314 | 383.000153 | 25.15 | 3 (8 harmonics) |
| Full generated 12-row bank | −230 | −0.2916666666666667 | 0.164314 | 383.000153 | 25.15 | 3 (8 harmonics) |
| Previously validated truth row | −235 | −0.25 | 0 | 382.999908 | 36.15 | 3 (8 harmonics) |

All runs exited normally. Each standalone nearest-template search took 10 s external wall. Compared to matched-truth S/N 36.15, nearest A lost **30.9087%**, nearest B **30.4354%** in **harmonic-summed spectral search S/N**. The two equally metric-distant templates differ by only 0.17 S/N (~0.68% of B S/N), reassuring but not statistically establishing global predictive metric accuracy. Most importantly, the full bank returned **exactly** the one-template B result: cross-template Doppler candidate distillation did **not** cause the observed mismatch-related S/N reduction in this case.

The predicted μ=0.164314 is a *quadratic approximation to fundamental coherent power loss*, not expected to equal eight-harmonic search-S/N loss. A controlled mismatch-versus-harmonic study will be needed before claiming harmonic-aware bank tolerance or population efficiency. Current test demonstrates the **generator-to-PULSEJET readback-to-GPU integration with off-grid truth and nearest-template robustness** for one injected signal in realistic observational background.

Complete GPU details have been appended to `PULSEJET_beta/docs/paper/PULSEJET_VALIDATION_LOG.md`, commit `ccfa1bf260c36c35bf476daa61c5484c07106383`. Original source and injected .fil were not modified.
