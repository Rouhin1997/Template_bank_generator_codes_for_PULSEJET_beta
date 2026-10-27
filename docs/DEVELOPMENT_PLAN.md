# Scientific development and validation plan

**Repository:** [Template_bank_generator_codes_for_PULSEJET_beta](https://github.com/Rouhin1997/Template_bank_generator_codes_for_PULSEJET_beta)
**Development branch:** `dev/midpoint-metric-bank` (original `main` preserved)
**As of:** 2026-10-27

The original 2025 Colab prototype is retained unchanged for provenance. New
modules live under `pulsejet_bank/`; we make no changes to PULSEJET_beta or
INCEPTION during the bank-generator mathematics/CPU-validation stage.

## Scientific contract

A generated row is exactly **`a_mid  j_mid`**, in m/s² and m/s³,
where the parameters are defined at the **midpoint of the searched FFT
segment**. The format is two whitespace-separated finite decimal floats,
no header needed, matching PULSEJET's Polynomial_TemplateBank_Reader.

A bank is designed for:

- an actual segment duration `T=N_fft*tsamp`;
- an acceleration–jerk rectangular domain;
- a conservative *fundamental* spin-frequency design ceiling `f_max`;
- a requested leading-order local coherent-**power** metric mismatch `mu`.

The metric can predict template-vs-truth phase coherence but cannot by
itself predict the final Peasoup/PULSEJET harmonic-summed candidate S/N.

## Phases and acceptance gates

### Phase 1 — Consistent phase and epoch model

- [x] Cross-check source-level PULSEJET polynomial GPU warp:
      `tau=(i-N_fft/2)*tsamp`,
      `t_arr=tau+(a*tau²/2+j*tau³/6)/c`.
- [x] Make midpoint and start acceleration conversion explicit.
- [x] Fix exact `c=299792458` m/s.
- [x] Unit tests for sign conventions and arrival-time mapping.

Acceptance: exact algebraic agreement with the GPU timing model and no
start/midpoint ambiguity. The physical phase formula is leading-order
in the propagation delay.

### Phase 2 — Frequency-projected metric

- [x] Derive projected metric using phase covariance/Schur complement.
- [x] Independent quadrature of phase derivatives and frequency projection.
- [x] Compare metric-predicted mismatch to numerical coherent-power loss
      for small offsets (with linear frequency phase detrending).
- [x] Test frequency and segment-duration scaling.

Acceptance: independently computed coefficient agreement at defined
tolerances; explicitly state limitations of small-mismatch expansion.

### Phase 3 — Bank construction

- [x] Deterministic rectangular metric grid with provable quadratic metric
      bound **everywhere in the supplied box**, including corners.
- [x] Independent seeded stochastic IID metric-volume sampler (reference
      comparison rather than an unvalidated MH/emcee implementation).
- [x] Report exact bank counts and budget provenance.
- [x] Reject pathological bank sizes and invalid parameters.

Acceptance: grid matches its global local-metric bound and stochastic
coverage claims are restricted to empirical measurements.

Future studies:
- [ ] Reimplement and benchmark the original MH and emcee variants if
      they outperform IID draws under a fair mismatch/CPU/GPU comparison.
- [ ] Compare triangular/A2 covering lattice and boundary treatments.
- [ ] Stress-test random seeds and long-duration/high-frequency banks.
- [ ] Benchmark coverage-calculation acceleration for N>20k.

### Phase 4 — File interface, CLI and provenance

- [x] Two columns, `%.17g` precision, no header.
- [x] SHA-256 checksum and machine-readable JSON validation report.
- [x] No accidental overwrite without `--overwrite`.
- [x] Unit tests for round-trip, reproducibility and CLI.
- [ ] Execute bank in the actual cluster image with
      `Polynomial_TemplateBank_Reader`; CPU-format verification by
      source inspection is not a full integration test.

### Phase 5 — Scientific validation with real observations

- [ ] Fix PeakFinder min-frequency range bug, regression-test, build
      versioned new PULSEJET image (separate explicit approval).
- [ ] Generate realistic window-specific banks spanning all injected
      accelerations and jerks, *without placing truth in every bank*.
- [ ] Test a shared DM grid and candidate-to-injection matching.
- [ ] Collect metric distances, predicted coherent mismatch, recovered
      frequency, a, j, search S/N and harmonic level.
- [ ] Compare with matched-template controls to measure actual S/N loss.
- [ ] Include uninjected observations to flag real pulsars and RFI.
- [ ] Verify recovered candidates by *independent* PulsarX folding.
- [ ] Preserve bank file SHA, metadata, versioned container, per-case logs
      and figures for paper reproducibility.

## Versioned recordkeeping

- `docs/VALIDATION_LOG.md`: append results, command lines, revisions,
  failures and limitations; never overwrite prior scientific outcomes.
- `tests/`: deterministic CPU regression suite.
- `.github/workflows/validate-bank.yml`: repeatable CI check.
- Optional CLI `--report report.json`: parameters, coefficients,
  template count, SHA256, empirical mismatch diagnostics.
- The source branch and generated bank checksum must accompany each
  PULSEJET search run.

No current result is a claim of complete detection efficiency or actual
flux-density completeness.
