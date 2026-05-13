#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone EPHNOGRAM WFDB extractor for IRIS grounding.

Why this exists:
The full grounding pipeline can hide the actual wfdb/import/read error.
This script does only one thing: read EPHNOGRAM WFDB records and extract ECG/PCG
segment-level signal-quality features.

Run:
  py .\iris_ephnogram_wfdb_extractor.py --eph-root .\real_data\physionet\ephnogram-1.0.0 --out .\human_grounding_eph_only --max-records 5 --seconds 60

Then:
  Import-Csv .\human_grounding_eph_only\ephnogram_wfdb_features.csv | Format-Table -AutoSize
  Get-Content .\human_grounding_eph_only\ephnogram_wfdb_diagnostics.json -TotalCount 120
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--eph-root", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-records", type=int, default=5)
    p.add_argument("--seconds", type=float, default=60.0)
    return p.parse_args()


def qnum(x):
    x = np.asarray(x, dtype=float)
    finite = np.isfinite(x)
    if len(x) == 0:
        return {"n": 0, "median": math.nan, "iqr": math.nan, "missing_rate": math.nan}
    if finite.sum() < 5:
        return {"n": int(finite.sum()), "median": math.nan, "iqr": math.nan, "missing_rate": float(1 - finite.mean())}
    xf = x[finite]
    return {
        "n": int(finite.sum()),
        "median": float(np.median(xf)),
        "iqr": float(np.quantile(xf, 0.75) - np.quantile(xf, 0.25)),
        "q05": float(np.quantile(xf, 0.05)),
        "q95": float(np.quantile(xf, 0.95)),
        "missing_rate": float(1 - finite.mean()),
    }


def load_activity_map(eph_root: Path):
    activity = {}
    sheet_path = None
    for p in eph_root.rglob("ECGPCGSpreadsheet.csv"):
        sheet_path = p
        break
    if sheet_path is None:
        return activity, None

    def infer(row):
        text = " ".join(str(v).lower() for v in row.values)
        if "run" in text:
            return "running"
        if "bike" in text or "bicycle" in text or "cycling" in text:
            return "biking"
        if "walk" in text:
            return "walking"
        if "rest" in text or "supine" in text or "sitting" in text:
            return "rest"
        return "unknown"

    for enc in ["utf-8", "latin1", "cp1252"]:
        try:
            df = pd.read_csv(sheet_path, encoding=enc, engine="python")
            for _, row in df.iterrows():
                rec = None
                for v in row.values:
                    m = re.search(r"ECGPCG\d{4}", str(v))
                    if m:
                        rec = m.group(0)
                        break
                if rec:
                    activity[rec] = infer(row)
            return activity, str(sheet_path)
        except Exception:
            pass
    return activity, str(sheet_path)


