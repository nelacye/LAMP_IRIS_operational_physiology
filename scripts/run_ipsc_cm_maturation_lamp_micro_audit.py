#!/usr/bin/env python3
"""GSE209997 iPSC cardiac maturation micro-audit for LAMP.

This is a deliberately small public-data artifact. It downloads processed
featureCounts files for GEO GSE209997, builds a sample-level transcriptomic
prediction table, and runs LAMP audits for a curated maturation-marker score
and intentionally invalid shortcut/sentinel scores.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402


ACCESSION = "GSE209997"
GEO_URL = f"https://www.ncbi.nlm.nih.gov/geo/download/?acc={ACCESSION}&format=file"
GEO_RECORD = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={ACCESSION}"
DATA_DIR = ROOT / "data" / "raw" / ACCESSION.lower()
OUT = ROOT / "results" / "ipsc_cm_maturation_lamp" / "gse209997_micro"
RAW_TAR = DATA_DIR / f"{ACCESSION}_RAW.tar"
SEED = 20260604

MARKER_GENES = {
    # Curated cardiomyocyte maturation / electrophysiology markers.
    # Keys are Ensembl gene IDs in the GSE209997 featureCounts files.
    "ENSG00000118194": "TNNT2",
    "ENSG00000129991": "TNNI3",
    "ENSG00000197616": "MYH6",
    "ENSG00000092054": "MYH7",
    "ENSG00000111245": "MYL2",
    "ENSG00000106631": "MYL7",
    "ENSG00000077522": "ACTN2",
    "ENSG00000155657": "TTN",
    "ENSG00000174437": "ATP2A2",
    "ENSG00000198523": "PLN",
    "ENSG00000198626": "RYR2",
    "ENSG00000151067": "CACNA1C",
    "ENSG00000183873": "SCN5A",
    "ENSG00000055118": "KCNH2",
}

MONITORS = [
    {
        "id": "curated_maturation_marker_score",
        "name": "Curated maturation-marker expression score",
        "score": "curated_maturation_marker_score",
        "features": ["curated_maturation_marker_panel"],
        "temporal_offsets": {"curated_maturation_marker_panel": 0},
        "description": "Mean z-scored logCPM over a fixed cardiomyocyte maturation marker panel.",
    },
    {
        "id": "timepoint_shortcut_score",
        "name": "Timepoint shortcut score",
        "score": "timepoint_shortcut_score",
        "features": ["day_numeric"],
        "temporal_offsets": {"day_numeric": 999},
        "description": "Uses sample day directly; invalid for an early hidden-state maturation claim.",
    },
    {
        "id": "protocol_shortcut_score",
        "name": "Protocol shortcut score",
        "score": "protocol_shortcut_score",
        "features": ["culture_3d"],
        "temporal_offsets": {"culture_3d": 0},
        "description": "Uses 3D-vs-2D culture protocol directly instead of hidden biological state.",
    },
    {
        "id": "endpoint_adjacent_marker_score",
        "name": "Endpoint-adjacent marker-selection score",
        "score": "endpoint_adjacent_marker_score",
        "features": ["endpoint_adjacent_marker_score"],
        "temporal_offsets": {"endpoint_adjacent_marker_score": 999},
        "description": "Top genes selected against the endpoint on the same tiny table; leaky comparator.",
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ensure_raw_tar()
    counts = load_counts()
    table, selected_endpoint_genes = build_prediction_table(counts)
    prediction_path = OUT / "gse209997_micro_prediction_table.csv"
    table.to_csv(prediction_path, index=False, lineterminator="\n")

    summary_rows = []
    for monitor in MONITORS:
        config = build_config(monitor)
        config_path = OUT / "configs" / f"{monitor['id']}.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        result = run_audit(config_path, prediction_path, OUT / "lamp" / monitor["id"])
        summary_rows.append(summary_row(monitor, result))

    write_csv(OUT / "gse209997_micro_lamp_summary.csv", summary_rows)
    write_report(table, summary_rows, selected_endpoint_genes)
    print(OUT / "gse209997_micro_lamp_report.md")
    return 0


def ensure_raw_tar() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_TAR.exists() and RAW_TAR.stat().st_size > 1_000_000:
        return
    print(f"Downloading {ACCESSION} processed files from GEO")
    with urllib.request.urlopen(GEO_URL, timeout=180) as response:
        RAW_TAR.write_bytes(response.read())


def load_counts() -> pd.DataFrame:
    sample_counts: dict[str, pd.Series] = {}
    sample_meta: dict[str, dict[str, Any]] = {}
    with tarfile.open(RAW_TAR) as archive:
        for member in archive.getmembers():
            if not member.name.endswith(".featureCounts.tsv.gz"):
                continue
            sample_id, day, culture, replicate = parse_member_name(member.name)
            handle = archive.extractfile(member)
            if handle is None:
                continue
            with gzip.GzipFile(fileobj=handle) as gz:
                frame = pd.read_csv(
                    io.TextIOWrapper(gz, encoding="utf-8"),
                    sep="\t",
                    comment="#",
                )
            count_col = frame.columns[-1]
            sample_counts[sample_id] = frame.set_index("Geneid")[count_col].astype(float)
            sample_meta[sample_id] = {
                "sample_id": sample_id,
                "geo_sample": sample_id.split("_")[0],
                "day": day,
                "culture": culture,
                "replicate": replicate,
                "culture_3d": 1 if culture == "3D" else 0,
                "day_numeric": day,
            }

    counts = pd.DataFrame(sample_counts).fillna(0.0)
    counts.attrs["sample_meta"] = sample_meta
    return counts


def parse_member_name(name: str) -> tuple[str, int, str, int]:
    stem = Path(name).name.replace(".featureCounts.tsv.gz", "")
    # Examples: GSM6412466_D50_3D_rep1, GSM6412472_D30-U_rep1.
    if "_D30-U_" in stem:
        day, culture = 30, "2D"
    elif "_D50-U_" in stem:
        day, culture = 50, "2D"
    elif "_D30_3D_" in stem:
        day, culture = 30, "3D"
    elif "_D50_3D_" in stem:
        day, culture = 50, "3D"
    else:
        raise ValueError(f"Could not parse day/culture from {name}")
    rep_match = re.search(r"_rep(\d+)$", stem)
    replicate = int(rep_match.group(1)) if rep_match else 0
    return stem, day, culture, replicate


def build_prediction_table(counts: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    log_cpm = log_counts_per_million(counts)
    z = zscore_rows(log_cpm)
    meta = counts.attrs["sample_meta"]

    marker_ids = [gene_id for gene_id in MARKER_GENES if gene_id in z.index]
    if len(marker_ids) < 5:
        raise RuntimeError(f"Too few marker genes found in {ACCESSION}: {marker_ids}")

    labels = {}
    for sample_id, item in meta.items():
        labels[sample_id] = int(item["day"] == 50 and item["culture"] == "3D")
    endpoint_genes = select_endpoint_adjacent_genes(z, labels)
    endpoint_gene_ids = [gene_id for gene_id, _ in endpoint_genes]
    endpoint_gene_signs = pd.Series(
        {gene_id: 1.0 if effect >= 0.0 else -1.0 for gene_id, effect in endpoint_genes}
    )

    rows = []
    for sample_id in z.columns:
        item = dict(meta[sample_id])
        label = labels[sample_id]
        marker_score = float(z.loc[marker_ids, sample_id].mean())
        endpoint_score = float(
            z.loc[endpoint_gene_ids, sample_id].mul(endpoint_gene_signs).mean()
        )
        rows.append(
            {
                **item,
                "anchor_time": 0,
                "label_d50_3d_mature_state": label,
                "curated_maturation_marker_score": marker_score,
                "timepoint_shortcut_score": 1.0 if item["day"] == 50 else 0.0,
                "protocol_shortcut_score": float(item["culture_3d"]),
                "oracle_mature_state_score": float(label),
                "endpoint_adjacent_marker_score": endpoint_score,
                "library_total_counts": float(counts[sample_id].sum()),
                "detected_gene_count": int((counts[sample_id] > 0).sum()),
                "marker_gene_count": len(marker_ids),
            }
        )
    table = pd.DataFrame(rows).sort_values(["day", "culture", "replicate"]).reset_index(drop=True)
    return table, [f"{gene_id}:{effect:.3f}" for gene_id, effect in endpoint_genes]


def log_counts_per_million(counts: pd.DataFrame) -> pd.DataFrame:
    totals = counts.sum(axis=0).replace(0, np.nan)
    cpm = counts.divide(totals, axis=1) * 1_000_000.0
    return np.log1p(cpm.fillna(0.0))


def zscore_rows(frame: pd.DataFrame) -> pd.DataFrame:
    mean = frame.mean(axis=1)
    sd = frame.std(axis=1).replace(0, np.nan)
    return frame.sub(mean, axis=0).divide(sd, axis=0).fillna(0.0)


def select_endpoint_adjacent_genes(
    z: pd.DataFrame,
    labels: dict[str, int],
    n_genes: int = 20,
) -> list[tuple[str, float]]:
    positive_samples = [sample for sample, label in labels.items() if label == 1]
    negative_samples = [sample for sample, label in labels.items() if label == 0]
    effects = z[positive_samples].mean(axis=1) - z[negative_samples].mean(axis=1)
    selected = effects.abs().sort_values(ascending=False).head(n_genes)
    return [(gene_id, float(effects.loc[gene_id])) for gene_id in selected.index]


def build_config(monitor: dict[str, Any]) -> dict[str, Any]:
    temporal_offsets = monitor.get("temporal_offsets", {})
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"{ACCESSION} iPSC-CM maturation micro-audit: {monitor['name']}",
            "task": "Audit early/latent maturation-state claim vs protocol/timepoint shortcuts",
            "role": "public iPSC cardiac maturation micro artifact",
            "source": GEO_RECORD,
            "processed_data_url": GEO_URL,
            "monitor_id": monitor["id"],
            "monitor_description": monitor["description"],
        },
        "columns": {
            "subject_id": "sample_id",
            "label": "label_d50_3d_mature_state",
            "positive_value": 1,
            "score": monitor["score"],
            "anchor_time": "anchor_time",
        },
        "temporal_isolation": {
            "anchor": "anchor_time",
            "valid_features_must_be": "pre-endpoint expression only for hidden maturation claim",
            "frozen_before_holdout": [
                "GSE209997 accession",
                "sample metadata parser",
                "curated marker list",
                "shortcut/sentinel definitions",
                "LAMP thresholds",
            ],
            "valid_score_features": [
                {"name": feature, "latest_offset_h": temporal_offsets.get(feature, 0)}
                for feature in monitor["features"]
            ],
        },
            "forbidden_features": {
            "columns": [
                "day_numeric",
                "culture_3d",
                "oracle_mature_state_score",
                "endpoint_adjacent_marker_score",
            ],
            "allowed_metadata_columns": ["day_numeric", "culture_3d"],
            "valid_score_features": list(monitor["features"]),
        },
        "sentinels": {
            "timepoint": {
                "column": "day_numeric",
                "role": "future_timepoint",
                "expected_signature": "invalid shortcut for early maturation prediction",
            },
            "protocol": {
                "column": "culture_3d",
                "role": "protocol_shortcut",
                "expected_signature": "3D-vs-2D culture shortcut, not hidden maturation state",
            },
            "oracle_endpoint": {
                "column": "oracle_mature_state_score",
                "role": "oracle_label",
                "expected_signature": "ceiling endpoint comparator",
            },
            "endpoint_adjacent_markers": {
                "column": "endpoint_adjacent_marker_score",
                "role": "oracle_label",
                "expected_signature": "genes selected against endpoint on same tiny table",
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
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.02,
            "matched_collapse_max": 0.005,
            "score_thresholds": [-1.0, 0.0, 1.0],
        },
    }


def summary_row(monitor: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    dossier = result["failure_mode_dossier"]
    primary = result["primary_score"]
    return {
        "monitor": monitor["name"],
        "monitor_id": monitor["id"],
        "score": monitor["score"],
        "auc": primary.get("auc"),
        "inverted_auc": primary.get("inverted_auc"),
        "direction_ambiguous": primary.get("direction_ambiguous"),
        "audit_pass": dossier["audit_pass_candidate"],
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "output_classes": ";".join(dossier["output_classes"]),
        "key_failures": key_failures(result),
    }


def key_failures(result: dict[str, Any]) -> str:
    failures = []
    if result["primary_score"].get("direction_ambiguous"):
        failures.append("score direction")
    if not result["temporal_isolation"]["passed"]:
        failures.append("temporal")
    if not result["forbidden_feature_screen"]["passed"]:
        failures.append("forbidden")
    classes = set(result["failure_mode_dossier"]["output_classes"])
    if "protocol_batch_or_donor_shortcut_sentinel" in classes:
        failures.append("protocol/batch/donor sentinel")
    if "oracle_label_leakage_sentinel" in classes:
        failures.append("oracle sentinel")
    if "future_physiology_invalid_comparator" in classes:
        failures.append("future/protocol sentinel")
    return ", ".join(dict.fromkeys(failures)) or "none"


def write_report(
    table: pd.DataFrame,
    summary_rows: list[dict[str, Any]],
    selected_endpoint_genes: list[str],
) -> None:
    positives = int(table["label_d50_3d_mature_state"].sum())
    lines = [
        "# GSE209997 iPSC-CM Maturation LAMP Micro Audit",
        "",
        "Public-data smoke test for applying LAMP to AI claims about early latent-state",
        "detection in iPSC-derived cardiac maturation systems.",
        "",
        "## Source",
        "",
        f"- GEO accession: `{ACCESSION}`",
        f"- GEO record: {GEO_RECORD}",
        "- Design: D30/D50 iPSC-derived 3D organotypic cardiac microtissues vs 2D monolayer controls.",
        f"- Samples used: {len(table)} ({positives} D50-3D endpoint positives, {len(table) - positives} controls).",
        "",
        "## LAMP Setup",
        "",
        "- Label: D50 3D mature organotypic state.",
        "- Candidate valid score: fixed curated cardiomyocyte maturation/electrophysiology marker panel.",
        "- Shortcut sentinels: sample day and 3D-vs-2D protocol.",
        "- Oracle sentinels: endpoint label and endpoint-adjacent genes selected on this tiny table.",
        "- Matching variables: library total counts and detected gene count.",
        "",
        "## Audit Summary",
        "",
        "| Monitor | AUC | Inverted AUC | Direction? | Audit Pass | Temporal | Forbidden | Matched Delta | Key Warnings | Output Classes |",
        "|---|---:|---:|:---:|:---:|:---:|:---:|---:|---|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['monitor']} | {fmt(row['auc'])} | {fmt(row['inverted_auc'])} | "
            f"{row['direction_ambiguous']} | {row['audit_pass']} | {row['temporal_passed']} | "
            f"{row['forbidden_passed']} | {fmt(row['matched_delta'])} | {row['key_failures']} | "
            f"`{row['output_classes']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is not a benchmark-level claim: the table has only 12 RNA-seq samples.",
            "Its purpose is to show how an iPSC maturation claim can be converted into a",
            "LAMP audit object. The important result is the separation of a declared",
            "maturation-marker score from explicit timepoint, protocol, and endpoint-adjacent",
            "sentinels.",
            "",
            "A high AUC here should not be read as prospective validity. The 3D protocol",
            "sentinel is also predictive, so the serious version must use donor-held-out,",
            "protocol-held-out, and",
            "timepoint-held-out splits on larger iPSC-CM or organoid datasets, preferably",
            "with electrophysiology or calcium-imaging endpoints.",
            "",
            "## Endpoint-Adjacent Genes",
            "",
            "These genes were selected against the endpoint on the same tiny table and are",
            "therefore treated only as an oracle/leaky sentinel, not as a valid model:",
            "",
        ]
    )
    for item in selected_endpoint_genes:
        lines.append(f"- `{item}`")
    lines.append("")
    (OUT / "gse209997_micro_lamp_report.md").write_text("\n".join(lines), encoding="utf-8")


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
