#!/usr/bin/env python3
"""Build the three-domain table for the metric-blind leakage preprint.

This script is intentionally narrow: it rebuilds the lambda=0.001 low-dose
oracle rows for the real PhysioNet and Anthropic benchmarks, then leaves the
NASA C-MAPSS row to `run_cmapss_lamp_bench.py`.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import LAMP_Audit  # noqa: E402


OUT_DIR = ROOT / "results" / "metric_blind_preprint"
PHYSIONET_PREDICTIONS = ROOT / "results" / "physionet_sequence_lamp" / "physionet_sequence_predictions.csv"
ANTHROPIC_PREDICTIONS = ROOT / "results" / "anthropic_sycophancy_lamp" / "anthropic_sycophancy_predictions.csv"
LAMBDA = 0.001
AUC_DELTA_ALERT = 0.01
MI_BOOTSTRAPS = 300
MI_ALPHA = 0.05
SEED = 20260531


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [physionet_row(), anthropic_row()]
    write_csv(OUT_DIR / "preprint_extra_rows.csv", rows)
    print(OUT_DIR / "preprint_extra_rows.csv")
    return 0


def physionet_row() -> dict[str, Any]:
    frame = pd.read_csv(PHYSIONET_PREDICTIONS)
    mixed_col = "rf_valid_score_oracle_mix_0p1pct"
    frame[mixed_col] = mix_scores(
        frame["rf_valid_score"].to_numpy(dtype=float),
        frame["oracle_label_sentinel_score"].to_numpy(dtype=float),
        LAMBDA,
    )
    result = LAMP_Audit(
        config=physionet_config(mixed_col),
        rows=records(frame),
        table_columns=list(frame.columns),
    ).run(OUT_DIR / "physionet_rf_oracle_mix_0p1pct")

    return summarize(
        name="PhysioNet RF",
        labels=frame["label_future_sepsis"].to_numpy(dtype=int),
        valid_scores=frame["rf_valid_score"].to_numpy(dtype=float),
        mixed_scores=frame[mixed_col].to_numpy(dtype=float),
        result=result,
        seed=SEED,
    )


def anthropic_row() -> dict[str, Any]:
    frame = pd.read_csv(ANTHROPIC_PREDICTIONS)
    mixed_col = "tfidf_prompt_valid_score_oracle_mix_0p1pct"
    frame[mixed_col] = mix_scores(
        frame["tfidf_prompt_valid_score"].to_numpy(dtype=float),
        frame["oracle_answer_key_score"].to_numpy(dtype=float),
        LAMBDA,
    )
    result = LAMP_Audit(
        config=anthropic_config(mixed_col),
        rows=records(frame),
        table_columns=list(frame.columns),
    ).run(OUT_DIR / "anthropic_tfidf_oracle_mix_0p1pct")

    return summarize(
        name="Anthropic TF-IDF",
        labels=frame["label_matching_answer_is_a"].to_numpy(dtype=int),
        valid_scores=frame["tfidf_prompt_valid_score"].to_numpy(dtype=float),
        mixed_scores=frame[mixed_col].to_numpy(dtype=float),
        result=result,
        seed=SEED + 1,
    )


def summarize(
    name: str,
    labels: np.ndarray,
    valid_scores: np.ndarray,
    mixed_scores: np.ndarray,
    result: dict[str, Any],
    seed: int,
) -> dict[str, Any]:
    valid_auc = float(roc_auc_score(labels, valid_scores))
    mixed_auc = float(roc_auc_score(labels, mixed_scores))
    mi = incremental_mi_bootstrap(valid_scores, mixed_scores, labels, seed=seed)
    dossier = result["failure_mode_dossier"]
    return {
        "name": name,
        "valid_auc": valid_auc,
        "mixed_auc": mixed_auc,
        "delta_auc": mixed_auc - valid_auc,
        "auc_alert": abs(mixed_auc - valid_auc) >= AUC_DELTA_ALERT,
        "mi_delta": mi["delta_mi"],
        "mi_ci_low": mi["ci_low"],
        "mi_ci_high": mi["ci_high"],
        "mi_p": mi["p_value"],
        "mi_sig": mi["significant"],
        "lamp_pass": dossier["audit_pass_candidate"],
        "temporal": result["temporal_isolation"]["passed"],
        "forbidden": result["forbidden_feature_screen"]["passed"],
        "classes": ";".join(dossier["output_classes"]),
    }


def physionet_config(score_col: str) -> dict[str, Any]:
    match_cols = ["Age", "HR_early_last", "O2Sat_early_last", "early_missing_rate"]
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": "PhysioNet/CinC 2019 raw PSV sequence bench",
            "task": "Random Forest valid + 0.1% oracle mixture",
            "role": "real_clinical_sequence_benchmark",
        },
        "columns": {
            "subject_id": "patient_id",
            "label": "label_future_sepsis",
            "positive_value": 1,
            "score": score_col,
            "anchor_time": "anchor_idx",
        },
        "temporal_isolation": {
            "anchor": "anchor_idx",
            "valid_features_must_be": "at_or_before_anchor",
            "frozen_before_holdout": ["patient split", "horizon definitions", "feature roles"],
            "valid_score_features": [
                {"name": "early_sequence_or_features", "latest_offset_h": 0},
                {"name": "oracle_label_sentinel_score", "latest_offset_h": 999},
            ],
        },
        "forbidden_features": {
            "columns": [
                "future_sequence_window",
                "future_engineered_features",
                "oracle_label_sentinel_score",
            ],
            "valid_score_features": [
                "early_sequence_or_features",
                "oracle_label_sentinel_score",
            ],
        },
        "sentinels": {
            "future_physiology": {
                "column": "future_physiology_sentinel_score",
                "role": "future_window_invalid_comparator",
                "expected_signature": "higher_auc_than_valid_if_future_physiology_is_informative",
            },
            "oracle_label": {
                "column": "oracle_label_sentinel_score",
                "role": "oracle_label_leakage",
                "expected_signature": "ceiling_auc_or_high_proximity",
            },
        },
        "leakage_proximity": {
            "baseline_score": "rf_valid_score",
            "oracle_proximity_alert_min": 0.01,
        },
        "negative_controls": {"n_permutations": 30, "seed": 2026},
        "visible_state_matching": {"columns": match_cols, "n_bins": 3, "min_bin_size": 4},
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.005,
            "matched_collapse_max": 0.002,
            "score_thresholds": [0.2, 0.4, 0.6, 0.8],
        },
    }


def anthropic_config(score_col: str) -> dict[str, Any]:
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": "Anthropic model-written-evals sycophancy: TF-IDF + 0.1% oracle mixture",
            "task": "public LLM sycophancy prompt audit",
            "role": "real LLM evaluation-data benchmark",
            "source": "Anthropic/model-written-evals sycophancy_on_nlp_survey",
            "monitor_id": "tfidf_prompt_valid_oracle_mix_0p1pct",
            "monitor_type": "low-dose oracle leakage",
        },
        "columns": {
            "subject_id": "example_id",
            "label": "label_matching_answer_is_a",
            "positive_value": 1,
            "score": score_col,
            "anchor_time": "anchor_step",
        },
        "temporal_isolation": {
            "anchor": "anchor_step",
            "valid_features_must_be": "prompt-only before model completion",
            "frozen_before_holdout": [
                "source file",
                "train/holdout split seed",
                "TF-IDF model specification",
                "sentinel columns",
                "visible matching variables",
                "thresholds",
            ],
            "valid_score_features": [
                {"name": "prompt_text_tfidf", "latest_offset_h": 0},
                {"name": "pre_answer_user_view_cues", "latest_offset_h": 0},
                {"name": "oracle_answer_key_score", "latest_offset_h": 999},
            ],
        },
        "forbidden_features": {
            "columns": [
                "answer_matching_behavior_is_a",
                "answer_not_matching_behavior_is_a",
                "oracle_answer_key_score",
            ],
            "allowed_metadata_columns": [
                "answer_matching_behavior_is_a",
                "answer_not_matching_behavior_is_a",
                "oracle_answer_key_score",
            ],
            "valid_score_features": [
                "prompt_text_tfidf",
                "pre_answer_user_view_cues",
                "oracle_answer_key_score",
            ],
        },
        "sentinels": {
            "oracle_answer_key": {
                "column": "oracle_answer_key_score",
                "role": "oracle_label",
                "expected_signature": "dataset answer_matching_behavior field",
            }
        },
        "leakage_proximity": {
            "baseline_score": "tfidf_prompt_valid_score",
            "oracle_proximity_alert_min": 0.01,
        },
        "negative_controls": {"n_permutations": 250, "seed": 2026},
        "visible_state_matching": {
            "columns": ["prompt_length", "persona_length"],
            "n_bins": 3,
            "min_bin_size": 8,
        },
        "early_window_sensitivity": {
            "score_columns": [
                "tfidf_prompt_valid_score",
                "cue_prompt_valid_score",
                "visible_length_shortcut_score",
                "answer_key_leakage_score",
                score_col,
            ]
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.70,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.05,
            "matched_collapse_max": 0.015,
            "score_thresholds": [0.25, 0.50, 0.75],
        },
    }


def mix_scores(valid_scores: np.ndarray, oracle_scores: np.ndarray, lam: float) -> np.ndarray:
    return (1.0 - lam) * valid_scores + lam * oracle_scores


def incremental_mi_bootstrap(
    valid_scores: np.ndarray,
    candidate_scores: np.ndarray,
    labels: np.ndarray,
    seed: int,
) -> dict[str, Any]:
    valid_mi = binned_mutual_information(valid_scores, labels)
    candidate_mi = binned_mutual_information(candidate_scores, labels)
    delta = candidate_mi - valid_mi
    if np.allclose(candidate_scores, valid_scores):
        return {
            "delta_mi": 0.0,
            "ci_low": 0.0,
            "ci_high": 0.0,
            "p_value": 1.0,
            "significant": False,
        }

    rng = np.random.default_rng(seed)
    boot = []
    n = len(labels)
    for _ in range(MI_BOOTSTRAPS):
        idx = rng.integers(0, n, n)
        boot.append(
            binned_mutual_information(candidate_scores[idx], labels[idx])
            - binned_mutual_information(valid_scores[idx], labels[idx])
        )
    boot_arr = np.array(boot)
    p_value = float((np.sum(boot_arr <= 0.0) + 1) / (len(boot_arr) + 1))
    return {
        "delta_mi": float(delta),
        "ci_low": float(np.quantile(boot_arr, 0.025)),
        "ci_high": float(np.quantile(boot_arr, 0.975)),
        "p_value": p_value,
        "significant": bool(p_value < MI_ALPHA),
    }


def binned_mutual_information(scores: np.ndarray, labels: np.ndarray, bins: int = 20) -> float:
    edges = np.unique(np.quantile(scores, np.linspace(0.0, 1.0, bins + 1)))
    if len(edges) <= 2:
        return 0.0
    score_bins = np.digitize(scores, edges[1:-1], right=True)
    mi = 0.0
    for score_bin in np.unique(score_bins):
        p_x = float(np.mean(score_bins == score_bin))
        for label in (0, 1):
            p_y = float(np.mean(labels == label))
            p_xy = float(np.mean((score_bins == score_bin) & (labels == label)))
            if p_x > 0.0 and p_y > 0.0 and p_xy > 0.0:
                mi += p_xy * np.log(p_xy / (p_x * p_y))
    return float(mi)


def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.replace({np.nan: None}).to_dict(orient="records")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
