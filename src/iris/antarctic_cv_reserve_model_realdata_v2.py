#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Antarctic / polar-spaceflight-analog cardiovascular reserve model with real-data adapters.

Purpose
-------
Mechanistic, hypothesis-generating in silico framework for hidden cardiovascular
reserve under coupled environmental stress: cold, hypoxia, workload,
radiation-associated oxidative burden, circadian/sleep stress, and measurement
validity degradation.

This is NOT a clinical diagnostic model, NOT a patient-specific prediction model,
and NOT a radiation dose-response estimator. It is a credibility-oriented
computational scaffold: explicit equations, parameter distributions, internal
verification tests, uncertainty/sensitivity-friendly structure, and reproducible
outputs.

PowerShell quick start
----------------------
1) Save this file as: antarctic_cv_reserve_model.py
2) Optional virtual environment:
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
3) Install dependencies:
   py -m pip install numpy pandas matplotlib
4) Run:
   py .\antarctic_cv_reserve_model.py --out results --n 600 --seed 42
5) Outputs:
   results\population_summary.csv
   results\time_series_sample.csv
   results\class_counts.csv
   results\false_stability_cases.csv
   results\reserve_margin_plot.png
   results\class_trajectories_plot.png

Author: generated with ChatGPT assistance.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# -----------------------------
# Model definitions
# -----------------------------

RESERVE_NAMES = [
    "pump",                  # cardiac pump reserve
    "vascular_autonomic",    # vascular / autonomic reserve
    "oxygen_delivery",       # oxygen-delivery reserve
    "electrophysiology",     # electrophysiological reserve
    "mito_endothelial",      # mitochondrial/endothelial stress tolerance
]

STRESS_NAMES = [
    "cold",       # C(t)
    "hypoxia",    # H(t)
    "workload",   # W(t)
    "radiation",  # R(t), represented as radiation-associated burden input
    "sleep",      # S(t), circadian/sleep disruption
]


@dataclass(frozen=True)
class SimulationConfig:
    """Simulation configuration."""
    n_systems: int = 600
    seed: int = 42
    duration_hours: float = 72.0
    dt_hours: float = 0.05
    critical_reserve: float = 0.22
    false_stability_drop: float = 0.18
    false_stability_observed_slope_abs: float = 0.015
    sample_systems_to_save: int = 30


@dataclass
class SystemParameters:
    """One baseline-healthy cardiovascular system with latent constraints."""
    system_id: int
    latent_class: str
    baseline_reserve: np.ndarray        # R_0, shape (5,)
    direct_sensitivity: np.ndarray      # A[j, i], shape (5, 5)
    interaction_sensitivity: np.ndarray # B[j, pair], shape (5, 10)
    recovery_rate: np.ndarray           # k_rec[j], shape (5,)
    observation_noise_base: float
    observation_noise_sensitivity: np.ndarray # q for C, W, S, shape (3,)
    compensation_gain: np.ndarray       # simplified compensatory strategy, shape (5,)


# -----------------------------
# Stress protocol
# -----------------------------

def logistic(x: np.ndarray, center: float, width: float) -> np.ndarray:
    """Stable logistic ramp."""
    z = np.clip((x - center) / width, -60, 60)
    return 1.0 / (1.0 + np.exp(-z))


def build_stress_protocol(t: np.ndarray) -> pd.DataFrame:
    """
    Antarctic-like coupled stress protocol.

    All stressors are normalized to approximately [0, 1]. They are not direct
    physical units. The mapping to units should be defined in a future calibrated
    version, because pretending otherwise would be how models become decorative
    fiction with extra decimals.
    """
    hours = t

    # Cold: rises early, fluctuates with operational cycles.
    cold = 0.15 + 0.65 * logistic(hours, center=6, width=2)
    cold += 0.08 * np.sin(2 * np.pi * hours / 24 + 0.6)

    # Hypoxia-like oxygen limitation: increases after acclimatization challenge.
    hypoxia = 0.10 + 0.55 * logistic(hours, center=18, width=4)
    hypoxia += 0.04 * np.sin(2 * np.pi * hours / 18)

    # Workload: periodic field activity blocks.
    workload = np.zeros_like(hours) + 0.12
    for start, end, amp in [(8, 12, 0.55), (24, 31, 0.70), (47, 54, 0.75), (64, 68, 0.50)]:
        workload += amp * (logistic(hours, start, 0.5) - logistic(hours, end, 0.5))

    # Radiation-associated burden input: low-dose-rate-like normalized stress.
    # Not a clinical dosimetry model. Treat as upstream stress input.
    radiation = 0.05 + 0.18 * logistic(hours, center=10, width=8)
    radiation += 0.04 * (logistic(hours, 42, 2) - logistic(hours, 56, 2))

    # Sleep/circadian disruption: worsens over time, oscillatory.
    sleep = 0.12 + 0.42 * logistic(hours, center=30, width=10)
    sleep += 0.08 * (1 + np.sin(2 * np.pi * hours / 24 - 1.2)) / 2

    data = np.vstack([cold, hypoxia, workload, radiation, sleep]).T
    data = np.clip(data, 0.0, 1.0)
    return pd.DataFrame(data, columns=STRESS_NAMES).assign(time_h=hours)


# -----------------------------
# Real-data adapters
# -----------------------------

def _safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def find_nmdb_file(real_data_root: Path) -> Path | None:
    """Find an NMDB SOPO file, preferring processed CSV over raw TXT."""
    candidates = []
    nmdir = real_data_root / "radiation_proxy" / "nmdb"
    if nmdir.exists():
        candidates.extend(sorted(nmdir.glob("*SOPO*processed*.csv")))
        candidates.extend(sorted(nmdir.glob("nmdb_SOPO*_60min.txt")))
        candidates.extend(sorted(nmdir.glob("*SOPO*.txt")))
    candidates.extend(sorted(real_data_root.rglob("*SOPO*processed*.csv")))
    candidates.extend(sorted(real_data_root.rglob("nmdb_SOPO*_60min.txt")))
    for c in candidates:
        if c.is_file() and c.stat().st_size > 0:
            return c
    return None


