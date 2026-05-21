#!/usr/bin/env python3
"""Build and run a MIMIC-IV onset benchmark for LAMP.

Primary intended endpoint: vasopressor initiation from ICU inputevents.
Secondary scaffold endpoint: ventilation initiation from ICU procedureevents.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402
from lamp.controls import as_float  # noqa: E402


DEFAULT_HORIZONS = [6, 12, 18]
DEFAULT_LAMBDAS = [0.0, 0.005, 0.01, 0.02, 0.05, 0.10]
VITALS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp"]
VITAL_PATTERNS = {
    "HR": re.compile(r"\bheart rate\b", re.I),
    "O2Sat": re.compile(r"\b(o2 saturation|spo2|oxygen saturation)\b", re.I),
    "Temp": re.compile(r"\btemperature\b", re.I),
    "SBP": re.compile(r"\b(systolic|sbp)\b", re.I),
    "MAP": re.compile(r"\b(mean arterial|blood pressure mean|map\b|mean blood pressure)", re.I),
    "DBP": re.compile(r"\b(diastolic|dbp)\b", re.I),
    "Resp": re.compile(r"\b(respiratory rate|resp rate)\b", re.I),
}
VASOPRESSOR_PATTERN = re.compile(
    r"\b(norepinephrine|noradrenaline|epinephrine|adrenaline|phenylephrine|vasopressin|dopamine)\b",
    re.I,
)
VENTILATION_PATTERN = re.compile(r"\b(intubation|mechanical ventilation|ventilator)\b", re.I)
EXCLUDE_VENTILATION_PATTERN = re.compile(r"\b(extubation|spontaneous awakening|weaning)\b", re.I)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mimic-root", required=True, help="Directory containing MIMIC-IV CSV/CSV.GZ files.")
    parser.add_argument("--task", choices=["vasopressor", "ventilation"], default="vasopressor")
    parser.add_argument("--out", default="results/mimic_iv_lamp/vasopressor")
    parser.add_argument("--horizons", default="6,12,18")
    parser.add_argument("--lookback-hours", type=int, default=6)
    parser.add_argument("--min-history-hours", type=int, default=6)
    parser.add_argument("--max-stays", type=int, default=0, help="Optional development cap after cohort construction.")
    parser.add_argument("--n-null", type=int, default=200)
    args = parser.parse_args(argv)

    mimic_root = Path(args.mimic_root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    horizons = [int(x) for x in args.horizons.split(",") if x.strip()]

    tables = find_mimic_tables(mimic_root, args.task)
    d_items = read_d_items(tables["d_items"])
    vital_item_map = build_vital_item_map(d_items)
    endpoint_itemids = build_endpoint_itemids(d_items, args.task)
    if not endpoint_itemids:
        raise RuntimeError(f"No {args.task} itemids found in d_items.")

    stays = read_icustays(tables["icustays"])
    add_patient_demographics(stays, tables.get("patients"))
    events = read_endpoint_events(tables, endpoint_itemids, args.task)
    rowspecs = make_prediction_specs(
        stays=stays,
        endpoint_events=events,
        horizons=horizons,
        min_history_hours=args.min_history_hours,
        max_stays=args.max_stays,
    )
    if not rowspecs:
        raise RuntimeError("No prediction rows met history and horizon requirements.")

    collect_chartevents(
        chartevents_path=tables["chartevents"],
        rowspecs=rowspecs,
        vital_item_map=vital_item_map,
    )
    score_rows = build_score_rows(rowspecs, args.lookback_hours)
    table_dir = out_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    score_table = table_dir / f"mimic_iv_{args.task}_score_table.csv"
    write_csv(score_table, score_rows)

    config_base = build_lamp_config(args.task, args.n_null)
    run_main_lamp(score_rows, score_table, config_base, out_dir, horizons)
    run_oracle_mixtures(score_rows, config_base, out_dir, horizons)
    run_visible_shortcut(score_rows, config_base, out_dir, horizons)

    write_dataset_note(out_dir, tables, args.task)
    print(out_dir)
    return 0


def find_mimic_tables(root: Path, task: str) -> dict[str, Path]:
    tables = {
        "icustays": find_table(root, ["icu/icustays.csv.gz", "icu/icustays.csv", "icustays.csv.gz", "icustays.csv"]),
        "d_items": find_table(root, ["icu/d_items.csv.gz", "icu/d_items.csv", "d_items.csv.gz", "d_items.csv"]),
        "chartevents": find_table(root, ["icu/chartevents.csv.gz", "icu/chartevents.csv", "chartevents.csv.gz", "chartevents.csv"]),
        "patients": find_optional_table(root, ["hosp/patients.csv.gz", "hosp/patients.csv", "patients.csv.gz", "patients.csv"]),
    }
    if task == "vasopressor":
        tables["inputevents"] = find_table(root, ["icu/inputevents.csv.gz", "icu/inputevents.csv", "inputevents.csv.gz", "inputevents.csv"])
    else:
        tables["procedureevents"] = find_table(root, ["icu/procedureevents.csv.gz", "icu/procedureevents.csv", "procedureevents.csv.gz", "procedureevents.csv"])
    return tables


def find_table(root: Path, candidates: list[str]) -> Path:
    found = find_optional_table(root, candidates)
    if found is None:
        raise FileNotFoundError(f"Missing required MIMIC table. Tried: {candidates}")
    return found


def find_optional_table(root: Path, candidates: list[str]) -> Path | None:
    for candidate in candidates:
        path = root / candidate
        if path.exists():
            return path
    return None


def read_d_items(path: Path) -> dict[int, str]:
    rows = read_csv_rows(path, usecols=["itemid", "label"])
    return {int(row["itemid"]): row.get("label", "") for row in rows if row.get("itemid")}


def build_vital_item_map(d_items: dict[int, str]) -> dict[int, str]:
    item_map: dict[int, str] = {}
    for itemid, label in d_items.items():
        for vital, pattern in VITAL_PATTERNS.items():
            if pattern.search(label):
                item_map[itemid] = vital
                break
    return item_map


def build_endpoint_itemids(d_items: dict[int, str], task: str) -> set[int]:
    itemids: set[int] = set()
    for itemid, label in d_items.items():
        if task == "vasopressor":
            if VASOPRESSOR_PATTERN.search(label):
                itemids.add(itemid)
        else:
            if VENTILATION_PATTERN.search(label) and not EXCLUDE_VENTILATION_PATTERN.search(label):
                itemids.add(itemid)
    return itemids


def read_icustays(path: Path) -> dict[int, dict[str, Any]]:
    stays: dict[int, dict[str, Any]] = {}
    for row in read_csv_rows(path, usecols=["subject_id", "hadm_id", "stay_id", "intime", "outtime"]):
        stay_id = int(row["stay_id"])
        intime = parse_time(row["intime"])
        outtime = parse_time(row["outtime"])
        if intime is None or outtime is None or outtime <= intime:
            continue
        stays[stay_id] = {
            "subject_id": row.get("subject_id"),
            "hadm_id": row.get("hadm_id"),
            "stay_id": stay_id,
            "intime": intime,
            "outtime": outtime,
            "anchor_age": None,
            "gender": None,
        }
    return stays


def add_patient_demographics(stays: dict[int, dict[str, Any]], patients_path: Path | None) -> None:
    if patients_path is None:
        return
    patients: dict[str, dict[str, str]] = {}
    for row in read_csv_rows(patients_path, usecols=["subject_id", "gender", "anchor_age"]):
        patients[row["subject_id"]] = row
    for stay in stays.values():
        patient = patients.get(str(stay["subject_id"]))
        if patient:
            stay["anchor_age"] = as_float(patient.get("anchor_age"))
            stay["gender"] = patient.get("gender")


def read_endpoint_events(
    tables: dict[str, Path],
    endpoint_itemids: set[int],
    task: str,
) -> dict[int, datetime]:
    if task == "vasopressor":
        path = tables["inputevents"]
        usecols = ["stay_id", "itemid", "starttime", "amount", "rate", "originalrate"]
        time_col = "starttime"
    else:
        path = tables["procedureevents"]
        usecols = ["stay_id", "itemid", "starttime"]
        time_col = "starttime"

    first: dict[int, datetime] = {}
    for row in read_csv_rows(path, usecols=usecols):
        itemid = safe_int(row.get("itemid"))
        stay_id = safe_int(row.get("stay_id"))
        if itemid not in endpoint_itemids or stay_id is None:
            continue
        if task == "vasopressor" and not positive_administration(row):
            continue
        event_time = parse_time(row.get(time_col))
        if event_time is None:
            continue
        if stay_id not in first or event_time < first[stay_id]:
            first[stay_id] = event_time
    return first


def positive_administration(row: dict[str, str]) -> bool:
    values = [as_float(row.get("amount")), as_float(row.get("rate")), as_float(row.get("originalrate"))]
    values = [value for value in values if value is not None]
    return not values or any(value > 0 for value in values)


def make_prediction_specs(
    stays: dict[int, dict[str, Any]],
    endpoint_events: dict[int, datetime],
    horizons: list[int],
    min_history_hours: int,
    max_stays: int,
) -> list[dict[str, Any]]:
    selected_stays = list(stays.values())
    if max_stays:
        selected_stays = selected_stays[:max_stays]

    specs: list[dict[str, Any]] = []
    for stay in selected_stays:
        event_time = endpoint_events.get(stay["stay_id"])
        for horizon in horizons:
            if event_time is not None and stay["intime"] < event_time < stay["outtime"]:
                label = 1
                anchor = event_time - timedelta(hours=horizon)
            else:
                label = 0
                duration_h = hours_between(stay["intime"], stay["outtime"])
                if duration_h < min_history_hours + horizon + 1:
                    continue
                anchor_h = min(max(min_history_hours, 0.70 * duration_h), duration_h - horizon)
                anchor = stay["intime"] + timedelta(hours=anchor_h)
            if hours_between(stay["intime"], anchor) < min_history_hours:
                continue
            if anchor + timedelta(hours=horizon) > stay["outtime"]:
                continue
            spec = dict(stay)
            spec.update(
                {
                    "horizon_h": horizon,
                    "label_event_within_horizon": label,
                    "event_time": event_time,
                    "anchor_time": anchor,
                    "anchor_iculos_h": hours_between(stay["intime"], anchor),
                    "pre_values": defaultdict(list),
                    "future_values": defaultdict(list),
                }
            )
            specs.append(spec)
    return specs


def collect_chartevents(
    chartevents_path: Path,
    rowspecs: list[dict[str, Any]],
    vital_item_map: dict[int, str],
) -> None:
    by_stay: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for spec in rowspecs:
        by_stay[spec["stay_id"]].append(spec)

    itemids = set(vital_item_map)
    usecols = ["stay_id", "itemid", "charttime", "valuenum"]
    for row in read_csv_rows(chartevents_path, usecols=usecols):
        stay_id = safe_int(row.get("stay_id"))
        itemid = safe_int(row.get("itemid"))
        if stay_id not in by_stay or itemid not in itemids:
            continue
        value = normalize_vital(vital_item_map[itemid], as_float(row.get("valuenum")))
        if value is None:
            continue
        charttime = parse_time(row.get("charttime"))
        if charttime is None:
            continue
        vital = vital_item_map[itemid]
        for spec in by_stay[stay_id]:
            if spec["intime"] <= charttime <= spec["anchor_time"]:
                spec["pre_values"][vital].append((charttime, value))
            elif spec["anchor_time"] < charttime <= spec["anchor_time"] + timedelta(hours=spec["horizon_h"]):
                spec["future_values"][vital].append((charttime, value))


def build_score_rows(rowspecs: list[dict[str, Any]], lookback_hours: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in rowspecs:
        row: dict[str, Any] = {
            "stay_id": spec["stay_id"],
            "subject_id": spec["subject_id"],
            "hadm_id": spec["hadm_id"],
            "horizon_h": spec["horizon_h"],
            "anchor_time": spec["anchor_time"].isoformat(sep=" "),
            "intime": spec["intime"].isoformat(sep=" "),
            "outtime": spec["outtime"].isoformat(sep=" "),
            "event_time": spec["event_time"].isoformat(sep=" ") if spec["event_time"] else "",
            "anchor_iculos_h": spec["anchor_iculos_h"],
            "label_event_within_horizon": spec["label_event_within_horizon"],
            "anchor_age": spec.get("anchor_age"),
            "gender": spec.get("gender"),
        }
        add_features(row, spec["pre_values"], "", spec["anchor_time"], lookback_hours)
        add_features(row, spec["future_values"], "future_", spec["anchor_time"] + timedelta(hours=spec["horizon_h"]), lookback_hours)
        row["valid_early_warning_score"] = warning_score(row, "")
        row["future_physiology_sentinel_score"] = warning_score(row, "future_")
        row["oracle_label_sentinel_score"] = oracle_score(spec)
        rows.append(row)
    return rows


def add_features(
    row: dict[str, Any],
    values_by_vital: dict[str, list[tuple[datetime, float]]],
    prefix: str,
    anchor: datetime,
    lookback_hours: int,
) -> None:
    missing = 0
    for vital in VITALS:
        values = sorted(values_by_vital.get(vital, []), key=lambda item: item[0])
        recent = [
            value
            for time, value in values
            if time >= anchor - timedelta(hours=lookback_hours)
        ]
        all_values = [value for _, value in values]
        row[f"{prefix}{vital}_last"] = all_values[-1] if all_values else ""
        row[f"{prefix}{vital}_recent_mean"] = mean(recent)
        row[f"{prefix}{vital}_recent_slope"] = slope(recent)
        if not recent:
            missing += 1
    row[f"{prefix}vital_missing_rate"] = missing / len(VITALS)
    row[f"{prefix}n_vital_observations"] = sum(
        len(values_by_vital.get(vital, [])) for vital in VITALS
    )


def warning_score(row: dict[str, Any], prefix: str) -> float:
    hr = as_float(row.get(prefix + "HR_last"))
    spo2 = as_float(row.get(prefix + "O2Sat_last"))
    temp = as_float(row.get(prefix + "Temp_last"))
    sbp = as_float(row.get(prefix + "SBP_last"))
    mapv = as_float(row.get(prefix + "MAP_last"))
    resp = as_float(row.get(prefix + "Resp_last"))
    score = 0.0
    score += clipped(((hr or 90.0) - 90.0) / 35.0)
    score += clipped(((resp or 20.0) - 20.0) / 8.0)
    score += clipped((95.0 - (spo2 or 95.0)) / 8.0)
    score += clipped((110.0 - (sbp or 110.0)) / 35.0)
    score += clipped((70.0 - (mapv or 70.0)) / 20.0)
    score += clipped(abs((temp or 37.0) - 37.0) / 1.5)
    score += 0.25 * clipped(as_float(row.get(prefix + "vital_missing_rate")) or 0.0, 0.0, 1.0)
    return float(score)


def oracle_score(spec: dict[str, Any]) -> float:
    if not spec["label_event_within_horizon"]:
        return 0.0
    if spec["event_time"] is None:
        return 10.0
    distance_h = max(hours_between(spec["anchor_time"], spec["event_time"]), 0.0)
    return float(10.0 + 1.0 / (1.0 + distance_h))


def run_main_lamp(
    score_rows: list[dict[str, Any]],
    score_table: Path,
    config_base: dict[str, Any],
    out_dir: Path,
    horizons: list[int],
) -> None:
    summary: list[dict[str, Any]] = []
    for horizon in horizons:
        horizon_rows = [row for row in score_rows if int(row["horizon_h"]) == horizon]
        if not horizon_rows:
            continue
        run_dir = out_dir / "main" / f"horizon_{horizon}"
        run_dir.mkdir(parents=True, exist_ok=True)
        table_path = run_dir / "score_table.csv"
        config_path = run_dir / "config.yaml"
        write_csv(table_path, horizon_rows)
        config = dict_with_dataset(config_base, f"MIMIC-IV onset h{horizon}", horizon)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        result = run_audit(config_path, table_path, run_dir)
        summary.append(flatten_main_result(horizon, result))
    write_csv(out_dir / "lamp_cli_scientific_summary.csv", summary)


def run_oracle_mixtures(
    score_rows: list[dict[str, Any]],
    config_base: dict[str, Any],
    out_dir: Path,
    horizons: list[int],
) -> None:
    summary: list[dict[str, Any]] = []
    for horizon in horizons:
        horizon_rows = [row for row in score_rows if int(row["horizon_h"]) == horizon]
        for lam in DEFAULT_LAMBDAS:
            mixed_rows = []
            for row in horizon_rows:
                new = dict(row)
                valid = as_float(row.get("valid_early_warning_score")) or 0.0
                oracle = as_float(row.get("oracle_label_sentinel_score")) or 0.0
                new["mixed_score"] = (1.0 - lam) * valid + lam * oracle
                mixed_rows.append(new)
            table_path = out_dir / "perturbations" / "tables" / f"oracle_h{horizon}_l{lambda_tag(lam)}.csv"
            write_csv(table_path, mixed_rows)
            for provenance in ["undeclared", "declared"]:
                run_dir = out_dir / "perturbations" / "oracle_mixture" / f"{provenance}_h{horizon}_l{lambda_tag(lam)}"
                run_dir.mkdir(parents=True, exist_ok=True)
                config = dict_with_dataset(config_base, f"MIMIC-IV oracle mixture h{horizon} lambda {lam:g}", horizon)
                config["columns"]["score"] = "mixed_score"
                config["negative_controls"]["n_permutations"] = 200
                config["leakage_proximity"] = {
                    "baseline_score": "valid_early_warning_score",
                    "oracle_proximity_alert_min": 0.01,
                }
                if provenance == "declared" and lam > 0:
                    config["temporal_isolation"]["valid_score_features"].append(
                        {"name": "oracle_label_sentinel_score", "latest_offset_h": 1}
                    )
                    config["forbidden_features"]["valid_score_features"].append(
                        "oracle_label_sentinel_score"
                    )
                config_path = run_dir / "config.yaml"
                config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
                result = run_audit(config_path, table_path, run_dir)
                summary.append(flatten_oracle_result(horizon, lam, provenance, result))
    write_csv(out_dir / "perturbations" / "oracle_mixture_summary.csv", summary)


def run_visible_shortcut(
    score_rows: list[dict[str, Any]],
    config_base: dict[str, Any],
    out_dir: Path,
    horizons: list[int],
) -> None:
    summary: list[dict[str, Any]] = []
    for horizon in horizons:
        horizon_rows = [dict(row) for row in score_rows if int(row["horizon_h"]) == horizon]
        bins = rank_bins(horizon_rows, "anchor_iculos_h", 3)
        for idx, row in enumerate(horizon_rows):
            row["visible_only_score"] = bins.get(idx, 1)
        table_path = out_dir / "perturbations" / "tables" / f"visible_h{horizon}.csv"
        write_csv(table_path, horizon_rows)
        run_dir = out_dir / "perturbations" / "visible_confounding" / f"horizon_{horizon}"
        run_dir.mkdir(parents=True, exist_ok=True)
        config = dict_with_dataset(config_base, f"MIMIC-IV visible workflow shortcut h{horizon}", horizon)
        config["columns"]["score"] = "visible_only_score"
        config["visible_state_matching"] = {
            "columns": ["anchor_iculos_h"],
            "n_bins": 3,
            "min_bin_size": 8,
        }
        config["temporal_isolation"]["valid_score_features"] = [
            {"name": "anchor_iculos_h", "latest_offset_h": 0}
        ]
        config["forbidden_features"]["valid_score_features"] = ["anchor_iculos_h"]
        config["negative_controls"]["n_permutations"] = 200
        config["leakage_proximity"] = {
            "baseline_score": "valid_early_warning_score",
            "oracle_proximity_alert_min": 1.1,
        }
        config_path = run_dir / "config.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        result = run_audit(config_path, table_path, run_dir)
        summary.append(flatten_visible_result(horizon, result))
    write_csv(out_dir / "perturbations" / "visible_confounding_summary.csv", summary)


def build_lamp_config(task: str, n_null: int) -> dict[str, Any]:
    future_columns = []
    for vital in VITALS:
        future_columns += [
            f"future_{vital}_last",
            f"future_{vital}_recent_mean",
            f"future_{vital}_recent_slope",
        ]
    future_columns += ["future_vital_missing_rate", "future_n_vital_observations"]
    valid_features = [
        "HR_last",
        "O2Sat_last",
        "Temp_last",
        "SBP_last",
        "MAP_last",
        "Resp_last",
        "vital_missing_rate",
        "anchor_iculos_h",
    ]
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {"name": f"MIMIC-IV {task} onset", "role": "external ICU benchmark"},
        "columns": {
            "subject_id": "stay_id",
            "label": "label_event_within_horizon",
            "positive_value": 1,
            "score": "valid_early_warning_score",
            "anchor_time": "anchor_time",
        },
        "temporal_isolation": {
            "anchor": "anchor_time",
            "valid_features_must_be": "at_or_before_anchor",
            "frozen_before_holdout": [
                "endpoint item regex",
                "horizons",
                "pre-anchor feature extraction",
                "valid score formula",
                "future sentinel formula",
                "oracle sentinel formula",
                "visible-state matching variables",
                "null-control seed",
                "LAMP thresholds",
            ],
            "valid_score_features": [
                {"name": feature, "latest_offset_h": 0} for feature in valid_features
            ],
        },
        "forbidden_features": {
            "columns": ["future_physiology_sentinel_score", "oracle_label_sentinel_score", "event_time"] + future_columns,
            "allowed_metadata_columns": ["event_time"] + future_columns,
            "valid_score_features": valid_features,
        },
        "sentinels": {
            "future_physiology": {
                "column": "future_physiology_sentinel_score",
                "role": "future_physiology",
                "expected_signature": "invalid post-anchor physiology comparator",
            },
            "oracle_label": {
                "column": "oracle_label_sentinel_score",
                "role": "oracle_label",
                "expected_signature": "ceiling label-adjacent leakage comparator",
            },
        },
        "negative_controls": {"n_permutations": n_null, "seed": 2026},
        "visible_state_matching": {
            "columns": ["HR_last", "O2Sat_last", "Temp_last", "MAP_last", "Resp_last", "anchor_iculos_h"],
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
            "score_thresholds": [1.5, 2.5, 3.5],
        },
    }


def dict_with_dataset(config: dict[str, Any], name: str, horizon: int) -> dict[str, Any]:
    data = yaml.safe_load(yaml.safe_dump(config))
    data["dataset"] = {
        "name": name,
        "role": "MIMIC-IV external ICU benchmark",
        "horizon_h": horizon,
    }
    return data


def flatten_main_result(horizon: int, result: dict[str, Any]) -> dict[str, Any]:
    primary = result["primary_score"]
    relations = result["sentinel_relations"]
    return {
        "horizon_h": horizon,
        "n": primary["n"],
        "n_positive": primary["n_positive"],
        "valid_auc": primary["auc"],
        "future_auc": relations["future_physiology"]["sentinel_auc"],
        "oracle_auc": relations["oracle_label"]["sentinel_auc"],
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "audit_pass_candidate": result["failure_mode_dossier"]["audit_pass_candidate"],
        "output_classes": ";".join(result["failure_mode_dossier"]["output_classes"]),
    }


def flatten_oracle_result(
    horizon: int,
    lam: float,
    provenance: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    primary = result["primary_score"]
    oracle = result["sentinel_relations"]["oracle_label"]
    return {
        "horizon_h": horizon,
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


def flatten_visible_result(horizon: int, result: dict[str, Any]) -> dict[str, Any]:
    primary = result["primary_score"]
    oracle = result["sentinel_relations"]["oracle_label"]
    return {
        "horizon_h": horizon,
        "n": primary["n"],
        "n_positive": primary["n_positive"],
        "visible_only_auc": primary["auc"],
        "baseline_valid_auc": oracle.get("baseline_auc"),
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "audit_pass_candidate": result["failure_mode_dossier"]["audit_pass_candidate"],
        "output_classes": ";".join(result["failure_mode_dossier"]["output_classes"]),
    }


def write_dataset_note(out_dir: Path, tables: dict[str, Path], task: str) -> None:
    note = [
        f"# MIMIC-IV LAMP Benchmark: {task}",
        "",
        "This directory is generated by `scripts/run_mimic_iv_onset_bench.py`.",
        "",
        "Required MIMIC-IV source tables:",
    ]
    for name, path in sorted(tables.items()):
        if path is not None:
            note.append(f"- `{name}`: `{path}`")
    note.extend(
        [
            "",
            "The benchmark creates a frozen per-anchor score table, runs LAMP per horizon,",
            "then repeats the same low-dose oracle leakage and visible-workflow shortcut",
            "perturbations used for the PhysioNet/CinC 2019 sepsis benchmark.",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(note) + "\n", encoding="utf-8")


def read_csv_rows(path: Path, usecols: list[str] | None = None) -> Iterable[dict[str, str]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if usecols:
            missing = [col for col in usecols if col not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"{path} missing columns: {missing}")
        for row in reader:
            if usecols:
                yield {col: row.get(col, "") for col in usecols}
            else:
                yield dict(row)


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


def parse_time(value: Any) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def safe_int(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(value))
    except ValueError:
        return None


def normalize_vital(vital: str, value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    if vital == "Temp" and value > 80:
        value = (value - 32.0) * 5.0 / 9.0
    ranges = {
        "HR": (20, 250),
        "O2Sat": (30, 100),
        "Temp": (25, 45),
        "SBP": (30, 260),
        "MAP": (20, 200),
        "DBP": (10, 180),
        "Resp": (1, 80),
    }
    low, high = ranges[vital]
    if value < low or value > high:
        return None
    return float(value)


def hours_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600.0


def mean(values: list[float]) -> float | str:
    return sum(values) / len(values) if values else ""


def slope(values: list[float]) -> float | str:
    if len(values) < 2:
        return ""
    x_mean = (len(values) - 1) / 2.0
    y_mean = sum(values) / len(values)
    denom = sum((i - x_mean) ** 2 for i in range(len(values)))
    if denom == 0:
        return ""
    return sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values)) / denom


def clipped(value: float, low: float = 0.0, high: float = 5.0) -> float:
    return min(max(value, low), high)


def rank_bins(rows: list[dict[str, Any]], column: str, n_bins: int) -> dict[int, int]:
    values = [
        (as_float(row.get(column)), idx)
        for idx, row in enumerate(rows)
        if as_float(row.get(column)) is not None
    ]
    ordered = sorted(values, key=lambda item: item[0])
    result: dict[int, int] = {}
    for pos, (_, idx) in enumerate(ordered):
        result[idx] = min(int(pos * n_bins / len(ordered)), n_bins - 1)
    return result


def lambda_tag(value: float) -> str:
    return str(value).replace(".", "p")


if __name__ == "__main__":
    raise SystemExit(main())