def main():
    args = parse_args()
    eph_root = Path(args.eph_root).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    diagnostics = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "eph_root": str(eph_root),
        "eph_root_exists": eph_root.exists(),
        "sys_path_head": sys.path[:5],
    }

    try:
        import wfdb
        diagnostics["wfdb_import_ok"] = True
        diagnostics["wfdb_version"] = getattr(wfdb, "__version__", "unknown")
    except Exception as e:
        diagnostics["wfdb_import_ok"] = False
        diagnostics["wfdb_import_error"] = repr(e)
        diagnostics["wfdb_import_traceback"] = traceback.format_exc()
        (out / "ephnogram_wfdb_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
        print(json.dumps(diagnostics, indent=2))
        sys.exit(2)

    heas = sorted(eph_root.rglob("*.hea"))
    diagnostics["hea_count"] = len(heas)
    diagnostics["first_hea_files"] = [str(p) for p in heas[:10]]

    activity, sheet_path = load_activity_map(eph_root)
    diagnostics["spreadsheet_path"] = sheet_path
    diagnostics["activity_labels_count"] = len(activity)

    rows = []
    for hp in heas[:args.max_records]:
        rec_path = hp.with_suffix("")
        rec = hp.stem
        row = {
            "source": "EPHNOGRAM",
            "record": rec,
            "hea_path": str(hp),
            "activity_label_inferred": activity.get(rec, "unknown"),
            "wfdb_read": False,
        }
        try:
            header = wfdb.rdheader(str(rec_path))
            fs = float(header.fs)
            sig_len = int(header.sig_len) if header.sig_len is not None else 0
            sampto = int(min(sig_len, max(1, int(fs * args.seconds)))) if sig_len else int(max(1, fs * args.seconds))
            rd = wfdb.rdrecord(str(rec_path), sampfrom=0, sampto=sampto, physical=True)
            sig = np.asarray(rd.p_signal, dtype=float)
            if sig.ndim == 1:
                sig = sig.reshape(-1, 1)
            ecg = sig[:, 0] if sig.shape[1] >= 1 else np.array([])
            pcg = sig[:, 1] if sig.shape[1] >= 2 else np.array([])
            eq = qnum(ecg)
            pq = qnum(pcg)
            row.update({
                "wfdb_read": True,
                "feature_source": "wfdb_segment",
                "fs_hz": fs,
                "segment_seconds": float(len(sig) / fs) if fs else math.nan,
                "full_signal_seconds": float(sig_len / fs) if fs and sig_len else math.nan,
                "n_channels": int(sig.shape[1]),
                "sig_names": ",".join(getattr(rd, "sig_name", []) or []),
                "ecg_n": eq.get("n"),
                "ecg_median": eq.get("median"),
                "ecg_iqr": eq.get("iqr"),
                "ecg_q05": eq.get("q05"),
                "ecg_q95": eq.get("q95"),
                "ecg_missing_rate": eq.get("missing_rate"),
                "pcg_n": pq.get("n"),
                "pcg_median": pq.get("median"),
                "pcg_iqr": pq.get("iqr"),
                "pcg_q05": pq.get("q05"),
                "pcg_q95": pq.get("q95"),
                "pcg_missing_rate": pq.get("missing_rate"),
                "error": "",
            })
        except Exception as e:
            row.update({
                "wfdb_read": False,
                "feature_source": "wfdb_read_error",
                "error": repr(e),
                "traceback": traceback.format_exc(),
            })
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(out / "ephnogram_wfdb_features.csv", index=False)

    ok = df[df["wfdb_read"].astype(str).str.lower().isin(["true", "1"])] if "wfdb_read" in df.columns else pd.DataFrame()
    priors = {
        "electrophysiology_workload": {
            "grounded": not ok.empty,
            "activity_labels_available": bool(activity),
            "records_read": int(len(ok)),
            "ecg_signal_quality": None,
            "pcg_signal_quality": None,
        }
    }
    if not ok.empty:
        priors["electrophysiology_workload"]["ecg_signal_quality"] = {
            "median_segment_seconds": float(pd.to_numeric(ok["segment_seconds"], errors="coerce").median()),
            "median_ecg_iqr": float(pd.to_numeric(ok["ecg_iqr"], errors="coerce").median()),
            "median_ecg_missing_rate": float(pd.to_numeric(ok["ecg_missing_rate"], errors="coerce").median()),
        }
        priors["electrophysiology_workload"]["pcg_signal_quality"] = {
            "median_pcg_iqr": float(pd.to_numeric(ok["pcg_iqr"], errors="coerce").median()),
            "median_pcg_missing_rate": float(pd.to_numeric(ok["pcg_missing_rate"], errors="coerce").median()),
        }

    (out / "ephnogram_wfdb_priors.json").write_text(json.dumps(priors, indent=2), encoding="utf-8")
    diagnostics["records_attempted"] = int(len(df))
    diagnostics["records_read_ok"] = int(len(ok))
    diagnostics["output_features"] = str(out / "ephnogram_wfdb_features.csv")
    diagnostics["output_priors"] = str(out / "ephnogram_wfdb_priors.json")
    (out / "ephnogram_wfdb_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")

    print(json.dumps({
        "out": str(out),
        "wfdb_import_ok": diagnostics["wfdb_import_ok"],
        "wfdb_version": diagnostics.get("wfdb_version"),
        "hea_count": diagnostics["hea_count"],
        "records_attempted": int(len(df)),
        "records_read_ok": int(len(ok)),
        "grounded": priors["electrophysiology_workload"]["grounded"],
        "features": str(out / "ephnogram_wfdb_features.csv"),
        "priors": str(out / "ephnogram_wfdb_priors.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
