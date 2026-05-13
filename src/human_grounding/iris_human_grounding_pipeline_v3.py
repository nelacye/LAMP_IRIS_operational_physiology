#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRIS Human-Signal Grounding Pipeline v3

Fixes v1 limitations:
- BIDMC .ts parser no longer assumes CSV.
- Harespod .7z archives are extracted if py7zr is installed.
- EPHNOGRAM WFDB records are searched recursively, not only in WFDB/.
- MATLAB .mat / text / CSV files are inventoried more intelligently.
- Grounding priors are populated when basic signal distributions are extractable.

Install:
  py -m pip install numpy pandas matplotlib wfdb py7zr scipy

Run:
  py .\\iris_human_grounding_pipeline_v3.py --real-data .\real_data --out .\human_grounding_run_v2 --extract-7z
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--real-data", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-ephnogram-records", type=int, default=20)
    p.add_argument("--extract-7z", action="store_true")
    p.add_argument("--max-harespod-files", type=int, default=80)
    p.add_argument("--max-bidmc-lines", type=int, default=20000)
    return p.parse_args()


def numeric_quality(x):
    x = np.asarray(x, dtype=float)
    finite = np.isfinite(x)
    if len(x) == 0:
        return {"n": 0, "mean": math.nan, "std": math.nan, "median": math.nan, "missing_rate": math.nan}
    if finite.sum() < 5:
        return {"n": int(finite.sum()), "mean": math.nan, "std": math.nan, "median": math.nan, "missing_rate": float(1 - finite.mean())}
    xf = x[finite]
    return {
        "n": int(finite.sum()),
        "mean": float(np.mean(xf)),
        "std": float(np.std(xf)),
        "median": float(np.median(xf)),
        "q05": float(np.quantile(xf, 0.05)),
        "q25": float(np.quantile(xf, 0.25)),
        "q75": float(np.quantile(xf, 0.75)),
        "q95": float(np.quantile(xf, 0.95)),
        "missing_rate": float(1 - finite.mean()),
        "iqr": float(np.quantile(xf, 0.75) - np.quantile(xf, 0.25)),
    }


def detect_inventory(root: Path):
    rows = []
    checks = [
        ("EPHNOGRAM", root / "physionet" / "ephnogram-1.0.0"),
        ("BIDMC_Zenodo_3902688", root / "zenodo" / "3902688"),
        ("OpenOximetry", root / "physionet" / "openox-repo-1.1.1"),
        ("Harespod", root / "high_altitude" / "harespod"),
        ("AntAWS", root / "antarctic_environment" / "antaws"),
        ("NMDB", root / "radiation_proxy" / "nmdb"),
    ]
    for name, p in checks:
        exists = p.exists()
        n_files = sum(1 for _ in p.rglob("*") if _.is_file()) if exists and p.is_dir() else (1 if exists else 0)
        size_mb = sum(_.stat().st_size for _ in p.rglob("*") if _.is_file())/1e6 if exists and p.is_dir() else (p.stat().st_size/1e6 if exists and p.is_file() else 0)
        rows.append({"source": name, "path": str(p), "exists": exists, "n_files": n_files, "size_mb": round(size_mb, 3)})
    return pd.DataFrame(rows)


def infer_activity_from_row(row):
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


