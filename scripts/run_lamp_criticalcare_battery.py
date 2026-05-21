#!/usr/bin/env python3
"""Run the LAMP-CriticalCare Battery.

Benchmark A is the existing PhysioNet/CinC 2019 sepsis result.
Benchmark B/C are Clinical Trajectory Flow ICU cardiac-arrest-risk and GIB
cohorts when the credentialed CSV files are present locally.

The Clinical Trajectory Flow ICU files provide first-24h trajectories and outcome
labels, not onset timestamps. In this battery, horizons are implemented as
early-window lengths and future sentinels use the later part of the first 24h.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402
from lamp.controls import as_float  # noqa: E402

LAMBDAS = [0.0, 0.005, 0.01, 0.05, 0.10]

COHORTS = {
    "cardiac_arrest": {
        "file": "eICU_cardiacArrest_physionet.csv",
        "display": "Clinical Trajectory Flow ICU cardiac-arrest-risk cohort",
        "id_cols": ["patientunitstayid", "HADM_ID", "hadm_id", "stay_id", "subject_id", "patient_id"],
        "time_cols": ["TIME_FROM_ADM", "time_from_adm"],
        "time_unit": "minutes",
        "windows_h": [1, 2, 4, 6],
        "outcome_cols": ["HOSP_MORT", "hosp_mort", "ICU_MORT", "icu_mort"],
        "split_cols": ["label", "split", "partition"],
        "early_features": ["hr_normalized", "dbp_normalized", "rr_normalized", "age_normalized"],
        "vitals": ["hr_normalized", "dbp_normalized", "rr_normalized"],
        "visible_shortcut": "age_normalized",
    },
    "gib": {
        "file": "MIMIC_gib_physionet.csv",
        "display": "Clinical Trajectory Flow ICU gastrointestinal bleeding cohort",
        "id_cols": ["HADM_ID", "hadm_id", "stay_id", "subject_id", "patient_id"],
        "time_cols": ["TIME_FROM_ADM", "time_from_adm"],
        "time_unit": "hours",
        "windows_h": [6, 12, 24],
        "outcome_cols": ["HOSP_MORT", "hosp_mort", "ICU_MORT", "icu_mort"],
        "split_cols": ["label", "split", "partition"],
        "early_features": [
            "hr_normalized",
            "map_normalized",
            "pressor",
            "bloodprod",
            "prbc",
            "severe_liver",
        ],
        "vitals": ["hr_normalized", "map_normalized"],
        "visible_shortcut": "severe_liver",
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ctf-root", default="real_data/clinical-trajectory-flow-icu-1.0.0")
    parser.add_argument("--out", default="results/lamp_criticalcare_battery")
    parser.add_argument("--n-null", type=int, default=500)
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    sepsis_summary = ROOT / "results/lamp_cli_scientific/sepsis_v3_5k/lamp_cli_scientific_summary.csv"
    if sepsis_summary.exists():
        rows.extend(read_existing_sepsis_summary(sepsis_summary))

    ctf_root = Path(args.ctf_root)
    for cohort_name, spec in COHORTS.items():
        csv_path = ctf_root / spec["file"]
        if not csv_path.exists():
            write_missing_note(out_dir / f"{cohort_name}_missing.md", csv_path, spec)
            continue
        cohort_rows = read_csv(csv_path)
        cohort_out = out_dir / cohort_name
        cohort_out.mkdir(parents=True, exist_ok=True)
        main_rows = run_cohort(cohort_name, spec, cohort_rows, cohort_out, args.n_null)
        rows.extend(main_rows)

    write_csv(out_dir / "criticalcare_battery_summary.csv", rows)
    write_report(out_dir / "criticalcare_battery_report.md", rows)
    print(out_dir)
    return 0


def run_cohort(
    cohort_name: str,
    spec: dict[str, Any],
    source_rows: list[dict[str, str]],
    out_dir: Path,
    n_null: int,
) -> list[dict[str, Any]]:
    grouped = group_by_patient(source_rows, spec["id_cols"])
    if not grouped:
        available = ", ".join(source_rows[0].keys()) if source_rows else "<empty file>"
        raise ValueError(
            f"No patient id column found for {cohort_name}. "
            f"Tried {spec['id_cols']}; available columns: {available}"
        )
    summary_rows = []
    for window_h in spec["windows_h"]:
        score_rows = build_score_table(grouped, spec, window_h)
        if not score_rows:
            continue
        table_path = out_dir / "tables" / f"{cohort_name}_window_{window_h}h_score_table.csv"
        write_csv(table_path, score_rows)
        config = build_config(cohort_name, spec, window_h, n_null)
        config_path = out_dir / "configs" / f"{cohort_name}_window_{window_h}h.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        run_dir = out_dir / "lamp" / f"window_{window_h}h"
        result = run_audit(config_path, table_path, run_dir)
        summary_rows.append(flatten_main_result(cohort_name, window_h, result))
        run_oracle_mixture(cohort_name, spec, window_h, score_rows, config, out_dir)
        run_visible_shortcut(cohort_name, spec, window_h, score_rows, config, out_dir)
    write_csv(out_dir / f"{cohort_name}_summary.csv", summary_rows)
    return summary_rows


def build_score_table(
    grouped: dict[str, list[dict[str, str]]],
    spec: dict[str, Any],
    window_h: float,
) -> list[dict[str, Any]]:
    rows = []
    for patient_id, patient_rows in grouped.items():
        ordered = sorted(patient_rows, key=lambda row: time_hours(row, spec))
        early = [row for row in ordered if time_hours(row, spec) <= window_h]
        future = [row for row in ordered if window_h < time_hours(row, spec) <= 24]
        if len(early) < 1 or len(future) < 1:
            continue
        label = int(float(first_nonempty(ordered, spec["outcome_cols"], default="0") or 0))
        score_row = {
            "patient_id": patient_id,
            "window_h": window_h,
            "label_outcome": label,
            "n_early_points": len(early),
            "n_future_points": len(future),
            "split_label": first_nonempty(ordered, spec.get("split_cols", []), default=""),
        }
        for feature in set(spec["early_features"] + spec["vitals"] + [spec["visible_shortcut"]]):
            add_feature_summary(score_row, early, feature, f"early_{feature}")
            add_feature_summary(score_row, future, feature, f"future_{feature}")
        score_row["valid_early_score"] = valid_score(score_row, spec)
        score_row["future_physiology_sentinel_score"] = future_score(score_row, spec)
        score_row["oracle_label_sentinel_score"] = float(label)
        score_row["visible_shortcut_score"] = visible_shortcut_score(score_row, spec)
        rows.append(score_row)
    return rows


def add_feature_summary(
    out: dict[str, Any],
    rows: list[dict[str, str]],
    feature: str,
    prefix: str,
) -> None:
    values = [as_float(row.get(feature)) for row in rows]
    values = [value for value in values if value is not None and math.isfinite(value)]
    out[f"{prefix}_mean"] = mean(values)
    out[f"{prefix}_last"] = values[-1] if values else ""
    out[f"{prefix}_sd"] = sd(values)
    out[f"{prefix}_slope"] = slope(values)


def valid_score(row: dict[str, Any], spec: dict[str, Any]) -> float:
    score = 0.0
    for feature in spec["vitals"]:
        mean_value = as_float(row.get(f"early_{feature}_mean")) or 0.0
        last_value = as_float(row.get(f"early_{feature}_last")) or 0.0
        slope_value = as_float(row.get(f"early_{feature}_slope")) or 0.0
        score += abs(mean_value) + 0.5 * abs(last_value) + 0.25 * abs(slope_value)
    for feature in spec["early_features"]:
        if feature not in spec["vitals"]:
            value = as_float(row.get(f"early_{feature}_mean"))
            if value is not None:
                score += 0.25 * abs(value)
    score += 0.05 * (as_float(row.get("n_early_points")) or 0.0)
    return float(score)


def future_score(row: dict[str, Any], spec: dict[str, Any]) -> float:
    score = 0.0
    for feature in spec["vitals"]:
        mean_value = as_float(row.get(f"future_{feature}_mean")) or 0.0
        last_value = as_float(row.get(f"future_{feature}_last")) or 0.0
        slope_value = as_float(row.get(f"future_{feature}_slope")) or 0.0
        score += abs(mean_value) + 0.5 * abs(last_value) + 0.25 * abs(slope_value)
    score += 0.05 * (as_float(row.get("n_future_points")) or 0.0)
    return float(score)


def visible_shortcut_score(row: dict[str, Any], spec: dict[str, Any]) -> float:
    feature = spec["visible_shortcut"]
    return float(as_float(row.get(f"early_{feature}_mean")) or 0.0)


def build_config(
    cohort_name: str,
    spec: dict[str, Any],
    window_h: float,
    n_null: int,
) -> dict[str, Any]:
    forbidden_columns = ["future_physiology_sentinel_score", "oracle_label_sentinel_score"]
    for feature in spec["early_features"] + spec["vitals"]:
        for suffix in ["mean", "last", "sd", "slope"]:
            forbidden_columns.append(f"future_{feature}_{suffix}")
    valid_features = []
    for feature in spec["early_features"] + spec["vitals"]:
        for suffix in ["mean", "last", "sd", "slope"]:
            valid_features.append(f"early_{feature}_{suffix}")
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"{spec['display']} window {window_h}h",
            "task": "first-24h critical-care outcome audit",
            "role": "LAMP-CriticalCare Battery",
            "cohort": cohort_name,
            "window_h": window_h,
        },
        "columns": {
            "subject_id": "patient_id",
            "label": "label_outcome",
            "positive_value": 1,
            "score": "valid_early_score",
            "anchor_time": "window_h",
        },
        "temporal_isolation": {
            "anchor": "window_h",
            "valid_features_must_be": "inside early window only",
            "frozen_before_holdout": [
                "source train/val/test split",
                "early window",
                "valid score formula",
                "future physiology sentinel",
                "oracle outcome sentinel",
                "visible shortcut",
                "LAMP thresholds",
            ],
            "valid_score_features": [
                {"name": feature, "latest_offset_h": 0} for feature in valid_features
            ],
        },
        "forbidden_features": {
            "columns": sorted(set(forbidden_columns)),
            "allowed_metadata_columns": [
                col for col in sorted(set(forbidden_columns)) if col.startswith("future_")
            ],
            "valid_score_features": valid_features,
        },
        "sentinels": {
            "future_physiology": {
                "column": "future_physiology_sentinel_score",
                "role": "future_physiology",
                "expected_signature": "later first-24h physiology comparator",
            },
            "oracle_label": {
                "column": "oracle_label_sentinel_score",
                "role": "oracle_label",
                "expected_signature": "outcome-label comparator",
            },
        },
        "negative_controls": {"n_permutations": n_null, "seed": 2026},
        "visible_state_matching": {
            "columns": [
                f"early_{spec['visible_shortcut']}_mean",
                "n_early_points",
            ],
            "n_bins": 3,
            "min_bin_size": 8,
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.01,
            "matched_collapse_max": 0.005,
            "score_thresholds": [1.0, 2.0, 3.0],
        },
    }


def run_oracle_mixture(
    cohort_name: str,
    spec: dict[str, Any],
    window_h: float,
    rows: list[dict[str, Any]],
    base_config: dict[str, Any],
    out_dir: Path,
) -> None:
    summary = []
    for lam in LAMBDAS:
        mixed_rows = []
        for row in rows:
            new = dict(row)
            valid = as_float(row.get("valid_early_score")) or 0.0
            oracle = as_float(row.get("oracle_label_sentinel_score")) or 0.0
            new["mixed_score"] = (1.0 - lam) * valid + lam * oracle
            mixed_rows.append(new)
        table_path = out_dir / "perturbations" / cohort_name / "tables" / f"oracle_w{window_h}_l{lambda_tag(lam)}.csv"
        write_csv(table_path, mixed_rows)
        for provenance in ["undeclared", "declared"]:
            config = yaml.safe_load(yaml.safe_dump(base_config))
            config["columns"]["score"] = "mixed_score"
            config["negative_controls"]["n_permutations"] = 200
            config["leakage_proximity"] = {
                "baseline_score": "valid_early_score",
                "oracle_proximity_alert_min": 0.01,
            }
            if provenance == "declared" and lam > 0:
                config["temporal_isolation"]["valid_score_features"].append(
                    {"name": "oracle_label_sentinel_score", "latest_offset_h": 1}
                )
                config["forbidden_features"]["valid_score_features"].append(
                    "oracle_label_sentinel_score"
                )
            run_dir = out_dir / "perturbations" / cohort_name / "oracle_mixture" / f"{provenance}_w{window_h}_l{lambda_tag(lam)}"
            config_path = run_dir / "config.yaml"
            run_dir.mkdir(parents=True, exist_ok=True)
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
            result = run_audit(config_path, table_path, run_dir)
            summary.append(flatten_oracle_result(cohort_name, window_h, lam, provenance, result))
    write_csv(
        out_dir / "perturbations" / cohort_name / f"oracle_mixture_window_{window_h}h_summary.csv",
        summary,
    )


def run_visible_shortcut(
    cohort_name: str,
    spec: dict[str, Any],
    window_h: float,
    rows: list[dict[str, Any]],
    base_config: dict[str, Any],
    out_dir: Path,
) -> None:
    visible_rows = [dict(row) for row in rows]
    bins = rank_bins(visible_rows, "visible_shortcut_score", 3)
    for idx, row in enumerate(visible_rows):
        row["visible_shortcut_binned_score"] = bins.get(idx, 1)
    table_path = out_dir / "perturbations" / cohort_name / "tables" / f"visible_w{window_h}.csv"
    write_csv(table_path, visible_rows)
    config = yaml.safe_load(yaml.safe_dump(base_config))
    config["columns"]["score"] = "visible_shortcut_binned_score"
    config["temporal_isolation"]["valid_score_features"] = [
        {"name": "visible_shortcut_score", "latest_offset_h": 0}
    ]
    config["forbidden_features"]["valid_score_features"] = ["visible_shortcut_score"]
    config["visible_state_matching"] = {
        "columns": ["visible_shortcut_binned_score"],
        "n_bins": 3,
        "min_bin_size": 8,
    }
    config["negative_controls"]["n_permutations"] = 200
    config["leakage_proximity"] = {
        "baseline_score": "valid_early_score",
        "oracle_proximity_alert_min": 1.1,
    }
    run_dir = out_dir / "perturbations" / cohort_name / "visible_confounding" / f"window_{window_h}h"
    run_dir.mkdir(parents=True, exist_ok=True)
    config_path = run_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    result = run_audit(config_path, table_path, run_dir)
    write_csv(
        out_dir / "perturbations" / cohort_name / f"visible_confounding_window_{window_h}h_summary.csv",
        [flatten_visible_result(cohort_name, window_h, result)],
    )


def flatten_main_result(cohort_name: str, window_h: float, result: dict[str, Any]) -> dict[str, Any]:
    primary = result["primary_score"]
    rel = result["sentinel_relations"]
    return {
        "benchmark": cohort_name,
        "window_h": window_h,
        "n": primary["n"],
        "n_positive": primary["n_positive"],
        "valid_auc": primary["auc"],
        "future_sentinel_auc": rel["future_physiology"]["sentinel_auc"],
        "oracle_auc": rel["oracle_label"]["sentinel_auc"],
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "audit_pass_candidate": result["failure_mode_dossier"]["audit_pass_candidate"],
        "output_classes": ";".join(result["failure_mode_dossier"]["output_classes"]),
    }


def flatten_oracle_result(
    cohort_name: str,
    window_h: float,
    lam: float,
    provenance: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    primary = result["primary_score"]
    oracle = result["sentinel_relations"]["oracle_label"]
    return {
        "benchmark": cohort_name,
        "window_h": window_h,
        "lambda": lam,
        "provenance": provenance,
        "auc": primary["auc"],
        "baseline_valid_auc": oracle.get("baseline_auc"),
        "oracle_auc_leakage_proximity": oracle.get("auc_leakage_proximity"),
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "audit_pass_candidate": result["failure_mode_dossier"]["audit_pass_candidate"],
        "output_classes": ";".join(result["failure_mode_dossier"]["output_classes"]),
    }


def flatten_visible_result(cohort_name: str, window_h: float, result: dict[str, Any]) -> dict[str, Any]:
    primary = result["primary_score"]
    oracle = result["sentinel_relations"]["oracle_label"]
    return {
        "benchmark": cohort_name,
        "window_h": window_h,
        "visible_auc": primary["auc"],
        "baseline_valid_auc": oracle.get("baseline_auc"),
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "audit_pass_candidate": result["failure_mode_dossier"]["audit_pass_candidate"],
        "output_classes": ";".join(result["failure_mode_dossier"]["output_classes"]),
    }


def read_existing_sepsis_summary(path: Path) -> list[dict[str, Any]]:
    rows = []
    for row in read_csv(path):
        rows.append(
            {
                "benchmark": "physionet_cinc_2019_sepsis",
                "window_h": row.get("horizon_h"),
                "n": row.get("n"),
                "n_positive": row.get("n_positive"),
                "valid_auc": row.get("valid_auc"),
                "future_sentinel_auc": row.get("future_physiology_auc"),
                "oracle_auc": row.get("oracle_auc"),
                "matched_delta": row.get("matched_observed_state_delta"),
                "temporal_passed": row.get("temporal_passed"),
                "forbidden_passed": row.get("forbidden_passed"),
                "audit_pass_candidate": row.get("audit_pass_candidate"),
                "output_classes": row.get("output_classes"),
            }
        )
    return rows


def write_missing_note(path: Path, csv_path: Path, spec: dict[str, Any]) -> None:
    path.write_text(
        "\n".join(
            [
                f"# Missing Clinical Trajectory Flow ICU file: {spec['display']}",
                "",
                f"Expected file: `{csv_path}`",
                "",
                "This PhysioNet resource is credentialed access, requires CITI training,",
                "and requires signing the project DUA. Run:",
                "",
                "```powershell",
                "powershell -ExecutionPolicy Bypass -File scripts\\download_clinical_trajectory_flow_icu.ps1",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# LAMP-CriticalCare Battery",
        "",
        "Benchmark A is the existing PhysioNet/CinC 2019 sepsis v3_5k audit.",
        "Cardiac-arrest-risk and GIB cohorts are included when the credentialed Clinical Trajectory Flow ICU CSV files are present locally.",
        "",
        "| benchmark | window_h | n | n_positive | valid_auc | future_sentinel_auc | oracle_auc | matched_delta | audit_pass | output_classes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('benchmark')} | {row.get('window_h')} | {row.get('n')} | {row.get('n_positive')} | {fmt(row.get('valid_auc'))} | {fmt(row.get('future_sentinel_auc'))} | {fmt(row.get('oracle_auc'))} | {fmt(row.get('matched_delta'))} | {row.get('audit_pass_candidate')} | `{row.get('output_classes')}` |"
        )
    lines.extend(
        [
            "",
            "## Access Note",
            "",
            "Clinical Trajectory Flow ICU is PhysioNet credentialed access, not open access. It requires CITI Data or Specimens Only Research training and a signed DUA.",
            "",
            "## Interpretation Boundary",
            "",
            "These audits test failure-mode separation, not clinical deployment readiness.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def group_by_patient(rows: list[dict[str, str]], id_cols: list[str]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        patient_id = first_value(row, id_cols)
        if patient_id:
            grouped.setdefault(patient_id, []).append(row)
    return grouped


def time_hours(row: dict[str, str], spec: dict[str, Any]) -> float:
    raw = as_float(first_value(row, spec["time_cols"])) or 0.0
    return raw / 60.0 if spec["time_unit"] == "minutes" else raw


def first_value(row: dict[str, str], columns: list[str]) -> str:
    for column in columns:
        value = row.get(column)
        if value not in {None, ""}:
            return str(value)
    return ""


def first_nonempty(rows: list[dict[str, str]], columns: str | list[str], default: str = "") -> str:
    candidates = [columns] if isinstance(columns, str) else columns
    for row in rows:
        value = first_value(row, candidates)
        if value:
            return value
    return default


def mean(values: list[float]) -> float | str:
    return sum(values) / len(values) if values else ""


def sd(values: list[float]) -> float | str:
    if len(values) < 2:
        return ""
    m = sum(values) / len(values)
    return math.sqrt(sum((value - m) ** 2 for value in values) / (len(values) - 1))


def slope(values: list[float]) -> float | str:
    if len(values) < 2:
        return ""
    x_mean = (len(values) - 1) / 2.0
    y_mean = sum(values) / len(values)
    denom = sum((idx - x_mean) ** 2 for idx in range(len(values)))
    return sum((idx - x_mean) * (value - y_mean) for idx, value in enumerate(values)) / denom


def rank_bins(rows: list[dict[str, Any]], column: str, n_bins: int) -> dict[int, int]:
    values = [
        (as_float(row.get(column)), idx)
        for idx, row in enumerate(rows)
        if as_float(row.get(column)) is not None
    ]
    ordered = sorted(values, key=lambda item: item[0])
    if not ordered:
        return {}
    return {
        idx: min(int(pos * n_bins / len(ordered)), n_bins - 1)
        for pos, (_, idx) in enumerate(ordered)
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def lambda_tag(value: float) -> str:
    return str(value).replace(".", "p")


def fmt(value: Any) -> str:
    if value in {None, ""}:
        return "NA"
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
