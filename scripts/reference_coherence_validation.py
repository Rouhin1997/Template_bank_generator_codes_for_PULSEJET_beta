#!/usr/bin/env python3
"""Reproducible phase-coherence validation for paper-development records.

Outputs both local quadratic predicted mismatch and independently evaluated
complex coherent-power loss after fitting a linear phase (spin frequency).
For offsets as large as 0.30 the metric is NOT expected to be exact.
This script does not execute PULSEJET or claim harmonic-summed S/N loss.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess

from pulsejet_bank.metric import ProjectedMetric, coherent_power_loss


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--frequency-hz",type=float,default=383.0)
    parser.add_argument("--duration-s",type=float,default=505.2902701172523)
    parser.add_argument("--samples",type=int,default=4096)
    args=parser.parse_args()
    m=ProjectedMetric(args.frequency_hz,args.duration_s)
    try:
        commit = subprocess.check_output(
            ["git","rev-parse","HEAD"],stderr=subprocess.DEVNULL,text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    rows=[]
    for mu in (0.01,0.03,0.1,0.3):
        for label,afrac,jfrac in (
            ("acceleration_only",1.0,0.0),
            ("jerk_only",0.0,1.0),
            ("mixed_equal_metric",1/math.sqrt(2),1/math.sqrt(2)),
        ):
            da=math.sqrt(mu/m.gaa)*afrac
            dj=math.sqrt(mu/m.gjj)*jfrac
            predicted=m.mismatch(da,dj)
            computed=coherent_power_loss(
                m.frequency_hz,m.duration_s,da,dj,samples=args.samples
            )
            rows.append({
                "case":label,"target_mismatch":mu,
                "delta_acceleration_m_s2":da,
                "delta_jerk_m_s3":dj,
                "predicted_quadratic_power_loss":predicted,
                "numerical_frequency_detrended_power_loss":computed,
                "numerical_minus_predicted":computed-predicted,
            })
    report={
        "format_version":1,
        "method":"midpoint phase residual + least-squares linear-frequency projection",
        "utc_created":datetime.now(timezone.utc).isoformat(),
        "git_commit":commit,
        "frequency_hz":m.frequency_hz,
        "duration_s":m.duration_s,
        "phase_samples":args.samples,
        "g_aa":m.gaa,"g_aj":0.0,"g_jj":m.gjj,
        "rows":rows,
        "note":("Validation of local coherent power only; 0.3 is outside "
                "strict asymptotic regime, and this is not a PULSEJET S/N test."),
    }
    if not args.output.parent.is_dir():
        raise FileNotFoundError("Report output directory must exist")
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "git_commit":commit,
        "cases":len(rows),
        "max_abs_residual_mu_le_0p1":max(
            abs(r["numerical_minus_predicted"]) for r in rows
            if r["target_mismatch"]<=0.1
        ),
        "output":str(args.output),
    },indent=2))


if __name__ == "__main__":
    main()
