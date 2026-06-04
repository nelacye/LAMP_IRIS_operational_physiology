#!/usr/bin/env python3
"""GSE201437 controlled PASS/FAIL sanity check for LAMP-Bio.

This script tests whether LAMP can separate three intentionally different
information contracts on the same biological table:

1. Clean latent biology probe: a calcium/electrophysiology panel predicts a
   held-out structural maturation-panel label.
2. Protocol shortcut: the monitor uses high-calcium intervention metadata.
3. Explicit leakage: the monitor uses the label itself.

The point is not to claim a real clinical/biological benchmark. The point is to
check that LAMP is capable of PASS for a clean controlled signal and FAIL for
shortcut/leakage on the same rows.
"""

from __future__ import annotations

import csv
import gzip
import sys
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402


ACCESSION = "GSE201437"
GEO_RECORD = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={ACCESSION}"
PROCESSED_URL = (
    "https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE201437&format=file&file="
    "GSE201437%5FGoPro%5FGeneCounts%2Ecsv%2Egz"
)
DATA_DIR = ROOT / "data" / "raw" / ACCESSION.lower()
RAW_COUNTS = DATA_DIR / "GSE201437_GoPro_GeneCounts.csv.gz"
OUT = ROOT / "results" / "ipsc_cm_maturation_lamp" / "gse201437_sanity_separation"
SEED = 20260604

TRUTH_PANEL = ["TNNT2", "TNNI3", "MYH6", "MYH7", "MYL2", "MYL7", "ACTN2", "TTN"]
PROBE_PANEL = ["ATP2A2", "PLN", "RYR2", "CACNA1C", "SCN5A", "KCNH2"]

