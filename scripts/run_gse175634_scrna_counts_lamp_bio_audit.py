#!/usr/bin/env python3
"""GSE175634 count-matrix LAMP-Bio disjoint-axis audit.

This runner is the count-level follow-up to the metadata-only GSE175634 audit.
It extracts only curated marker-panel genes from the GEO sparse count matrix and
asks the biological question that metadata alone cannot answer:

Do disjoint biological axes survive after day, pseudotime, and annotation
shortcuts are treated as forbidden/sentinel channels?

The default pilot uses the first 60,000 matrix-order cells. That keeps the
artifact reproducible on a laptop while still using real scRNA counts.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402
from lamp.controls import auc_score  # noqa: E402


ACCESSION = "GSE175634"
GEO_RECORD = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={ACCESSION}"
SUPPL_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE175nnn/GSE175634/suppl"
DATA_DIR = ROOT / "data" / "raw" / "gse175634"
CACHE_DIR = ROOT / "data" / "processed" / "gse175634"
OUT = ROOT / "results" / "lamp_bio_scrna" / "gse175634_counts"
FIG_DIR = OUT / "figures"
SEED = 20260605

SUPPLEMENTARY_FILES = {
    "cell_metadata": "GSE175634_cell_metadata.tsv.gz",
    "cell_indices": "GSE175634_cell_indices.tsv.gz",
    "gene_indices": "GSE175634_gene_indices_counts.tsv.gz",
    "cell_counts": "GSE175634_cell_counts.mtx.gz",
}

PANELS = {
    "structural": [
        "TNNT2",
        "TNNI3",
        "MYH6",
        "MYH7",
        "MYL2",
        "MYL7",
        "ACTN2",
        "MYBPC3",
        "TTN",
        "TNNC1",
    ],
    "calcium_ephys": [
        "RYR2",
        "ATP2A2",
        "PLN",
        "CASQ2",
        "CACNA1C",
        "SCN5A",
        "KCNH2",
        "KCNQ1",
        "KCND3",
        "GJA1",
    ],
    "metabolic": [
        "PPARGC1A",
        "CPT1B",
        "ACADVL",
        "HADHA",
        "NDUFA4",
        "COX5A",
        "COX6A2",
        "SLC25A4",
        "CKMT2",
        "PDK4",
    ],
    "cell_cycle": ["MKI67", "TOP2A", "PCNA", "CCNB1", "CCNB2", "CDK1", "MCM5"],
}

MONITORS = [
    {
        "id": "calcium_to_structural_disjoint_probe",
        "name": "Calcium/electrophysiology -> structural endpoint",
        "score": "calcium_ephys_panel_score",
        "features": ["calcium_ephys_panel_score"],
        "expected": "PASS_OR_FRAGILE",
        "description": "Disjoint calcium/electrophysiology panel predicts structural-axis maturity.",
    },
    {
        "id": "metabolic_to_structural_disjoint_probe",
        "name": "Metabolic -> structural endpoint",
        "score": "metabolic_panel_score",
        "features": ["metabolic_panel_score"],
        "expected": "PASS_OR_FRAGILE",
        "description": "Disjoint metabolic panel predicts structural-axis maturity.",
    },
    {
        "id": "combined_biology_to_structural_probe",
        "name": "Combined disjoint biology -> structural endpoint",
        "score": "combined_disjoint_biology_score",
        "features": ["calcium_ephys_panel_score", "metabolic_panel_score"],
        "expected": "PASS_OR_FRAGILE",
        "description": "Average of calcium/electrophysiology and metabolic axes.",
    },
    {
        "id": "structural_endpoint_adjacent_oracle",
        "name": "Structural endpoint-adjacent oracle",
        "score": "structural_panel_score",
        "features": ["structural_panel_score"],
        "expected": "FAIL",
        "latest_offset_h": 999,
        "description": "Uses the same marker axis that defines the endpoint.",
    },
    {
        "id": "day_protocol_shortcut",
        "name": "Differentiation-day protocol shortcut",
        "score": "diffday_numeric_score",
        "features": ["diffday_numeric_score"],
        "expected": "FAIL",
        "description": "Uses day/protocol timing instead of molecular evidence.",
    },
    {
        "id": "published_annotation_shortcut",
        "name": "Published annotation shortcut",
        "score": "annotation_cm_score",
        "features": ["annotation_cm_score"],
        "expected": "FAIL",
        "latest_offset_h": 999,
        "description": "Uses the published CM annotation as a monitor.",
    },
    {
        "id": "published_pseudotime_shortcut",
        "name": "Published pseudotime shortcut",
        "score": "dpt_pseudotime_score",
        "features": ["dpt_pseudotime_score"],
        "expected": "FAIL",
        "latest_offset_h": 999,
        "description": "Uses full-trajectory pseudotime inferred from the dataset.",
    },
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    ensure_inputs()

    table, inventory = build_prediction_table(max_cells=args.max_cells)
    prediction_path = OUT / "gse175634_scrna_counts_prediction_table.csv"
    table.to_csv(prediction_path, index=False, lineterminator="\n")

    summary_rows: list[dict[str, Any]] = []
    for monitor in MONITORS:
        config = build_config(monitor)
        config_path = OUT / "configs" / f"{monitor['id']}.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        result = run_audit(config_path, prediction_path, OUT / "lamp" / monitor["id"])
        stability = stability_summary(
            table=table,
            label_col="label_structural_maturity_high",
            score_col=monitor["score"],
        )
        summary_rows.append(summary_row(monitor, result, stability))

    summary_path = OUT / "gse175634_scrna_counts_lamp_summary.csv"
    write_csv(summary_path, summary_rows)
    inventory_path = OUT / "gse175634_scrna_counts_inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    plot_panel_scores(table, FIG_DIR / "panel_scores_by_structural_endpoint.png")
    plot_monitor_auc(summary_rows, FIG_DIR / "counts_monitor_auc_summary.png")

    report_path = OUT / "gse175634_scrna_counts_lamp_report.md"
    write_report(report_path, table, inventory, summary_rows, args.max_cells)

    manifest = {
        "accession": ACCESSION,
        "geo_record": GEO_RECORD,
        "report": relpath(report_path),
        "summary": relpath(summary_path),
        "inventory": relpath(inventory_path),
        "prediction_table": relpath(prediction_path),
        "figures": [
            relpath(FIG_DIR / "panel_scores_by_structural_endpoint.png"),
            relpath(FIG_DIR / "counts_monitor_auc_summary.png"),
        ],
        "lamp_dirs": [relpath(OUT / "lamp" / monitor["id"]) for monitor in MONITORS],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(report_path)
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-cells",
        type=int,
        default=60000,
        help="Use first N matrix-order cells; 0 means all cells and requires a full matrix scan.",
    )
    return parser.parse_args(argv)


def ensure_inputs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for filename in SUPPLEMENTARY_FILES.values():
        path = DATA_DIR / filename
        min_size = 900_000_000 if filename.endswith(".mtx.gz") else 100
        if path.exists() and path.stat().st_size > min_size:
            continue
        url = f"{SUPPL_BASE}/{filename}"
        print(f"Downloading {url}")
        with urllib.request.urlopen(url, timeout=240) as response:
            path.write_bytes(response.read())


def build_prediction_table(max_cells: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    genes = pd.read_csv(DATA_DIR / SUPPLEMENTARY_FILES["gene_indices"], sep="\t")
    cells = pd.read_csv(DATA_DIR / SUPPLEMENTARY_FILES["cell_indices"], sep="\t")
    metadata = pd.read_csv(DATA_DIR / SUPPLEMENTARY_FILES["cell_metadata"], sep="\t")
    if max_cells and max_cells > 0:
        cells = cells.head(max_cells).copy()

    selected_genes = sorted({gene for panel in PANELS.values() for gene in panel})
    panel_counts, extraction = extract_marker_counts(genes, len(cells), selected_genes)
    table = cells.merge(metadata, left_on="cell_name", right_on="cell", how="left")
    if table["cell"].isna().any():
        raise RuntimeError("Cell index to metadata join failed for some cells")

    libsize = panel_counts["library_size"].astype(float)
    detected_genes = panel_counts["detected_genes"].astype(float)
    table["library_size"] = libsize
    table["detected_genes"] = detected_genes
    table["log_library_size"] = np.log1p(libsize)
    table["log_detected_genes"] = np.log1p(detected_genes)

    normalized = normalize_marker_counts(panel_counts["gene_counts"], libsize)
    for panel_name, panel in PANELS.items():
        present = [gene for gene in panel if gene in normalized]
        table[f"{panel_name}_panel_score"] = panel_score(normalized, present)
        table[f"{panel_name}_genes_present"] = len(present)

    table["combined_disjoint_biology_score"] = 0.5 * (
        table["calcium_ephys_panel_score"] + table["metabolic_panel_score"]
    )
    table["diffday_num"] = table["diffday"].map(parse_day).astype(float)
    table["diffday_numeric_score"] = minmax(table["diffday_num"])
    table["dpt_pseudotime_score"] = pd.to_numeric(table["dpt_pseudotime"], errors="coerce")
    table["annotation_cm_score"] = (table["type"] == "CM").astype(float)
    table["cell_cycle_exit_score"] = -0.5 * (zscore(table["S.Score"]) + zscore(table["G2M.Score"]))
    table["demux_dbl_log10"] = np.log10(
        pd.to_numeric(table["demux.dbl.prb"], errors="coerce").fillna(0.0) + 1e-300
    )
    table["demux_dbl_z"] = zscore(table["demux_dbl_log10"])

    structural = table["structural_panel_score"]
    threshold = float(structural.quantile(0.70))
    table["label_structural_maturity_high"] = (structural >= threshold).astype(int)
    table["structural_endpoint_score"] = structural

    keep = [
        "cell_name",
        "cell_index",
        "sample",
        "exp.grp",
        "individual",
        "diffday",
        "diffday_num",
        "type",
        "leiden",
        "label_structural_maturity_high",
        "structural_endpoint_score",
        "structural_panel_score",
        "calcium_ephys_panel_score",
        "metabolic_panel_score",
        "combined_disjoint_biology_score",
        "cell_cycle_panel_score",
        "diffday_numeric_score",
        "dpt_pseudotime_score",
        "annotation_cm_score",
        "cell_cycle_exit_score",
        "demux_dbl_z",
        "log_library_size",
        "log_detected_genes",
        "library_size",
        "detected_genes",
    ]
    table = table[keep].rename(columns={"cell_name": "cell_id", "exp.grp": "collection_id"})

    inventory = {
        "accession": ACCESSION,
        "geo_record": GEO_RECORD,
        "matrix_file": str(DATA_DIR / SUPPLEMENTARY_FILES["cell_counts"]),
        "audit_rows": int(len(table)),
        "max_cells": int(max_cells),
        "structural_endpoint_quantile": 0.70,
        "structural_endpoint_threshold": threshold,
        "positive_rows": int(table["label_structural_maturity_high"].sum()),
        "panels": PANELS,
        "genes_found": extraction["genes_found"],
        "genes_missing": extraction["genes_missing"],
        "matrix_header": extraction["matrix_header"],
        "entries_scanned": extraction["entries_scanned"],
        "stopped_at_column": extraction["stopped_at_column"],
        "diffday_counts": {
            str(k): int(v) for k, v in table["diffday"].value_counts().sort_index().items()
        },
        "cell_type_counts": {
            str(k): int(v) for k, v in table["type"].value_counts().items()
        },
        "n_individuals": int(table["individual"].nunique()),
        "n_collections": int(table["collection_id"].nunique()),
        "contract": {
            "endpoint_axis": "structural maturation marker panel high state",
            "allowed_probe_axes": ["calcium/electrophysiology", "metabolic"],
            "forbidden_axes": [
                "differentiation day",
                "published pseudotime",
                "published annotation",
                "endpoint structural panel as a monitor",
            ],
            "matching_axes": ["diffday", "cell-cycle scores", "doublet probability"],
        },
    }
    return table, inventory


def extract_marker_counts(
    genes: pd.DataFrame,
    n_cells: int,
    selected_genes: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"panel_counts_first_{n_cells}.npz"
    cache_meta_path = CACHE_DIR / f"panel_counts_first_{n_cells}.json"
    if cache_path.exists() and cache_meta_path.exists():
        cached = np.load(cache_path)
        meta = json.loads(cache_meta_path.read_text(encoding="utf-8"))
        return {
            "gene_counts": {gene: cached[gene] for gene in meta["genes_found"]},
            "library_size": cached["library_size"],
            "detected_genes": cached["detected_genes"],
        }, meta

    gene_hits = genes[genes["gene_name"].isin(selected_genes)].copy()
    index_to_gene = {
        int(row.gene_index): str(row.gene_name) for row in gene_hits.itertuples(index=False)
    }
    missing = sorted(set(selected_genes) - set(index_to_gene.values()))
    counts = {gene: np.zeros(n_cells, dtype=np.float32) for gene in index_to_gene.values()}
    library_size = np.zeros(n_cells, dtype=np.float32)
    detected_genes = np.zeros(n_cells, dtype=np.float32)

    matrix_path = DATA_DIR / SUPPLEMENTARY_FILES["cell_counts"]
    entries_scanned = 0
    stopped_at_column = None
    with gzip.open(matrix_path, "rb") as handle:
        header = handle.readline().decode("utf-8").strip()
        dims_line = handle.readline().decode("utf-8").strip()
        n_gene_rows, n_cell_cols, nnz = [int(x) for x in dims_line.split()]
        for raw in handle:
            parts = raw.split()
            if len(parts) != 3:
                continue
            col = int(parts[1])
            if col > n_cells:
                stopped_at_column = col
                break
            row = int(parts[0])
            value = float(parts[2])
            idx = col - 1
            library_size[idx] += value
            if value > 0:
                detected_genes[idx] += 1
            gene = index_to_gene.get(row)
            if gene is not None:
                counts[gene][idx] = value
            entries_scanned += 1
            if entries_scanned % 10_000_000 == 0:
                print(f"scanned {entries_scanned:,} matrix entries through column {col:,}")

    meta = {
        "genes_found": sorted(counts),
        "genes_missing": missing,
        "matrix_header": {
            "header": header,
            "n_gene_rows": n_gene_rows,
            "n_cell_cols": n_cell_cols,
            "nnz": nnz,
        },
        "entries_scanned": entries_scanned,
        "stopped_at_column": stopped_at_column,
    }
    np.savez_compressed(
        cache_path,
        library_size=library_size,
        detected_genes=detected_genes,
        **counts,
    )
    cache_meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"gene_counts": counts, "library_size": library_size, "detected_genes": detected_genes}, meta


def normalize_marker_counts(
    gene_counts: dict[str, np.ndarray],
    library_size: np.ndarray,
) -> dict[str, np.ndarray]:
    lib = np.asarray(library_size, dtype=float)
    lib = np.where(lib <= 0, np.nan, lib)
    normalized: dict[str, np.ndarray] = {}
    for gene, values in gene_counts.items():
        cpm = np.asarray(values, dtype=float) / lib * 10_000.0
        normalized[gene] = zscore(np.log1p(np.nan_to_num(cpm, nan=0.0)))
    return normalized


def panel_score(normalized: dict[str, np.ndarray], genes: list[str]) -> np.ndarray:
    if not genes:
        raise RuntimeError("Panel has no genes in count matrix")
    matrix = np.vstack([normalized[gene] for gene in genes])
    return np.nanmean(matrix, axis=0)


def build_config(monitor: dict[str, Any]) -> dict[str, Any]:
    latest_offset_h = float(monitor.get("latest_offset_h", 0))
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"{ACCESSION} scRNA counts: {monitor['name']}",
            "task": "Count-level disjoint biological-axis audit for hiPSC-CM differentiation",
            "role": "LAMP-Bio real scRNA count-matrix pilot",
            "source": GEO_RECORD,
            "monitor_id": monitor["id"],
            "monitor_description": monitor["description"],
            "expected_result": monitor["expected"],
        },
        "columns": {
            "subject_id": "cell_id",
            "label": "label_structural_maturity_high",
            "positive_value": 1,
            "score": monitor["score"],
            "anchor_time": "diffday_num",
        },
        "temporal_isolation": {
            "anchor": "diffday_num",
            "valid_features_must_be": "no day, pseudotime, annotation, or endpoint-axis features in valid score",
            "frozen_before_holdout": [
                "GSE175634 accession",
                "structural endpoint marker panel",
                "disjoint allowed calcium/electrophysiology and metabolic panels",
                "forbidden day/pseudotime/annotation shortcuts",
                "LAMP thresholds",
            ],
            "valid_score_features": [
                {"name": feature, "latest_offset_h": latest_offset_h}
                for feature in monitor["features"]
            ],
        },
        "forbidden_features": {
            "columns": [
                "structural_panel_score",
                "diffday_numeric_score",
                "dpt_pseudotime_score",
                "annotation_cm_score",
            ],
            "valid_score_features": list(monitor["features"]),
        },
        "sentinels": {
            "structural_endpoint_oracle": {
                "column": "structural_panel_score",
                "role": "endpoint_adjacent_oracle",
                "expected_signature": "same marker axis that defines the endpoint",
            },
            "day_protocol": {
                "column": "diffday_numeric_score",
                "role": "timepoint_protocol_shortcut",
                "expected_signature": "differentiation day should not be used as molecular evidence",
            },
            "published_pseudotime": {
                "column": "dpt_pseudotime_score",
                "role": "endpoint_adjacent_oracle",
                "expected_signature": "published pseudotime is inferred from full expression trajectory",
            },
            "published_annotation": {
                "column": "annotation_cm_score",
                "role": "annotation_shortcut",
                "expected_signature": "published cell-type annotation is a label-adjacent channel",
            },
        },
        "negative_controls": {"n_permutations": 60, "seed": SEED},
        "visible_state_matching": {
            "columns": [
                "diffday_numeric_score",
                "cell_cycle_exit_score",
                "demux_dbl_z",
            ],
            "n_bins": 3,
            "min_bin_size": 50,
        },
        "early_window_sensitivity": {
            "score_columns": [
                "calcium_ephys_panel_score",
                "metabolic_panel_score",
                "combined_disjoint_biology_score",
                "diffday_numeric_score",
                "dpt_pseudotime_score",
            ]
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.02,
            "matched_collapse_max": 0.005,
            "score_thresholds": [-0.75, 0.0, 0.75],
        },
    }


def stability_summary(
    table: pd.DataFrame,
    label_col: str,
    score_col: str,
    n_bootstrap: int = 100,
) -> dict[str, Any]:
    labels = table[label_col].astype(int).to_numpy()
    scores = pd.to_numeric(table[score_col], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(scores)
    labels = labels[mask]
    scores = scores[mask]
    rng = np.random.default_rng(SEED)
    boot_aucs = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, len(labels), size=len(labels))
        auc = auc_score(labels[idx].tolist(), scores[idx].tolist())
        if auc is not None:
            boot_aucs.append(auc)

    leave_individual = []
    for individual, group in table.groupby("individual"):
        sub = table[table["individual"] != individual]
        auc = auc_score(
            sub[label_col].astype(int).tolist(),
            pd.to_numeric(sub[score_col], errors="coerce").fillna(0.0).tolist(),
        )
        leave_individual.append({"held_out_individual": str(individual), "auc": auc})

    return {
        "bootstrap_auc_mean": float(np.mean(boot_aucs)) if boot_aucs else None,
        "bootstrap_auc_sd": float(np.std(boot_aucs, ddof=1)) if len(boot_aucs) > 1 else None,
        "bootstrap_pass_rate_auc_ge_0p60": float(np.mean(np.asarray(boot_aucs) >= 0.60))
        if boot_aucs
        else None,
        "leave_individual_auc_min": float(
            np.nanmin([row["auc"] for row in leave_individual if row["auc"] is not None])
        )
        if leave_individual
        else None,
    }


def summary_row(
    monitor: dict[str, Any],
    result: dict[str, Any],
    stability: dict[str, Any],
) -> dict[str, Any]:
    dossier = result["failure_mode_dossier"]
    primary = result["primary_score"]
    bio_diagnosis = biological_diagnosis(dossier, stability)
    return {
        "monitor": monitor["name"],
        "monitor_id": monitor["id"],
        "expected": monitor["expected"],
        "score": monitor["score"],
        "auc": primary.get("auc"),
        "audit_pass": dossier["audit_pass_candidate"],
        "biological_diagnosis": bio_diagnosis,
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "threshold_fragile": result["threshold_sensitivity"].get("fragile"),
        "bootstrap_auc_mean": stability["bootstrap_auc_mean"],
        "bootstrap_auc_sd": stability["bootstrap_auc_sd"],
        "bootstrap_pass_rate_auc_ge_0p60": stability["bootstrap_pass_rate_auc_ge_0p60"],
        "leave_individual_auc_min": stability["leave_individual_auc_min"],
        "structural_oracle_auc": result["sentinels"]["structural_endpoint_oracle"].get("auc"),
        "day_sentinel_auc": result["sentinels"]["day_protocol"].get("auc"),
        "pseudotime_sentinel_auc": result["sentinels"]["published_pseudotime"].get("auc"),
        "annotation_sentinel_auc": result["sentinels"]["published_annotation"].get("auc"),
        "output_classes": ";".join(dossier["output_classes"]),
        "key_reasons": key_reasons(result),
    }


def biological_diagnosis(dossier: dict[str, Any], stability: dict[str, Any]) -> str:
    if not dossier["audit_pass_candidate"]:
        return "not_biologically_interpretable_under_contract"
    pass_rate = stability.get("bootstrap_pass_rate_auc_ge_0p60") or 0.0
    leave_min = stability.get("leave_individual_auc_min") or 0.0
    if pass_rate >= 0.90 and leave_min >= 0.60:
        return "valid_biological_signal_stable"
    return "valid_biological_signal_fragile"


def key_reasons(result: dict[str, Any]) -> str:
    reasons = []
    if not result["temporal_isolation"]["passed"]:
        reasons.append("temporal isolation")
    if not result["forbidden_feature_screen"]["passed"]:
        reasons.append("forbidden feature")
    if result["threshold_sensitivity"].get("fragile"):
        reasons.append("threshold fragile")
    if not result["failure_mode_dossier"].get("audit_pass_candidate"):
        classes = set(result["failure_mode_dossier"]["output_classes"])
        if "visible_state_confounding" in classes:
            reasons.append("matched collapse")
        if "null_or_destroyed_signal" in classes:
            reasons.append("null/destroyed")
    return ", ".join(dict.fromkeys(reasons)) or "none"


def write_report(
    report_path: Path,
    table: pd.DataFrame,
    inventory: dict[str, Any],
    rows: list[dict[str, Any]],
    max_cells: int,
) -> None:
    lines = [
        "# GSE175634 scRNA Count-Matrix LAMP-Bio Audit",
        "",
        "This count-level pilot asks whether disjoint biological marker axes survive",
        "after day, published pseudotime, published annotation, and endpoint-axis",
        "reuse are treated as forbidden/sentinel channels.",
        "",
        "## Contract",
        "",
        f"- Source: `{ACCESSION}` ({GEO_RECORD})",
        f"- Rows: {len(table):,} first matrix-order cells (max_cells={max_cells}).",
        f"- Individuals: {inventory['n_individuals']}; collections: {inventory['n_collections']}.",
        "- Endpoint axis: high structural maturation marker-panel score.",
        "- Allowed disjoint axes: calcium/electrophysiology and metabolic marker panels.",
        "- Forbidden/sentinel axes: day, pseudotime, published annotation, and structural endpoint score as monitor.",
        f"- Structural endpoint positives: {inventory['positive_rows']:,} / {inventory['audit_rows']:,}.",
        "",
        "## LAMP Results",
        "",
        "| Monitor | AUC | Diagnosis | LAMP | Key reasons | Bootstrap pass | Leave-individual min AUC |",
        "| --- | ---: | --- | --- | --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {monitor} | {auc:.3f} | {diag} | {lamp} | {reasons} | {boot:.2f} | {leave:.3f} |".format(
                monitor=row["monitor"],
                auc=float(row["auc"]) if row["auc"] is not None else float("nan"),
                diag=row["biological_diagnosis"],
                lamp="PASS" if row["audit_pass"] else "FAIL",
                reasons=row["key_reasons"],
                boot=float(row["bootstrap_pass_rate_auc_ge_0p60"] or 0.0),
                leave=float(row["leave_individual_auc_min"] or float("nan")),
            )
        )
    lines.extend(
        [
            "",
            "## Sentinel AUCs",
            "",
            "| Sentinel | AUC vs structural endpoint |",
            "| --- | ---: |",
            f"| Structural endpoint oracle | {float(rows[0]['structural_oracle_auc']):.3f} |",
            f"| Differentiation day | {float(rows[0]['day_sentinel_auc']):.3f} |",
            f"| Published pseudotime | {float(rows[0]['pseudotime_sentinel_auc']):.3f} |",
            f"| Published CM annotation | {float(rows[0]['annotation_sentinel_auc']):.3f} |",
            "",
            "## Interpretation",
            "",
            "A PASS here would mean a disjoint marker axis still separates structural",
            "maturation after matching on day and QC-like visible state. A fragile PASS",
            "would be interesting but not enough for a strong maturation claim. A FAIL",
            "means the apparent biological signal is null, shortcut-like, threshold",
            "fragile, or violates the declared information contract.",
            "",
            "This is not yet a true early-to-late longitudinal prediction. It is a",
            "same-cell disjoint-axis contract test. The next stronger design is an",
            "individual/collection-level early-day panel predicting late-day endpoint",
            "held out by individual or collection.",
            "",
            "## Files",
            "",
            f"- Prediction table: `{relpath(OUT / 'gse175634_scrna_counts_prediction_table.csv')}`",
            f"- Summary: `{relpath(OUT / 'gse175634_scrna_counts_lamp_summary.csv')}`",
            f"- Inventory: `{relpath(OUT / 'gse175634_scrna_counts_inventory.json')}`",
            f"- Figure: `{relpath(FIG_DIR / 'panel_scores_by_structural_endpoint.png')}`",
            f"- Figure: `{relpath(FIG_DIR / 'counts_monitor_auc_summary.png')}`",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_panel_scores(table: pd.DataFrame, path: Path) -> None:
    cols = [
        "structural_panel_score",
        "calcium_ephys_panel_score",
        "metabolic_panel_score",
        "diffday_numeric_score",
        "dpt_pseudotime_score",
    ]
    labels = table["label_structural_maturity_high"].map({0: "structural low", 1: "structural high"})
    data = []
    for col in cols:
        for label in ["structural low", "structural high"]:
            values = pd.to_numeric(table.loc[labels == label, col], errors="coerce").dropna()
            data.append({"score": col, "label": label, "mean": values.mean(), "sem": values.sem()})
    frame = pd.DataFrame(data)
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(cols))
    width = 0.35
    for offset, label in [(-width / 2, "structural low"), (width / 2, "structural high")]:
        sub = frame[frame["label"] == label]
        ax.bar(x + offset, sub["mean"], width=width, yerr=sub["sem"], label=label, color="#666666" if label.endswith("low") else "#111111")
    ax.set_xticks(x)
    ax.set_xticklabels(cols, rotation=25, ha="right")
    ax.set_ylabel("Mean score")
    ax.set_title("Disjoint panel scores by structural endpoint")
    ax.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_monitor_auc(rows: list[dict[str, Any]], path: Path) -> None:
    labels = [row["monitor_id"] for row in rows]
    aucs = [float(row["auc"] or 0.0) for row in rows]
    colors = ["#222222" if row["audit_pass"] else "#999999" for row in rows]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(labels, aucs, color=colors, edgecolor="black", linewidth=0.8)
    ax.axhline(0.60, color="black", linestyle="--", linewidth=1.0)
    ax.axhline(0.95, color="black", linestyle=":", linewidth=1.0)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("AUC")
    ax.set_title("GSE175634 count-level LAMP monitors")
    ax.tick_params(axis="x", labelrotation=25)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def parse_day(value: Any) -> int:
    return int(str(value).strip().lower().replace("day", "").replace(" ", ""))


def zscore(values: Any) -> np.ndarray:
    arr = np.asarray(pd.to_numeric(pd.Series(values), errors="coerce"), dtype=float)
    mean = np.nanmean(arr)
    sd = np.nanstd(arr, ddof=1)
    if not np.isfinite(sd) or sd == 0:
        return np.zeros_like(arr)
    return (arr - mean) / sd


def minmax(values: Any) -> np.ndarray:
    arr = np.asarray(pd.to_numeric(pd.Series(values), errors="coerce"), dtype=float)
    lo = np.nanmin(arr)
    hi = np.nanmax(arr)
    if not np.isfinite(hi - lo) or hi == lo:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def relpath(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


if __name__ == "__main__":
    raise SystemExit(main())