def extract_ephnogram(root: Path, max_records: int):
    eph = root / "physionet" / "ephnogram-1.0.0"
    if not eph.exists():
        return pd.DataFrame()

    rows = []

    # Spreadsheet metadata
    spreadsheet = None
    for candidate in eph.rglob("ECGPCGSpreadsheet.csv"):
        spreadsheet = candidate
        break
    sheet = None
    if spreadsheet is not None:
        for enc in ["utf-8", "latin1", "cp1252"]:
            try:
                sheet = pd.read_csv(spreadsheet, encoding=enc, engine="python")
                break
            except Exception:
                pass
    if sheet is not None:
        for idx, row in sheet.iterrows():
            rec = None
            for v in row.values:
                m = re.search(r"ECGPCG\d{4}", str(v))
                if m:
                    rec = m.group(0)
                    break
            rows.append({
                "source": "EPHNOGRAM",
                "record": rec or f"spreadsheet_row_{idx}",
                "activity_label_inferred": infer_activity_from_row(row),
                "metadata_available": True,
                "wfdb_read": False,
                "feature_source": "spreadsheet",
            })

    # WFDB read, recursive.
    heas = sorted(eph.rglob("*.hea"))[:max_records]
    if heas:
        try:
            import wfdb
            signal_rows = []
            for hp in heas:
                rec_path_no_ext = str(hp.with_suffix(""))
                rec = hp.stem
                try:
                    rd = wfdb.rdrecord(rec_path_no_ext)
                    sig = np.asarray(rd.p_signal, dtype=float)
                    fs = float(rd.fs)
                    duration_s = len(sig) / fs if fs > 0 else math.nan
                    ecg = sig[:, 0] if sig.ndim == 2 and sig.shape[1] >= 1 else sig.ravel()
                    pcg = sig[:, 1] if sig.ndim == 2 and sig.shape[1] >= 2 else np.full_like(ecg, np.nan)
                    eq = numeric_quality(ecg)
                    pq = numeric_quality(pcg)
                    signal_rows.append({
                        "source": "EPHNOGRAM",
                        "record": rec,
                        "activity_label_inferred": "unknown",
                        "metadata_available": sheet is not None,
                        "wfdb_read": True,
                        "feature_source": "wfdb_signal",
                        "fs_hz": fs,
                        "duration_s": duration_s,
                        "n_channels": int(sig.shape[1]) if sig.ndim == 2 else 1,
                        "ecg_n": eq.get("n"),
                        "ecg_median": eq.get("median"),
                        "ecg_iqr": eq.get("iqr"),
                        "ecg_missing_rate": eq.get("missing_rate"),
                        "pcg_n": pq.get("n"),
                        "pcg_median": pq.get("median"),
                        "pcg_iqr": pq.get("iqr"),
                        "pcg_missing_rate": pq.get("missing_rate"),
                    })
                except Exception as e:
                    signal_rows.append({
                        "source": "EPHNOGRAM",
                        "record": rec,
                        "metadata_available": sheet is not None,
                        "wfdb_read": False,
                        "feature_source": "wfdb_error",
                        "error": str(e),
                    })
            if signal_rows:
                return pd.DataFrame(signal_rows)
        except Exception as e:
            rows.append({"source": "EPHNOGRAM", "record": "wfdb_import_failed", "feature_source": "error", "error": str(e)})

    # MATLAB .mat inventory if no WFDB read.
    mat_files = sorted(eph.rglob("*.mat"))[:max_records]
    for mp in mat_files:
        rows.append({"source": "EPHNOGRAM", "record": mp.stem, "feature_source": "mat_file_detected", "path": str(mp), "wfdb_read": False})

    return pd.DataFrame(rows)


def parse_ts_numeric_values(path: Path, max_lines: int):
    """
    Robust-ish parser for sktime .ts files.
    Extracts numeric tokens from data lines only. This is not a classifier loader;
    it is a grounding parser for distribution/missingness/signal ranges.
    """
    values = []
    n_data_lines = 0
    n_header = 0
    class_labels = {}
    numeric_re = re.compile(r"[-+]?\d*\.\d+|[-+]?\d+")
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line_i, line in enumerate(f):
            if line_i >= max_lines:
                break
            s = line.strip()
            if not s:
                continue
            if s.startswith("@") or s.startswith("#"):
                n_header += 1
                continue
            # sktime rows may end with :label
            parts = s.split(":")
            if len(parts) > 1:
                possible_label = parts[-1].strip()
                if possible_label and not re.search(r"\d", possible_label):
                    class_labels[possible_label] = class_labels.get(possible_label, 0) + 1
                    signal_part = ":".join(parts[:-1])
                else:
                    signal_part = s
            else:
                signal_part = s
            nums = numeric_re.findall(signal_part)
            if nums:
                n_data_lines += 1
                # cap per line so giant files do not explode memory
                for tok in nums[:2000]:
                    try:
                        values.append(float(tok))
                    except Exception:
                        pass
    return np.asarray(values, dtype=float), n_header, n_data_lines, class_labels


