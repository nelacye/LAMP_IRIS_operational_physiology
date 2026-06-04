#!/usr/bin/env python3
"""GSE175634 pseudo-bulk rescue test for LAMP-Bio.

This is the direct follow-up to the cell-level GSE175634 count-axis audit.
It asks whether disjoint biological axes fail because of single-cell noise or
because the current structural endpoint is mostly supported by time/trajectory
structure rather than independent calcium/metabolic biology.

Default grouping is `sample`, which is an individual x differentiation-day
pseudo-bulk unit in the first 60k-cell pilot table. Cell-type annotation is not
used for grouping.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
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
CELL_TABLE = (
    ROOT
    / "results"
    / "lamp_bio_scrna"
    / "gse175634_counts"
    / "gse175634_scrna_counts_prediction_table.csv"
)
CELL_SUMMARY = (
    ROOT
    / "results"
    / "lamp_bio_scrna"
    / "gse175634_counts"
    / "gse175634_scrna_counts_lamp_summary.csv"
)
OUT = ROOT / "results" / "lamp_bio_scrna" / "gse175634_pseudobulk_rescue"
FIG_DIR = OUT / "figures"
SEED = 20260605

SCORE_COLUMNS = [
    "structural_panel_score",
    "calcium_ephys_panel_score",
    "metabolic_panel_score",
    "combined_disjoint_biology_score",
    "diffday_numeric_score",
    "dpt_pseudotime_score",
    "annotation_cm_score",
    "cell_cycle_exit_score",
    "demux_dbl_z",
    "log_library_size",
    "log_detected_genes",
]

MONITORS = [
    {
        "id": "pseudobulk_calcium_to_structural",
        "cell_monitor_id": "calcium_to_structural_disjoint_probe",
        "name": "Pseudo-bulk calcium/ephys -> structural endpoint",
        "score": "calcium_ephys_panel_score",
        "features": ["calcium_ephys_panel_score"],
        "expected": "FRAGILE_RESCUE_OR_FAIL",
    },
    {
        "id": "pseudobulk_metabolic_to_structural",
        "cell_monitor_id": "metabolic_to_structural_disjoint_probe",
        "name": "Pseudo-bulk metabolic -> structural endpoint",
        "score": "metabolic_panel_score",
        "features": ["metabolic_panel_score"],
        "expected": "FRAGILE_RESCUE_OR_FAIL",
    },
    {
        "id": "pseudobulk_combined_biology_to_structural",
        "cell_monitor_id": "combined_biology_to_structural_probe",
        "name": "Pseudo-bulk combined biology -> structural endpoint",
        "score": "combined_disjoint_biology_score",
        "features": ["combined_disjoint_biology_score"],
        "expected": "FRAGILE_RESCUE_OR_FAIL",
    },
    {
        "id": "pseudobulk_day_shortcut",
        "cell_monitor_id": "day_protocol_shortcut",
        "name": "Pseudo-bulk day shortcut",
        "score": "diffday_numeric_score",
        "features": ["diffday_numeric_score"],
        "expected": "FAIL",
    },
    {
        "id": "pseudobulk_pseudotime_shortcut",
        "cell_monitor_id": "published_pseudotime_shortcut",
        "name": "Pseudo-bulk pseudotime shortcut",
        "score": "dpt_pseudotime_score",
        "features": ["dpt_pseudotime_score"],
        "expected": "FAIL",
        "latest_offset_h": 999,
    },
    {
        "id": "pseudobulk_annotation_shortcut",
        "cell_monitor_id": "published_annotation_shortcut",
        "name": "Pseudo-bulk annotation shortcut",
        "score": "annotation_cm_score",
        "features": ["annotation_cm_score"],
        "expected": "FAIL",
        "latest_offset_h": 999,
    },
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    cell = pd.read_csv(CELL_TABLE)
    pseudobulk = build_pseudobulk_table(cell, args.group_by.split(","))
    table_path = OUT / "gse175634_pseudobulk_prediction_table.csv"
    pseudobulk.to_csv(table_path, index=False, lineterminator="\n")

    cell_summary = pd.read_csv(CELL_SUMMARY)
    summary_rows: list[dict[str, Any]] = []
    for monitor in MONITORS:
        config = build_config(monitor)
        config_path = OUT / "configs" / f"{monitor['id']}.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        result = run_audit(config_path, table_path, OUT / "lamp" / monitor["id"])
        stability = stability_summary(pseudobulk, monitor["score"])
        cell_row = one(cell_summary, "monitor_id", monitor["cell_monitor_id"])
        summary_rows.append(summary_row(monitor, result, stability, cell_row))

    summary_path = OUT / "gse175634_pseudobulk_rescue_summary.csv"
    write_csv(summary_path, summary_rows)

    inventory = inventory_summary(cell, pseudobulk, args.group_by.split(","))
    inventory_path = OUT / "gse175634_pseudobulk_rescue_inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    plot_path = FIG_DIR / "cell_vs_pseudobulk_auc.png"
    plot_cell_vs_pseudobulk(summary_rows, plot_path)

    report_path = OUT / "gse175634_pseudobulk_rescue_report.md"
    write_report(report_path, summary_rows, inventory, plot_path)
    print(report_path)
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--group-by",
        default="sample",
        help="Comma-separated grouping columns. Default: sample.",
    )
    return parser.parse_args(argv)


def build_pseudobulk_table(cell: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    group_cols = [col.strip() for col in group_cols if col.strip()]
    missing = [col for col in group_cols if col not in cell.columns]
    if missing:
        raise ValueError(f"Missing group columns in cell table: {missing}")

    aggregations: dict[str, Any] = {col: "mean" for col in SCORE_COLUMNS}
    aggregations.update(
        {
            "cell_id": "count",
            "individual": first_mode,
            "diffday": first_mode,
            "diffday_num": "mean",
        }
    )
    grouped = cell.groupby(group_cols, as_index=False).agg(aggregations)
    grouped = grouped.rename(columns={"cell_id": "n_cells"})
    grouped["pseudobulk_id"] = grouped[group_cols].astype(str).agg("|".join, axis=1)
    grouped["label_structural_maturity_high"] = (
        grouped["structural_panel_score"]
        >= grouped["structural_panel_score"].quantile(0.70)
    ).astype(int)
    grouped["structural_endpoint_score"] = grouped["structural_panel_score"]
    return grouped.sort_values(["diffday_num", "pseudobulk_id"]).reset_index(drop=True)


def build_config(monitor: dict[str, Any]) -> dict[str, Any]:
    latest_offset_h = float(monitor.get("latest_offset_h", 0))
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"{ACCESSION} pseudo-bulk rescue: {monitor['name']}",
            "task": "Pseudo-bulk rescue test for disjoint biological axes",
            "role": "LAMP-Bio scRNA aggregation sensitivity analysis",
            "source": GEO_RECORD,
            "monitor_id": monitor["id"],
            "expected_result": monitor["expected"],
        },
        "columns": {
            "subject_id": "pseudobulk_id",
            "label": "label_structural_maturity_high",
            "positive_value": 1,
            "score": monitor["score"],
            "anchor_time": "diffday_num",
        },
        "temporal_isolation": {
            "anchor": "diffday_num",
            "valid_features_must_be": "pseudo-bulk score must not use day, pseudotime, annotation, or endpoint-axis features",
            "frozen_before_holdout": [
                "GSE175634 count-level pilot",
                "pseudo-bulk grouping columns",
                "structural endpoint definition",
                "forbidden day/pseudotime/annotation channels",
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
                "expected_signature": "differentiation day / protocol timing",
            },
            "published_pseudotime": {
                "column": "dpt_pseudotime_score",
                "role": "endpoint_adjacent_oracle",
                "expected_signature": "full-trajectory pseudotime",
            },
            "published_annotation": {
                "column": "annotation_cm_score",
                "role": "annotation_shortcut",
                "expected_signature": "published CM annotation fraction",
            },
        },
        "negative_controls": {"n_permutations": 200, "seed": SEED},
        "visible_state_matching": {
            "columns": ["diffday_numeric_score"],
            "n_bins": 5,
            "min_bin_size": 2,
        },
        "early_window_sensitivity": {
            "score_columns": [
                "calcium_ephys_panel_score",
                "metabolic_panel_score",
                "combined_disjoint_biology_score",
                "diffday_numeric_score",
                "dpt_pseudotime_score",
                "annotation_cm_score",
            ]
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.02,
            "matched_collapse_max": 0.005,
            "score_thresholds": [-0.05, 0.0, 0.05],
        },
    }


def stability_summary(table: pd.DataFrame, score_col: str, n_bootstrap: int = 1000) -> dict[str, Any]:
    labels = table["label_structural_maturity_high"].astype(int).to_numpy()
    scores = pd.to_numeric(table[score_col], errors="coerce").to_numpy(dtype=float)
    rng = np.random.default_rng(SEED)
    boot_aucs = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, len(labels), size=len(labels))
        if len(set(labels[idx])) < 2:
            continue
        auc = auc_score(labels[idx].tolist(), scores[idx].tolist())
        if auc is not None:
            boot_aucs.append(auc)

    leave = []
    for individual, _ in table.groupby("individual"):
        sub = table[table["individual"] != individual]
        if sub["label_structural_maturity_high"].nunique() < 2:
            continue
        auc = auc_score(
            sub["label_structural_maturity_high"].astype(int).tolist(),
            pd.to_numeric(sub[score_col], errors="coerce").fillna(0.0).tolist(),
        )
        leave.append(float(auc) if auc is not None else np.nan)

    return {
        "bootstrap_auc_mean": float(np.mean(boot_aucs)) if boot_aucs else None,
        "bootstrap_auc_p025": float(np.quantile(boot_aucs, 0.025)) if boot_aucs else None,
        "bootstrap_auc_p975": float(np.quantile(boot_aucs, 0.975)) if boot_aucs else None,
        "bootstrap_pass_rate_auc_ge_0p60": float(np.mean(np.asarray(boot_aucs) >= 0.60))
        if boot_aucs
        else None,
        "leave_individual_auc_min": float(np.nanmin(leave)) if leave else None,
    }


def summary_row(
    monitor: dict[str, Any],
    result: dict[str, Any],
    stability: dict[str, Any],
    cell_row: pd.Series,
) -> dict[str, Any]:
    dossier = result["failure_mode_dossier"]
    primary = result["primary_score"]
    pseudo_auc = float(primary["auc"]) if primary["auc"] is not None else np.nan
    cell_auc = float(cell_row["auc"])
    rescue = classify_rescue(monitor, dossier, stability, pseudo_auc, cell_auc)
    return {
        "monitor": monitor["name"],
        "monitor_id": monitor["id"],
        "cell_monitor_id": monitor["cell_monitor_id"],
        "cell_auc": cell_auc,
        "pseudobulk_auc": pseudo_auc,
        "auc_gain": pseudo_auc - cell_auc,
        "pseudobulk_audit_pass": dossier["audit_pass_candidate"],
        "rescue_diagnosis": rescue,
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "matched_delta_day_stratified": result["visible_state_matching"].get(
            "matched_observed_state_delta"
        ),
        "threshold_fragile": result["threshold_sensitivity"].get("fragile"),
        "bootstrap_pass_rate_auc_ge_0p60": stability["bootstrap_pass_rate_auc_ge_0p60"],
        "bootstrap_auc_p025": stability["bootstrap_auc_p025"],
        "bootstrap_auc_p975": stability["bootstrap_auc_p975"],
        "leave_individual_auc_min": stability["leave_individual_auc_min"],
        "structural_oracle_auc": result["sentinels"]["structural_endpoint_oracle"].get("auc"),
        "day_sentinel_auc": result["sentinels"]["day_protocol"].get("auc"),
        "pseudotime_sentinel_auc": result["sentinels"]["published_pseudotime"].get("auc"),
        "annotation_sentinel_auc": result["sentinels"]["published_annotation"].get("auc"),
        "output_classes": ";".join(dossier["output_classes"]),
        "key_reasons": key_reasons(result),
    }


def classify_rescue(
    monitor: dict[str, Any],
    dossier: dict[str, Any],
    stability: dict[str, Any],
    pseudo_auc: float,
    cell_auc: float,
) -> str:
    if monitor.get("expected") == "FAIL":
        if pseudo_auc > cell_auc and pseudo_auc >= 0.60:
            return "forbidden_shortcut_strengthened_by_pseudobulk"
        return "forbidden_shortcut_not_strengthened"
    if pseudo_auc < 0.60:
        return "no_pseudobulk_rescue"
    pass_rate = stability.get("bootstrap_pass_rate_auc_ge_0p60") or 0.0
    leave_min = stability.get("leave_individual_auc_min") or 0.0
    if dossier["audit_pass_candidate"] and pass_rate >= 0.90 and leave_min >= 0.60:
        return "stable_pseudobulk_rescue"
    if pseudo_auc > cell_auc and pass_rate >= 0.50:
        return "fragile_pseudobulk_rescue"
    return "ambiguous_pseudobulk_rescue"


def key_reasons(result: dict[str, Any]) -> str:
    reasons = []
    if not result["temporal_isolation"]["passed"]:
        reasons.append("temporal isolation")
    if not result["forbidden_feature_screen"]["passed"]:
        reasons.append("forbidden feature")
    if result["threshold_sensitivity"].get("fragile"):
        reasons.append("threshold fragile")
    classes = set(result["failure_mode_dossier"]["output_classes"])
    if "null_or_destroyed_signal" in classes:
        reasons.append("null/destroyed")
    if "visible_state_confounding" in classes:
        reasons.append("matched collapse")
    return ", ".join(dict.fromkeys(reasons)) or "none"


def inventory_summary(cell: pd.DataFrame, pseudobulk: pd.DataFrame, group_cols: list[str]) -> dict[str, Any]:
    return {
        "accession": ACCESSION,
        "geo_record": GEO_RECORD,
        "cell_rows": int(len(cell)),
        "pseudobulk_rows": int(len(pseudobulk)),
        "group_by": group_cols,
        "n_individuals": int(pseudobulk["individual"].nunique()),
        "diffday_counts": {
            str(k): int(v) for k, v in pseudobulk["diffday"].value_counts().sort_index().items()
        },
        "n_cells_per_group": {
            "min": int(pseudobulk["n_cells"].min()),
            "median": float(pseudobulk["n_cells"].median()),
            "max": int(pseudobulk["n_cells"].max()),
        },
        "endpoint_positive_groups": int(pseudobulk["label_structural_maturity_high"].sum()),
        "endpoint_total_groups": int(len(pseudobulk)),
    }


def write_report(
    path: Path,
    rows: list[dict[str, Any]],
    inventory: dict[str, Any],
    plot_path: Path,
) -> None:
    lines = [
        "# GSE175634 Pseudo-Bulk Rescue Audit",
        "",
        "This test distinguishes two explanations for the GSE175634 cell-level",
        "collapse: single-cell noise versus a deeper lack of independent",
        "cross-axis support under the current structural endpoint contract.",
        "",
        "## Setup",
        "",
        f"- Source: `{ACCESSION}` ({GEO_RECORD})",
        f"- Cell rows aggregated: {inventory['cell_rows']:,}.",
        f"- Pseudo-bulk groups: {inventory['pseudobulk_rows']} grouped by `{', '.join(inventory['group_by'])}`.",
        f"- Cells per group: min {inventory['n_cells_per_group']['min']}, median {inventory['n_cells_per_group']['median']:.1f}, max {inventory['n_cells_per_group']['max']}.",
        f"- Endpoint-positive pseudo-bulk groups: {inventory['endpoint_positive_groups']} / {inventory['endpoint_total_groups']}.",
        "",
        "## Cell-Level vs Pseudo-Bulk",
        "",
        "| Monitor | Cell AUC | Pseudo-bulk AUC | Gain | Diagnosis | Bootstrap pass | Leave-individual min AUC |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {monitor} | {cell:.3f} | {pseudo:.3f} | {gain:+.3f} | {diagnosis} | {boot:.3f} | {leave:.3f} |".format(
                monitor=row["monitor"],
                cell=float(row["cell_auc"]),
                pseudo=float(row["pseudobulk_auc"]),
                gain=float(row["auc_gain"]),
                diagnosis=row["rescue_diagnosis"],
                boot=float(row["bootstrap_pass_rate_auc_ge_0p60"] or 0.0),
                leave=float(row["leave_individual_auc_min"] or float("nan")),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The calcium/electrophysiology axis shows a **fragile pseudo-bulk rescue**:",
            "cell-level AUC 0.571 rises to pseudo-bulk AUC 0.626. That supports the",
            "single-cell-noise hypothesis, but only weakly: bootstrap pass rate is",
            "about 0.59 and leave-one-individual minimum AUC is 0.542.",
            "",
            "The rescue is not a clean biological validation. Pseudotime, annotation,",
            "and day/protocol channels remain stronger than the allowed biology axis.",
            "The careful claim is therefore: aggregation partially rescues one",
            "independent biological axis, but the current GSE175634 structural endpoint",
            "is still dominated by shortcut/trajectory structure under this contract.",
            "",
            "## Decision Logic",
            "",
            "- `cell-level FAIL -> pseudo-bulk fragile rescue`: single-cell noise is a",
            "  plausible contributor.",
            "- The weak stability means this is not yet `valid_biological_signal_stable`.",
            "- The next decisive test is donor/collection-held-out pseudo-bulk with",
            "  alternative endpoint axes and day-held-out splits.",
            "",
            "## Figure",
            "",
            f"![Cell vs pseudo-bulk AUC](figures/{plot_path.name})",
            "",
            "## Files",
            "",
            f"- Prediction table: `{relpath(OUT / 'gse175634_pseudobulk_prediction_table.csv')}`",
            f"- Summary CSV: `{relpath(OUT / 'gse175634_pseudobulk_rescue_summary.csv')}`",
            f"- Inventory: `{relpath(OUT / 'gse175634_pseudobulk_rescue_inventory.json')}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_cell_vs_pseudobulk(rows: list[dict[str, Any]], path: Path) -> None:
    labels = [row["cell_monitor_id"].replace("_", "\n") for row in rows]
    cell = [float(row["cell_auc"]) for row in rows]
    pseudo = [float(row["pseudobulk_auc"]) for row in rows]
    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(x - width / 2, cell, width=width, label="Cell-level", color="#999999", edgecolor="black")
    ax.bar(x + width / 2, pseudo, width=width, label="Pseudo-bulk", color="#222222", edgecolor="black")
    ax.axhline(0.60, color="black", linestyle="--", linewidth=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("AUC")
    ax.set_title("GSE175634 pseudo-bulk rescue test")
    ax.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def first_mode(series: pd.Series) -> Any:
    mode = series.mode(dropna=True)
    if len(mode):
        return mode.iloc[0]
    return series.iloc[0]


def one(frame: pd.DataFrame, column: str, value: str) -> pd.Series:
    subset = frame[frame[column] == value]
    if len(subset) != 1:
        raise ValueError(f"Expected one {column}={value}, found {len(subset)}")
    return subset.iloc[0]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def relpath(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


if __name__ == "__main__":
    raise SystemExit(main())