def read_nmdb(path: Path) -> pd.DataFrame:
    """
    Read NMDB ASCII or processed CSV.

    Expected raw lines look like:
        2021-01-01 00:00:00;326.479
    The header is intentionally ignored because NMDB ASCII is... adventurous.
    """
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        # Accept common processed column names.
        cols = {c.lower().strip(): c for c in df.columns}
        tcol = cols.get("start_date_time") or cols.get("time") or cols.get("datetime")
        vcol = cols.get("mcorr_e") or cols.get("value")
        if tcol is None or vcol is None:
            raise ValueError(f"Cannot identify timestamp/value columns in {path}")
        out = df[[tcol, vcol]].copy()
        out.columns = ["start_date_time", "MCORR_E"]
    else:
        import re
        rows = []
        text = _safe_read_text(path)
        if "<html" in text.lower() or "<!doctype html" in text.lower():
            raise ValueError(f"NMDB file is HTML, not ASCII data: {path}")
        for line in text.splitlines():
            line = line.strip()
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2};", line):
                timestamp, value = line.split(";", 1)
                rows.append((timestamp, value))
        if not rows:
            raise ValueError(f"No NMDB data rows found in {path}")
        out = pd.DataFrame(rows, columns=["start_date_time", "MCORR_E"])

    out["start_date_time"] = pd.to_datetime(out["start_date_time"], errors="coerce", utc=False)
    out["MCORR_E"] = pd.to_numeric(out["MCORR_E"], errors="coerce")
    out = out.dropna(subset=["start_date_time", "MCORR_E"]).sort_values("start_date_time")
    if out.empty:
        raise ValueError(f"NMDB file had no valid numeric rows: {path}")
    median = out["MCORR_E"].median()
    std = out["MCORR_E"].std(ddof=0)
    std = std if np.isfinite(std) and std > 0 else 1.0
    out["radiation_proxy_rel"] = out["MCORR_E"] / median - 1.0
    out["radiation_proxy_zpos"] = ((out["MCORR_E"] - median) / std).clip(lower=0)
    out["radiation_proxy_positive"] = out["radiation_proxy_rel"].clip(lower=0)
    return out.reset_index(drop=True)


def build_real_radiation_input(real_data_root: Path, t: np.ndarray) -> tuple[np.ndarray, pd.DataFrame, dict]:
    """
    Build normalized model input R(t) from NMDB neutron-monitor data.

    This is an environmental cosmic-ray proxy, not absorbed dose, organ dose,
    equivalent dose, or patient-specific radiation dose-response. Tiny but vital
    difference, because reality refuses to be a PowerPoint shape.
    """
    nmdb_path = find_nmdb_file(real_data_root)
    if nmdb_path is None:
        raise FileNotFoundError(
            "Could not find NMDB SOPO data under real_data/radiation_proxy/nmdb. "
            "Run download_extreme_cv_sources_v4.py --nmdb first."
        )
    nmdb = read_nmdb(nmdb_path)

    # Use elapsed hours in the NMDB record and interpolate/cycle to model duration.
    elapsed_h = (nmdb["start_date_time"] - nmdb["start_date_time"].iloc[0]).dt.total_seconds().to_numpy() / 3600.0
    zpos = nmdb["radiation_proxy_zpos"].to_numpy(dtype=float)

    # If model duration exceeds the real record, tile the record. This is flagged in metadata.
    record_duration = float(elapsed_h[-1] - elapsed_h[0]) if len(elapsed_h) > 1 else 0.0
    if record_duration <= 0:
        interp_z = np.full_like(t, float(np.nanmean(zpos)))
        tiled = False
    elif t[-1] <= elapsed_h[-1]:
        interp_z = np.interp(t, elapsed_h, zpos)
        tiled = False
    else:
        period = elapsed_h[-1] + (elapsed_h[1] - elapsed_h[0] if len(elapsed_h) > 1 else 1.0)
        interp_z = np.interp(np.mod(t, period), elapsed_h, zpos)
        tiled = True

    # Map count-rate anomaly to normalized stress input roughly matching original 0.05-0.35 scale.
    # Cap zpos at 3 SD to avoid one solar-weather spike turning the model into a comic-book laser.
    radiation = 0.05 + 0.30 * np.clip(interp_z / 3.0, 0.0, 1.0)
    radiation = np.clip(radiation, 0.0, 1.0)

    source_meta = {
        "nmdb_file": str(nmdb_path),
        "nmdb_rows": int(len(nmdb)),
        "nmdb_start": str(nmdb["start_date_time"].iloc[0]),
        "nmdb_end": str(nmdb["start_date_time"].iloc[-1]),
        "nmdb_value_column": "MCORR_E",
        "radiation_input_mapping": "R(t)=0.05+0.30*clip(z_positive/3,0,1), z_positive=max(0,(MCORR_E-median)/std)",
        "radiation_interpolation_tiled": bool(tiled),
        "radiation_disclaimer": "NMDB neutron monitor count-rate variation used as environmental cosmic-ray proxy, not individual absorbed dose or organ-specific dose.",
    }
    return radiation, nmdb, source_meta



