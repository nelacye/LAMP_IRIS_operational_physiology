#!/usr/bin/env python3
"""Run a BIDSleep wearable sleep LAMP benchmark from open PhysioNet files.

The minimal benchmark uses all downloaded `hr.csv` and `labels.mat` files.
Accelerometry is optional and can be added later without changing the audit idea.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import yaml
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402
from lamp.controls import as_float  # noqa: E402

LAMBDAS = [0.0, 0.005, 0.01, 0.02, 0.05, 0.10]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="real_data/bidsleep-dataset-1.0.0")
    parser.add_argument("--out", default="results/bidsleep_lamp/hr_labels")
    parser.add_argument("--early-minutes", type=int, default=90)
    parser.add_argument("--n-null", type=int, default=500)
    args = parser.parse_args(argv)

    data_root = Path(args.data_root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = build_rows(data_root, args.early_minutes)
    if len(rows) < 20:
        raise RuntimeError(f"Too few BIDSleep nights available: {len(rows)}")
    label_rows(rows)

    table_dir = out_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    score_table = table_dir / "bidsleep_hr_labels_score_table.csv"
    write_csv(score_table, rows)

    config = build_config(args.n_null)
    config_path = out_dir / "bidsleep_config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    main_result = run_audit(config_path, score_table, out_dir / "main")
    write_main_summary(out_dir / "bidsleep_main_summary.csv", main_result)

    oracle_rows = run_oracle_mixture(rows, config, out_dir)
    visible_rows = run_visible_confounding(rows, config, out_dir)
    write_csv(out_dir / "oracle_mixture_summary.csv", oracle_rows)
    write_csv(out_dir / "visible_confounding_summary.csv", visible_rows)
    write_report(out_dir / "bidsleep_lamp_report.md", main_result, oracle_rows, visible_rows)
    print(out_dir)
    return 0


def build_rows(data_root: Path, early_minutes: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for labels_path in sorted(data_root.glob("Bidslab*/[0-9]*/labels.mat")):
        night_dir = labels_path.parent
        hr_path = night_dir / "hr.csv"
        if not hr_path.exists():
            continue
        subject_id = night_dir.parent.name
        night_id = night_dir.name
        mat = loadmat(labels_path)
        labels = np.asarray(mat["expert_label"]).ravel().astype(int)
        rec_start = parse_rec_start(str(np.asarray(mat["recStart"]).ravel()[0]))
        rec_start_ts = rec_start.timestamp()
        hr = read_hr(hr_path, rec_start_ts)
        duration_min = len(labels) * 0.5
        if duration_min <= early_minutes + 60:
            continue

        early_label = labels[: int(early_minutes * 2)]
        later_label = labels[int(early_minutes * 2) :]
        early_hr = [value for minute, value in hr if 0 <= minute < early_minutes]
        later_hr = [value for minute, value in hr if early_minutes <= minute <= duration_min]
        if len(early_hr) < 20 or len(later_hr) < 20:
            continue

        row = {
            "subject_id": subject_id,
            "night_id": night_id,
            "subject_night": f"{subject_id}_{night_id}",
            "early_minutes": early_minutes,
            "duration_minutes": duration_min,
            "rec_start": rec_start.isoformat(),
        }
        row.update(stage_features(early_label, "early_"))
        row.update(stage_features(later_label, "later_"))
        row.update(hr_features(early_hr, "early_"))
        row.update(hr_features(later_hr, "future_"))
        row["valid_early_hr_score"] = early_hr_score(row)
        row["future_hr_sentinel_score"] = future_hr_score(row)
        row["oracle_sleep_stage_sentinel_score"] = 10.0 * later_instability(row)
        row["visible_stage_shortcut_score"] = row["early_wake_fraction"]
        rows.append(row)
    return rows


def label_rows(rows: list[dict[str, Any]]) -> None:
    scores = sorted(float(row["oracle_sleep_stage_sentinel_score"]) for row in rows)
    threshold = scores[int(0.70 * (len(scores) - 1))]
    for row in rows:
        row["later_instability_threshold"] = threshold
        row["label_later_sleep_instability"] = (
            1 if float(row["oracle_sleep_stage_sentinel_score"]) >= threshold else 0
        )


def parse_rec_start(value: str) -> datetime:
    text = value.strip().strip("[]'\"")
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=ZoneInfo("America/New_York")
    )


def read_hr(path: Path, rec_start_ts: float) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for raw in reader:
            if len(raw) < 2:
                continue
            try:
                ts = float(raw[0])
                value = float(raw[1])
            except ValueError:
                continue
            if 25 <= value <= 220:
                rows.append(((ts - rec_start_ts) / 60.0, value))
    return rows


def stage_features(labels: np.ndarray, prefix: str) -> dict[str, float]:
    clean = labels[labels != 5]
    if clean.size == 0:
        return {
            f"{prefix}wake_fraction": 0.0,
            f"{prefix}rem_fraction": 0.0,
            f"{prefix}deep_fraction": 0.0,
            f"{prefix}transition_rate": 0.0,
            f"{prefix}unknown_fraction": 1.0,
        }
    transitions = np.diff(clean) != 0
    return {
        f"{prefix}wake_fraction": float(np.mean(clean == 0)),
        f"{prefix}rem_fraction": float(np.mean(clean == 4)),
        f"{prefix}deep_fraction": float(np.mean(clean == 3)),
        f"{prefix}transition_rate": float(np.mean(transitions)) if transitions.size else 0.0,
        f"{prefix}unknown_fraction": float(np.mean(labels == 5)),
    }


def hr_features(values: list[float], prefix: str) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    diffs = np.abs(np.diff(arr))
    return {
        f"{prefix}hr_mean": float(np.mean(arr)),
        f"{prefix}hr_sd": float(np.std(arr)),
        f"{prefix}hr_range": float(np.max(arr) - np.min(arr)),
        f"{prefix}hr_rmssd_proxy": float(np.sqrt(np.mean(diffs * diffs))) if diffs.size else 0.0,
        f"{prefix}hr_fragmentation": float(np.mean(diffs > 5.0)) if diffs.size else 0.0,
        f"{prefix}hr_n": int(arr.size),
    }


def later_instability(row: dict[str, Any]) -> float:
    return float(row["later_wake_fraction"]) + 0.75 * float(row["later_transition_rate"])


def early_hr_score(row: dict[str, Any]) -> float:
    return (
        0.020 * float(row["early_hr_mean"])
        + 0.080 * float(row["early_hr_sd"])
        + 0.080 * float(row["early_hr_rmssd_proxy"])
        + 1.500 * float(row["early_hr_fragmentation"])
    )


def future_hr_score(row: dict[str, Any]) -> float:
    return (
        0.020 * float(row["future_hr_mean"])
        + 0.080 * float(row["future_hr_sd"])
        + 0.080 * float(row["future_hr_rmssd_proxy"])
        + 1.500 * float(row["future_hr_fragmentation"])
    )


def build_config(n_null: int) -> dict[str, Any]:
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": "BIDSleep HR plus EEG-label wearable sleep benchmark",
            "task": "early-night wearable prediction of later-night sleep instability",
            "role": "open wearable external benchmark",
        },
        "columns": {
            "subject_id": "subject_night",
            "label": "label_later_sleep_instability",
            "positive_value": 1,
            "score": "valid_early_hr_score",
            "anchor_time": "early_minutes",
        },
        "temporal_isolation": {
            "anchor": "early_minutes",
            "valid_features_must_be": "first 90 minutes only",
            "frozen_before_holdout": [
                "early window",
                "later-instability endpoint threshold",
                "valid HR-only score",
                "future HR sentinel",
                "oracle EEG-label sentinel",
                "visible-state matching variables",
                "LAMP thresholds",
            ],
            "valid_score_features": [
                {"name": "early_hr_mean", "latest_offset_h": 0},
                {"name": "early_hr_sd", "latest_offset_h": 0},
                {"name": "early_hr_rmssd_proxy", "latest_offset_h": 0},
                {"name": "early_hr_fragmentation", "latest_offset_h": 0},
            ],
        },
        "forbidden_features": {
            "columns": [
                "future_hr_sentinel_score",
                "oracle_sleep_stage_sentinel_score",
                "later_wake_fraction",
                "later_rem_fraction",
                "later_deep_fraction",
                "later_transition_rate",
                "later_unknown_fraction",
            ],
            "allowed_metadata_columns": [
                "later_wake_fraction",
                "later_rem_fraction",
                "later_deep_fraction",
                "later_transition_rate",
                "later_unknown_fraction",
            ],
            "valid_score_features": [
                "early_hr_mean",
                "early_hr_sd",
                "early_hr_rmssd_proxy",
                "early_hr_fragmentation",
            ],
        },
        "sentinels": {
            "future_physiology": {
                "column": "future_hr_sentinel_score",
                "role": "future_physiology",
                "expected_signature": "invalid later-night wearable HR comparator",
            },
            "oracle_label": {
                "column": "oracle_sleep_stage_sentinel_score",
                "role": "oracle_label",
                "expected_signature": "ceiling future EEG-label comparator",
            },
        },
        "negative_controls": {"n_permutations": n_null, "seed": 2026},
        "visible_state_matching": {
            "columns": ["early_hr_mean", "early_hr_sd", "early_wake_fraction"],
            "n_bins": 3,
            "min_bin_size": 5,
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.90,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.01,
            "matched_collapse_max": 0.005,
            "score_thresholds": [1.5, 2.0, 2.5],
        },
    }


def run_oracle_mixture(
    rows: list[dict[str, Any]],
    base_config: dict[str, Any],
    out_dir: Path,
) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for lam in LAMBDAS:
        mixed_rows = []
        for row in rows:
            new = dict(row)
            valid = as_float(row["valid_early_hr_score"]) or 0.0
            oracle = as_float(row["oracle_sleep_stage_sentinel_score"]) or 0.0
            new["mixed_score"] = (1.0 - lam) * valid + lam * oracle
            mixed_rows.append(new)
        table_path = out_dir / "perturbations" / "tables" / f"oracle_l{lambda_tag(lam)}.csv"
        write_csv(table_path, mixed_rows)
        for provenance in ["undeclared", "declared"]:
            run_dir = out_dir / "perturbations" / "oracle_mixture" / f"{provenance}_l{lambda_tag(lam)}"
            run_dir.mkdir(parents=True, exist_ok=True)
            config = yaml.safe_load(yaml.safe_dump(base_config))
            config["columns"]["score"] = "mixed_score"
            config["negative_controls"]["n_permutations"] = 200
            config["leakage_proximity"] = {
                "baseline_score": "valid_early_hr_score",
                "oracle_proximity_alert_min": 0.01,
            }
            if provenance == "declared" and lam > 0:
                config["temporal_isolation"]["valid_score_features"].append(
                    {"name": "oracle_sleep_stage_sentinel_score", "latest_offset_h": 1}
                )
                config["forbidden_features"]["valid_score_features"].append(
                    "oracle_sleep_stage_sentinel_score"
                )
            config_path = run_dir / "config.yaml"
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
            result = run_audit(config_path, table_path, run_dir)
            summary.append(flatten_oracle_result(lam, provenance, result))
    return summary


def run_visible_confounding(
    rows: list[dict[str, Any]],
    base_config: dict[str, Any],
    out_dir: Path,
) -> list[dict[str, Any]]:
    visible_rows = [dict(row) for row in rows]
    bins = rank_bins(visible_rows, "early_wake_fraction", 3)
    for idx, row in enumerate(visible_rows):
        row["visible_stage_shortcut_score"] = bins.get(idx, 1)
    table_path = out_dir / "perturbations" / "tables" / "visible_stage_shortcut.csv"
    write_csv(table_path, visible_rows)
    run_dir = out_dir / "perturbations" / "visible_confounding"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(yaml.safe_dump(base_config))
    config["columns"]["score"] = "visible_stage_shortcut_score"
    config["temporal_isolation"]["valid_score_features"] = [
        {"name": "early_wake_fraction", "latest_offset_h": 0}
    ]
    config["forbidden_features"]["valid_score_features"] = ["early_wake_fraction"]
    config["visible_state_matching"] = {
        "columns": ["early_wake_fraction"],
        "n_bins": 3,
        "min_bin_size": 5,
    }
    config["negative_controls"]["n_permutations"] = 200
    config["leakage_proximity"] = {
        "baseline_score": "valid_early_hr_score",
        "oracle_proximity_alert_min": 1.1,
    }
    config_path = run_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    result = run_audit(config_path, table_path, run_dir)
    return [flatten_visible_result(result)]


def flatten_oracle_result(lam: float, provenance: str, result: dict[str, Any]) -> dict[str, Any]:
    primary = result["primary_score"]
    oracle = result["sentinel_relations"]["oracle_label"]
    return {
        "lambda": lam,
        "provenance": provenance,
        "n": primary["n"],
        "n_positive": primary["n_positive"],
        "auc": primary["auc"],
        "baseline_valid_auc": oracle.get("baseline_auc"),
        "oracle_auc": oracle.get("sentinel_auc"),
        "distance_to_oracle_auc": oracle.get("sentinel_minus_primary_auc"),
        "oracle_auc_leakage_proximity": oracle.get("auc_leakage_proximity"),
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "audit_pass_candidate": result["failure_mode_dossier"]["audit_pass_candidate"],
        "output_classes": ";".join(result["failure_mode_dossier"]["output_classes"]),
    }


def flatten_visible_result(result: dict[str, Any]) -> dict[str, Any]:
    primary = result["primary_score"]
    oracle = result["sentinel_relations"]["oracle_label"]
    return {
        "n": primary["n"],
        "n_positive": primary["n_positive"],
        "visible_only_auc": primary["auc"],
        "baseline_valid_auc": oracle.get("baseline_auc"),
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "audit_pass_candidate": result["failure_mode_dossier"]["audit_pass_candidate"],
        "output_classes": ";".join(result["failure_mode_dossier"]["output_classes"]),
    }


def write_main_summary(path: Path, result: dict[str, Any]) -> None:
    primary = result["primary_score"]
    relations = result["sentinel_relations"]
    write_csv(
        path,
        [
            {
                "n": primary["n"],
                "n_positive": primary["n_positive"],
                "valid_auc": primary["auc"],
                "future_hr_auc": relations["future_physiology"]["sentinel_auc"],
                "oracle_auc": relations["oracle_label"]["sentinel_auc"],
                "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
                "temporal_passed": result["temporal_isolation"]["passed"],
                "forbidden_passed": result["forbidden_feature_screen"]["passed"],
                "audit_pass_candidate": result["failure_mode_dossier"]["audit_pass_candidate"],
                "output_classes": ";".join(result["failure_mode_dossier"]["output_classes"]),
            }
        ],
    )


def write_report(
    path: Path,
    main_result: dict[str, Any],
    oracle_rows: list[dict[str, Any]],
    visible_rows: list[dict[str, Any]],
) -> None:
    primary = main_result["primary_score"]
    relations = main_result["sentinel_relations"]
    lines = [
        "# BIDSleep LAMP benchmark: HR plus EEG labels",
        "",
        "Open wearable sleep benchmark using Apple Watch instantaneous HR and Dreem 2 expert EEG labels.",
        "",
        "## Main Audit",
        "",
        "| n | n_positive | valid_auc | future_hr_auc | oracle_auc | matched_delta | audit_pass | output_classes |",
        "|---:|---:|---:|---:|---:|---:|:---:|---|",
        f"| {primary['n']} | {primary['n_positive']} | {fmt(primary['auc'])} | {fmt(relations['future_physiology']['sentinel_auc'])} | {fmt(relations['oracle_label']['sentinel_auc'])} | {fmt(main_result['visible_state_matching'].get('matched_observed_state_delta'))} | {main_result['failure_mode_dossier']['audit_pass_candidate']} | `{';'.join(main_result['failure_mode_dossier']['output_classes'])}` |",
        "",
        "## Low-Dose Oracle Mixture",
        "",
        "| lambda | provenance | auc | oracle_proximity | temporal | forbidden | audit_pass | output_classes |",
        "|---:|---|---:|---:|:---:|:---:|:---:|---|",
    ]
    for row in oracle_rows:
        lines.append(
            f"| {row['lambda']:.3g} | {row['provenance']} | {fmt(row['auc'])} | {fmt(row['oracle_auc_leakage_proximity'])} | {row['temporal_passed']} | {row['forbidden_passed']} | {row['audit_pass_candidate']} | `{row['output_classes']}` |"
        )
    lines.extend(
        [
            "",
            "## Visible-State Shortcut",
            "",
            "| visible_auc | baseline_valid_auc | matched_delta | audit_pass | output_classes |",
            "|---:|---:|---:|:---:|---|",
        ]
    )
    for row in visible_rows:
        lines.append(
            f"| {fmt(row['visible_only_auc'])} | {fmt(row['baseline_valid_auc'])} | {fmt(row['matched_delta'])} | {row['audit_pass_candidate']} | `{row['output_classes']}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This is an open wearable-domain LAMP transfer benchmark. It is not a clinical sleep-device validation study.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    return f"{float(value):.6f}"


def lambda_tag(value: float) -> str:
    return str(value).replace(".", "p")


def rank_bins(rows: list[dict[str, Any]], column: str, n_bins: int) -> dict[int, int]:
    values = [
        (as_float(row.get(column)), idx)
        for idx, row in enumerate(rows)
        if as_float(row.get(column)) is not None
    ]
    ordered = sorted(values, key=lambda item: item[0])
    result: dict[int, int] = {}
    if not ordered:
        return result
    for pos, (_, idx) in enumerate(ordered):
        result[idx] = min(int(pos * n_bins / len(ordered)), n_bins - 1)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
