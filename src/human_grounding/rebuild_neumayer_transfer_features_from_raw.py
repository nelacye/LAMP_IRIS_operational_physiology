#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild Neumayer transfer features from raw HRV text/table.

Finds raw Neumayer/Neymayer HRV file under real_data by default, reads UTF-16/CSV/TSV,
normalizes columns, and outputs:

  antarctic_human_transfer_v2/tables/neumayer_transfer_features.csv

Expected output columns:
  subject_id / id
  sex
  hr_0..hr_9
  log_hf_0..log_hf_9
  lfnu_0..lfnu_9
  hfnu_0..hfnu_9
  log_lfhf_0..log_lfhf_9
  log_lf_0..log_lf_9

Run:
  py .\rebuild_neumayer_transfer_features_from_raw.py --real-data .\real_data --out .\antarctic_human_transfer_v2

Then:
  dir .\antarctic_human_transfer_v2\tables\neumayer_transfer_features.csv
  Get-Content .\antarctic_human_transfer_v2\tables\neumayer_transfer_features.csv -TotalCount 5
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--real-data", default="real_data")
    p.add_argument("--raw-file", default=None)
    p.add_argument("--out", required=True)
    return p.parse_args()


def sniff_encoding(path: Path):
    b = path.read_bytes()[:8]
    if b.startswith(b"\xff\xfe") or b.startswith(b"\xfe\xff"):
        return "utf-16"
    if b.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    return "utf-8"


def find_raw(root: Path):
    candidates = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        name = p.name.lower()
        if any(x in name for x in ["neumayer", "neymayer", "hrv_data", "antarctic station"]):
            if p.suffix.lower() in [".txt", ".csv", ".tsv", ".dat"]:
                candidates.append(p)
    if not candidates:
        # broader search
        for p in root.rglob("*HRV*"):
            if p.is_file() and p.suffix.lower() in [".txt", ".csv", ".tsv", ".dat"]:
                candidates.append(p)
    if not candidates:
        raise FileNotFoundError("No raw Neumayer/Neymayer HRV file found under real_data.")
    return sorted(candidates, key=lambda x: x.stat().st_size, reverse=True)[0]


def read_table(path: Path):
    enc = sniff_encoding(path)
    attempts = []
    for sep in [None, "\t", ";", ",", r"\s+"]:
        try:
            df = pd.read_csv(path, sep=sep, engine="python", encoding=enc)
            if df.shape[1] >= 5 and df.shape[0] >= 5:
                return df, enc, sep
            attempts.append((str(sep), df.shape))
        except Exception as e:
            attempts.append((str(sep), repr(e)))
    raise RuntimeError(f"Could not parse {path}. Attempts: {attempts}")


def norm_col(c):
    c = str(c).strip().replace("\ufeff", "")
    c = c.replace(" ", "_").replace("-", "_").replace("/", "_")
    c = re.sub(r"[^A-Za-z0-9_]+", "_", c)
    c = re.sub(r"_+", "_", c).strip("_").lower()
    return c


def normalize_columns(df):
    out = df.copy()
    out.columns = [norm_col(c) for c in out.columns]
    return out


def detect_wide_hrv(df):
    cols = list(df.columns)
    # Already in expected feature format
    required_prefixes = ["hr_", "log_hf_", "lfnu_", "hfnu_", "log_lfhf_", "log_lf_"]
    n_hits = sum(any(c.startswith(pref) for c in cols) for pref in required_prefixes)
    return n_hits >= 3


def rename_known_patterns(df):
    out = df.copy()
    rename = {}
    for c in out.columns:
        cc = c.lower()
        # subject/id
        if cc in ["subject", "subject_id", "id", "participant", "participant_id", "case", "no"]:
            rename[c] = "subject_id"
        elif cc in ["gender", "sex"]:
            rename[c] = "sex"
    out = out.rename(columns=rename)
    return out


def try_convert_wide(df):
    """
    Handles common Neumayer HRV exported columns after normalization:
    HR_0, Log_HF_0, LFnu_0 etc become hr_0, log_hf_0...
    If data are already normalized, this is mostly no-op.
    """
    df = normalize_columns(df)
    df = rename_known_patterns(df)

    colmap = {}
    for c in df.columns:
        cc = c.lower()
        cc = cc.replace("loghf", "log_hf")
        cc = cc.replace("loglfhf", "log_lfhf")
        cc = cc.replace("loglf", "log_lf")
        cc = cc.replace("lf_hf", "lfhf")
        cc = cc.replace("log_lf_hf", "log_lfhf")
        cc = cc.replace("lfnu", "lfnu")
        cc = cc.replace("hfnu", "hfnu")

        # Convert variants like hr0 -> hr_0, hr_1 already okay.
        m = re.match(r"^(hr|log_hf|lfnu|hfnu|log_lfhf|log_lf)_?(\d+)$", cc)
        if m:
            colmap[c] = f"{m.group(1)}_{int(m.group(2))}"
            continue

        # Variants like mean_hr_0 from previous outputs
        m = re.match(r"^mean_(hr|log_hf|lfnu|hfnu|log_lfhf|log_lf)_?(\d+)$", cc)
        if m:
            colmap[c] = f"{m.group(1)}_{int(m.group(2))}"

    df = df.rename(columns=colmap)

    if "subject_id" not in df.columns:
        if "id" in df.columns:
            df = df.rename(columns={"id": "subject_id"})
        else:
            df.insert(0, "subject_id", range(1, len(df) + 1))

    # Keep relevant columns
    keep = ["subject_id"]
    if "sex" in df.columns:
        keep.append("sex")

    for prefix in ["hr", "log_hf", "lfnu", "hfnu", "log_lfhf", "log_lf"]:
        for t in range(0, 20):
            c = f"{prefix}_{t}"
            if c in df.columns:
                keep.append(c)

    out = df[keep].copy()

    # Coerce numeric except subject_id
    for c in out.columns:
        if c != "subject_id":
            out[c] = pd.to_numeric(out[c], errors="coerce")

    return out


def main():
    args = parse_args()
    raw = Path(args.raw_file) if args.raw_file else find_raw(Path(args.real_data))
    df, enc, sep = read_table(raw)
    features = try_convert_wide(df)

    # Sanity
    hrv_cols = [c for c in features.columns if re.match(r"^(hr|log_hf|lfnu|hfnu|log_lfhf|log_lf)_\d+$", c)]
    if len(hrv_cols) < 10:
        raise RuntimeError(
            f"Parsed too few HRV feature columns ({len(hrv_cols)}). Raw columns: {list(normalize_columns(df).columns)[:80]}"
        )

    out = Path(args.out)
    tables = out / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    out_csv = tables / "neumayer_transfer_features.csv"
    features.to_csv(out_csv, index=False)

    diag = {
        "raw_file": str(raw),
        "encoding": enc,
        "sep": str(sep),
        "raw_shape": list(df.shape),
        "features_shape": list(features.shape),
        "hrv_feature_columns": len(hrv_cols),
        "output_csv": str(out_csv),
        "columns": list(features.columns),
    }
    (tables / "neumayer_rebuild_diagnostics.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")

    print(json.dumps(diag, indent=2))


if __name__ == "__main__":
    main()