def extract_bidmc(root: Path, max_lines: int):
    d = root / "zenodo" / "3902688"
    if not d.exists():
        return pd.DataFrame()
    rows = []
    for fp in sorted(d.glob("*")):
        if fp.suffix.lower() not in [".ts", ".csv", ".txt"]:
            continue
        row = {"source": "BIDMC_Zenodo_3902688", "file": fp.name, "size_mb": round(fp.stat().st_size/1e6, 3)}
        if fp.suffix.lower() == ".ts":
            vals, n_header, n_data, labels = parse_ts_numeric_values(fp, max_lines)
            q = numeric_quality(vals)
            row.update({
                "read_ok": q.get("n") > 0,
                "parser": "ts_numeric_token_parser",
                "n_header_lines_sampled": n_header,
                "n_data_lines_sampled": n_data,
                "n_numeric_values_sampled": q.get("n"),
                "numeric_median": q.get("median"),
                "numeric_iqr": q.get("iqr"),
                "numeric_q05": q.get("q05"),
                "numeric_q95": q.get("q95"),
                "numeric_missing_rate": q.get("missing_rate"),
                "class_labels_json": json.dumps(labels),
            })
        else:
            try:
                df = pd.read_csv(fp, sep=None, engine="python", nrows=200000)
                numeric = df.select_dtypes(include=[np.number])
                row.update({"read_ok": True, "parser": "pandas", "n_rows_sampled": int(len(df)), "n_numeric_cols": int(numeric.shape[1])})
                vals = numeric.to_numpy(dtype=float).ravel() if numeric.shape[1] else np.array([])
                q = numeric_quality(vals)
                row.update({"numeric_median": q.get("median"), "numeric_iqr": q.get("iqr"), "numeric_missing_rate": q.get("missing_rate")})
            except Exception as e:
                row.update({"read_ok": False, "parser": "pandas_failed", "error": str(e)})
        rows.append(row)
    return pd.DataFrame(rows)


def extract_7z_archives(root: Path):
    try:
        import py7zr
    except Exception as e:
        return [{"archive": "py7zr_missing", "status": "failed", "error": str(e)}]
    rows = []
    for z in root.rglob("*.7z"):
        dest = z.with_suffix("")
        marker = dest / ".extracted"
        if marker.exists():
            rows.append({"archive": str(z), "dest": str(dest), "status": "already_extracted"})
            continue
        dest.mkdir(parents=True, exist_ok=True)
        try:
            with py7zr.SevenZipFile(z, mode="r") as archive:
                archive.extractall(path=dest)
            marker.write_text("ok", encoding="utf-8")
            rows.append({"archive": str(z), "dest": str(dest), "status": "extracted"})
        except Exception as e:
            rows.append({"archive": str(z), "dest": str(dest), "status": "failed", "error": str(e)})
    return rows


def read_table(path: Path, nrows=200000):
    try:
        if path.suffix.lower() in [".csv", ".txt", ".tsv"]:
            return pd.read_csv(path, sep=None, engine="python", nrows=nrows)
        if path.suffix.lower() in [".xlsx", ".xls"]:
            return pd.read_excel(path, nrows=nrows)
    except Exception:
        try:
            return pd.read_csv(path, sep=r"\s+", engine="python", nrows=nrows)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def mat_summary(path: Path):
    try:
        import scipy.io
        data = scipy.io.loadmat(path, simplify_cells=True)
        rows = []
        for k, v in data.items():
            if k.startswith("__"):
                continue
            if isinstance(v, np.ndarray) and np.issubdtype(v.dtype, np.number):
                arr = np.asarray(v, dtype=float).ravel()
                q = numeric_quality(arr)
                rows.append({"var": k, "shape": str(np.shape(v)), "n": q.get("n"), "median": q.get("median"), "iqr": q.get("iqr"), "missing_rate": q.get("missing_rate")})
        return rows
    except Exception as e:
        return [{"var": "mat_read_failed", "error": str(e)}]


