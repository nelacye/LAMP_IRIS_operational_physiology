#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify radiation ablation actually changed stress_protocol.csv.

Run:
  py .\verify_radiation_ablation_stress.py --root .\radiation_ablation_runs_env
"""

from __future__ import annotations
import argparse
from pathlib import Path
import json
import pandas as pd
import numpy as np


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    return p.parse_args()


def main():
    args = parse_args()
    root = Path(args.root)
    rows = []
    series = {}
    for arm in ["rad0", "rad05", "rad1", "radshuffle"]:
        files = list((root / arm).rglob("stress_protocol.csv"))
        for p in files:
            station = p.parent.name
            df = pd.read_csv(p)
            if "radiation" not in df.columns:
                rows.append({"arm": arm, "station": station, "file": str(p), "error": "NO radiation column"})
                continue
            r = pd.to_numeric(df["radiation"], errors="coerce")
            rows.append({
                "arm": arm,
                "station": station,
                "file": str(p),
                "n": int(r.notna().sum()),
                "mean": float(r.mean()),
                "std": float(r.std()),
                "min": float(r.min()),
                "median": float(r.median()),
                "max": float(r.max()),
            })
            if station == "Byrd":
                series[arm] = r.to_numpy(dtype=float)
    out = pd.DataFrame(rows)
    out_path = root / "radiation_ablation_stress_verification.csv"
    out.to_csv(out_path, index=False)

    checks = {}
    if all(k in series for k in ["rad0", "rad05", "rad1", "radshuffle"]):
        checks["rad0_all_zero"] = bool(np.allclose(series["rad0"], 0))
        checks["rad05_half_rad1"] = bool(np.allclose(series["rad05"], 0.5 * series["rad1"]))
        checks["radshuffle_same_distribution_as_rad1"] = bool(np.allclose(np.sort(series["radshuffle"]), np.sort(series["rad1"])))
        checks["radshuffle_different_order_than_rad1"] = bool(not np.allclose(series["radshuffle"], series["rad1"]))

    print(json.dumps({
        "rows": len(out),
        "verification_csv": str(out_path),
        "checks": checks
    }, indent=2))


if __name__ == "__main__":
    main()