def find_antaws_file(real_data_root: Path, station: str = "Concordia") -> Path | None:
    """Find an AntAWS 3-hourly CSV for a requested station name."""
    search_roots = [
        real_data_root / "antarctic_environment" / "antaws" / "AntAWS_3_hourly" / "3_hourly",
        real_data_root / "antarctic_environment" / "antaws",
        real_data_root,
    ]
    wanted = f"{station}_3h.csv".lower()
    loose = station.lower().replace("_", " ").replace("-", " ")
    candidates = []
    for root in search_roots:
        if not root.exists():
            continue
        for f in root.rglob("*_3h.csv"):
            name = f.name.lower()
            if name == wanted or station.lower() in name or loose in name.replace("_", " ").replace("-", " "):
                candidates.append(f)
    if candidates:
        # Prefer exact filename match, then largest file.
        candidates = sorted(candidates, key=lambda x: (x.name.lower() != wanted, -x.stat().st_size))
        return candidates[0]
    return None


def read_antaws_3hourly(path: Path) -> pd.DataFrame:
    """
    Read AntAWS 3-hourly CSV robustly.

    Some AntAWS files have a non-UTF8 degree symbol in the temperature column
    header. Use latin1 and rename by position, because headers should not be
    allowed to bully an entire model. Humans invented encodings and then left.
    """
    df = pd.read_csv(path, encoding="latin1", na_values=["NA", "NaN", "", " "])
    if df.shape[1] < 9:
        raise ValueError(f"AntAWS file has fewer columns than expected: {path}")
    # Rename by known AntAWS 3-hourly column positions.
    df = df.iloc[:, :9].copy()
    df.columns = [
        "year", "month", "day", "hour_utc", "temperature_C", "pressure_hPa",
        "wind_speed_m_s", "wind_direction_deg", "relative_humidity_pct"
    ]
    for col in ["year", "month", "day", "hour_utc", "temperature_C", "pressure_hPa", "wind_speed_m_s"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["year", "month", "day", "hour_utc"])
    df["timestamp"] = pd.to_datetime(
        dict(
            year=df["year"].astype(int),
            month=df["month"].astype(int),
            day=df["day"].astype(int),
            hour=df["hour_utc"].astype(int),
        ),
        errors="coerce",
    )
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df


def _wind_chill_celsius(temp_c: np.ndarray, wind_m_s: np.ndarray) -> np.ndarray:
    """Canadian wind chill formula, fallback to air temperature where invalid/missing."""
    temp = np.asarray(temp_c, dtype=float)
    wind = np.asarray(wind_m_s, dtype=float)
    wind_kmh = wind * 3.6
    wc = temp.copy()
    valid = np.isfinite(temp) & np.isfinite(wind_kmh) & (temp <= 10.0) & (wind_kmh > 4.8)
    wc[valid] = 13.12 + 0.6215 * temp[valid] - 11.37 * (wind_kmh[valid] ** 0.16) + 0.3965 * temp[valid] * (wind_kmh[valid] ** 0.16)
    return wc


def _choose_antaws_segment(df: pd.DataFrame, duration_hours: float) -> pd.DataFrame:
    """Choose a recent segment with enough valid temperature data for the model duration."""
    needed_points = max(3, int(np.ceil(duration_hours / 3.0)) + 1)
    valid = df[df["temperature_C"].notna()].copy()
    if len(valid) < 3:
        # Pressure-only stations exist; use rows with pressure as weak fallback.
        valid = df[df[["temperature_C", "pressure_hPa", "wind_speed_m_s"]].notna().any(axis=1)].copy()
    if valid.empty:
        raise ValueError("AntAWS station file has no usable temperature/pressure/wind rows.")
    # Use the latest enough valid rows. This avoids early all-NA station startup years.
    seg = valid.tail(needed_points).copy()
    if len(seg) < needed_points:
        seg = valid.copy()
    seg = seg.sort_values("timestamp").reset_index(drop=True)
    return seg