def extract_harespod(root: Path, extract_7z: bool, max_files: int):
    h = root / "high_altitude" / "harespod"
    if not h.exists():
        return pd.DataFrame(), pd.DataFrame()

    extraction_log = pd.DataFrame(extract_7z_archives(h)) if extract_7z else pd.DataFrame()

    rows = []
    files = [p for p in h.rglob("*") if p.is_file() and not p.name.startswith(".")]
    # Prefer readable physiological tables / mat files.
    candidates = [p for p in files if p.suffix.lower() in [".csv", ".txt", ".tsv", ".xlsx", ".xls", ".mat"]]
    for fp in candidates[:max_files]:
        rel = str(fp.relative_to(h))
        if fp.suffix.lower() == ".mat":
            matrows = mat_summary(fp)
            for mr in matrows:
                row = {"source": "Harespod", "file": rel, "suffix": fp.suffix, "read_ok": "error" not in mr, "parser": "scipy_mat"}
                row.update(mr)
                rows.append(row)
            continue
        df = read_table(fp)
        row = {"source": "Harespod", "file": rel, "suffix": fp.suffix, "read_ok": not df.empty, "parser": "table", "n_rows_sampled": int(len(df)) if not df.empty else 0}
        if not df.empty:
            numeric = df.select_dtypes(include=[np.number])
            row["n_numeric_cols"] = int(numeric.shape[1])
            vals = numeric.to_numpy(dtype=float).ravel() if numeric.shape[1] else np.array([])
            q = numeric_quality(vals)
            row["numeric_median"] = q.get("median")
            row["numeric_iqr"] = q.get("iqr")
            row["numeric_missing_rate"] = q.get("missing_rate")
            # Specific columns
            for col in df.columns:
                low = str(col).lower()
                if any(k in low for k in ["spo2", "spo", "oxygen", "hr", "heart", "pulse", "resp", "breath", "altitude", "saturation"]):
                    cvals = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
                    cq = numeric_quality(cvals)
                    safe = re.sub(r"[^A-Za-z0-9]+", "_", str(col))[:40]
                    row[f"{safe}_median"] = cq.get("median")
                    row[f"{safe}_iqr"] = cq.get("iqr")
                    row[f"{safe}_missing_rate"] = cq.get("missing_rate")
        rows.append(row)

    # If no extracted readable candidates, inventory archive files.
    if not rows:
        for fp in files[:max_files]:
            rows.append({
                "source": "Harespod",
                "file": str(fp.relative_to(h)),
                "suffix": fp.suffix,
                "read_ok": False,
                "size_mb": round(fp.stat().st_size/1e6, 3),
                "parser": "inventory_only",
            })
    return pd.DataFrame(rows), extraction_log


def build_priors(eph: pd.DataFrame, bidmc: pd.DataFrame, hares: pd.DataFrame):
    priors = {
        "electrophysiology_workload": {
            "grounded": False,
            "ecg_signal_quality": None,
            "pcg_signal_quality": None,
            "activity_labels_available": False,
        },
        "observation_validity": {
            "grounded": False,
            "oxygenation_signal_numeric_distribution": None,
        },
        "hypoxia_oxygenation": {
            "grounded": False,
            "harespod_files_read": 0,
            "notes": "Harespod grounding is accepted only when physiological tables or MATLAB numeric variables are parsed.",
        },
    }

    if not eph.empty:
        priors["electrophysiology_workload"]["activity_labels_available"] = bool("activity_label_inferred" in eph.columns and (eph["activity_label_inferred"].astype(str) != "unknown").any())
        if "ecg_missing_rate" in eph.columns:
            priors["electrophysiology_workload"]["grounded"] = True
            priors["electrophysiology_workload"]["ecg_signal_quality"] = {
                "median_missing_rate": float(pd.to_numeric(eph["ecg_missing_rate"], errors="coerce").median()),
                "median_ecg_iqr": float(pd.to_numeric(eph.get("ecg_iqr", pd.Series(dtype=float)), errors="coerce").median()),
            }
        if "pcg_missing_rate" in eph.columns:
            priors["electrophysiology_workload"]["pcg_signal_quality"] = {
                "median_missing_rate": float(pd.to_numeric(eph["pcg_missing_rate"], errors="coerce").median()),
                "median_pcg_iqr": float(pd.to_numeric(eph.get("pcg_iqr", pd.Series(dtype=float)), errors="coerce").median()),
            }

    if not bidmc.empty and "numeric_median" in bidmc.columns:
        ok = bidmc[bidmc.get("read_ok", False).astype(str).str.lower().isin(["true", "1"])] if "read_ok" in bidmc.columns else bidmc
        if not ok.empty:
            priors["observation_validity"]["grounded"] = True
            priors["observation_validity"]["oxygenation_signal_numeric_distribution"] = {
                "files_read": int(len(ok)),
                "median_of_file_medians": float(pd.to_numeric(ok["numeric_median"], errors="coerce").median()),
                "median_iqr": float(pd.to_numeric(ok["numeric_iqr"], errors="coerce").median()),
            }

    if not hares.empty:
        read_ok = hares[hares.get("read_ok", False).astype(str).str.lower().isin(["true", "1"])] if "read_ok" in hares.columns else pd.DataFrame()
        if not read_ok.empty:
            priors["hypoxia_oxygenation"]["grounded"] = True
            priors["hypoxia_oxygenation"]["harespod_files_read"] = int(len(read_ok))
    return priors


