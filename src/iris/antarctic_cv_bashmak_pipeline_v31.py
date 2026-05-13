#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Bashmak-level pipeline scaffold for stress-revealed cardiovascular reserve topology.

This script runs multi-station real environmental forcing experiments using:
  - AntAWS 3-hourly station weather -> cold(t), pressure-derived hypoxia proxy(t)
  - NMDB SOPO neutron monitor -> radiation-associated environmental proxy(t)
  - Mechanistic reserve dynamics from antarctic_cv_reserve_model_realdata_v2.py

It adds manuscript-oriented analyses:
  - station comparison
  - reserve anisotropy / hidden divergence
  - class trajectory separability
  - stricter false-stability modes
  - manuscript-ready tables and figures

It is still a hypothesis-generating computational model, not clinical diagnosis,
not patient-specific prediction, not absorbed dose, and not organ-specific radiation
estimation. Yes, we say it repeatedly because reviewers own knives.

PowerShell quick start:
  cd $env:USERPROFILE\Downloads
  py -m pip install numpy pandas matplotlib
  py .\antarctic_cv_bashmak_pipeline.py --real-data .\real_data --out .\results_bashmak --mode paper --n 600 --seed 42

If the base model file is not in the same folder, pass:
  --base-model .\antarctic_cv_reserve_model_realdata_v2.py
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import itertools
import json
import math
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


DEFAULT_STATIONS = [
    "Concordia",
    "Dome C",
    "Dome Fuji",
    "Dome_A",
    "Byrd",
    "Clean Air",
    "Cape Denison",
]

MODE_PRESETS = {
    # exploratory, intentionally permissive
    "screening": {"critical_reserve": 0.22, "false_stability_drop": 0.18, "false_stability_observed_slope_abs": 0.015},
    # manuscript/default: false stability should be specific, not a confetti cannon
    "paper": {"critical_reserve": 0.22, "false_stability_drop": 0.30, "false_stability_observed_slope_abs": 0.006},
    # stress-test model sensitivity; not main inference
    "severe": {"critical_reserve": 0.35, "false_stability_drop": 0.25, "false_stability_observed_slope_abs": 0.008},
}


def load_base_module(base_model: Path):
    if not base_model.exists():
        raise FileNotFoundError(
            f"Base model not found: {base_model}\n"
            "Put antarctic_cv_reserve_model_realdata_v2.py in the same folder or pass --base-model."
        )
    spec = importlib.util.spec_from_file_location("cv_base_model_v2", str(base_model))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import base model from {base_model}")
    mod = importlib.util.module_from_spec(spec)
    # Python 3.13 dataclasses expect dynamically loaded modules to be registered
    # in sys.modules while class decorators run. Without this, @dataclass can
    # fail with: AttributeError: 'NoneType' object has no attribute '__dict__'.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def safe_station_name(station: str) -> str:
    return station.replace(" ", "_").replace("/", "_").replace("\\", "_").replace("!", "")


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def reserve_columns(base) -> List[str]:
    return [f"reserve_{name}" for name in base.RESERVE_NAMES]


def add_topology_columns(ts: pd.DataFrame, base) -> pd.DataFrame:
    rcols = reserve_columns(base)
    arr = ts[rcols].to_numpy(dtype=float)
    ts = ts.copy()
    ts["reserve_anisotropy"] = np.nanmax(arr, axis=1) - np.nanmin(arr, axis=1)
    ts["reserve_mean"] = np.nanmean(arr, axis=1)
    ts["reserve_std_across_axes"] = np.nanstd(arr, axis=1)
    # Observability Collapse Index: high latent divergence with high measurement degradation.
    # Normalize sigma within run for comparability.
    sig = ts["observation_sigma"].to_numpy(dtype=float)
    sig_norm = (sig - np.nanmin(sig)) / (np.nanmax(sig) - np.nanmin(sig) + 1e-12)
    ts["observability_collapse_index"] = ts["reserve_anisotropy"].to_numpy(dtype=float) * sig_norm
    return ts


