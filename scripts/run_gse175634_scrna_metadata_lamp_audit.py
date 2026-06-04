#!/usr/bin/env python3
"""GSE175634 real hiPSC-CM scRNA metadata LAMP-Bio audit.

GSE175634 is a time-course single-cell RNA-seq dataset of differentiating human
iPSC-derived cardiac cells. This runner intentionally starts with the small GEO
metadata files rather than the ~1 GB sparse count matrix. The goal is to create
a real scRNA provenance/annotation smoke test:

- QC and cell-cycle metadata probe: weak allowed metadata evidence.
- Pseudotime probe: biologically meaningful, but endpoint-adjacent for an early
  prediction claim because it is inferred from the full expression trajectory.
- Timepoint shortcut: differentiation day as protocol structure.
- Annotation oracle: direct cell-type label leakage.

The result should be read as a dataset-selection and contract test, not as a
marker-panel maturation claim. Marker-panel biology requires downloading the
count matrix and defining disjoint endpoint/evidence genes.
"""

from __future__ import annotations

import argparse
import csv
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


ACCESSION = "GSE175634"
GEO_RECORD = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={ACCESSION}"
SUPPL_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE175nnn/GSE175634/suppl"
DATA_DIR = ROOT / "data" / "raw" / "gse175634"
OUT = ROOT / "results" / "lamp_bio_scrna" / "gse175634_metadata"
FIG_DIR = OUT / "figures"
SEED = 20260605

SUPPLEMENTARY_FILES = {
    "cell_metadata": "GSE175634_cell_metadata.tsv.gz",
    "cell_indices": "GSE175634_cell_indices.tsv.gz",
    "gene_indices": "GSE175634_gene_indices_counts.tsv.gz",
    "collection_metadata": "GSE175634_collection_metadata.txt.gz",
    "experimental_design": "GSE175634_experimental_design.txt.gz",
}