def build_real_antaws_inputs(real_data_root: Path, t: np.ndarray, station: str = "Concordia") -> tuple[np.ndarray, np.ndarray, pd.DataFrame, dict]:
    """
    Build cold(t) and hypoxia-like pressure proxy from AntAWS 3-hourly weather.

    cold(t) uses wind-chill/air-temperature burden. hypoxia(t) uses station pressure
    as an oxygen-availability proxy, not measured arterial oxygen saturation.
    """
    antaws_path = find_antaws_file(real_data_root, station=station)
    if antaws_path is None:
        raise FileNotFoundError(f"Could not find AntAWS station CSV for station={station!r} under {real_data_root}")
    raw = read_antaws_3hourly(antaws_path)
    seg = _choose_antaws_segment(raw, float(t[-1]))

    # Fill short gaps inside the chosen segment. Keep provenance honest in metadata.
    for col in ["temperature_C", "pressure_hPa", "wind_speed_m_s"]:
        seg[col] = pd.to_numeric(seg[col], errors="coerce")
        seg[col] = seg[col].interpolate(limit_direction="both")

    elapsed_h = (seg["timestamp"] - seg["timestamp"].iloc[0]).dt.total_seconds().to_numpy() / 3600.0
    if len(elapsed_h) < 2 or elapsed_h[-1] <= 0:
        raise ValueError(f"AntAWS segment too short after preprocessing: {antaws_path}")

    temp = seg["temperature_C"].to_numpy(dtype=float)
    wind = seg["wind_speed_m_s"].to_numpy(dtype=float)
    pressure = seg["pressure_hPa"].to_numpy(dtype=float)
    wind_chill = _wind_chill_celsius(temp, wind)

    # If duration exceeds segment, tile. Normally latest 72h segment is enough.
    period = elapsed_h[-1] + np.median(np.diff(elapsed_h))
    t_for_interp = np.mod(t, period) if t[-1] > elapsed_h[-1] else t
    tiled = bool(t[-1] > elapsed_h[-1])

    interp_wc = np.interp(t_for_interp, elapsed_h, wind_chill)
    interp_temp = np.interp(t_for_interp, elapsed_h, temp)
    interp_wind = np.interp(t_for_interp, elapsed_h, wind)
    interp_pressure = np.interp(t_for_interp, elapsed_h, pressure) if np.isfinite(pressure).any() else np.full_like(t, np.nan)

    # Normalized cold burden. 0 around +5C, near 1 around -65C wind chill.
    cold = np.clip((5.0 - interp_wc) / 70.0, 0.0, 1.0)
    # Pressure-derived oxygen limitation proxy. At ~800 hPa mild, ~650 hPa strong plateau limitation.
    if np.isfinite(interp_pressure).any():
        hypoxia = np.clip((800.0 - interp_pressure) / 250.0, 0.0, 1.0)
    else:
        hypoxia = np.zeros_like(t) + 0.10

    processed = pd.DataFrame({
        "timestamp": seg["timestamp"],
        "elapsed_h": elapsed_h,
        "temperature_C": temp,
        "wind_speed_m_s": wind,
        "wind_chill_C": wind_chill,
        "pressure_hPa": pressure,
    })
    meta = {
        "antaws_file": str(antaws_path),
        "station_requested": station,
        "rows_raw": int(len(raw)),
        "rows_segment_used": int(len(seg)),
        "segment_start": str(seg["timestamp"].iloc[0]),
        "segment_end": str(seg["timestamp"].iloc[-1]),
        "temperature_column": "Temperature(degC) / renamed by position from AntAWS header",
        "pressure_column": "Pressure(hPa)",
        "wind_column": "Wind Speed(m/s)",
        "cold_input_mapping": "cold(t)=clip((5 - wind_chill_C)/70,0,1); wind chill falls back to air temperature when invalid",
        "hypoxia_input_mapping": "hypoxia(t)=clip((800 - pressure_hPa)/250,0,1), pressure-derived oxygen-availability proxy, not SpO2",
        "antaws_interpolation_tiled": tiled,
        "antaws_disclaimer": "AntAWS station weather used as environmental forcing. Pressure is a hypoxia-like proxy, not individual oxygen saturation.",
    }
    return cold, hypoxia, processed, meta

def inventory_real_data(real_data_root: Path) -> pd.DataFrame:
    """Make a simple file inventory for downloaded sources."""
    rows = []
    patterns = {
        "nmdb_radiation_proxy": ["radiation_proxy/nmdb/*"],
        "zenodo_bidmc_spo2": ["zenodo/3902688/*"],
        "antaws_environment": ["antarctic_environment/antaws/*", "antarctic_environment/*"],
        "physionet_ephnogram": ["physionet/ephnogram-1.0.0/**/*"],
    }
    for source, pats in patterns.items():
        for pat in pats:
            for p in sorted(real_data_root.glob(pat)):
                if p.is_file():
                    rows.append({"source_layer": source, "path": str(p), "size_bytes": int(p.stat().st_size)})
    return pd.DataFrame(rows)


def build_stress_protocol_from_real_data(
    t: np.ndarray,
    real_data_root: Path,
    antaws_station: str = "Concordia",
) -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame | None]:
    """
    Build the stress protocol using real NMDB radiation proxy and AntAWS station weather.

    Directly fused real-data layers:
      - NMDB SOPO neutron monitor -> radiation(t) environmental cosmic-ray proxy
      - AntAWS 3-hourly station weather -> cold(t), pressure-derived hypoxia proxy(t)

    workload and sleep remain protocol-defined scaffolds because they need human
    activity/sleep data, not station meteorology. Annoying, but honest.
    """
    stress_df = build_stress_protocol(t)

    radiation, nmdb_df, nmdb_meta = build_real_radiation_input(real_data_root, t)
    stress_df["radiation"] = radiation
    # --- IRIS radiation ablation patch at source ---
    try:
        _iris_rad_scale = float(os.environ.get('IRIS_RADIATION_SCALE', '1.0'))
    except Exception:
        _iris_rad_scale = 1.0
    try:
        _iris_rad_shuffle = str(os.environ.get('IRIS_RADIATION_SHUFFLE', '0')).lower() in ('1', 'true', 'yes', 'y')
    except Exception:
        _iris_rad_shuffle = False
    if 'radiation' in stress_df.columns:
        stress_df['radiation'] = stress_df['radiation'] * _iris_rad_scale
        if _iris_rad_shuffle:
            stress_df['radiation'] = stress_df['radiation'].sample(
                frac=1.0, random_state=int(os.environ.get('IRIS_RADIATION_SEED', '42'))
            ).to_numpy()
    # --- end IRIS radiation ablation patch at source ---
    stress_df["radiation_source"] = "NMDB_SOPO_MCORR_E"

    antaws_df = None
    antaws_meta = None
    try:
        cold, hypoxia, antaws_df, antaws_meta = build_real_antaws_inputs(real_data_root, t, station=antaws_station)
        stress_df["cold"] = cold
        stress_df["hypoxia"] = hypoxia
        stress_df["cold_source"] = f"AntAWS_{antaws_station}"
        stress_df["hypoxia_source"] = f"AntAWS_{antaws_station}_pressure_proxy"
    except Exception as exc:
        antaws_meta = {"error": str(exc), "fallback": "cold and hypoxia retained from synthetic protocol scaffold"}
        stress_df["cold_source"] = "synthetic_protocol_fallback"
        stress_df["hypoxia_source"] = "synthetic_protocol_fallback"

    inv = inventory_real_data(real_data_root)
    used = ["NMDB SOPO neutron-monitor count rate -> radiation stress proxy"]
    if antaws_df is not None:
        used.extend([
            f"AntAWS {antaws_station} 3-hourly temperature/wind -> cold stress",
            f"AntAWS {antaws_station} 3-hourly pressure -> hypoxia-like oxygen limitation proxy",
        ])
    usage = {
        "real_data_root": str(real_data_root),
        "used_directly": used,
        "detected_sources": sorted(inv["source_layer"].unique().tolist()) if not inv.empty else [],
        "not_yet_fused": (
            "BIDMC SpO2 and EPHNOGRAM can be detected in inventory but are not yet fused in this version. "
            "Workload and sleep remain protocol scaffolds. AntAWS and NMDB are fused directly when available."
        ),
        "nmdb": nmdb_meta,
        "antaws": antaws_meta,
    }
    return stress_df, usage, nmdb_df, antaws_df