def class_separability(ts: pd.DataFrame, base) -> pd.DataFrame:
    """Between-class centroid distance divided by within-class scatter over time."""
    rcols = reserve_columns(base)
    rows = []
    for time_h, g in ts.groupby("time_h", sort=True):
        classes = sorted(g["latent_class"].dropna().unique().tolist())
        if len(classes) < 2:
            continue
        centroids = []
        within = []
        for cls in classes:
            sub = g[g["latent_class"] == cls][rcols].to_numpy(dtype=float)
            if len(sub) == 0:
                continue
            c = np.nanmean(sub, axis=0)
            centroids.append(c)
            within.append(float(np.nanmean(np.linalg.norm(sub - c, axis=1))))
        if len(centroids) < 2:
            continue
        dists = [float(np.linalg.norm(a - b)) for a, b in itertools.combinations(centroids, 2)]
        between = float(np.nanmean(dists)) if dists else math.nan
        within_mean = float(np.nanmean(within)) if within else math.nan
        sep = between / (within_mean + 1e-9) if np.isfinite(between) and np.isfinite(within_mean) else math.nan
        rows.append({
            "time_h": float(time_h),
            "between_class_distance": between,
            "within_class_scatter": within_mean,
            "separability_index": sep,
            "n_classes": int(len(classes)),
        })
    return pd.DataFrame(rows)


def summarize_station(station: str, run_dir: Path, base, mode: str) -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    summary = pd.read_csv(run_dir / "population_summary.csv")
    stress = pd.read_csv(run_dir / "stress_protocol.csv")
    ts = pd.read_csv(run_dir / "time_series_full.csv.gz")
    ts = add_topology_columns(ts, base)
    sep = class_separability(ts, base)

    false_rate = float(summary["false_stability_flag"].mean()) if "false_stability_flag" in summary else math.nan
    limiting_counts = summary["limiting_axis_at_min"].value_counts().to_dict() if "limiting_axis_at_min" in summary else {}
    class_counts = summary["latent_class"].value_counts().to_dict() if "latent_class" in summary else {}

    # Environment summary
    env_stats = {}
    for col in ["cold", "hypoxia", "radiation", "workload", "sleep"]:
        if col in stress:
            env_stats[f"{col}_mean"] = float(stress[col].mean())
            env_stats[f"{col}_min"] = float(stress[col].min())
            env_stats[f"{col}_max"] = float(stress[col].max())

    row = {
        "station": station,
        "mode": mode,
        "n_systems": int(len(summary)),
        "false_stability_cases": int(summary["false_stability_flag"].sum()) if "false_stability_flag" in summary else 0,
        "false_stability_rate": false_rate,
        "min_margin_overall": float(summary["min_true_reserve_margin"].min()),
        "median_min_margin": float(summary["min_true_reserve_margin"].median()),
        "q05_min_margin": float(summary["min_true_reserve_margin"].quantile(0.05)),
        "q95_min_margin": float(summary["min_true_reserve_margin"].quantile(0.95)),
        "peak_mean_reserve_anisotropy": float(ts.groupby("time_h")["reserve_anisotropy"].mean().max()),
        "median_peak_system_anisotropy": float(ts.groupby("system_id")["reserve_anisotropy"].max().median()),
        "peak_observability_collapse_index": float(ts.groupby("time_h")["observability_collapse_index"].mean().max()),
        "peak_separability_index": float(sep["separability_index"].max()) if not sep.empty else math.nan,
        "time_peak_separability_h": float(sep.loc[sep["separability_index"].idxmax(), "time_h"]) if not sep.empty else math.nan,
        "dominant_limiting_axis": max(limiting_counts, key=limiting_counts.get) if limiting_counts else "NA",
        "limiting_axis_counts_json": json.dumps(limiting_counts, ensure_ascii=False),
        "latent_class_counts_json": json.dumps(class_counts, ensure_ascii=False),
        **env_stats,
    }

    # Save enriched topology time series but keep it compressed. Humans love giant files, disks do not.
    ts.to_csv(run_dir / "time_series_full_with_topology.csv.gz", index=False, compression="gzip")
    sep.to_csv(run_dir / "trajectory_separability.csv", index=False)
    return row, ts, sep


def plot_station_forcing(station_rows: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # One plot per variable, no subplots, no explicit colors. The chart rules are silly but less silly than unreadable figures.
    for var in ["cold_mean", "hypoxia_mean", "radiation_mean", "peak_separability_index", "false_stability_rate", "median_min_margin"]:
        if var not in station_rows:
            continue
        plt.figure(figsize=(9, 4.8))
        station_rows.sort_values(var, ascending=False).plot(kind="bar", x="station", y=var, legend=False, ax=plt.gca())
        plt.ylabel(var)
        plt.xlabel("AntAWS station")
        plt.title(var.replace("_", " "))
        plt.xticks(rotation=35, ha="right")
        plt.tight_layout()
        plt.savefig(out_dir / f"{var}.png", dpi=180)
        plt.close()


def plot_separability_curves(sep_tables: Dict[str, pd.DataFrame], out_dir: Path) -> None:
    plt.figure(figsize=(9, 5.2))
    for station, sep in sep_tables.items():
        if sep.empty:
            continue
        plt.plot(sep["time_h"], sep["separability_index"], label=station, linewidth=1.8)
    plt.xlabel("Time (h)")
    plt.ylabel("Trajectory separability index")
    plt.title("Stress-revealed reserve trajectory separability")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "figure_trajectory_separability_by_station.png", dpi=180)
    plt.close()