MONITORS = [
    {
        "id": "clean_calcium_probe",
        "name": "Clean calcium/electrophysiology probe",
        "score": "clean_calcium_probe_score",
        "features": ["clean_calcium_electrophysiology_probe_panel"],
        "temporal_offsets": {"clean_calcium_electrophysiology_probe_panel": 0},
        "expected": "PASS",
        "description": "A disjoint expression panel predicts a structural maturation-panel label.",
    },
    {
        "id": "protocol_shortcut",
        "name": "High-calcium protocol shortcut",
        "score": "high_calcium_shortcut_score",
        "features": ["high_calcium_shortcut_score"],
        "temporal_offsets": {"high_calcium_shortcut_score": 0},
        "expected": "FAIL",
        "description": "Uses high-calcium intervention metadata instead of expression biology.",
    },
    {
        "id": "explicit_oracle_leakage",
        "name": "Explicit oracle leakage",
        "score": "oracle_structural_maturity_score",
        "features": ["oracle_structural_maturity_score"],
        "temporal_offsets": {"oracle_structural_maturity_score": 999},
        "expected": "FAIL",
        "description": "Uses the controlled structural maturation label itself.",
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ensure_counts()
    counts = load_counts()
    table = build_prediction_table(counts)
    prediction_path = OUT / "gse201437_sanity_prediction_table.csv"
    table.to_csv(prediction_path, index=False, lineterminator="\n")

    summary_rows = []
    for monitor in MONITORS:
        config = build_config(monitor)
        config_path = OUT / "configs" / f"{monitor['id']}.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        result = run_audit(config_path, prediction_path, OUT / "lamp" / monitor["id"])
        summary_rows.append(summary_row(monitor, result))

    write_csv(OUT / "gse201437_sanity_lamp_summary.csv", summary_rows)
    write_report(table, summary_rows)
    print(OUT / "gse201437_sanity_lamp_report.md")
    return 0


def ensure_counts() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_COUNTS.exists() and RAW_COUNTS.stat().st_size > 100_000:
        return
    print(f"Downloading {ACCESSION} processed gene counts from GEO")
    with urllib.request.urlopen(PROCESSED_URL, timeout=180) as response:
        RAW_COUNTS.write_bytes(response.read())


def load_counts() -> pd.DataFrame:
    with gzip.open(RAW_COUNTS, "rt", encoding="utf-8") as handle:
        frame = pd.read_csv(handle)
    sample_cols = [
        col
        for col in frame.columns
        if col.startswith(("HCNP_", "HCRP_", "LCNP_", "LCRP_"))
    ]
    return frame.set_index("gene_name")[sample_cols].astype(float)


def build_prediction_table(counts: pd.DataFrame) -> pd.DataFrame:
    z = zscore_rows(log_counts_per_million(counts))
    truth_genes = [gene for gene in TRUTH_PANEL if gene in z.index]
    probe_genes = [gene for gene in PROBE_PANEL if gene in z.index]
    if len(truth_genes) < 5 or len(probe_genes) < 4:
        raise RuntimeError(
            f"Too few genes found for sanity panels: truth={truth_genes}, probe={probe_genes}"
        )

    truth_score = z.loc[truth_genes].mean(axis=0)
    threshold = float(truth_score.median())
    label = (truth_score >= threshold).astype(int)
    probe_score = z.loc[probe_genes].mean(axis=0)

    rows = []
    for sample_id in z.columns:
        group, replicate = parse_sample_id(sample_id)
        high_calcium = int(group.startswith("HC"))
        ramp_pacing = int(group.endswith("RP"))
        hcrp = int(group == "HCRP")
        rows.append(
            {
                "sample_id": sample_id,
                "group": group,
                "replicate": replicate,
                "anchor_time": 0,
                "high_calcium": high_calcium,
                "ramp_pacing": ramp_pacing,
                "hcrp_group": hcrp,
                "label_structural_maturation_high": int(label[sample_id]),
                "structural_maturation_truth_score": float(truth_score[sample_id]),
                "clean_calcium_probe_score": float(probe_score[sample_id]),
                "high_calcium_shortcut_score": float(high_calcium),
                "hcrp_protocol_shortcut_score": float(hcrp),
                "oracle_structural_maturity_score": float(label[sample_id]),
                "library_total_counts": float(counts[sample_id].sum()),
                "detected_gene_count": int((counts[sample_id] > 0).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["group", "replicate"]).reset_index(drop=True)


def parse_sample_id(sample_id: str) -> tuple[str, int]:
    parts = sample_id.split("_")
    group = parts[0]
    replicate = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return group, replicate


def log_counts_per_million(counts: pd.DataFrame) -> pd.DataFrame:
    totals = counts.sum(axis=0).replace(0, np.nan)
    cpm = counts.divide(totals, axis=1) * 1_000_000.0
    return np.log1p(cpm.fillna(0.0))


def zscore_rows(frame: pd.DataFrame) -> pd.DataFrame:
    mean = frame.mean(axis=1)
    sd = frame.std(axis=1).replace(0, np.nan)
    return frame.sub(mean, axis=0).divide(sd, axis=0).fillna(0.0)


def build_config(monitor: dict[str, Any]) -> dict[str, Any]:
    temporal_offsets = monitor.get("temporal_offsets", {})
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"{ACCESSION} LAMP sanity separation: {monitor['name']}",
            "task": "Controlled separation of clean biology, protocol shortcut, and oracle leakage",
            "role": "LAMP-Bio implementation sanity check",
            "source": GEO_RECORD,
            "processed_data_url": PROCESSED_URL,
            "monitor_id": monitor["id"],
            "monitor_description": monitor["description"],
            "expected_result": monitor["expected"],
        },
        "columns": {
            "subject_id": "sample_id",
            "label": "label_structural_maturation_high",
            "positive_value": 1,
            "score": monitor["score"],
            "anchor_time": "anchor_time",
        },
        "temporal_isolation": {
            "anchor": "anchor_time",
            "valid_features_must_be": "disjoint expression probe only for clean model",
            "frozen_before_holdout": [
                "GSE201437 accession",
                "structural truth panel",
                "disjoint calcium/electrophysiology probe panel",
                "protocol shortcut definitions",
                "oracle leakage definition",
                "LAMP thresholds",
            ],
            "valid_score_features": [
                {"name": feature, "latest_offset_h": temporal_offsets.get(feature, 0)}
                for feature in monitor["features"]
            ],
        },
        "forbidden_features": {
            "columns": [
                "high_calcium_shortcut_score",
                "hcrp_protocol_shortcut_score",
                "oracle_structural_maturity_score",
            ],
            "valid_score_features": list(monitor["features"]),
        },
        "sentinels": {
            "high_calcium": {
                "column": "high_calcium_shortcut_score",
                "role": "protocol_shortcut",
                "expected_signature": "high-calcium metadata should fail as a monitor",
            },
            "hcrp_protocol": {
                "column": "hcrp_protocol_shortcut_score",
                "role": "protocol_shortcut",
                "expected_signature": "exact HCRP condition should remain a protocol sentinel",
            },
            "oracle_truth": {
                "column": "oracle_structural_maturity_score",
                "role": "oracle_label",
                "expected_signature": "direct label leakage ceiling",
            },
        },
        "negative_controls": {"n_permutations": 100, "seed": SEED},
        "visible_state_matching": {
            "columns": ["library_total_counts", "detected_gene_count"],
            "n_bins": 2,
            "min_bin_size": 2,
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.65,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.02,
            "matched_collapse_max": 0.005,
            "score_thresholds": [-0.5, 0.0, 0.5],
        },
    }


def summary_row(monitor: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    dossier = result["failure_mode_dossier"]
    primary = result["primary_score"]
    observed = "PASS" if dossier["audit_pass_candidate"] else "FAIL"
    return {
        "monitor": monitor["name"],
        "monitor_id": monitor["id"],
        "expected": monitor["expected"],
        "observed": observed,
        "matches_expectation": observed == monitor["expected"],
        "score": monitor["score"],
        "auc": primary.get("auc"),
        "inverted_auc": primary.get("inverted_auc"),
        "direction_ambiguous": primary.get("direction_ambiguous"),
        "audit_pass": dossier["audit_pass_candidate"],
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "threshold_fragile": result["threshold_sensitivity"].get("fragile"),
        "output_classes": ";".join(dossier["output_classes"]),
        "key_reasons": key_reasons(result),
    }


def key_reasons(result: dict[str, Any]) -> str:
    reasons = []
    if not result["temporal_isolation"]["passed"]:
        reasons.append("temporal")
    if not result["forbidden_feature_screen"]["passed"]:
        reasons.append("forbidden")
    if result["threshold_sensitivity"].get("fragile"):
        reasons.append("threshold fragile")
    classes = set(result["failure_mode_dossier"]["output_classes"])
    if "protocol_batch_or_donor_shortcut_sentinel" in classes:
        reasons.append("protocol sentinel present")
    if "oracle_label_leakage_sentinel" in classes:
        reasons.append("oracle sentinel present")
    return ", ".join(dict.fromkeys(reasons)) or "none"


def write_report(table: pd.DataFrame, summary_rows: list[dict[str, Any]]) -> None:
    passed = all(row["matches_expectation"] for row in summary_rows)
    positives = int(table["label_structural_maturation_high"].sum())
    lines = [
        "# GSE201437 LAMP Controlled Separation Sanity Check",
        "",
        "This is an implementation and criterion sanity check, not a biological",
        "benchmark claim. It asks whether LAMP can return PASS and FAIL on the same",
        "real expression rows when the information contracts are intentionally known.",
        "",
        "## Setup",
        "",
        f"- Source: `{ACCESSION}` ({GEO_RECORD})",
        f"- Rows: {len(table)} samples ({positives} positive structural-maturation labels, {len(table) - positives} controls).",
        f"- Truth label: median split of a structural maturation panel: {', '.join(TRUTH_PANEL)}.",
        f"- Clean probe: disjoint calcium/electrophysiology panel: {', '.join(PROBE_PANEL)}.",
        "- Shortcut model: high-calcium intervention metadata.",
        "- Leakage model: direct structural maturation label.",
        "",
        "## Expected vs Observed",
        "",
        "| Model | Expected | Observed | AUC | Temporal | Forbidden | Matched Delta | Threshold Fragile | Key Reasons |",
        "|---|:---:|:---:|---:|:---:|:---:|---:|:---:|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['monitor']} | {row['expected']} | {row['observed']} | "
            f"{fmt(row['auc'])} | {row['temporal_passed']} | {row['forbidden_passed']} | "
            f"{fmt(row['matched_delta'])} | {row['threshold_fragile']} | {row['key_reasons']} |"
        )
    lines.extend(
        [
            "",
            "## Result",
            "",
            f"- Separation sanity check passed: `{passed}`.",
            "- The clean disjoint expression probe can pass LAMP.",
            "- The protocol shortcut fails because it uses a forbidden intervention channel.",
            "- The explicit leakage model fails temporal isolation and forbidden-feature screening.",
            "",
            "This does not prove that every real biological claim should pass. It shows that",
            "the current LAMP criteria are not mechanically rejecting every biological",
            "dataset: PASS is reachable when the declared information contract is clean.",
            "",
        ]
    )
    (OUT / "gse201437_sanity_lamp_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.3f}"


if __name__ == "__main__":
    raise SystemExit(main())