def interaction_terms(x: np.ndarray) -> np.ndarray:
    """Pairwise stress interactions X_i * X_k for i < k."""
    pairs = []
    for i in range(x.shape[-1]):
        for k in range(i + 1, x.shape[-1]):
            pairs.append(x[..., i] * x[..., k])
    return np.stack(pairs, axis=-1)


INTERACTION_PAIR_NAMES = [
    f"{STRESS_NAMES[i]}_x_{STRESS_NAMES[k]}"
    for i in range(len(STRESS_NAMES))
    for k in range(i + 1, len(STRESS_NAMES))
]


# -----------------------------
# Population generation
# -----------------------------

def make_positive_normal(rng: np.random.Generator, mean: float, sd: float, size) -> np.ndarray:
    """Normal values clipped to positive range."""
    return np.clip(rng.normal(mean, sd, size=size), 1e-6, None)


def generate_system_parameters(config: SimulationConfig) -> List[SystemParameters]:
    """
    Generate baseline-healthy systems.

    All systems have matched resting reserve proxies but different latent
    sensitivities and recovery rates. Classes are labels for parameter generation,
    not labels used by the classifier during collapse detection.
    """
    rng = np.random.default_rng(config.seed)
    classes = [
        "pump_limited",
        "vascular_limited",
        "oxygen_delivery_limited",
        "electrophysiology_limited",
        "mito_endothelial_limited",
        "balanced_resilient",
    ]

    systems: List[SystemParameters] = []
    for sid in range(config.n_systems):
        latent_class = classes[sid % len(classes)]

        # Baseline resting equivalence: reserve close to 1 across systems.
        baseline_reserve = np.clip(rng.normal(1.0, 0.025, size=5), 0.92, 1.06)

        # Direct stress sensitivity A[j, i]
        A = make_positive_normal(rng, 0.030, 0.008, size=(5, 5))

        # Physiologically plausible stronger links.
        # rows: reserve dimensions, cols: cold, hypoxia, workload, radiation, sleep
        A[0, 2] += 0.035  # pump affected by workload
        A[0, 1] += 0.020  # pump affected by hypoxia
        A[1, 0] += 0.035  # vascular/autonomic affected by cold
        A[1, 4] += 0.018  # autonomic affected by sleep/circadian disruption
        A[2, 1] += 0.055  # oxygen delivery affected by hypoxia
        A[2, 2] += 0.025  # oxygen delivery affected by workload
        A[3, 1] += 0.022  # electrophysiology affected by hypoxia
        A[3, 4] += 0.024  # electrophysiology affected by sleep disruption
        A[4, 3] += 0.050  # mito/endothelial affected by radiation-associated burden
        A[4, 1] += 0.020  # mito/endothelial affected by hypoxia

        # Interaction sensitivity B[j, pair]
        B = make_positive_normal(rng, 0.010, 0.004, size=(5, len(INTERACTION_PAIR_NAMES)))
        pair_idx = {name: idx for idx, name in enumerate(INTERACTION_PAIR_NAMES)}
        B[:, pair_idx["cold_x_hypoxia"]] += 0.006
        B[:, pair_idx["hypoxia_x_workload"]] += 0.015
        B[4, pair_idx["hypoxia_x_radiation"]] += 0.020
        B[4, pair_idx["workload_x_radiation"]] += 0.015
        B[3, pair_idx["hypoxia_x_sleep"]] += 0.012

        # Recovery rate toward baseline reserve.
        k_rec = make_positive_normal(rng, 0.060, 0.012, size=5)

        # Introduce latent constraints while preserving resting equivalence.
        if latent_class == "pump_limited":
            A[0, :] *= rng.uniform(1.55, 1.95)
            B[0, :] *= rng.uniform(1.40, 1.80)
            k_rec[0] *= rng.uniform(0.40, 0.65)
        elif latent_class == "vascular_limited":
            A[1, :] *= rng.uniform(1.55, 1.95)
            B[1, :] *= rng.uniform(1.35, 1.75)
            k_rec[1] *= rng.uniform(0.40, 0.65)
        elif latent_class == "oxygen_delivery_limited":
            A[2, :] *= rng.uniform(1.60, 2.05)
            B[2, :] *= rng.uniform(1.40, 1.85)
            k_rec[2] *= rng.uniform(0.38, 0.62)
        elif latent_class == "electrophysiology_limited":
            A[3, :] *= rng.uniform(1.50, 1.95)
            B[3, :] *= rng.uniform(1.45, 1.90)
            k_rec[3] *= rng.uniform(0.40, 0.65)
        elif latent_class == "mito_endothelial_limited":
            A[4, :] *= rng.uniform(1.60, 2.15)
            B[4, :] *= rng.uniform(1.55, 2.10)
            k_rec[4] *= rng.uniform(0.35, 0.60)
        else:  # balanced_resilient
            A *= rng.uniform(0.72, 0.88)
            B *= rng.uniform(0.68, 0.85)
            k_rec *= rng.uniform(1.15, 1.35)

        # Global calibration for normalized stress inputs. Without this, a normalized
        # toy stressor becomes an absurd death laser, because decimals are treacherous.
        A *= 0.045
        B *= 0.030

        observation_noise_base = float(rng.uniform(0.010, 0.025))
        observation_noise_sensitivity = rng.uniform(0.015, 0.060, size=3)  # cold, workload, sleep
        compensation_gain = rng.uniform(0.0005, 0.0040, size=5)

        systems.append(SystemParameters(
            system_id=sid,
            latent_class=latent_class,
            baseline_reserve=baseline_reserve,
            direct_sensitivity=A,
            interaction_sensitivity=B,
            recovery_rate=k_rec,
            observation_noise_base=observation_noise_base,
            observation_noise_sensitivity=observation_noise_sensitivity,
            compensation_gain=compensation_gain,
        ))
    return systems


