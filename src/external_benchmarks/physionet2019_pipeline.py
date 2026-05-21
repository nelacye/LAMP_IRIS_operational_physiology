"""Unified raw `.psv` pipeline for the PhysioNet/CinC 2019 sepsis task.

The functions here convert patient-level hourly `.psv` files into a common
example table used by both classical probes and sequence models:

- valid early-window tensors and engineered features
- leaky future-window tensors/features
- oracle/onset-distance sentinels
- visible-state matching columns for LAMP
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


RAW_SIGNAL_COLUMNS = [
    "HR",
    "O2Sat",
    "Temp",
    "SBP",
    "MAP",
    "DBP",
    "Resp",
    "EtCO2",
    "BaseExcess",
    "HCO3",
    "FiO2",
    "pH",
    "PaCO2",
    "SaO2",
    "AST",
    "BUN",
    "Alkalinephos",
    "Calcium",
    "Chloride",
    "Creatinine",
    "Bilirubin_direct",
    "Glucose",
    "Lactate",
    "Magnesium",
    "Phosphate",
    "Potassium",
    "Bilirubin_total",
    "TroponinI",
    "Hct",
    "Hgb",
    "PTT",
    "WBC",
    "Fibrinogen",
    "Platelets",
]

SEQUENCE_COLUMNS = [
    "HR",
    "O2Sat",
    "Temp",
    "SBP",
    "MAP",
    "DBP",
    "Resp",
    "FiO2",
    "pH",
    "Creatinine",
    "Glucose",
    "Lactate",
    "WBC",
    "Platelets",
]

STATIC_COLUMNS = ["Age", "Gender", "Unit1", "Unit2", "HospAdmTime"]
VISIBLE_MATCH_COLUMNS = [
    "Age",
    "anchor_idx",
    "ICULOS_anchor",
    "HR_early_last",
    "O2Sat_early_last",
    "SBP_early_last",
    "MAP_early_last",
    "Resp_early_last",
    "early_missing_rate",
]


@dataclass(frozen=True)
class ExampleConfig:
    horizons: tuple[int, ...] = (6, 12, 18)
    early_window_h: int = 12
    negative_gap_h: int = 6
    max_patients: int = 0
    include_sets: tuple[str, ...] = ("A", "B")
    seed: int = 2026


def discover_psv_files(
    training_root: Path,
    include_sets: Iterable[str] = ("A", "B"),
    max_patients: int = 0,
    seed: int = 2026,
) -> list[Path]:
    """Return raw PSV files from `training_setA` and/or `training_setB`."""

    files: list[Path] = []
    for set_name in include_sets:
        set_dir = training_root / f"training_set{set_name.upper()}"
        if set_dir.exists():
            files.extend(sorted(set_dir.glob("*.psv")))
    if max_patients and len(files) > max_patients:
        rng = np.random.default_rng(seed)
        indices = np.sort(rng.choice(len(files), size=max_patients, replace=False))
        files = [files[int(idx)] for idx in indices]
    return files


def load_patient(path: Path) -> pd.DataFrame:
    """Read one patient `.psv` and add stable patient/set identifiers."""

    frame = pd.read_csv(path, sep="|")
    frame["patient_id"] = path.stem
    frame["source_set"] = infer_source_set(path)
    frame["row_idx"] = np.arange(len(frame), dtype=int)
    return frame


def infer_source_set(path: Path) -> str:
    parent = path.parent.name
    if parent.endswith("A"):
        return "A"
    if parent.endswith("B"):
        return "B"
    return parent


def resample_patient(frame: pd.DataFrame, freq: str = "1h") -> pd.DataFrame:
    """Resample one patient to hourly or sub-hourly aggregates.

    The CinC 2019 files are already hourly. This function keeps the native
    cadence for `1h`; for `30min`-style use it interpolates numeric physiology
    with forward/backward fill while preserving the maximum sepsis label in
    each bin.
    """

    if freq.lower() in {"1h", "1hr", "hourly", "native"}:
        return frame.copy()

    work = frame.copy()
    elapsed_h = pd.to_numeric(work["ICULOS"], errors="coerce").fillna(work["row_idx"] + 1) - 1
    work.index = pd.to_timedelta(elapsed_h, unit="h")
    numeric = work.select_dtypes(include=[np.number]).columns.tolist()
    grouped = work[numeric].resample(freq).mean()
    if "SepsisLabel" in grouped:
        grouped["SepsisLabel"] = work["SepsisLabel"].resample(freq).max().fillna(0)
    grouped = grouped.ffill().bfill()
    grouped["patient_id"] = frame["patient_id"].iloc[0]
    grouped["source_set"] = frame["source_set"].iloc[0]
    grouped["row_idx"] = np.arange(len(grouped), dtype=int)
    grouped["ICULOS"] = np.arange(1, len(grouped) + 1, dtype=float)
    return grouped.reset_index(drop=True)


def build_examples_from_files(
    paths: list[Path],
    config: ExampleConfig,
    resample_freq: str = "1h",
) -> tuple[pd.DataFrame, dict[int, np.ndarray], dict[int, np.ndarray]]:
    """Create metadata/features and valid/leaky sequence tensors for horizons."""

    rows: list[dict[str, float | int | str]] = []
    valid_sequences: dict[int, list[np.ndarray]] = {h: [] for h in config.horizons}
    leaky_sequences: dict[int, list[np.ndarray]] = {h: [] for h in config.horizons}

    for path in paths:
        patient = resample_patient(load_patient(path), freq=resample_freq)
        if len(patient) < config.early_window_h + 1:
            continue
        onset_idx = first_onset_idx(patient)
        for horizon in config.horizons:
            for anchor_idx, example_kind in choose_anchors(
                n_rows=len(patient),
                onset_idx=onset_idx,
                horizon_h=horizon,
                early_window_h=config.early_window_h,
                negative_gap_h=config.negative_gap_h,
            ):
                label = int(
                    onset_idx is not None
                    and anchor_idx < onset_idx
                    and onset_idx - anchor_idx <= horizon
                )
                early = window_before(patient, anchor_idx, config.early_window_h)
                future = window_after(patient, anchor_idx, horizon)
                if len(early) != config.early_window_h or len(future) != horizon:
                    continue

                row = build_feature_row(
                    patient=patient,
                    early=early,
                    future=future,
                    path=path,
                    anchor_idx=anchor_idx,
                    horizon_h=horizon,
                    onset_idx=onset_idx,
                    label=label,
                    example_kind=example_kind,
                )
                rows.append(row)
                valid_sequences[horizon].append(sequence_matrix(early, SEQUENCE_COLUMNS))
                leaky_sequences[horizon].append(
                    sequence_matrix(pd.concat([early, future], ignore_index=True), SEQUENCE_COLUMNS)
                )

    table = pd.DataFrame(rows)
    valid_arrays = {
        horizon: np.stack(items).astype(np.float32) if items else empty_sequence(config.early_window_h)
        for horizon, items in valid_sequences.items()
    }
    leaky_arrays = {
        horizon: np.stack(items).astype(np.float32) if items else empty_sequence(config.early_window_h + horizon)
        for horizon, items in leaky_sequences.items()
    }
    return table, valid_arrays, leaky_arrays


def first_onset_idx(frame: pd.DataFrame) -> int | None:
    labels = pd.to_numeric(frame["SepsisLabel"], errors="coerce").fillna(0).to_numpy()
    positives = np.flatnonzero(labels > 0)
    if len(positives) == 0:
        return None
    return int(positives[0])


def choose_anchors(
    n_rows: int,
    onset_idx: int | None,
    horizon_h: int,
    early_window_h: int,
    negative_gap_h: int,
) -> list[tuple[int, str]]:
    """Choose one positive and/or one clean negative anchor per patient/horizon."""

    anchors: list[tuple[int, str]] = []
    latest_anchor = n_rows - horizon_h - 1
    earliest_anchor = early_window_h - 1
    if latest_anchor < earliest_anchor:
        return anchors

    if onset_idx is not None:
        positive_anchor = onset_idx - horizon_h
        if earliest_anchor <= positive_anchor <= latest_anchor:
            anchors.append((int(positive_anchor), "event_horizon_positive"))

        negative_anchor = onset_idx - horizon_h - negative_gap_h
        if earliest_anchor <= negative_anchor <= latest_anchor:
            anchors.append((int(negative_anchor), "pre_event_negative"))
    else:
        anchors.append((int(max(earliest_anchor, latest_anchor)), "non_event_negative"))

    return dedupe_anchors(anchors)


def dedupe_anchors(anchors: list[tuple[int, str]]) -> list[tuple[int, str]]:
    seen: set[int] = set()
    clean: list[tuple[int, str]] = []
    for anchor, kind in anchors:
        if anchor in seen:
            continue
        seen.add(anchor)
        clean.append((anchor, kind))
    return clean


def window_before(frame: pd.DataFrame, anchor_idx: int, length: int) -> pd.DataFrame:
    return frame.iloc[anchor_idx - length + 1 : anchor_idx + 1].copy()


def window_after(frame: pd.DataFrame, anchor_idx: int, length: int) -> pd.DataFrame:
    return frame.iloc[anchor_idx + 1 : anchor_idx + 1 + length].copy()


def build_feature_row(
    patient: pd.DataFrame,
    early: pd.DataFrame,
    future: pd.DataFrame,
    path: Path,
    anchor_idx: int,
    horizon_h: int,
    onset_idx: int | None,
    label: int,
    example_kind: str,
) -> dict[str, float | int | str]:
    row: dict[str, float | int | str] = {
        "patient_id": patient["patient_id"].iloc[0],
        "source_set": patient["source_set"].iloc[0],
        "file_path": str(path),
        "horizon_h": int(horizon_h),
        "anchor_idx": int(anchor_idx),
        "ICULOS_anchor": value_at(patient, "ICULOS", anchor_idx),
        "sepsis_onset_idx": -1 if onset_idx is None else int(onset_idx),
        "hours_to_onset": 999.0 if onset_idx is None else float(onset_idx - anchor_idx),
        "label_future_sepsis": int(label),
        "example_kind": example_kind,
    }

    for column in STATIC_COLUMNS:
        row[column] = value_at(patient, column, anchor_idx)

    add_window_features(row, early, prefix="early")
    add_window_features(row, future, prefix="future")
    row["early_missing_rate"] = missing_rate(early, RAW_SIGNAL_COLUMNS)
    row["future_missing_rate"] = missing_rate(future, RAW_SIGNAL_COLUMNS)
    row["future_physiology_sentinel_score"] = physiology_sentinel(future)
    row["oracle_label_sentinel_score"] = oracle_sentinel(onset_idx, anchor_idx, horizon_h)
    return row


def add_window_features(
    row: dict[str, float | int | str],
    frame: pd.DataFrame,
    prefix: str,
) -> None:
    for column in RAW_SIGNAL_COLUMNS:
        if column not in frame:
            continue
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        observed = values[np.isfinite(values)]
        base = f"{column}_{prefix}"
        row[f"{base}_last"] = safe_last(values)
        row[f"{base}_mean"] = float(np.nanmean(values)) if len(observed) else math.nan
        row[f"{base}_std"] = float(np.nanstd(values)) if len(observed) else math.nan
        row[f"{base}_min"] = float(np.nanmin(values)) if len(observed) else math.nan
        row[f"{base}_max"] = float(np.nanmax(values)) if len(observed) else math.nan
        row[f"{base}_slope"] = slope(values)
        row[f"{base}_missing_rate"] = float(np.mean(~np.isfinite(values)))


def value_at(frame: pd.DataFrame, column: str, idx: int) -> float:
    if column not in frame:
        return math.nan
    value = pd.to_numeric(pd.Series([frame[column].iloc[idx]]), errors="coerce").iloc[0]
    return float(value) if pd.notna(value) else math.nan


def safe_last(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    return float(finite[-1]) if len(finite) else math.nan


def slope(values: np.ndarray) -> float:
    mask = np.isfinite(values)
    if mask.sum() < 2:
        return math.nan
    x = np.flatnonzero(mask).astype(float)
    y = values[mask].astype(float)
    x = x - x.mean()
    denom = float(np.dot(x, x))
    if denom == 0:
        return 0.0
    return float(np.dot(x, y - y.mean()) / denom)


def missing_rate(frame: pd.DataFrame, columns: list[str]) -> float:
    present = [column for column in columns if column in frame]
    if not present:
        return math.nan
    return float(frame[present].isna().to_numpy().mean())


def physiology_sentinel(frame: pd.DataFrame) -> float:
    """A simple future physiology score with plausible sepsis directionality."""

    pieces = []
    for column, sign in [
        ("HR", 1.0),
        ("Resp", 1.0),
        ("Temp", 1.0),
        ("Lactate", 1.0),
        ("WBC", 1.0),
        ("MAP", -1.0),
        ("SBP", -1.0),
        ("O2Sat", -1.0),
        ("Platelets", -1.0),
    ]:
        if column in frame:
            values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
            if np.isfinite(values).any():
                pieces.append(sign * float(np.nanmean(values)))
    if not pieces:
        return 0.0
    value = float(np.nanmean(pieces))
    return float(1.0 / (1.0 + np.exp(-value / 50.0)))


def oracle_sentinel(onset_idx: int | None, anchor_idx: int, horizon_h: int) -> float:
    if onset_idx is None or onset_idx <= anchor_idx:
        return 0.0
    distance = onset_idx - anchor_idx
    if distance > horizon_h:
        return 0.0
    return float(1.0 - (distance - 1) / max(horizon_h, 1))


def sequence_matrix(frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    matrix = frame.reindex(columns=columns).apply(pd.to_numeric, errors="coerce").to_numpy()
    return matrix.astype(np.float32)


def empty_sequence(length: int) -> np.ndarray:
    return np.empty((0, length, len(SEQUENCE_COLUMNS)), dtype=np.float32)


def early_feature_columns(frame: pd.DataFrame) -> list[str]:
    blocked = {
        "label_future_sepsis",
        "sepsis_onset_idx",
        "hours_to_onset",
        "oracle_label_sentinel_score",
        "future_physiology_sentinel_score",
    }
    return [
        column
        for column in frame.columns
        if is_numeric_series(frame[column])
        and frame[column].notna().any()
        and column not in blocked
        and not column.startswith("future_")
    ]


def future_feature_columns(frame: pd.DataFrame) -> list[str]:
    return [
        column
        for column in frame.columns
        if is_numeric_series(frame[column])
        and frame[column].notna().any()
        and column.startswith("future_")
        and column != "future_physiology_sentinel_score"
    ]


def is_numeric_series(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)
