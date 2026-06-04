#!/usr/bin/env python3
"""GSE201437 protocol-shortcut audit for LAMP-Bio.

This public-data artifact audits a common iPSC-CM maturation claim: does a
transcriptomic monitor detect a hidden maturation state, or does it exploit the
experimental intervention structure itself?

GSE201437 contains engineered heart tissues under four conditions:
High Calcium No Pacing (HCNP), High Calcium Ramp Pacing (HCRP), Low Calcium No
Pacing (LCNP), and Low Calcium Ramp Pacing (LCRP). The intentionally sharp
endpoint here is the combined HCRP condition, while high-calcium and pacing
flags are declared protocol sentinels.
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
OUT = ROOT / "results" / "ipsc_cm_maturation_lamp" / "gse201437_protocol_shortcut"
SEED = 20260604

MARKER_GENES = {
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
        "id": "high_calcium_shortcut_score",
        "name": "High-calcium protocol shortcut score",
        "score": "high_calcium_shortcut_score",
        "features": ["high_calcium"],
        "temporal_offsets": {"high_calcium": 0},
        "description": "Uses the experimental high-calcium intervention as the monitor.",
    },
    {
        "id": "ramp_pacing_shortcut_score",
        "name": "Ramp-pacing protocol shortcut score",
        "score": "ramp_pacing_shortcut_score",
        "features": ["ramp_pacing"],
        "temporal_offsets": {"ramp_pacing": 0},
        "description": "Uses the experimental ramp-pacing intervention as the monitor.",
    },
    {
        "id": "combined_intervention_shortcut_score",
        "name": "Combined HCRP intervention shortcut score",
        "score": "combined_intervention_shortcut_score",
        "features": ["combined_intervention_shortcut_score"],
        "temporal_offsets": {"combined_intervention_shortcut_score": 0},
        "description": "Uses the exact high-calcium plus ramp-pacing condition code.",
    },
    {
        "id": "endpoint_adjacent_marker_score",
        "name": "Endpoint-adjacent marker-selection score",
        "score": "endpoint_adjacent_marker_score",
        "features": ["endpoint_adjacent_marker_score"],
        "temporal_offsets": {"endpoint_adjacent_marker_score": 999},
        "description": "Top genes selected against the HCRP endpoint on the same tiny table.",
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ensure_counts()
    counts, gene_names = load_counts()
    table, endpoint_genes = build_prediction_table(counts, gene_names)
    prediction_path = OUT / "gse201437_protocol_shortcut_prediction_table.csv"
    table.to_csv(prediction_path, index=False, lineterminator="\n")

    summary_rows = []
    for monitor in MONITORS:
        config = build_config(monitor)
        config_path = OUT / "configs" / f"{monitor['id']}.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        result = run_audit(config_path, prediction_path, OUT / "lamp" / monitor["id"])
        summary_rows.append(summary_row(monitor, result))

    write_csv(OUT / "gse201437_protocol_shortcut_lamp_summary.csv", summary_rows)
    write_report(table, summary_rows, endpoint_genes)
    print(OUT / "gse201437_protocol_shortcut_lamp_report.md")
    return 0


def ensure_counts() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_COUNTS.exists() and RAW_COUNTS.stat().st_size > 100_000:
        return
    print(f"Downloading {ACCESSION} processed gene counts from GEO")
    with urllib.request.urlopen(PROCESSED_URL, timeout=180) as response:
        RAW_COUNTS.write_bytes(response.read())


def load_counts() -> tuple[pd.DataFrame, dict[str, str]]:
    with gzip.open(RAW_COUNTS, "rt", encoding="utf-8") as handle:
        frame = pd.read_csv(handle)
    sample_cols = [
        col
        for col in frame.columns
        if col.startswith(("HCNP_", "HCRP_", "LCNP_", "LCRP_"))
    ]
    counts = frame.set_index("gene_id")[sample_cols].astype(float)
    gene_names = frame.set_index("gene_id")["gene_name"].astype(str).to_dict()
    return counts, gene_names


def build_prediction_table(
    counts: pd.DataFrame,
    gene_names: dict[str, str],
) -> tuple[pd.DataFrame, list[str]]:
    log_cpm = log_counts_per_million(counts)
    z = zscore_rows(log_cpm)

    marker_ids = [gene_id for gene_id in MARKER_GENES if gene_id in z.index]
    if len(marker_ids) < 5:
        raise RuntimeError(f"Too few marker genes found in {ACCESSION}: {marker_ids}")

    labels = {sample_id: int(sample_id.startswith("HCRP_")) for sample_id in z.columns}
    endpoint_genes = select_endpoint_adjacent_genes(z, labels)
    endpoint_gene_ids = [gene_id for gene_id, _ in endpoint_genes]
    endpoint_gene_signs = pd.Series(
        {gene_id: 1.0 if effect >= 0.0 else -1.0 for gene_id, effect in endpoint_genes}
    )

    rows = []
    for sample_id in z.columns:
        group, replicate = parse_sample_id(sample_id)
        high_calcium = int(group.startswith("HC"))
        ramp_pacing = int(group.endswith("RP"))
        hcrp = int(group == "HCRP")
        marker_score = float(z.loc[marker_ids, sample_id].mean())
        endpoint_score = float(
            z.loc[endpoint_gene_ids, sample_id].mul(endpoint_gene_signs).mean()
        )
        rows.append(
            {
                "sample_id": sample_id,
                "group": group,
                "replicate": replicate,
                "anchor_time": 0,
                "high_calcium": high_calcium,
                "ramp_pacing": ramp_pacing,
                "label_hcrp_mature_intervention": labels[sample_id],
                "curated_maturation_marker_score": marker_score,
                "high_calcium_shortcut_score": float(high_calcium),
                "ramp_pacing_shortcut_score": float(ramp_pacing),
                "combined_intervention_shortcut_score": float(hcrp),
                "oracle_hcrp_label_score": float(labels[sample_id]),
                "endpoint_adjacent_marker_score": endpoint_score,
                "library_total_counts": float(counts[sample_id].sum()),
                "detected_gene_count": int((counts[sample_id] > 0).sum()),
                "marker_gene_count": len(marker_ids),
            }
        )

    table = pd.DataFrame(rows).sort_values(["group", "replicate"]).reset_index(drop=True)
    endpoint_items = []
    for gene_id, effect in endpoint_genes:
        name = gene_names.get(gene_id, gene_id)
        endpoint_items.append(f"{gene_id}/{name}:{effect:.3f}")
    return table, endpoint_items


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
            "name": f"{ACCESSION} protocol-shortcut audit: {monitor['name']}",
            "task": "Audit iPSC-CM maturation claim vs calcium/pacing intervention shortcuts",
            "role": "LAMP-Bio public iPSC-CM protocol-shortcut artifact",
            "source": GEO_RECORD,
            "processed_data_url": PROCESSED_URL,
            "monitor_id": monitor["id"],
            "monitor_description": monitor["description"],
        },
        "columns": {
            "subject_id": "sample_id",
            "label": "label_hcrp_mature_intervention",
            "positive_value": 1,
            "score": monitor["score"],
            "anchor_time": "anchor_time",
        },
        "temporal_isolation": {
            "anchor": "anchor_time",
            "valid_features_must_be": "pre-claim expression features only; intervention codes must be sentinels",
            "frozen_before_holdout": [
                "GSE201437 accession",
                "GEO processed counts",
                "sample group parser",
                "curated marker list",
                "protocol sentinel definitions",
                "LAMP thresholds",
            ],
            "valid_score_features": [
                {"name": feature, "latest_offset_h": temporal_offsets.get(feature, 0)}
                for feature in monitor["features"]
            ],
        },
        "forbidden_features": {
            "columns": [
                "high_calcium",
                "ramp_pacing",
                "combined_intervention_shortcut_score",
                "oracle_hcrp_label_score",
                "endpoint_adjacent_marker_score",
            ],
            "valid_score_features": list(monitor["features"]),
        },
        "sentinels": {
            "high_calcium": {
                "column": "high_calcium",
                "role": "protocol_shortcut",
                "expected_signature": "high-calcium intervention should not count as hidden maturation inference",
            },
            "ramp_pacing": {
                "column": "ramp_pacing",
                "role": "protocol_shortcut",
                "expected_signature": "ramp-pacing intervention should not count as hidden maturation inference",
            },
            "combined_intervention": {
                "column": "combined_intervention_shortcut_score",
                "role": "protocol_shortcut",
                "expected_signature": "exact HCRP intervention code is a protocol shortcut",
            },
            "oracle_endpoint": {
                "column": "oracle_hcrp_label_score",
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
        "key_warnings": key_warnings(result),
    }


def key_warnings(result: dict[str, Any]) -> str:
    warnings = []
    if result["primary_score"].get("direction_ambiguous"):
        warnings.append("score direction")
    if not result["temporal_isolation"]["passed"]:
        warnings.append("temporal")
    if not result["forbidden_feature_screen"]["passed"]:
        warnings.append("forbidden")
    classes = set(result["failure_mode_dossier"]["output_classes"])
    if "protocol_batch_or_donor_shortcut_sentinel" in classes:
        warnings.append("protocol/intervention sentinel")
    if "oracle_label_leakage_sentinel" in classes:
        warnings.append("oracle sentinel")
    if "future_physiology_invalid_comparator" in classes:
        warnings.append("future/protocol sentinel")
    return ", ".join(dict.fromkeys(warnings)) or "none"


def write_report(
    table: pd.DataFrame,
    summary_rows: list[dict[str, Any]],
    endpoint_genes: list[str],
) -> None:
    positives = int(table["label_hcrp_mature_intervention"].sum())
    group_counts = table["group"].value_counts().sort_index().to_dict()
    lines = [
        "# GSE201437 iPSC-CM Protocol-Shortcut LAMP Audit",
        "",
        "Public-data LAMP-Bio artifact for auditing whether an iPSC-CM maturation",
        "monitor distinguishes biological expression evidence from intervention",
        "structure: high calcium, ramp pacing, or the exact combined HCRP condition.",
        "",
        "## Source",
        "",
        f"- GEO accession: `{ACCESSION}`",
        f"- GEO record: {GEO_RECORD}",
        "- GEO title: Physiological Calcium Combined with Electrical Pacing accelerates Maturation of Human Engineered Heart Tissue.",
        "- Design: four engineered-heart-tissue RNA-seq groups: HCNP, HCRP, LCNP, and LCRP.",
        f"- Samples used: {len(table)} ({positives} HCRP endpoint positives, {len(table) - positives} controls).",
        f"- Group counts: {', '.join(f'{key}={value}' for key, value in group_counts.items())}.",
        "",
        "## LAMP Setup",
        "",
        "- Label: HCRP combined high-calcium plus ramp-pacing condition.",
        "- Candidate biological score: fixed curated cardiomyocyte maturation/electrophysiology marker panel.",
        "- Protocol sentinels: high calcium, ramp pacing, and exact HCRP intervention code.",
        "- Oracle sentinels: endpoint label and endpoint-adjacent genes selected on this table.",
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
            f"{row['forbidden_passed']} | {fmt(row['matched_delta'])} | {row['key_warnings']} | "
            f"`{row['output_classes']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a deliberately small protocol-shortcut audit, not a prospective",
            "biological validation. The key signal is not that a marker panel separates",
            "HCRP samples on 14 RNA-seq profiles; it is that intervention sentinels also",
            "carry strong predictive information. That is exactly the failure mode LAMP-Bio",
            "is meant to expose: an AI maturation monitor may be reading the experimental",
            "condition rather than a latent biological readiness state.",
            "",
            "A serious follow-up should use donor-held-out, protocol-held-out, and",
            "stage-held-out splits, preferably on high-replicate scRNA-seq or multimodal",
            "iPSC-CM datasets with electrophysiology or calcium-imaging endpoints.",
            "",
            "## Endpoint-Adjacent Genes",
            "",
            "These genes were selected against the HCRP endpoint on the same tiny table and",
            "are treated only as an oracle/leaky sentinel, not as a valid model:",
            "",
        ]
    )
    for item in endpoint_genes:
        lines.append(f"- `{item}`")
    lines.append("")
    (OUT / "gse201437_protocol_shortcut_lamp_report.md").write_text(
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