# -----------------------------
# Dynamics and observability
# -----------------------------

def reserve_derivative(
    R: np.ndarray,
    x: np.ndarray,
    params: SystemParameters,
) -> np.ndarray:
    """
    dR_j/dt = -sum_i a_ji X_i - sum_i<k b_jik X_iX_k + k_rec_j(R0_j - R_j) + compensation

    R and R0 are normalized reserve units. Stressors are normalized.
    Time unit is hours.
    """
    direct_depletion = params.direct_sensitivity @ x
    interactions = interaction_terms(x.reshape(1, -1))[0]
    interaction_depletion = params.interaction_sensitivity @ interactions

    recovery = params.recovery_rate * (params.baseline_reserve - R)

    # Simple compensation: when one reserve drops, other dimensions may carry a small burden.
    # This is deliberately conservative to avoid turning the model into fantasy hydraulics.
    relative_reserve = R / np.maximum(params.baseline_reserve, 1e-9)
    global_strain = max(0.0, 1.0 - float(np.min(relative_reserve)))
    compensation_cost = params.compensation_gain * global_strain

    dRdt = -direct_depletion - interaction_depletion + recovery - compensation_cost
    return dRdt


def rk4_step(R: np.ndarray, x: np.ndarray, dt: float, params: SystemParameters) -> np.ndarray:
    """Fourth-order Runge-Kutta step with stress treated as piecewise constant."""
    k1 = reserve_derivative(R, x, params)
    k2 = reserve_derivative(R + 0.5 * dt * k1, x, params)
    k3 = reserve_derivative(R + 0.5 * dt * k2, x, params)
    k4 = reserve_derivative(R + dt * k3, x, params)
    R_next = R + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
    return np.clip(R_next, 0.0, 1.20)



def euler_step(R: np.ndarray, x: np.ndarray, dt: float, params: SystemParameters) -> np.ndarray:
    """Explicit Euler step. Fast and stable here because dt is small and dynamics are smooth."""
    R_next = R + dt * reserve_derivative(R, x, params)
    return np.clip(R_next, 0.0, 1.20)

