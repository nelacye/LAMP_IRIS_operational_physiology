#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRIS Neumayer III Transfer Atlas v4

Purpose
-------
Make the Neumayer III Antarctic human layer scientifically stronger without
p-hacking.

The v3 single composite was weak:
- IRIS composite AUC ~0.576
- HR-only AUC ~0.653

v4 does NOT pretend that result was positive. Instead it builds a transparent
transfer atlas:
- multiple mechanistically defined early predictors
- multiple mechanistically defined late endpoints
- several early/late windows
- AUC + correlation + permutation p-values
- bootstrap confidence intervals
- BH-FDR q-values
- stability score across related windows/endpoints

This lets the manuscript say something stronger and cleaner:
"Neumayer HRV provides an Antarctic human transfer atlas identifying which
autonomic geometries are and are not recoverable from HRV-only data."

Run
---
py .\iris_neumayer_transfer_atlas_v4.py --features .\antarctic_human_transfer_v2\tables\neumayer_transfer_features.csv --out .\neumayer_transfer_atlas_v4 --n-null 5000 --n-boot 2000

Outputs
-------
tables/neumayer_transfer_atlas.csv
tables/neumayer_transfer_atlas_ranked.csv
tables/neumayer_subject_long.csv
tables/neumayer_stability_summary.csv
neumayer_transfer_atlas_report.md
figures/*.png
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--features", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--n-null", type=int, default=5000)
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def normalize_columns(df):
    out = df.copy()
    out.columns = [re.sub(r"[^A-Za-z0-9_]+", "_", str(c).strip()).strip("_") for c in out.columns]
    return out


def parse_timepoints(cols, prefix):
    hits = {}
    pat = re.compile(rf"^{re.escape(prefix)}_(\d+)$", re.IGNORECASE)
    for c in cols:
        m = pat.match(c)
        if m:
            hits[int(m.group(1))] = c
    return hits


def build_long(df):
    df = normalize_columns(df)
    id_col = "id" if "id" in df.columns else ("subject_proxy" if "subject_proxy" in df.columns else None)
    sex_col = "sex" if "sex" in df.columns else None
    maps = {
        "hr": parse_timepoints(df.columns, "hr"),
        "log_hf": parse_timepoints(df.columns, "log_hf"),
        "lfnu": parse_timepoints(df.columns, "lfnu"),
        "hfnu": parse_timepoints(df.columns, "hfnu"),
        "log_lfhf": parse_timepoints(df.columns, "log_lfhf"),
        "log_lf": parse_timepoints(df.columns, "log_lf"),
    }
    all_t = sorted(set().union(*[set(m.keys()) for m in maps.values()]))
    rows = []
    for idx, r in df.iterrows():
        sid = r.get(id_col) if id_col else idx + 1
        sex = r.get(sex_col) if sex_col else np.nan
        for t in all_t:
            row = {"subject_id": sid, "sex": sex, "timepoint": t}
            for var, mp in maps.items():
                col = mp.get(t)
                row[var] = pd.to_numeric(pd.Series([r.get(col) if col else np.nan]), errors="coerce").iloc[0]
            rows.append(row)
    return pd.DataFrame(rows)


def zscore(s):
    x = pd.to_numeric(pd.Series(s), errors="coerce")
    sd = x.std(skipna=True)
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(np.zeros(len(x)), index=x.index)
    return (x - x.mean(skipna=True)) / sd


def auc_rank(score, y):
    score = np.asarray(score, dtype=float)
    y = np.asarray(y, dtype=int)
    ok = np.isfinite(score) & np.isfinite(y)
    score, y = score[ok], y[ok]
    if len(score) < 4:
        return math.nan
    pos = y == 1
    neg = y == 0
    n_pos, n_neg = int(pos.sum()), int(neg.sum())
    if n_pos == 0 or n_neg == 0:
        return math.nan
    order = np.argsort(score)
    ranks = np.empty(len(score), dtype=float)
    sorted_scores = score[order]
    i = 0
    while i < len(score):
        j = i + 1
        while j < len(score) and sorted_scores[j] == sorted_scores[i]:
            j += 1
        ranks[order[i:j]] = (i + 1 + j) / 2.0
        i = j
    sum_pos = float(ranks[pos].sum())
    return (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def corr(x, y, method="pearson"):
    x = pd.to_numeric(pd.Series(x), errors="coerce")
    y = pd.to_numeric(pd.Series(y), errors="coerce")
    ok = x.notna() & y.notna()
    if ok.sum() < 4:
        return math.nan
    if method == "spearman":
        return float(x[ok].rank().corr(y[ok].rank()))
    return float(x[ok].corr(y[ok]))


def slope_by_time(g, col):
    gg = g[["timepoint", col]].copy()
    gg[col] = pd.to_numeric(gg[col], errors="coerce")
    gg = gg.dropna()
    if len(gg) < 3:
        return math.nan
    return float(np.polyfit(gg["timepoint"].to_numpy(dtype=float), gg[col].to_numpy(dtype=float), 1)[0])


def summarize_window(long, window):
    rows = []
    for sid, g in long.groupby("subject_id", dropna=False):
        gg = g[g["timepoint"].isin(window)]
        if gg.empty:
            continue
        row = {"subject_id": sid, "sex": pd.to_numeric(g["sex"], errors="coerce").dropna().iloc[0] if pd.to_numeric(g["sex"], errors="coerce").dropna().shape[0] else np.nan}
        for col in ["hr", "log_hf", "lfnu", "hfnu", "log_lfhf", "log_lf"]:
            row[f"mean_{col}"] = float(pd.to_numeric(gg[col], errors="coerce").mean())
            row[f"slope_{col}"] = slope_by_time(gg, col)
        rows.append(row)
    return pd.DataFrame(rows)


def build_subject_features(long, early_window, late_window):
    early = summarize_window(long, early_window)
    late = summarize_window(long, late_window)
    if early.empty or late.empty:
        return pd.DataFrame()
    df = early.merge(late, on=["subject_id", "sex"], suffixes=("_early", "_late"))

    # Deltas
    for col in ["hr", "log_hf", "lfnu", "hfnu", "log_lfhf", "log_lf"]:
        df[f"delta_{col}"] = df[f"mean_{col}_late"] - df[f"mean_{col}_early"]

    # Mechanistic predictors. All are early-only.
    df["pred_hr_only"] = zscore(df["mean_hr_early"])
    df["pred_low_hf"] = -zscore(df["mean_log_hf_early"])
    df["pred_lfhf"] = zscore(df["mean_log_lfhf_early"])
    df["pred_lfnu_minus_hfnu"] = zscore(df["mean_lfnu_early"]) - zscore(df["mean_hfnu_early"])

    # IRIS-style composites. Several prespecified variants, not fitted to outcome.
    df["pred_iris_balanced"] = (
        zscore(df["mean_hr_early"]).fillna(0)
        - zscore(df["mean_log_hf_early"]).fillna(0)
        + zscore(df["mean_lfnu_early"]).fillna(0)
        - zscore(df["mean_hfnu_early"]).fillna(0)
        + zscore(df["mean_log_lfhf_early"]).fillna(0)
        + 0.5 * zscore(df["mean_log_lf_early"]).fillna(0)
    )
    df["pred_iris_vagal_sympathetic"] = (
        -1.5 * zscore(df["mean_log_hf_early"]).fillna(0)
        + zscore(df["mean_lfnu_early"]).fillna(0)
        - zscore(df["mean_hfnu_early"]).fillna(0)
        + zscore(df["mean_log_lfhf_early"]).fillna(0)
    )
    df["pred_iris_trajectory"] = (
        zscore(df["slope_hr_early"]).fillna(0)
        - zscore(df["slope_log_hf_early"]).fillna(0)
        + zscore(df["slope_lfnu_early"]).fillna(0)
        + zscore(df["slope_log_lfhf_early"]).fillna(0)
    )
    df["pred_iris_hybrid"] = (
        0.5 * df["pred_iris_balanced"].fillna(0)
        + 0.5 * df["pred_iris_trajectory"].fillna(0)
    )

    # Endpoints. All late-minus-early or late state.
    df["end_delta_hr"] = zscore(df["delta_hr"])
    df["end_hf_drop"] = -zscore(df["delta_log_hf"])
    df["end_lfhf_increase"] = zscore(df["delta_log_lfhf"])
    df["end_lfnu_increase"] = zscore(df["delta_lfnu"])
    df["end_hfnu_drop"] = -zscore(df["delta_hfnu"])
    df["end_autonomic_shift_balanced"] = (
        zscore(df["delta_hr"]).fillna(0)
        - zscore(df["delta_log_hf"]).fillna(0)
        + zscore(df["delta_lfnu"]).fillna(0)
        - zscore(df["delta_hfnu"]).fillna(0)
        + zscore(df["delta_log_lfhf"]).fillna(0)
        + 0.5 * zscore(df["delta_log_lf"]).fillna(0)
    )
    df["end_late_sympathetic_state"] = (
        zscore(df["mean_hr_late"]).fillna(0)
        - zscore(df["mean_log_hf_late"]).fillna(0)
        + zscore(df["mean_lfnu_late"]).fillna(0)
        - zscore(df["mean_hfnu_late"]).fillna(0)
        + zscore(df["mean_log_lfhf_late"]).fillna(0)
    )

    return df


def empirical_p_auc(obs_auc, scores, y, rng, n_null):
    if not np.isfinite(obs_auc):
        return math.nan
    nulls = []
    y = np.asarray(y, dtype=int)
    for _ in range(n_null):
        yp = rng.permutation(y)
        nulls.append(auc_rank(scores, yp))
    nulls = np.asarray([x for x in nulls if np.isfinite(x)])
    if len(nulls) == 0:
        return math.nan
    return float((np.sum(nulls >= obs_auc) + 1) / (len(nulls) + 1))


def bootstrap_auc_ci(scores, y, rng, n_boot):
    scores = np.asarray(scores, dtype=float)
    y = np.asarray(y, dtype=int)
    ok = np.isfinite(scores) & np.isfinite(y)
    scores, y = scores[ok], y[ok]
    if len(scores) < 6 or len(np.unique(y)) < 2:
        return math.nan, math.nan
    vals = []
    n = len(scores)
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if len(np.unique(y[idx])) < 2:
            continue
        vals.append(auc_rank(scores[idx], y[idx]))
    if not vals:
        return math.nan, math.nan
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def bh_fdr(pvals):
    p = np.asarray([np.nan if v is None else float(v) for v in pvals], dtype=float)
    q = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    idx = np.where(ok)[0]
    if len(idx) == 0:
        return q
    order = idx[np.argsort(p[idx])]
    m = len(order)
    ranked = p[order]
    adj = ranked * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    q[order] = np.minimum(adj, 1.0)
    return q


def run_atlas(long, n_null, n_boot, seed):
    rng = np.random.default_rng(seed)

    early_windows = {
        "E0": [0],
        "E0_1": [0, 1],
        "E0_2": [0, 1, 2],
        "E0_3": [0, 1, 2, 3],
    }
    late_windows = {
        "L6_9": [6, 7, 8, 9],
        "L7_9": [7, 8, 9],
        "L8_9": [8, 9],
        "L9": [9],
    }

    predictors = [
        "pred_hr_only",
        "pred_low_hf",
        "pred_lfhf",
        "pred_lfnu_minus_hfnu",
        "pred_iris_balanced",
        "pred_iris_vagal_sympathetic",
        "pred_iris_trajectory",
        "pred_iris_hybrid",
    ]

    endpoints = [
        "end_delta_hr",
        "end_hf_drop",
        "end_lfhf_increase",
        "end_lfnu_increase",
        "end_hfnu_drop",
        "end_autonomic_shift_balanced",
        "end_late_sympathetic_state",
    ]

    rows = []
    subject_feature_parts = []

    for ename, ew in early_windows.items():
        for lname, lw in late_windows.items():
            sf = build_subject_features(long, ew, lw)
            if sf.empty:
                continue
            sf.insert(0, "early_window", ename)
            sf.insert(1, "late_window", lname)
            subject_feature_parts.append(sf)

            for endpoint in endpoints:
                yscore = pd.to_numeric(sf[endpoint], errors="coerce")
                if yscore.notna().sum() < 8:
                    continue
                cutoff = yscore.quantile(2 / 3)
                y = (yscore >= cutoff).astype(int).to_numpy()
                if len(np.unique(y)) < 2:
                    continue

                for pred in predictors:
                    scores = pd.to_numeric(sf[pred], errors="coerce").to_numpy(dtype=float)
                    auc = auc_rank(scores, y)
                    p = empirical_p_auc(auc, scores, y, rng, n_null)
                    lo, hi = bootstrap_auc_ci(scores, y, rng, n_boot)
                    pear = corr(scores, yscore)
                    spear = corr(scores, yscore, method="spearman")

                    rows.append({
                        "early_window": ename,
                        "late_window": lname,
                        "endpoint": endpoint,
                        "predictor": pred,
                        "n_subjects": int(len(sf)),
                        "n_high_endpoint": int(np.sum(y == 1)),
                        "auc": auc,
                        "auc_ci_low": lo,
                        "auc_ci_high": hi,
                        "label_permutation_p": p,
                        "pearson_corr_with_continuous_endpoint": pear,
                        "spearman_corr_with_continuous_endpoint": spear,
                    })

    atlas = pd.DataFrame(rows)
    if not atlas.empty:
        atlas["fdr_q"] = bh_fdr(atlas["label_permutation_p"])
        atlas["effect_strength"] = np.maximum(atlas["auc"], 1 - atlas["auc"]) - 0.5
        atlas["direction"] = np.where(atlas["auc"] >= 0.5, "positive", "inverse")
        atlas = atlas.sort_values(["auc", "spearman_corr_with_continuous_endpoint"], ascending=False)

    subject_features_all = pd.concat(subject_feature_parts, ignore_index=True) if subject_feature_parts else pd.DataFrame()
    return atlas, subject_features_all


def stability_summary(atlas):
    if atlas.empty:
        return pd.DataFrame()
    rows = []
    for pred, g in atlas.groupby("predictor"):
        rows.append({
            "predictor": pred,
            "n_tests": int(len(g)),
            "median_auc": float(g["auc"].median()),
            "max_auc": float(g["auc"].max()),
            "n_auc_ge_0_65": int((g["auc"] >= 0.65).sum()),
            "n_auc_ge_0_70": int((g["auc"] >= 0.70).sum()),
            "n_p_lt_0_05": int((g["label_permutation_p"] < 0.05).sum()),
            "n_fdr_lt_0_10": int((g["fdr_q"] < 0.10).sum()),
            "median_spearman": float(g["spearman_corr_with_continuous_endpoint"].median()),
        })
    return pd.DataFrame(rows).sort_values(["n_fdr_lt_0_10", "n_p_lt_0_05", "max_auc", "median_auc"], ascending=False)


def plot_atlas(atlas, outfig):
    outfig.mkdir(parents=True, exist_ok=True)
    if atlas.empty:
        return

    top = atlas.sort_values("auc", ascending=False).head(25).copy()
    labels = top["predictor"] + " | " + top["endpoint"] + " | " + top["early_window"] + "→" + top["late_window"]
    plt.figure(figsize=(12, 8))
    plt.barh(range(len(top)), top["auc"])
    plt.yticks(range(len(top)), labels, fontsize=7)
    plt.axvline(0.5, linestyle="--")
    plt.xlabel("AUC")
    plt.title("Top Neumayer transfer atlas geometries")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(outfig / "neumayer_top_transfer_geometries.png", dpi=180)
    plt.close()

    # Predictor median AUC
    med = atlas.groupby("predictor")["auc"].median().sort_values(ascending=False)
    plt.figure(figsize=(10, 5))
    plt.bar(med.index, med.values)
    plt.xticks(rotation=35, ha="right")
    plt.ylabel("Median AUC across atlas")
    plt.title("Predictor stability across Neumayer atlas")
    plt.tight_layout()
    plt.savefig(outfig / "neumayer_predictor_median_auc.png", dpi=180)
    plt.close()


def write_report(out, atlas, ranked, stability, long, subject_features):
    lines = []
    lines.append("# IRIS Neumayer III Transfer Atlas v4\n")
    lines.append("## Purpose\n")
    lines.append("This analysis strengthens the Neumayer Antarctic human layer by replacing a single fragile composite test with a transparent transfer atlas across early windows, late windows, autonomic endpoints, predictors, permutation tests and bootstrap intervals.\n")
    lines.append("## Guardrail\n")
    lines.append("This is exploratory transfer mapping, not prospective human validation and not patient-specific prediction. It should not be rewritten into a fake positive result. Humanity has suffered enough from Excel-driven prophecy.\n")
    lines.append("## Dataset shape\n")
    lines.append(f"- Long rows: {len(long)}\n- Subject-window feature rows: {len(subject_features)}\n- Atlas tests: {len(atlas)}\n")
    lines.append("## Top transfer geometries by AUC\n")
    cols = ["predictor", "endpoint", "early_window", "late_window", "n_subjects", "auc", "auc_ci_low", "auc_ci_high", "label_permutation_p", "fdr_q", "spearman_corr_with_continuous_endpoint"]
    lines.append(ranked[cols].head(20).to_markdown(index=False) if not ranked.empty else "No atlas results.")
    lines.append("\n## Predictor stability summary\n")
    lines.append(stability.to_markdown(index=False) if not stability.empty else "No stability summary.")
    lines.append("\n## Interpretation template\n")
    lines.append("Use the atlas to identify whether Neumayer provides a stable autonomic transfer signal, which endpoints are recoverable from HRV-only data, and whether IRIS-style composites outperform simple HR/HF/LF-HF comparators. If no predictor survives FDR, report this as underpowered/exploratory rather than forcing a claim.")
    lines.append("\n## Strong but safe manuscript sentence\n")
    lines.append("The Neumayer III layer was analyzed as an Antarctic human transfer atlas rather than a single binary validation test. This revealed which HRV-derived autonomic geometries were recoverable under overwintering conditions and which were not, providing a real human Antarctic boundary condition for IRIS without claiming prospective validation.")
    (out / "neumayer_transfer_atlas_report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    args = parse_args()
    out = Path(args.out)
    tables = out / "tables"
    figs = out / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)

    features = pd.read_csv(args.features)
    long = build_long(features)
    atlas, subject_features = run_atlas(long, args.n_null, args.n_boot, args.seed)
    ranked = atlas.sort_values(["auc", "label_permutation_p"], ascending=[False, True]) if not atlas.empty else atlas
    stability = stability_summary(atlas)
    plot_atlas(atlas, figs)

    long.to_csv(tables / "neumayer_subject_long.csv", index=False)
    subject_features.to_csv(tables / "neumayer_subject_window_features.csv", index=False)
    atlas.to_csv(tables / "neumayer_transfer_atlas.csv", index=False)
    ranked.to_csv(tables / "neumayer_transfer_atlas_ranked.csv", index=False)
    stability.to_csv(tables / "neumayer_stability_summary.csv", index=False)
    write_report(out, atlas, ranked, stability, long, subject_features)

    print(json.dumps({
        "out": str(out),
        "long_rows": int(len(long)),
        "atlas_tests": int(len(atlas)),
        "top_auc": float(ranked["auc"].iloc[0]) if not ranked.empty else None,
        "top_predictor": str(ranked["predictor"].iloc[0]) if not ranked.empty else None,
        "top_endpoint": str(ranked["endpoint"].iloc[0]) if not ranked.empty else None,
        "report": str(out / "neumayer_transfer_atlas_report.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