def write_report(out: Path, inv, eph, bidmc, hares, priors, extraction_log):
    lines = []
    lines.append("# IRIS Human-Signal Grounding Run v3\n")
    lines.append("## Purpose\n")
    lines.append("This run uses real human physiological signal datasets as retrospective grounding layers for IRIS observability, workload/electrophysiology, and oxygenation components. It is not Antarctic human validation.\n")
    lines.append("## Inventory\n")
    lines.append(inv.to_markdown(index=False))
    lines.append("\n## Archive extraction log\n")
    lines.append(extraction_log.to_markdown(index=False) if extraction_log is not None and not extraction_log.empty else "No 7z extraction attempted or no archives found.")
    lines.append("\n## EPHNOGRAM grounding\n")
    lines.append(eph.head(30).to_markdown(index=False) if not eph.empty else "EPHNOGRAM not detected or not readable.")
    lines.append("\n## BIDMC / oxygenation grounding\n")
    lines.append(bidmc.head(20).to_markdown(index=False) if not bidmc.empty else "BIDMC oxygenation files not detected or not readable.")
    lines.append("\n## Harespod / hypoxia grounding\n")
    lines.append(hares.head(40).to_markdown(index=False) if not hares.empty else "Harespod files not detected or not readable.")
    lines.append("\n## Grounding priors\n")
    lines.append("```json")
    lines.append(json.dumps(priors, indent=2))
    lines.append("```")
    lines.append("\n## Supported claims\n")
    lines.append("- EPHNOGRAM supports human ECG/PCG activity-label and signal-quality grounding only if WFDB or MATLAB features are readable.")
    lines.append("- BIDMC supports oxygenation/PPG-style numeric signal grounding if `.ts` numeric distributions are parsed.")
    lines.append("- Harespod supports hypoxia/oxygenation grounding only after 7z extraction and readable physiologic files.")
    lines.append("\n## Not supported\n")
    lines.append("- No human Antarctic cohort.")
    lines.append("- No longitudinal baseline-to-exposure-to-later-deterioration human validation.")
    lines.append("- No clinical or patient-specific prediction.")
    lines.append("- No individual radiation dose or organ dose.")
    (out / "human_signal_grounding_report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    args = parse_args()
    root = Path(args.real_data)
    out = Path(args.out)
    tables = out / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    inv = detect_inventory(root)
    eph = extract_ephnogram(root, args.max_ephnogram_records)
    bidmc = extract_bidmc(root, args.max_bidmc_lines)
    hares, extraction_log = extract_harespod(root, args.extract_7z, args.max_harespod_files)
    priors = build_priors(eph, bidmc, hares)

    inv.to_csv(tables / "human_grounding_inventory.csv", index=False)
    eph.to_csv(tables / "ephnogram_grounding_features.csv", index=False)
    bidmc.to_csv(tables / "bidmc_spo2_grounding_features.csv", index=False)
    hares.to_csv(tables / "harespod_grounding_features.csv", index=False)
    if extraction_log is not None and not extraction_log.empty:
        extraction_log.to_csv(tables / "harespod_7z_extraction_log.csv", index=False)
    (tables / "grounding_priors.json").write_text(json.dumps(priors, indent=2), encoding="utf-8")
    write_report(out, inv, eph, bidmc, hares, priors, extraction_log)

    print(json.dumps({
        "out": str(out),
        "report": str(out / "human_signal_grounding_report.md"),
        "ephnogram_rows": int(len(eph)),
        "bidmc_rows": int(len(bidmc)),
        "harespod_rows": int(len(hares)),
        "ephnogram_grounded": priors["electrophysiology_workload"]["grounded"],
        "observation_validity_grounded": priors["observation_validity"]["grounded"],
        "hypoxia_grounded": priors["hypoxia_oxygenation"]["grounded"],
    }, indent=2))


if __name__ == "__main__":
    main()