def observe_reserve_margin(
    true_R: np.ndarray,
    stress_df: pd.DataFrame,
    params: SystemParameters,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Observed reserve margin y(t)=min(R(t))+noise, with environment-dependent noise.

    Measurement degradation Q is represented through cold, workload and sleep stress.
    """
    true_margin = np.min(true_R, axis=1)
    cold = stress_df["cold"].to_numpy()
    workload = stress_df["workload"].to_numpy()
    sleep = stress_df["sleep"].to_numpy()
    q = params.observation_noise_sensitivity
    sigma = params.observation_noise_base + q[0]*cold + q[1]*workload + q[2]*sleep
    observed = true_margin + rng.normal(0.0, sigma, size=true_margin.shape)
    return np.clip(observed, 0.0, 1.2), sigma


def simulate_one_system(
    params: SystemParameters,
    stress_df: pd.DataFrame,
    dt: float,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Simulate one system and return time series."""
    x_values = stress_df[STRESS_NAMES].to_numpy()
    n_steps = len(stress_df)
    R = np.zeros((n_steps, len(RESERVE_NAMES)))
    R[0] = params.baseline_reserve.copy()

    for idx in range(1, n_steps):
        R[idx] = euler_step(R[idx - 1], x_values[idx - 1], dt, params)

    observed_margin, sigma = observe_reserve_margin(R, stress_df, params, rng)
    out = pd.DataFrame(R, columns=[f"reserve_{name}" for name in RESERVE_NAMES])
    out.insert(0, "time_h", stress_df["time_h"].to_numpy())
    out["system_id"] = params.system_id
    out["latent_class"] = params.latent_class
    out["true_reserve_margin"] = np.min(R, axis=1)
    out["limiting_axis"] = [RESERVE_NAMES[int(i)] for i in np.argmin(R, axis=1)]
    out["observed_reserve_margin"] = observed_margin
    out["observation_sigma"] = sigma
    return out


# -----------------------------
# Verification and summaries
# -----------------------------

def run_internal_checks(config: SimulationConfig, stress_df: pd.DataFrame, systems: List[SystemParameters]) -> None:
    """
    Lightweight verification checks.

    These are not validation against external data. They detect broken equations,
    impossible signs, unstable outputs, and baseline equivalence failures.
    """
    assert config.n_systems > 0, "n_systems must be positive"
    assert config.dt_hours > 0, "dt_hours must be positive"
    assert set(STRESS_NAMES).issubset(stress_df.columns), "stress protocol missing stress columns"
    assert np.all(stress_df[STRESS_NAMES].to_numpy() >= 0), "stressors must be non-negative"
    assert np.all(stress_df[STRESS_NAMES].to_numpy() <= 1), "stressors must be normalized <= 1"

    baselines = np.vstack([p.baseline_reserve for p in systems])
    baseline_span = baselines.max(axis=0) - baselines.min(axis=0)
    if np.any(baseline_span > 0.18):
        raise AssertionError("baseline equivalence too loose; check baseline generation")

    for p in systems[: min(10, len(systems))]:
        assert p.direct_sensitivity.shape == (len(RESERVE_NAMES), len(STRESS_NAMES))
        assert p.interaction_sensitivity.shape == (len(RESERVE_NAMES), len(INTERACTION_PAIR_NAMES))
        assert p.recovery_rate.shape == (len(RESERVE_NAMES),)
        assert np.all(p.direct_sensitivity >= 0), "direct sensitivities must be non-negative"
        assert np.all(p.interaction_sensitivity >= 0), "interaction sensitivities must be non-negative"
        assert np.all(p.recovery_rate > 0), "recovery rates must be positive"

    # Zero-stress sanity check: system should remain near baseline.
    p0 = systems[0]
    R = p0.baseline_reserve.copy()
    zero_x = np.zeros(len(STRESS_NAMES))
    for _ in range(100):
        R = euler_step(R, zero_x, config.dt_hours, p0)
    if not np.allclose(R, p0.baseline_reserve, atol=1e-4):
        raise AssertionError("zero-stress reserve should remain at baseline")


def summarize_system(ts: pd.DataFrame, config: SimulationConfig) -> Dict[str, object]:
    """Summarize one system's trajectory."""
    min_idx = int(ts["true_reserve_margin"].idxmin())
    min_row = ts.loc[min_idx]
    final_row = ts.iloc[-1]

    below = ts[ts["true_reserve_margin"] < config.critical_reserve]
    collapse_time = float(below["time_h"].iloc[0]) if len(below) else math.nan

    # Recovery slope over final 12 hours.
    tail = ts[ts["time_h"] >= ts["time_h"].max() - 12]
    if len(tail) >= 3:
        recovery_slope = float(np.polyfit(tail["time_h"], tail["true_reserve_margin"], 1)[0])
    else:
        recovery_slope = math.nan

    # False stability: true margin drops materially while observed slope is almost flat.
    early = ts[ts["time_h"] <= 6]["true_reserve_margin"].mean()
    late = ts[ts["time_h"] >= ts["time_h"].max() - 6]
    true_drop = float(early - late["true_reserve_margin"].mean())
    observed_slope = float(np.polyfit(late["time_h"], late["observed_reserve_margin"], 1)[0]) if len(late) >= 3 else math.nan
    false_stability = bool(
        true_drop >= config.false_stability_drop and
        abs(observed_slope) <= config.false_stability_observed_slope_abs and
        late["observation_sigma"].mean() > ts["observation_sigma"].quantile(0.60)
    )

    return {
        "system_id": int(ts["system_id"].iloc[0]),
        "latent_class": str(ts["latent_class"].iloc[0]),
        "min_true_reserve_margin": float(ts["true_reserve_margin"].min()),
        "time_of_min_margin_h": float(min_row["time_h"]),
        "limiting_axis_at_min": str(min_row["limiting_axis"]),
        "final_true_reserve_margin": float(final_row["true_reserve_margin"]),
        "final_observed_reserve_margin": float(final_row["observed_reserve_margin"]),
        "collapse_time_h": collapse_time,
        "recovery_slope_final_12h": recovery_slope,
        "true_drop_from_early_to_late": true_drop,
        "observed_slope_final_6h": observed_slope,
        "mean_observation_sigma": float(ts["observation_sigma"].mean()),
        "false_stability_flag": false_stability,
    }


def build_parameter_table(systems: List[SystemParameters]) -> pd.DataFrame:
    """Parameter provenance-like table for generated in silico population."""
    rows = []
    for p in systems:
        row = {
            "system_id": p.system_id,
            "latent_class": p.latent_class,
            "observation_noise_base": p.observation_noise_base,
        }
        for j, name in enumerate(RESERVE_NAMES):
            row[f"baseline_{name}"] = p.baseline_reserve[j]
            row[f"recovery_{name}"] = p.recovery_rate[j]
        for j, rname in enumerate(RESERVE_NAMES):
            for i, sname in enumerate(STRESS_NAMES):
                row[f"A_{rname}_by_{sname}"] = p.direct_sensitivity[j, i]
        rows.append(row)
    return pd.DataFrame(rows)


# -----------------------------
# Plotting
# -----------------------------

def plot_reserve_margin(sample_ts: pd.DataFrame, out_dir: Path) -> None:
    """Plot true reserve margin for sample systems."""
    plt.figure(figsize=(10, 6))
    for sid, grp in sample_ts.groupby("system_id"):
        plt.plot(grp["time_h"], grp["true_reserve_margin"], linewidth=1, alpha=0.75)
    plt.xlabel("Time (hours)")
    plt.ylabel("True reserve margin")
    plt.title("Sample reserve-margin trajectories")
    plt.tight_layout()
    plt.savefig(out_dir / "reserve_margin_plot.png", dpi=180)
    plt.close()


def plot_class_trajectories(all_ts: pd.DataFrame, out_dir: Path) -> None:
    """Plot class-level mean true reserve margin."""
    class_mean = (
        all_ts.groupby(["time_h", "latent_class"], as_index=False)["true_reserve_margin"]
        .mean()
    )
    plt.figure(figsize=(10, 6))
    for cls, grp in class_mean.groupby("latent_class"):
        plt.plot(grp["time_h"], grp["true_reserve_margin"], label=cls, linewidth=2)
    plt.xlabel("Time (hours)")
    plt.ylabel("Mean true reserve margin")
    plt.title("Hidden reserve classes separate under coupled stress")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "class_trajectories_plot.png", dpi=180)
    plt.close()


# -----------------------------
# Main pipeline
# -----------------------------