def make_methods_and_claims(out_dir: Path, station_rows: pd.DataFrame, mode: str, stations_requested: List[str]) -> None:
    best_sep = station_rows.sort_values("peak_separability_index", ascending=False).head(1)
    best_false = station_rows.sort_values("false_stability_rate", ascending=False).head(1)
    text = []
    text.append("# Manuscript-ready analysis scaffold\n")
    text.append("## Central claim\n")
    text.append(
        "Resting cardiovascular normality is treated as an observational equivalence class, "
        "not as proof of reserve equivalence. Under real Antarctic environmental forcing, "
        "baseline-matched systems can separate into reserve-limiting trajectories before overt collapse.\n"
    )
    text.append("## Real data fused directly\n")
    text.append("- AntAWS 3-hourly station meteorology: cold load and pressure-derived oxygen-limitation proxy.\n")
    text.append("- NMDB South Pole neutron-monitor count rate: environmental cosmic-ray proxy.\n")
    text.append("- Workload and sleep remain protocol-defined scaffolds in this version; BIDMC/EPHNOGRAM are not yet fused here.\n")
    text.append("## New metrics\n")
    text.append("- Reserve margin: RM(t)=min(PR, VAR, ODR, EPR, MET).\n")
    text.append("- Reserve anisotropy: max_j R_j(t)-min_j R_j(t), a hidden within-system divergence measure.\n")
    text.append("- Trajectory separability: between-class centroid distance / within-class scatter.\n")
    text.append("- Observability Collapse Index: reserve anisotropy × normalized observation degradation.\n")
    text.append("## False-stability calibration\n")
    text.append(f"Mode used: `{mode}`. Presets are screening, paper, severe. The paper mode uses stricter false-stability criteria to avoid turning observation failure into confetti.\n")
    text.append("## Station summary\n")
    text.append(station_rows.to_markdown(index=False))
    text.append("\n## Strongest preliminary signals\n")
    if not best_sep.empty:
        r = best_sep.iloc[0]
        text.append(f"- Highest trajectory separability: {r['station']} (peak SI={r['peak_separability_index']:.3f} at {r['time_peak_separability_h']:.2f} h).\n")
    if not best_false.empty:
        r = best_false.iloc[0]
        text.append(f"- Highest false-stability rate: {r['station']} ({100*r['false_stability_rate']:.1f}%). Treat as calibration-sensitive, not final biology.\n")
    text.append("## Non-negotiable limitations\n")
    text.append("This is not individual absorbed dose, not organ-specific dose, not SpO2, not clinical diagnosis, and not patient-specific prediction. Pressure is a hypoxia-like proxy, NMDB is a cosmic-ray environmental proxy. The point is observability and reserve topology, not fake clinical omniscience.\n")
    (out_dir / "methods_and_claims.md").write_text("\n".join(text), encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    base_model = Path(args.base_model) if args.base_model else Path(__file__).with_name("antarctic_cv_reserve_model_realdata_v2.py")
    base = load_base_module(base_model)

    if args.mode not in MODE_PRESETS:
        raise ValueError(f"Unknown mode {args.mode!r}; choose {sorted(MODE_PRESETS)}")
    preset = MODE_PRESETS[args.mode]
    config = base.SimulationConfig(
        n_systems=args.n,
        seed=args.seed,
        duration_hours=args.duration_hours,
        dt_hours=args.dt_hours,
        critical_reserve=preset["critical_reserve"],
        false_stability_drop=preset["false_stability_drop"],
        false_stability_observed_slope_abs=preset["false_stability_observed_slope_abs"],
        sample_systems_to_save=args.sample_systems,
    )

    stations = args.stations or DEFAULT_STATIONS
    real_data = Path(args.real_data).resolve()

    station_rows = []
    sep_tables: Dict[str, pd.DataFrame] = {}
    failures = []

    print(f"Output root: {out_dir}")
    print(f"Mode: {args.mode} | stations: {', '.join(stations)}")

    for station in stations:
        station_key = safe_station_name(station)
        run_dir = out_dir / "station_runs" / station_key
        print(f"\n=== Running station: {station} -> {run_dir} ===")
        try:
            result = base.run_pipeline(config, run_dir, real_data_root=real_data, antaws_station=station)
            metadata = read_json(run_dir / "metadata.json")
            antaws_meta = metadata.get("real_data_usage", {}).get("antaws", {})
            if isinstance(antaws_meta, dict) and "error" in antaws_meta:
                print(f"  Warning: AntAWS fallback for {station}: {antaws_meta.get('error')}")
            row, ts, sep = summarize_station(station, run_dir, base, args.mode)
            station_rows.append(row)
            sep_tables[station] = sep
            print(json.dumps({"station": station, "false_rate": row["false_stability_rate"], "median_min_margin": row["median_min_margin"], "peak_SI": row["peak_separability_index"]}, indent=2))
        except Exception as exc:
            failures.append({"station": station, "error": str(exc)})
            print(f"  FAILED {station}: {exc}")

    if not station_rows:
        raise RuntimeError("No station runs completed. Check AntAWS paths and base model.")

    station_df = pd.DataFrame(station_rows).sort_values("station")
    tables_dir = out_dir / "tables"
    figs_dir = out_dir / "figures"
    tables_dir.mkdir(exist_ok=True)
    figs_dir.mkdir(exist_ok=True)

    station_df.to_csv(tables_dir / "station_comparison.csv", index=False)
    pd.DataFrame(failures).to_csv(tables_dir / "station_failures.csv", index=False)

    plot_station_forcing(station_df, figs_dir)
    plot_separability_curves(sep_tables, figs_dir)
    make_methods_and_claims(out_dir, station_df, args.mode, stations)

    meta = {
        "pipeline": "antarctic_cv_bashmak_pipeline.py",
        "mode": args.mode,
        "mode_preset": preset,
        "base_model": str(base_model),
        "real_data": str(real_data),
        "stations_requested": stations,
        "stations_completed": station_df["station"].tolist(),
        "failures": failures,
        "claim_status": "real environmental forcing + topology analysis; human signal priors not yet fused",
        "disclaimer": "Hypothesis-generating computational physiology model. Not diagnosis, not patient-specific prediction, not absorbed dose, not organ dose.",
    }
    (out_dir / "pipeline_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # Convenience zip of key manuscript assets, not massive station time series.
    assets_zip = out_dir / "manuscript_assets.zip"
    if assets_zip.exists():
        assets_zip.unlink()
    temp_assets = out_dir / "manuscript_assets"
    if temp_assets.exists():
        shutil.rmtree(temp_assets)
    temp_assets.mkdir()
    shutil.copy2(tables_dir / "station_comparison.csv", temp_assets / "station_comparison.csv")
    shutil.copy2(out_dir / "methods_and_claims.md", temp_assets / "methods_and_claims.md")
    shutil.copy2(out_dir / "pipeline_metadata.json", temp_assets / "pipeline_metadata.json")
    fig_dest = temp_assets / "figures"
    fig_dest.mkdir()
    for p in figs_dir.glob("*.png"):
        shutil.copy2(p, fig_dest / p.name)
    shutil.make_archive(str(assets_zip.with_suffix("")), "zip", temp_assets)

    print("\nCompleted bashmak pipeline. Not a bashmak yet, but at least it has bones, data, and fewer lies.")
    print(json.dumps({
        "stations_completed": len(station_df),
        "outputs": [
            str(tables_dir / "station_comparison.csv"),
            str(out_dir / "methods_and_claims.md"),
            str(figs_dir),
            str(assets_zip),
        ],
    }, indent=2, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run multi-station reserve topology pipeline with real Antarctic/NMDB forcing.")
    p.add_argument("--real-data", required=True, help="Path to real_data folder.")
    p.add_argument("--out", default="results_bashmak", help="Output folder.")
    p.add_argument("--base-model", default=None, help="Path to antarctic_cv_reserve_model_realdata_v2.py. Defaults to same folder as this script.")
    p.add_argument("--mode", default="paper", choices=sorted(MODE_PRESETS), help="False-stability/calibration mode.")
    p.add_argument("--stations", nargs="*", default=None, help="AntAWS station names. Default uses a multi-station panel.")
    p.add_argument("--n", type=int, default=600, help="Number of in silico systems per station.")
    p.add_argument("--seed", type=int, default=42, help="Random seed.")
    p.add_argument("--radiation-scale", type=float, default=1.0, help="Scale radiation forcing channel for ablation sensitivity.")
    p.add_argument("--radiation-shuffle", action="store_true", help="Shuffle radiation forcing channel in time for ablation sensitivity.")
    p.add_argument("--duration-hours", type=float, default=72.0, help="Simulation duration.")
    p.add_argument("--dt-hours", type=float, default=0.05, help="Simulation timestep.")
    p.add_argument("--sample-systems", type=int, default=30, help="Number of systems saved in sample time series.")
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
