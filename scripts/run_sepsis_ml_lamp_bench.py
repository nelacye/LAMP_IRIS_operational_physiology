#!/usr/bin/env python3
"""Train lightweight ML monitors on PhysioNet/CinC 2019 sepsis score tables.

This runner uses the available v3_5k patient-level feature table. It does not
reconstruct raw hourly `.psv` trajectories; instead it trains on early-window
summary features already exported by the locked sepsis benchmark. Contaminated
variants deliberately include future-window or oracle information so LAMP can
audit the resulting predictions.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402

SOURCE = ROOT / "results/sepsis_external/v3_5k/tables/sepsis_patient_scores.csv"
OUT = ROOT / "results/sepsis_ml_lamp"
SEED = 2026


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(SOURCE)
    df["label_future_sepsis"] = df["label_future_sepsis"].astype(int)

    early_cols = numeric_columns(
        df,
        exclude_prefixes=("future_",),
        exclude_exact={
            "label_future_sepsis",
            "sepsis_onset_idx",
            "anchor_idx",
            "valid_early_warning_score",
            "future_physiology_sentinel_score",
            "oracle_label_sentinel_score",
        },
    )
    future_cols = [col for col in df.columns if col.startswith("future_") and is_numeric(df[col])]
    future_feature_cols = [
        col
        for col in future_cols
        if col
        not in {
            "future_physiology_sentinel_score",
        }
    ]
    match_cols = [
        col
        for col in ["Age", "HR_recent_mean", "O2Sat_recent_mean", "ICULOS", "vital_missing_rate"]
        if col in df.columns
    ]

    patient_labels = (
        df.groupby("patient_id")["label_future_sepsis"].max().rename("patient_label").reset_index()
    )
    train_ids, test_ids = train_test_split(
        patient_labels["patient_id"].tolist(),
        test_size=0.35,
        random_state=SEED,
        stratify=patient_labels["patient_label"].tolist(),
    )
    train_ids = set(train_ids)
    test_ids = set(test_ids)

    prediction_frames = []
    model_metrics = []
    for horizon in sorted(df["horizon_h"].dropna().unique()):
        horizon_df = df[df["horizon_h"] == horizon].copy()
        train = horizon_df[horizon_df["patient_id"].isin(train_ids)].copy()
        test = horizon_df[horizon_df["patient_id"].isin(test_ids)].copy()
        if train["label_future_sepsis"].nunique() < 2 or test["label_future_sepsis"].nunique() < 2:
            continue

        y_train = train["label_future_sepsis"].to_numpy()
        y_test = test["label_future_sepsis"].to_numpy()
        weights = compute_sample_weight("balanced", y_train)

        X_train_early = train[early_cols]
        X_test_early = test[early_cols]
        X_train_future = train[early_cols + future_feature_cols]
        X_test_future = test[early_cols + future_feature_cols]

        models = {
            "mlp_early_score": make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(),
                MLPClassifier(
                    hidden_layer_sizes=(32, 16),
                    activation="relu",
                    alpha=0.001,
                    learning_rate_init=0.002,
                    max_iter=450,
                    early_stopping=True,
                    random_state=SEED,
                ),
            ),
            "gb_early_score": make_pipeline(
                SimpleImputer(strategy="median"),
                HistGradientBoostingClassifier(
                    max_iter=220,
                    learning_rate=0.04,
                    l2_regularization=0.01,
                    random_state=SEED,
                ),
            ),
            "linear_sequence_score": make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(),
                LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED),
            ),
        }
        future_models = {
            "mlp_future_leak_score": make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(),
                MLPClassifier(
                    hidden_layer_sizes=(32, 16),
                    activation="relu",
                    alpha=0.001,
                    learning_rate_init=0.002,
                    max_iter=450,
                    early_stopping=True,
                    random_state=SEED + 1,
                ),
            ),
            "gb_future_leak_score": make_pipeline(
                SimpleImputer(strategy="median"),
                HistGradientBoostingClassifier(
                    max_iter=220,
                    learning_rate=0.04,
                    l2_regularization=0.01,
                    random_state=SEED + 1,
                ),
            ),
        }

        pred = base_prediction_frame(test, match_cols)
        for score_col, model in models.items():
            fit_with_optional_weights(model, X_train_early, y_train, weights)
            pred[score_col] = model.predict_proba(X_test_early)[:, 1]
            model_metrics.append(metric_row(horizon, score_col, y_test, pred[score_col]))

        mlp_model = models["mlp_early_score"]
        hidden_train = mlp_hidden_layer(mlp_model, X_train_early)
        hidden_test = mlp_hidden_layer(mlp_model, X_test_early)
        probe = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED),
        )
        fit_with_optional_weights(probe, hidden_train, y_train, weights)
        pred["mlp_hidden_probe_score"] = probe.predict_proba(hidden_test)[:, 1]
        model_metrics.append(
            metric_row(horizon, "mlp_hidden_probe_score", y_test, pred["mlp_hidden_probe_score"])
        )

        for score_col, model in future_models.items():
            fit_with_optional_weights(model, X_train_future, y_train, weights)
            pred[score_col] = model.predict_proba(X_test_future)[:, 1]
            model_metrics.append(metric_row(horizon, score_col, y_test, pred[score_col]))

        pred["mlp_oracle_mix_score"] = (
            0.95 * pred["mlp_early_score"] + 0.05 * pred["oracle_label_sentinel_score"]
        )
        pred["mlp_hidden_oracle_probe_score"] = (
            0.95 * pred["mlp_hidden_probe_score"] + 0.05 * pred["oracle_label_sentinel_score"]
        )
        model_metrics.append(
            metric_row(horizon, "mlp_oracle_mix_score", y_test, pred["mlp_oracle_mix_score"])
        )
        model_metrics.append(
            metric_row(
                horizon,
                "mlp_hidden_oracle_probe_score",
                y_test,
                pred["mlp_hidden_oracle_probe_score"],
            )
        )
        prediction_frames.append(pred)

    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions_path = OUT / "sepsis_ml_predictions.csv"
    predictions.to_csv(predictions_path, index=False)
    pd.DataFrame(model_metrics).to_csv(OUT / "sepsis_ml_auc_by_horizon.csv", index=False)

    monitors = build_monitor_specs(early_cols, future_feature_cols)
    summary_rows = []
    for monitor in monitors:
        cfg = build_lamp_config(monitor, match_cols)
        cfg_path = OUT / "configs" / f"{monitor['id']}.yaml"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        result = run_audit(cfg_path, predictions_path, OUT / "lamp" / monitor["id"])
        summary_rows.append(summarize_lamp(monitor, result))

    pd.DataFrame(summary_rows).to_csv(OUT / "sepsis_ml_lamp_summary.csv", index=False)
    write_report(OUT / "sepsis_ml_lamp_report.md", summary_rows, model_metrics)
    print(OUT)
    return 0


def numeric_columns(
    df: pd.DataFrame,
    exclude_prefixes: tuple[str, ...],
    exclude_exact: set[str],
) -> list[str]:
    cols = []
    for col in df.columns:
        if col in exclude_exact or any(col.startswith(prefix) for prefix in exclude_prefixes):
            continue
        if col in {"patient_id", "source_file"}:
            continue
        if is_numeric(df[col]):
            cols.append(col)
    return cols


def is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def base_prediction_frame(test: pd.DataFrame, match_cols: list[str]) -> pd.DataFrame:
    cols = ["patient_id", "horizon_h", "label_future_sepsis"] + match_cols
    out = test[cols].copy()
    out["row_id"] = [
        stable_row_id(pid, horizon) for pid, horizon in zip(out["patient_id"], out["horizon_h"])
    ]
    out["future_physiology_sentinel_score"] = test["future_physiology_sentinel_score"].to_numpy()
    out["oracle_label_sentinel_score"] = test["oracle_label_sentinel_score"].to_numpy()
    out["existing_valid_early_warning_score"] = test["valid_early_warning_score"].to_numpy()
    return out


def stable_row_id(patient_id: Any, horizon: Any) -> str:
    raw = f"{patient_id}:{horizon}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def fit_with_optional_weights(model: Any, x: Any, y: np.ndarray, weights: np.ndarray) -> None:
    try:
        model.fit(x, y, **{model.steps[-1][0] + "__sample_weight": weights})
    except Exception:
        model.fit(x, y)


def mlp_hidden_layer(model: Any, x: pd.DataFrame) -> pd.DataFrame:
    imputer = model.named_steps["simpleimputer"]
    scaler = model.named_steps["standardscaler"]
    mlp = model.named_steps["mlpclassifier"]
    arr = scaler.transform(imputer.transform(x))
    hidden = np.maximum(0.0, arr @ mlp.coefs_[0] + mlp.intercepts_[0])
    return pd.DataFrame(hidden, index=x.index)


def metric_row(horizon: float, score_col: str, y_true: np.ndarray, scores: Any) -> dict[str, Any]:
    return {
        "horizon_h": horizon,
        "score": score_col,
        "auc": safe_auc(y_true, np.asarray(scores)),
        "n": int(len(y_true)),
        "n_positive": int(np.sum(y_true)),
    }


def safe_auc(y_true: np.ndarray, scores: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, scores))


def build_monitor_specs(early_cols: list[str], future_cols: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "id": "existing_valid",
            "score": "existing_valid_early_warning_score",
            "name": "Existing locked early score",
            "features": early_cols,
            "future_features": [],
            "oracle": False,
            "baseline": None,
        },
        {
            "id": "mlp_early",
            "score": "mlp_early_score",
            "name": "MLP early-window model",
            "features": early_cols,
            "future_features": [],
            "oracle": False,
            "baseline": None,
        },
        {
            "id": "gb_early",
            "score": "gb_early_score",
            "name": "Gradient-boosted early-window model",
            "features": early_cols,
            "future_features": [],
            "oracle": False,
            "baseline": None,
        },
        {
            "id": "linear_sequence",
            "score": "linear_sequence_score",
            "name": "Linear sequential-feature model",
            "features": early_cols,
            "future_features": [],
            "oracle": False,
            "baseline": None,
        },
        {
            "id": "mlp_hidden_probe",
            "score": "mlp_hidden_probe_score",
            "name": "Linear probe on MLP hidden activation",
            "features": ["mlp_hidden_activation_probe"],
            "future_features": [],
            "oracle": False,
            "baseline": None,
        },
        {
            "id": "mlp_future_leak",
            "score": "mlp_future_leak_score",
            "name": "MLP future-window contaminated model",
            "features": early_cols,
            "future_features": future_cols,
            "oracle": False,
            "baseline": "mlp_early_score",
        },
        {
            "id": "gb_future_leak",
            "score": "gb_future_leak_score",
            "name": "Gradient-boosted future-window contaminated model",
            "features": early_cols,
            "future_features": future_cols,
            "oracle": False,
            "baseline": "gb_early_score",
        },
        {
            "id": "mlp_oracle_mix",
            "score": "mlp_oracle_mix_score",
            "name": "MLP low-dose oracle mixture",
            "features": early_cols,
            "future_features": [],
            "oracle": True,
            "baseline": "mlp_early_score",
        },
        {
            "id": "mlp_hidden_oracle_probe",
            "score": "mlp_hidden_oracle_probe_score",
            "name": "Hidden-activation probe with oracle contamination",
            "features": ["mlp_hidden_activation_probe"],
            "future_features": [],
            "oracle": True,
            "baseline": "mlp_hidden_probe_score",
        },
    ]


def build_lamp_config(monitor: dict[str, Any], match_cols: list[str]) -> dict[str, Any]:
    valid_features = [
        {"name": col, "latest_offset_h": 0} for col in monitor["features"]
    ] + [{"name": col, "latest_offset_h": 1} for col in monitor["future_features"]]
    forbidden_columns = [
        "future_physiology_sentinel_score",
        "oracle_label_sentinel_score",
    ] + monitor["future_features"]
    valid_score_features = list(monitor["features"]) + monitor["future_features"]
    if monitor["oracle"]:
        valid_features.append({"name": "oracle_label_sentinel_score", "latest_offset_h": 1})
        valid_score_features.append("oracle_label_sentinel_score")

    cfg = {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": monitor["name"],
            "task": "PhysioNet/CinC 2019 sepsis ML prediction audit",
            "role": "real clinical ML LAMP benchmark",
            "source": str(SOURCE),
        },
        "columns": {
            "subject_id": "row_id",
            "label": "label_future_sepsis",
            "positive_value": 1,
            "score": monitor["score"],
            "anchor_time": "horizon_h",
        },
        "temporal_isolation": {
            "anchor": "horizon_h",
            "valid_features_must_be": "early-window summaries only",
            "frozen_before_holdout": [
                "patient-level split",
                "horizon list",
                "model family",
                "feature groups",
                "contamination definitions",
                "LAMP thresholds",
                "random seed",
            ],
            "valid_score_features": valid_features,
        },
        "forbidden_features": {
            "columns": sorted(set(forbidden_columns)),
            "allowed_metadata_columns": [
                "future_physiology_sentinel_score",
                "oracle_label_sentinel_score",
            ],
            "valid_score_features": valid_score_features,
        },
        "sentinels": {
            "future_physiology": {
                "column": "future_physiology_sentinel_score",
                "role": "future_physiology",
                "expected_signature": "post-anchor physiology comparator",
            },
            "oracle_label": {
                "column": "oracle_label_sentinel_score",
                "role": "oracle_label",
                "expected_signature": "ceiling label leakage comparator",
            },
        },
        "negative_controls": {"n_permutations": 250, "seed": SEED},
        "visible_state_matching": {"columns": match_cols, "n_bins": 3, "min_bin_size": 8},
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.01,
            "matched_collapse_max": 0.005,
            "score_thresholds": [0.2, 0.4, 0.6, 0.8],
        },
    }
    if monitor.get("baseline"):
        cfg["leakage_proximity"] = {
            "baseline_score": monitor["baseline"],
            "oracle_proximity_alert_min": 0.01,
        }
    return cfg


def summarize_lamp(monitor: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    classes = result["failure_mode_dossier"]["output_classes"]
    return {
        "monitor": monitor["name"],
        "score": monitor["score"],
        "auc": result["primary_score"]["auc"],
        "audit_pass": result["failure_mode_dossier"]["audit_pass_candidate"],
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "oracle_proximity_shift": "oracle_leakage_proximity_shift" in classes,
        "output_classes": ";".join(classes),
    }


def write_report(
    path: Path,
    summary_rows: list[dict[str, Any]],
    model_metrics: list[dict[str, Any]],
) -> None:
    lines = [
        "# Sepsis ML LAMP Benchmark",
        "",
        "This benchmark trains lightweight ML monitors on the available PhysioNet/CinC",
        "2019 v3_5k patient-level score table. Valid models use early-window summary",
        "features only. Contaminated variants deliberately use future-window features",
        "or low-dose oracle information.",
        "",
        "Raw hourly `.psv` trajectories are not present in this checkout, so this is a",
        "real clinical feature-table ML benchmark rather than a raw-sequence LSTM/TFT run.",
        "",
        "| monitor | score | auc | audit_pass | temporal | forbidden | oracle proximity | output_classes |",
        "|---|---|---:|:---:|:---:|:---:|:---:|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['monitor']} | `{row['score']}` | {fmt(row['auc'])} | "
            f"{row['audit_pass']} | {row['temporal_passed']} | {row['forbidden_passed']} | "
            f"{row['oracle_proximity_shift']} | `{row['output_classes']}` |"
        )
    lines.extend(["", "## Per-Horizon AUC", ""])
    lines.append("| horizon_h | score | auc | n | n_positive |")
    lines.append("|---:|---|---:|---:|---:|")
    for row in model_metrics:
        lines.append(
            f"| {row['horizon_h']} | `{row['score']}` | {fmt(row['auc'])} | {row['n']} | {row['n_positive']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "LAMP is applied to predictions, not just to data tables: the same audit",
            "flags future-window contamination, low-dose oracle mixtures, and",
            "representation-level oracle contamination even when AUC improves.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def fmt(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