def run_pipeline(config: SimulationConfig, out_dir: Path, real_data_root: Path | None = None, antaws_station: str = "Concordia") -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(config.seed + 10_000)

    t = np.arange(0.0, config.duration_hours + config.dt_hours, config.dt_hours)

    real_data_usage = None
    nmdb_df = None
    antaws_df = None
    if real_data_root is not None:
        stress_df, real_data_usage, nmdb_df, antaws_df = build_stress_protocol_from_real_data(t, real_data_root, antaws_station=antaws_station)
    else:
        stress_df = build_stress_protocol(t)

    systems = generate_system_parameters(config)
    # Only numeric stress columns are checked; radiation_source is metadata.
    run_internal_checks(config, stress_df[STRESS_NAMES + ["time_h"]], systems)

    all_series: List[pd.DataFrame] = []
    summaries: List[Dict[str, object]] = []

    for p in systems:
        ts = simulate_one_system(p, stress_df, config.dt_hours, rng)
        all_series.append(ts)
        summaries.append(summarize_system(ts, config))

    all_ts = pd.concat(all_series, ignore_index=True)
    summary_df = pd.DataFrame(summaries)
    parameter_df = build_parameter_table(systems)

    class_counts = (
        summary_df.groupby(["latent_class", "limiting_axis_at_min"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["latent_class", "count"], ascending=[True, False])
    )

    false_stability_cases = summary_df[summary_df["false_stability_flag"]].copy()

    # Save outputs.

    
    stress_df.to_csv(out_dir / "stress_protocol.csv", index=False)
    summary_df.to_csv(out_dir / "population_summary.csv", index=False)
    parameter_df.to_csv(out_dir / "generated_parameters.csv", index=False)
    class_counts.to_csv(out_dir / "class_counts.csv", index=False)
    false_stability_cases.to_csv(out_dir / "false_stability_cases.csv", index=False)

    if nmdb_df is not None:
        nmdb_df.to_csv(out_dir / "nmdb_SOPO_processed_for_model.csv", index=False)
    if antaws_df is not None:
        antaws_df.to_csv(out_dir / "antaws_processed_for_model.csv", index=False)
    if real_data_root is not None:
        inv = inventory_real_data(real_data_root)
        inv.to_csv(out_dir / "real_data_inventory.csv", index=False)

    sample_ids = sorted(summary_df["system_id"].unique()[: config.sample_systems_to_save])
    sample_ts = all_ts[all_ts["system_id"].isin(sample_ids)].copy()
    sample_ts.to_csv(out_dir / "time_series_sample.csv", index=False)
    all_ts.to_csv(out_dir / "time_series_full.csv.gz", index=False, compression="gzip")

    plot_reserve_margin(sample_ts, out_dir)
    plot_class_trajectories(all_ts, out_dir)

    metadata = {
        "config": asdict(config),
        "reserve_names": RESERVE_NAMES,
        "stress_names": STRESS_NAMES,
        "interaction_pair_names": INTERACTION_PAIR_NAMES,
        "real_data_usage": real_data_usage,
        "disclaimer": (
            "Hypothesis-generating mechanistic in silico model; not clinical diagnosis, "
            "not patient-specific prediction, not radiation dose-response estimation. "
            "When --real-data is used, NMDB neutron monitor data are used as an environmental "
            "cosmic-ray proxy, not as individual absorbed dose."
        ),
        "key_equation": "dR_j/dt = -sum_i a_ji X_i - sum_i<k b_jik X_iX_k + k_rec_j(R0_j - R_j)",
        "reserve_margin": "RM(t)=min(PR, VAR, ODR, EPR, MET)",
    }
    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return {
        "n_systems": config.n_systems,
        "n_false_stability_cases": int(false_stability_cases.shape[0]),
        "min_margin_overall": float(summary_df["min_true_reserve_margin"].min()),
        "median_min_margin": float(summary_df["min_true_reserve_margin"].median()),
        "real_data_used": bool(real_data_root is not None),
        "direct_real_data_layer": "NMDB SOPO radiation proxy + AntAWS cold/pressure proxy" if real_data_root is not None else None,
        "outputs": [str(p.name) for p in sorted(out_dir.iterdir())],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Antarctic hidden cardiovascular reserve simulation with optional real NMDB radiation proxy."
    )
    parser.add_argument("--out", type=str, default="results_real", help="Output directory")
    parser.add_argument("--real-data", type=str, default=None, help="Path to downloaded real_data folder")
    parser.add_argument("--n", type=int, default=600, help="Number of in silico systems")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--radiation-scale", type=float, default=1.0)
    parser.add_argument("--radiation-shuffle", action="store_true")
    parser.add_argument("--duration", type=float, default=72.0, help="Duration in hours")
    parser.add_argument("--dt", type=float, default=0.05, help="Time step in hours")
    parser.add_argument("--critical-reserve", type=float, default=0.22, help="Reserve collapse threshold")
    parser.add_argument("--antaws-station", type=str, default="Concordia", help="AntAWS station CSV to use, e.g. Concordia, Dome C, Dome_A")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SimulationConfig(
        n_systems=args.n,
        seed=args.seed,
        duration_hours=args.duration,
        dt_hours=args.dt,
        critical_reserve=args.critical_reserve,
    )
    out_dir = Path(args.out)
    real_data_root = Path(args.real_data) if args.real_data else None
    if real_data_root is not None and not real_data_root.exists():
        raise FileNotFoundError(f"--real-data path does not exist: {real_data_root}")
    result = run_pipeline(config, out_dir, real_data_root=real_data_root, antaws_station=args.antaws_station)
    print("\nSimulation completed. Humanity survives another CSV folder, now with real radiation and Antarctic weather forcing.\n")
    print(json.dumps(result, indent=2))
    print(f"\nOutputs saved to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
