"""Reproducible metric-bank generator CLI."""
import argparse
import json
from pathlib import Path
import sys

from .bank import (BankSpec, grid_shape, grid_worst_case_metric_bound,
                   make_grid, make_stochastic, metric_coverage,
                   stochastic_count, write_bank)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=("Generate a midpoint-referenced PULSEJET a/j bank. "
                     "Use a design frequency at least as high as the "
                     "highest fundamental spin frequency in the search.")
    )
    p.add_argument("--frequency-hz", type=float, required=True, help="Maximum design spin frequency in Hz")
    p.add_argument("--duration-s", type=float, required=True, help="Actual search FFT segment duration in seconds")
    p.add_argument("--a-min", type=float, required=True, help="Lower acceleration bound (m/s^2)")
    p.add_argument("--a-max", type=float, required=True, help="Upper acceleration bound (m/s^2)")
    p.add_argument("--j-min", type=float, required=True, help="Lower jerk bound (m/s^3)")
    p.add_argument("--j-max", type=float, required=True, help="Upper jerk bound (m/s^3)")
    p.add_argument("--mismatch", type=float, required=True,
                   help="Target LOCAL fractional coherent power mismatch (0 < mu < 1)")
    p.add_argument("--method", choices=("grid","stochastic"), default="grid",
                   help="grid = deterministic quadratic metric bound; stochastic = IID draws")
    p.add_argument("--coverage", type=float, default=0.9,
                   help="Stochastic-only INTERIOR Poisson coverage estimate; not a guarantee")
    p.add_argument("--templates", type=int, help="Stochastic-only explicit bank size")
    p.add_argument("--seed", type=int, default=1, help="Bank random seed (stochastic only)")
    p.add_argument("--validation-points", type=int, default=1000)
    p.add_argument("--validation-seed", type=int, default=2026)
    p.add_argument("--output", type=Path, required=True, help="Header-free two-column text bank")
    p.add_argument("--report", type=Path, help="Optional JSON validation report")
    p.add_argument("--overwrite", action="store_true", help="Permit replacing existing outputs")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.method == "grid" and args.templates is not None:
        parser().error("--templates is only valid with --method stochastic")
    spec = BankSpec(
        frequency_hz=args.frequency_hz, duration_s=args.duration_s,
        a_min=args.a_min, a_max=args.a_max, j_min=args.j_min,
        j_max=args.j_max, max_mismatch=args.mismatch,
    )
    if args.report and args.report.resolve() == args.output.resolve():
        raise ValueError("Report and bank paths must be different")
    if args.report and args.report.exists() and not args.overwrite:
        raise FileExistsError(f"Report exists: {args.report}; use --overwrite")
    if args.method == "grid":
        bank = make_grid(spec)
        na,nj = grid_shape(spec)
        method_meta = {
            "grid_shape": [na,nj],
            "grid_worst_case_quadratic_mismatch_bound": grid_worst_case_metric_bound(spec),
        }
    else:
        n = args.templates if args.templates is not None else stochastic_count(spec,args.coverage)
        bank = make_stochastic(spec, count=n, target_coverage=args.coverage, seed=args.seed)
        method_meta = {
            "seed": args.seed, "poisson_interior_coverage_design": args.coverage,
            "budget_source": "explicit" if args.templates is not None else "interior_poisson_estimate",
            "note": "No coverage guarantee. Near-edge coverage is usually lower.",
        }
    # Estimate coverage before committing bank and report.
    empirical = metric_coverage(spec, bank, samples=args.validation_points,seed=args.validation_seed)
    hash_hex = write_bank(args.output,bank,overwrite=args.overwrite)
    report = {
        "format_version": 1,
        "model": "midpoint_phase_metric_frequency_projected_leading_order",
        "method": args.method,
        "design": vars(spec),
        "metric": {"g_aa":spec.metric.gaa, "g_aj":0.0, "g_jj":spec.metric.gjj},
        "proper_area": spec.proper_area,
        "template_count": len(bank),
        "bank_sha256": hash_hex,
        "validation": empirical,
        "construction": method_meta,
        "limitations": [
            "Quadratic metric controls coherent power only to leading order/small mismatch.",
            "Spin frequency is projected out; higher harmonics may have larger mismatch.",
            "Not a guarantee on PULSEJET spectral S/N or end-to-end detection completeness.",
            "Jerk and acceleration refer to the FFT segment midpoint.",
        ],
    }
    if args.report:
        if not args.report.parent.is_dir():
            raise FileNotFoundError(f"Report directory does not exist: {args.report.parent}")
        args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