MONITORS = [
    {
        "id": "cell_cycle_exit_metadata_probe",
        "name": "Cell-cycle exit metadata probe",
        "score": "cell_cycle_exit_score",
        "features": ["cell_cycle_exit_score"],
        "expected": "NULL_OR_FRAGILE",
        "description": (
            "Allowed metadata-only probe. It asks whether low S/G2M activity is "
            "enough to support a cardiomyocyte-state claim."
        ),
    },
    {
        "id": "pseudotime_endpoint_adjacent_probe",
        "name": "DPT pseudotime endpoint-adjacent probe",
        "score": "dpt_pseudotime_score",
        "features": ["dpt_pseudotime_score"],
        "expected": "FAIL",
        "latest_offset_h": 999,
        "description": (
            "Uses trajectory pseudotime inferred from the expression manifold. "
            "This is useful biology, but not clean early evidence for this "
            "metadata-only contract."
        ),
    },
    {
        "id": "timepoint_protocol_shortcut",
        "name": "Differentiation-day protocol shortcut",
        "score": "diffday_numeric_score",
        "features": ["diffday_numeric_score"],
        "expected": "FAIL",
        "description": (
            "Uses differentiation day / protocol timing rather than cell-intrinsic "
            "evidence."
        ),
    },
    {
        "id": "annotation_oracle",
        "name": "Published annotation oracle",
        "score": "annotation_oracle_score",
        "features": ["annotation_oracle_score"],
        "expected": "FAIL",
        "latest_offset_h": 999,
        "description": "Uses the published cell-type endpoint label itself.",
    },
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    ensure_metadata()

    cells, collections, design = load_metadata()
    table, inventory = build_prediction_table(cells, collections, max_cells=args.max_cells)
    prediction_path = OUT / "gse175634_scrna_metadata_prediction_table.csv"
    table.to_csv(prediction_path, index=False, lineterminator="\n")

    summary_rows: list[dict[str, Any]] = []
    for monitor in MONITORS:
        config = build_config(monitor)
        config_path = OUT / "configs" / f"{monitor['id']}.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        result = run_audit(config_path, prediction_path, OUT / "lamp" / monitor["id"])
        summary_rows.append(summary_row(monitor, result))

    summary_path = OUT / "gse175634_scrna_metadata_lamp_summary.csv"
    write_csv(summary_path, summary_rows)

    inventory_path = OUT / "gse175634_scrna_metadata_inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    plot_cell_type_by_day(table, FIG_DIR / "cell_type_by_day.png")
    plot_monitor_auc(summary_rows, FIG_DIR / "monitor_auc_summary.png")

    report_path = OUT / "gse175634_scrna_metadata_lamp_report.md"
    write_report(
        report_path=report_path,
        table=table,
        cells=cells,
        collections=collections,
        design=design,
        inventory=inventory,
        summary_rows=summary_rows,
        max_cells=args.max_cells,
    )

    manifest = {
        "accession": ACCESSION,
        "geo_record": GEO_RECORD,
        "report": relpath(report_path),
        "summary": relpath(summary_path),
        "inventory": relpath(inventory_path),
        "prediction_table": relpath(prediction_path),
        "figures": [
            relpath(FIG_DIR / "cell_type_by_day.png"),
            relpath(FIG_DIR / "monitor_auc_summary.png"),
        ],
        "lamp_dirs": [relpath(OUT / "lamp" / monitor["id"]) for monitor in MONITORS],
        "raw_metadata_files": {
            key: str(DATA_DIR / filename) for key, filename in SUPPLEMENTARY_FILES.items()
        },
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
        help=(
            "Maximum number of cells to include in the committed audit table. "
            "Use 0 for all cells."
        ),
    )
    return parser.parse_args(argv)


def ensure_metadata() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for filename in SUPPLEMENTARY_FILES.values():
        path = DATA_DIR / filename
        if path.exists() and path.stat().st_size > 100:
            continue
        url = f"{SUPPL_BASE}/{filename}"
        print(f"Downloading {url}")
        with urllib.request.urlopen(url, timeout=240) as response:
            path.write_bytes(response.read())


def load_metadata() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cells = pd.read_csv(DATA_DIR / SUPPLEMENTARY_FILES["cell_metadata"], sep="\t")
    collections = pd.read_csv(DATA_DIR / SUPPLEMENTARY_FILES["collection_metadata"], sep="\t")
    design = pd.read_csv(DATA_DIR / SUPPLEMENTARY_FILES["experimental_design"], sep="\t")
    return cells, collections, design


def build_prediction_table(
    cells: pd.DataFrame,
    collections: pd.DataFrame,
    max_cells: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = cells.copy()
    df["diffday_num"] = df["diffday"].map(parse_day).astype(float)
    df["individual"] = df["individual"].astype(str)

    collection_context = normalize_collection_metadata(collections)
    df = df.merge(
        collection_context,
        how="left",
        left_on=["exp.grp", "individual", "diffday_num"],
        right_on=["orig_ident", "individual", "diffday_num"],
    )
    joined_context_rate = float(df["experiment_batch"].notna().mean())

    if max_cells and len(df) > max_cells:
        df = (
            df.sample(n=max_cells, random_state=SEED)
            .sort_values(["diffday_num", "type", "cell"])
            .reset_index(drop=True)
        )
    else:
        df = df.sort_values(["diffday_num", "type", "cell"]).reset_index(drop=True)

    df["label_cm_state"] = (df["type"] == "CM").astype(int)
    df["label_terminal_cardiac_state"] = df["type"].isin(["CM", "CF"]).astype(int)

    df["S_z"] = zscore(df["S.Score"])
    df["G2M_z"] = zscore(df["G2M.Score"])
    df["CC_z"] = zscore(df["CC.Difference"])
    df["demux_dbl_log10"] = np.log10(
        pd.to_numeric(df["demux.dbl.prb"], errors="coerce").fillna(0.0) + 1e-300
    )
    df["demux_dbl_z"] = zscore(df["demux_dbl_log10"])
    df["diffday_numeric_score"] = minmax(df["diffday_num"])
    df["cell_cycle_exit_score"] = -0.5 * (df["S_z"] + df["G2M_z"])
    df["dpt_pseudotime_score"] = pd.to_numeric(df["dpt_pseudotime"], errors="coerce")
    df["annotation_oracle_score"] = df["label_cm_state"].astype(float)
    df["terminal_state_oracle_score"] = df["label_terminal_cardiac_state"].astype(float)
    df["collection_beating_score"] = (
        pd.to_numeric(df["beating_on_collection"], errors="coerce").fillna(0.0)
        + 0.01 * pd.to_numeric(df["percent_beating"], errors="coerce").fillna(0.0)
    )
    df["experiment_batch_score"] = minmax(
        pd.to_numeric(df["experiment_batch"], errors="coerce").fillna(-1.0)
    )
    df["leiden_label_rate_score"] = df.groupby("leiden")["label_cm_state"].transform("mean")
    df["individual_cm_rate_score"] = df.groupby("individual")["label_cm_state"].transform(
        "mean"
    )
    df["collection_cm_rate_score"] = df.groupby("exp.grp")["label_cm_state"].transform(
        "mean"
    )

    keep_columns = [
        "cell",
        "sample",
        "exp.grp",
        "individual",
        "diffday",
        "diffday_num",
        "type",
        "leiden",
        "label_cm_state",
        "label_terminal_cardiac_state",
        "S.Score",
        "G2M.Score",
        "CC.Difference",
        "demux.dbl.prb",
        "dpt_pseudotime",
        "S_z",
        "G2M_z",
        "CC_z",
        "demux_dbl_z",
        "diffday_numeric_score",
        "cell_cycle_exit_score",
        "dpt_pseudotime_score",
        "annotation_oracle_score",
        "terminal_state_oracle_score",
        "collection_beating_score",
        "experiment_batch_score",
        "leiden_label_rate_score",
        "individual_cm_rate_score",
        "collection_cm_rate_score",
        "experiment_batch",
        "diff_start_batch",
        "day0_confluence",
        "beating_on_collection",
        "percent_beating",
        "debris_score",
    ]
    table = df[keep_columns].rename(
        columns={
            "cell": "cell_id",
            "exp.grp": "collection_id",
            "S.Score": "s_score",
            "G2M.Score": "g2m_score",
            "CC.Difference": "cell_cycle_difference",
            "demux.dbl.prb": "demux_doublet_probability",
            "dpt_pseudotime": "published_dpt_pseudotime",
        }
    )

    inventory = {
        "accession": ACCESSION,
        "geo_record": GEO_RECORD,
        "full_cell_metadata_rows": int(len(cells)),
        "audit_rows": int(len(table)),
        "max_cells": int(max_cells),
        "collection_context_join_rate": joined_context_rate,
        "n_individuals_full": int(cells["individual"].nunique()),
        "n_collections_full": int(cells["exp.grp"].nunique()),
        "n_samples_full": int(cells["sample"].nunique()),
        "diffday_counts_full": {
            str(k): int(v) for k, v in cells["diffday"].value_counts().sort_index().items()
        },
        "cell_type_counts_full": {
            str(k): int(v) for k, v in cells["type"].value_counts().items()
        },
        "audit_diffday_counts": {
            str(k): int(v) for k, v in table["diffday"].value_counts().sort_index().items()
        },
        "audit_cell_type_counts": {
            str(k): int(v) for k, v in table["type"].value_counts().items()
        },
        "limitations": [
            "This first-pass artifact uses GEO metadata only.",
            "Marker-panel maturation claims require downloading the sparse count matrix.",
            "Published pseudotime and cell-type labels are treated as endpoint-adjacent sentinels, not clean early evidence.",
        ],
    }
    return table, inventory


def normalize_collection_metadata(collections: pd.DataFrame) -> pd.DataFrame:
    frame = collections.copy()
    frame["individual"] = frame["Line"].astype(str).str.replace("NA", "", regex=False)
    frame["diffday_num"] = pd.to_numeric(frame["Differentiation Day"], errors="coerce")
    frame = frame.rename(
        columns={
            "orig.ident": "orig_ident",
            "Experiment Batch": "experiment_batch",
            "Diff Start  Batch": "diff_start_batch",
            "Day 0 Confluence (%)": "day0_confluence",
            "Beating on day of collection Y 1/N 0": "beating_on_collection",
            "% beating when collected": "percent_beating",
            "debris (0-none or not noted, 1-some, 2- lots)": "debris_score",
        }
    )
    return frame[
        [
            "orig_ident",
            "individual",
            "diffday_num",
            "experiment_batch",
            "diff_start_batch",
            "day0_confluence",
            "beating_on_collection",
            "percent_beating",
            "debris_score",
        ]
    ]


def parse_day(value: Any) -> int:
    text = str(value).strip().lower().replace("day", "").replace(" ", "")
    return int(text)


def zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    mean = float(values.mean())
    sd = float(values.std())
    if not np.isfinite(sd) or sd == 0:
        return values * 0.0
    return (values - mean) / sd


def minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    lo = float(values.min())
    hi = float(values.max())
    if not np.isfinite(hi - lo) or hi == lo:
        return values * 0.0
    return (values - lo) / (hi - lo)


def build_config(monitor: dict[str, Any]) -> dict[str, Any]:
    latest_offset_h = float(monitor.get("latest_offset_h", 0))
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"{ACCESSION} scRNA metadata: {monitor['name']}",
            "task": "Metadata-first LAMP-Bio audit of hiPSC-derived cardiac differentiation",
            "role": "Real scRNA dataset-selection and contract smoke test",
            "source": GEO_RECORD,
            "monitor_id": monitor["id"],
            "monitor_description": monitor["description"],
            "expected_result": monitor["expected"],
        },
        "columns": {
            "subject_id": "cell_id",
            "label": "label_cm_state",
            "positive_value": 1,
            "score": monitor["score"],
            "anchor_time": "diffday_num",
        },
        "temporal_isolation": {
            "anchor": "diffday_num",
            "valid_features_must_be": (
                "feature must be available without reading published endpoint labels, "
                "future trajectory pseudotime, or protocol timepoint shortcuts"
            ),
            "frozen_before_holdout": [
                "GSE175634 accession",
                "metadata-only first-pass contract",
                "cardiomyocyte-state endpoint label",
                "forbidden endpoint-adjacent sentinels",
                "LAMP thresholds",
            ],
            "valid_score_features": [
                {"name": feature, "latest_offset_h": latest_offset_h}
                for feature in monitor["features"]
            ],
        },
        "forbidden_features": {
            "columns": [
                "dpt_pseudotime_score",
                "diffday_numeric_score",
                "annotation_oracle_score",
                "terminal_state_oracle_score",
                "collection_beating_score",
                "experiment_batch_score",
                "leiden_label_rate_score",
                "individual_cm_rate_score",
                "collection_cm_rate_score",
            ],
            "valid_score_features": list(monitor["features"]),
        },
        "sentinels": {
            "timepoint_protocol": {
                "column": "diffday_numeric_score",
                "role": "timepoint_protocol_shortcut",
                "expected_signature": "differentiation day is a protocol shortcut for endpoint state",
            },
            "published_pseudotime": {
                "column": "dpt_pseudotime_score",
                "role": "endpoint_adjacent_oracle",
                "expected_signature": "trajectory pseudotime is not clean early evidence here",
            },
            "annotation_oracle": {
                "column": "annotation_oracle_score",
                "role": "oracle_label",
                "expected_signature": "direct published cell-type label leakage",
            },
            "terminal_state_oracle": {
                "column": "terminal_state_oracle_score",
                "role": "oracle_label",
                "expected_signature": "broader terminal cardiac-state label leakage",
            },
            "collection_beating": {
                "column": "collection_beating_score",
                "role": "protocol_context_shortcut",
                "expected_signature": "collection-level beating notes are context, not cell-intrinsic evidence",
            },
            "experiment_batch": {
                "column": "experiment_batch_score",
                "role": "batch_shortcut",
                "expected_signature": "experiment batch checks provenance shortcut risk",
            },
            "leiden_cluster_label_rate": {
                "column": "leiden_label_rate_score",
                "role": "endpoint_adjacent_cluster_oracle",
                "expected_signature": "cluster label-rate score is endpoint-adjacent",
            },
            "individual_cm_rate": {
                "column": "individual_cm_rate_score",
                "role": "donor_batch_shortcut",
                "expected_signature": "line-level CM prevalence checks donor/protocol confounding",
            },
            "collection_cm_rate": {
                "column": "collection_cm_rate_score",
                "role": "collection_target_rate_shortcut",
                "expected_signature": "collection-level CM prevalence checks pooled-collection shortcut risk",
            },
        },
        "negative_controls": {"n_permutations": 80, "seed": SEED},
        "visible_state_matching": {
            "columns": ["S_z", "G2M_z", "demux_dbl_z", "diffday_numeric_score"],
            "n_bins": 3,
            "min_bin_size": 50,
        },
        "early_window_sensitivity": {
            "score_columns": [
                "cell_cycle_exit_score",
                "dpt_pseudotime_score",
                "diffday_numeric_score",
            ]
        },
        "leakage_proximity": {
            "baseline_score": "cell_cycle_exit_score",
            "oracle_proximity_alert_min": 0.01,
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
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
        "score": monitor["score"],
        "auc": primary.get("auc"),
        "inverted_auc": primary.get("inverted_auc"),
        "direction_ambiguous": primary.get("direction_ambiguous"),
        "audit_pass": dossier["audit_pass_candidate"],
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "threshold_fragile": result["threshold_sensitivity"].get("fragile"),
        "timepoint_sentinel_auc": result["sentinels"]["timepoint_protocol"].get("auc"),
        "pseudotime_sentinel_auc": result["sentinels"]["published_pseudotime"].get("auc"),
        "oracle_sentinel_auc": result["sentinels"]["annotation_oracle"].get("auc"),
        "output_classes": ";".join(dossier["output_classes"]),
        "key_reasons": key_reasons(result),
    }


def key_reasons(result: dict[str, Any]) -> str:
    reasons = []
    if not result["temporal_isolation"]["passed"]:
        reasons.append("temporal isolation")
    if not result["forbidden_feature_screen"]["passed"]:
        reasons.append("forbidden feature")
    if result["threshold_sensitivity"].get("fragile"):
        reasons.append("threshold fragile")
    classes = set(result["failure_mode_dossier"]["output_classes"])
    if "oracle_label_leakage_sentinel" in classes:
        reasons.append("oracle sentinel")
    if "protocol_batch_or_donor_shortcut_sentinel" in classes:
        reasons.append("protocol/donor sentinel")
    if "oracle_leakage_proximity_shift" in classes:
        reasons.append("oracle proximity")
    return ", ".join(dict.fromkeys(reasons)) or "none"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_cell_type_by_day(table: pd.DataFrame, path: Path) -> None:
    counts = table.pivot_table(
        index="diffday",
        columns="type",
        values="cell_id",
        aggfunc="count",
        fill_value=0,
    )
    counts = counts.div(counts.sum(axis=1), axis=0)
    order = [day for day in ["day0", "day1", "day3", "day5", "day7", "day11", "day15"] if day in counts.index]
    counts = counts.loc[order]
    ax = counts.plot(kind="bar", stacked=True, figsize=(9, 4), colormap="tab20")
    ax.set_ylabel("Cell-type fraction")
    ax.set_xlabel("Differentiation day")
    ax.set_title("GSE175634 scRNA cell states by day")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_monitor_auc(rows: list[dict[str, Any]], path: Path) -> None:
    labels = [row["monitor_id"] for row in rows]
    aucs = [row["auc"] if row["auc"] is not None else 0.0 for row in rows]
    colors = ["#444444" if bool(row["audit_pass"]) else "#999999" for row in rows]
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    ax.bar(labels, aucs, color=colors, edgecolor="black", linewidth=0.8)
    ax.axhline(0.60, color="black", linewidth=1.0, linestyle="--", label="valid_auc_min")
    ax.axhline(0.95, color="black", linewidth=1.0, linestyle=":", label="oracle_auc_min")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("AUC vs CM endpoint label")
    ax.set_title("Real scRNA metadata monitor scores")
    ax.tick_params(axis="x", labelrotation=25)
    ax.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def write_report(
    report_path: Path,
    table: pd.DataFrame,
    cells: pd.DataFrame,
    collections: pd.DataFrame,
    design: pd.DataFrame,
    inventory: dict[str, Any],
    summary_rows: list[dict[str, Any]],
    max_cells: int,
) -> None:
    cm_count = int(table["label_cm_state"].sum())
    rows = [
        "# GSE175634 Real scRNA Metadata LAMP-Bio Audit",
        "",
        "This is the first real hiPSC/hiPSC-CM single-cell RNA-seq artifact for LAMP-Bio.",
        "It is intentionally metadata-first: it tests provenance, annotation, QC/context",
        "and endpoint-adjacent sentinels before making marker-panel maturation claims.",
        "",
        "## Dataset Found",
        "",
        f"- Source: `{ACCESSION}` ({GEO_RECORD})",
        "- GEO summary: differentiating human iPSC-derived cardiac cells across multiple",
        "  timepoints, collections, and cell lines.",
        f"- Full cell metadata rows loaded: {len(cells):,}.",
        f"- Audit rows used: {len(table):,} (max-cells={max_cells}; use `--max-cells 0` for all rows).",
        f"- Individuals: {cells['individual'].nunique()}; collections: {cells['exp.grp'].nunique()}; samples: {cells['sample'].nunique()}.",
        f"- Collection-context join rate: {inventory['collection_context_join_rate']:.3f}.",
        f"- CM endpoint positives in audit table: {cm_count:,} / {len(table):,}.",
        "",
        "## Cell-State Inventory",
        "",
        "| Field | Values |",
        "| --- | --- |",
        f"| diffday | {', '.join(f'{k}: {v:,}' for k, v in inventory['audit_diffday_counts'].items())} |",
        f"| type | {', '.join(f'{k}: {v:,}' for k, v in inventory['audit_cell_type_counts'].items())} |",
        "",
        "## LAMP Monitors",
        "",
        "| Monitor | AUC | LAMP | Key reasons | Output classes |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for row in summary_rows:
        rows.append(
            "| {monitor} | {auc:.3f} | {status} | {reasons} | {classes} |".format(
                monitor=row["monitor"],
                auc=float(row["auc"]) if row["auc"] is not None else float("nan"),
                status="PASS" if row["audit_pass"] else "FAIL",
                reasons=row["key_reasons"],
                classes=row["output_classes"],
            )
        )

    rows.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `cell_cycle_exit_metadata_probe` is an intentionally weak allowed metadata",
            "  probe. It is a QC/annotation sanity check, not a maturation marker panel.",
            "- `dpt_pseudotime_score` is biologically meaningful but endpoint-adjacent for",
            "  this contract because pseudotime is inferred from the full expression",
            "  trajectory rather than available as a clean early measurement.",
            "- `diffday_numeric_score` tests the obvious protocol/timepoint shortcut.",
            "- `annotation_oracle_score` tests direct published-label leakage.",
            "",
            "## Why This Dataset Is Useful",
            "",
            "GSE175634 has exactly the metadata structure LAMP-Bio needs for a serious",
            "single-cell contract: cell-level labels, pseudotime, donor/line IDs,",
            "differentiation days, pooled collections, and collection-level experimental",
            "context. The next step is to download the sparse count matrix and define a",
            "disjoint marker-panel contract: endpoint axis versus allowed evidence axis.",
            "",
            "## Files",
            "",
            f"- Prediction table: `{relpath(OUT / 'gse175634_scrna_metadata_prediction_table.csv')}`",
            f"- Summary: `{relpath(OUT / 'gse175634_scrna_metadata_lamp_summary.csv')}`",
            f"- Inventory: `{relpath(OUT / 'gse175634_scrna_metadata_inventory.json')}`",
            f"- Figure: `{relpath(FIG_DIR / 'cell_type_by_day.png')}`",
            f"- Figure: `{relpath(FIG_DIR / 'monitor_auc_summary.png')}`",
            "",
            "## Limitations",
            "",
            "- This first pass does not use raw gene expression counts.",
            "- It should not be cited as evidence that an early transcriptomic maturation",
            "  monitor passes LAMP.",
            "- The useful result here is dataset suitability plus explicit detection of",
            "  endpoint-adjacent and protocol shortcut channels.",
        ]
    )
    report_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def relpath(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


if __name__ == "__main__":
    raise SystemExit(main())
