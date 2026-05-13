#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRIS Neumayer Modern Comparator Audit

Purpose
-------
Addresses the critique:
"the conventional comparator is intentionally weak."

This script compares IRIS-style predictors against stronger modern-but-small-n
comparators on the Neumayer III HRV transfer layer.

Comparators:
1. HR-only conventional baseline.
2. Best single early HRV marker.
3. IRIS prespecified composite predictors.
4. Regularized logistic regression on early HRV features with LOOCV.
5. Ridge-style linear risk score with LOOCV.
6. Permuted-label controls.

Important:
- This is still n=25 and retrospective.
- A strong comparator can reduce or erase ΔAUC.
- If it does, report that honestly. The goal is not to protect a toy comparator.
"""

from __future__ import annotations

import argparse, json, math, re
from pathlib import Path
import numpy as np
import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--subject-window-features", required=True,
                   help="From neumayer_transfer_atlas_v4/tables/neumayer_subject_window_features.csv")
    p.add_argument("--atlas", required=True,
                   help="From neumayer_transfer_atlas_v4/tables/neumayer_transfer_atlas.csv")
    p.add_argument("--out", required=True)
    p.add_argument("--endpoint", default="end_late_sympathetic_state")
    p.add_argument("--early-window", default="E0")
    p.add_argument("--late-window", default="L6_9")
    p.add_argument("--n-null", type=int, default=5000)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def auc_rank(score, y):
    score = np.asarray(score, dtype=float)
    y = np.asarray(y, dtype=int)
    ok = np.isfinite(score) & np.isfinite(y)
    score, y = score[ok], y[ok]
    if len(score) < 4 or len(np.unique(y)) < 2:
        return math.nan
    pos = y == 1
    neg = y == 0
    n_pos, n_neg = int(pos.sum()), int(neg.sum())
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
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def zmat(X):
    X = np.asarray(X, dtype=float)
    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0)
    sd[~np.isfinite(sd) | (sd == 0)] = 1.0
    X = (X - mu) / sd
    X = np.where(np.isfinite(X), X, 0.0)
    return X


def sigmoid(x):
    x = np.clip(x, -40, 40)
    return 1/(1+np.exp(-x))


def fit_logistic_ridge(X, y, lam=1.0, steps=1500, lr=0.05):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    Xb = np.c_[np.ones(len(X)), X]
    w = np.zeros(Xb.shape[1])
    for _ in range(steps):
        p = sigmoid(Xb @ w)
        grad = Xb.T @ (p - y) / len(y)
        grad[1:] += lam * w[1:] / len(y)
        w -= lr * grad
    return w


def predict_logistic_ridge(w, X):
    Xb = np.c_[np.ones(len(X)), X]
    return sigmoid(Xb @ w)


def fit_ridge_linear(X, y, lam=1.0):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    Xb = np.c_[np.ones(len(X)), X]
    I = np.eye(Xb.shape[1])
    I[0,0] = 0
    return np.linalg.pinv(Xb.T @ Xb + lam * I) @ Xb.T @ y


def predict_ridge_linear(w, X):
    Xb = np.c_[np.ones(len(X)), X]
    return Xb @ w


def loocv_scores(X, y, model="logistic", lam=1.0):
    X = zmat(X)
    y = np.asarray(y, dtype=int)
    preds = np.zeros(len(y), dtype=float)
    for i in range(len(y)):
        train = np.ones(len(y), dtype=bool)
        train[i] = False
        Xtr, ytr = X[train], y[train]
        Xte = X[~train]
        if model == "logistic":
            w = fit_logistic_ridge(Xtr, ytr, lam=lam)
            preds[i] = predict_logistic_ridge(w, Xte)[0]
        else:
            w = fit_ridge_linear(Xtr, ytr, lam=lam)
            preds[i] = predict_ridge_linear(w, Xte)[0]
    return preds


def emp_p(obs, arr):
    arr = np.asarray([x for x in arr if np.isfinite(x)], dtype=float)
    if len(arr) == 0 or not np.isfinite(obs):
        return math.nan
    return float((np.sum(arr >= obs) + 1)/(len(arr)+1))


def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    out = Path(args.out); tables = out/"tables"; out.mkdir(parents=True, exist_ok=True); tables.mkdir(exist_ok=True)

    sf = pd.read_csv(args.subject_window_features)
    sf = sf[(sf["early_window"] == args.early_window) & (sf["late_window"] == args.late_window)].copy()
    if sf.empty:
        raise ValueError("No matching early/late window rows found.")

    endpoint = pd.to_numeric(sf[args.endpoint], errors="coerce")
    cutoff = endpoint.quantile(2/3)
    y = (endpoint >= cutoff).astype(int).to_numpy()

    early_cols = [c for c in sf.columns if c.endswith("_early") and any(k in c for k in ["mean_hr", "mean_log_hf", "mean_lfnu", "mean_hfnu", "mean_log_lfhf", "mean_log_lf", "slope_hr", "slope_log_hf", "slope_lfnu", "slope_hfnu", "slope_log_lfhf", "slope_log_lf"])]
    X = sf[early_cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)

    predictors = {
        "HR_only": pd.to_numeric(sf["pred_hr_only"], errors="coerce").to_numpy(dtype=float),
        "IRIS_balanced": pd.to_numeric(sf["pred_iris_balanced"], errors="coerce").to_numpy(dtype=float),
        "IRIS_vagal_sympathetic": pd.to_numeric(sf["pred_iris_vagal_sympathetic"], errors="coerce").to_numpy(dtype=float),
        "IRIS_hybrid": pd.to_numeric(sf["pred_iris_hybrid"], errors="coerce").to_numpy(dtype=float),
        "best_single_early_marker_placeholder": None,
    }

    # Best single early marker, transparently labeled as optimistic in-sample screen.
    single_rows = []
    for col in early_cols:
        sc = pd.to_numeric(sf[col], errors="coerce").to_numpy(dtype=float)
        a = auc_rank(sc, y)
        ai = auc_rank(-sc, y)
        if np.isfinite(ai) and (not np.isfinite(a) or ai > a):
            a = ai; direction = "inverse"
        else:
            direction = "positive"
        single_rows.append({"marker": col, "auc": a, "direction": direction})
    single_df = pd.DataFrame(single_rows).sort_values("auc", ascending=False)
    best_col = single_df.iloc[0]["marker"]
    best_score = pd.to_numeric(sf[best_col], errors="coerce").to_numpy(dtype=float)
    if single_df.iloc[0]["direction"] == "inverse":
        best_score = -best_score
    predictors[f"best_single_marker_in_sample__{best_col}"] = best_score

    # Modern LOOCV models.
    for lam in [0.1, 1.0, 10.0]:
        predictors[f"LOOCV_logistic_ridge_lam_{lam}"] = loocv_scores(X, y, model="logistic", lam=lam)
        predictors[f"LOOCV_linear_ridge_lam_{lam}"] = loocv_scores(X, y, model="linear", lam=lam)

    rows = []
    for name, score in predictors.items():
        if score is None:
            continue
        auc = auc_rank(score, y)
        null_auc = [auc_rank(score, rng.permutation(y)) for _ in range(args.n_null)]
        rows.append({
            "model": name,
            "endpoint": args.endpoint,
            "early_window": args.early_window,
            "late_window": args.late_window,
            "n_subjects": int(len(y)),
            "n_high_endpoint": int(y.sum()),
            "auc": auc,
            "label_permutation_p": emp_p(auc, null_auc),
        })

    res = pd.DataFrame(rows).sort_values("auc", ascending=False)
    res.to_csv(tables/"modern_comparator_audit.csv", index=False)
    single_df.to_csv(tables/"single_marker_screen.csv", index=False)

    report = []
    report.append("# Neumayer modern comparator audit\n")
    report.append("## Purpose\n")
    report.append("This audit addresses the critique that HR-only is a weak conventional comparator. It compares IRIS-style scores against best single markers and regularized LOOCV models using early HRV features.\n")
    report.append("## Results\n")
    report.append(res.to_markdown(index=False))
    report.append("\n## Interpretation guardrail\n")
    report.append("If LOOCV ridge/logistic models match or outperform IRIS composites, the claim should be reframed from 'IRIS beats conventional monitoring' to 'IRIS captures an interpretable autonomic geometry comparable to small-n multivariable HRV models.'\n")
    report.append("The best single-marker screen is optimistic and should not be treated as a validated comparator unless cross-validated or replicated.\n")
    (out/"modern_comparator_audit_report.md").write_text("\n".join(report), encoding="utf-8")

    print(json.dumps({"out": str(out), "rows": len(res), "top_model": str(res.iloc[0]["model"]), "top_auc": float(res.iloc[0]["auc"])}, indent=2))


if __name__ == "__main__":
    main()
