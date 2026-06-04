#!/usr/bin/env python3
"""Compare LAMP-Bio outcomes across GSE201437 and GSE175634.

The question is not "where did LAMP find PASS?" The more interesting question
is why a fragile disjoint biological signal appears in one iPSC-CM dataset while
it collapses in another under a stricter single-cell count-matrix contract.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "lamp_bio_cross_dataset_contrast"
FIG_DIR = OUT / "figures"

GSE201437_SUMMARY = (
    ROOT
    / "results"
    / "ipsc_cm_maturation_lamp"
    / "gse201437_sanity_separation"
    / "gse201437_sanity_lamp_summary.csv"
)
GSE201437_BOOTSTRAP = (
    ROOT
    / "results"
    / "ipsc_cm_maturation_lamp"
    / "gse201437_sanity_robustness"
    / "gse201437_robustness_bootstrap.csv"
)
GSE201437_LEAVE_GROUP = (
    ROOT
    / "results"
    / "ipsc_cm_maturation_lamp"
    / "gse201437_sanity_robustness"
    / "gse201437_robustness_leave_group_out.csv"
)
GSE175634_COUNTS = (
    ROOT
    / "results"
    / "lamp_bio_scrna"
    / "gse175634_counts"
    / "gse175634_scrna_counts_lamp_summary.csv"
)
GSE175634_PSEUDOBULK = (
    ROOT
    / "results"
    / "lamp_bio_scrna"
    / "gse175634_pseudobulk_rescue"
    / "gse175634_pseudobulk_rescue_summary.csv"
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    rows = build_contrast_rows()
    summary_path = OUT / "gse201437_vs_gse175634_contrast_summary.csv"
    write_csv(summary_path, rows)

    hypothesis_rows = build_hypothesis_rows()
    hypothesis_path = OUT / "gse201437_vs_gse175634_hypotheses.csv"
    write_csv(hypothesis_path, hypothesis_rows)

    plot_path = FIG_DIR / "allowed_biology_vs_shortcut_auc.png"
    plot_allowed_vs_shortcut(rows, plot_path)

    report_path = OUT / "gse201437_vs_gse175634_contrast_report.md"
    write_report(report_path, rows, hypothesis_rows, plot_path)
    print(report_path)
    return 0


def build_contrast_rows() -> list[dict[str, Any]]:
    g201 = pd.read_csv(GSE201437_SUMMARY)
    g201_boot = pd.read_csv(GSE201437_BOOTSTRAP)
    g201_leave = pd.read_csv(GSE201437_LEAVE_GROUP)
    g175 = pd.read_csv(GSE175634_COUNTS)
    g175_pb = pd.read_csv(GSE175634_PSEUDOBULK)

    clean_201 = one(g201, "monitor_id", "clean_calcium_probe")
    shortcut_201 = one(g201, "monitor_id", "protocol_shortcut")
    oracle_201 = one(g201, "monitor_id", "explicit_oracle_leakage")
    clean_201_boot = one(g201_boot, "monitor_id", "clean_calcium_probe")
    clean_201_leave = g201_leave[g201_leave["monitor_id"] == "clean_calcium_probe"]

    calcium_175 = one(g175, "monitor_id", "calcium_to_structural_disjoint_probe")
    metabolic_175 = one(g175, "monitor_id", "metabolic_to_structural_disjoint_probe")
    combined_175 = one(g175, "monitor_id", "combined_biology_to_structural_probe")
    day_175 = one(g175, "monitor_id", "day_protocol_shortcut")
    pseudo_175 = one(g175, "monitor_id", "published_pseudotime_shortcut")
    annotation_175 = one(g175, "monitor_id", "published_annotation_shortcut")
    oracle_175 = one(g175, "monitor_id", "structural_endpoint_adjacent_oracle")
    calcium_175_pb = one(g175_pb, "monitor_id", "pseudobulk_calcium_to_structural")
    metabolic_175_pb = one(g175_pb, "monitor_id", "pseudobulk_metabolic_to_structural")
    combined_175_pb = one(
        g175_pb,
        "monitor_id",
        "pseudobulk_combined_biology_to_structural",
    )
    day_175_pb = one(g175_pb, "monitor_id", "pseudobulk_day_shortcut")
    pseudo_175_pb = one(g175_pb, "monitor_id", "pseudobulk_pseudotime_shortcut")
    annotation_175_pb = one(g175_pb, "monitor_id", "pseudobulk_annotation_shortcut")

    best_175_allowed = max(
        [calcium_175, metabolic_175, combined_175],
        key=lambda row: float(row["auc"]),
    )
    best_175_shortcut = max(
        [day_175, pseudo_175, annotation_175],
        key=lambda row: float(row["auc"]),
    )
    best_175_pb_allowed = max(
        [calcium_175_pb, metabolic_175_pb, combined_175_pb],
        key=lambda row: float(row["pseudobulk_auc"]),
    )
    best_175_pb_shortcut = max(
        [day_175_pb, pseudo_175_pb, annotation_175_pb],
        key=lambda row: float(row["pseudobulk_auc"]),
    )

    return [
        {
            "dataset": "GSE201437",
            "resolution": "sample-level processed expression",
            "rows": 14,
            "endpoint_axis": "structural maturation marker median split",
            "allowed_biology_monitor": clean_201["monitor_id"],
            "allowed_biology_auc": clean_201["auc"],
            "allowed_biology_lamp_pass": clean_201["audit_pass"],
            "diagnosis": "valid_biological_signal_fragile",
            "fragility_evidence": (
                f"bootstrap PASS rate {float(clean_201_boot['pass_rate']):.3f}; "
                f"leave-group min AUC {float(clean_201_leave['auc'].min()):.3f}"
            ),
            "best_forbidden_shortcut": shortcut_201["monitor_id"],
            "best_forbidden_shortcut_auc": shortcut_201["auc"],
            "oracle_auc": oracle_201["auc"],
            "interpretation": (
                "A clean disjoint calcium/electrophysiology probe can pass, but "
                "stability is weak and HCRP leave-out collapses."
            ),
        },
        {
            "dataset": "GSE175634",
            "resolution": "cell-level scRNA counts",
            "rows": 60000,
            "endpoint_axis": "top-30% structural marker-panel score",
            "allowed_biology_monitor": best_175_allowed["monitor_id"],
            "allowed_biology_auc": best_175_allowed["auc"],
            "allowed_biology_lamp_pass": best_175_allowed["audit_pass"],
            "diagnosis": "not_biologically_interpretable_under_contract",
            "fragility_evidence": (
                f"allowed bootstrap PASS rate {float(best_175_allowed['bootstrap_pass_rate_auc_ge_0p60']):.3f}; "
                f"leave-individual min AUC {float(best_175_allowed['leave_individual_auc_min']):.3f}"
            ),
            "best_forbidden_shortcut": best_175_shortcut["monitor_id"],
            "best_forbidden_shortcut_auc": best_175_shortcut["auc"],
            "oracle_auc": oracle_175["auc"],
            "interpretation": (
                "Disjoint calcium/metabolic axes collapse under the strict "
                "single-cell contract, while day and pseudotime remain predictive."
            ),
        },
        {
            "dataset": "GSE175634",
            "resolution": "sample pseudo-bulk scRNA",
            "rows": 28,
            "endpoint_axis": "top-30% pseudo-bulk structural marker-panel score",
            "allowed_biology_monitor": best_175_pb_allowed["monitor_id"],
            "allowed_biology_auc": best_175_pb_allowed["pseudobulk_auc"],
            "allowed_biology_lamp_pass": best_175_pb_allowed["pseudobulk_audit_pass"],
            "diagnosis": best_175_pb_allowed["rescue_diagnosis"],
            "fragility_evidence": (
                f"bootstrap PASS rate {float(best_175_pb_allowed['bootstrap_pass_rate_auc_ge_0p60']):.3f}; "
                f"leave-individual min AUC {float(best_175_pb_allowed['leave_individual_auc_min']):.3f}"
            ),
            "best_forbidden_shortcut": best_175_pb_shortcut["monitor_id"],
            "best_forbidden_shortcut_auc": best_175_pb_shortcut["pseudobulk_auc"],
            "oracle_auc": 1.0,
            "interpretation": (
                "Aggregation partially rescues the calcium/electrophysiology axis, "
                "but the rescue is fragile and forbidden annotation/pseudotime "
                "channels strengthen more."
            ),
        },
    ]


def build_hypothesis_rows() -> list[dict[str, Any]]:
    return [
        {
            "hypothesis": "A_marker_panels_are_bad",
            "current_evidence": (
                "Possible, but not sufficient: the calcium/electrophysiology panel "
                "supports a fragile signal in GSE201437 and all selected marker "
                "genes are present in GSE175634."
            ),
            "next_test": (
                "Repeat with alternative curated panels and data-driven disjoint "
                "gene modules learned without endpoint genes."
            ),
            "status": "open_but_not_primary",
        },
        {
            "hypothesis": "B_stage_specific_axis_decoupling",
            "current_evidence": (
                "Plausible: GSE175634 pilot covers early/intermediate single-cell "
                "states where structural markers may rise before calcium/metabolic "
                "maturation becomes coordinated."
            ),
            "next_test": (
                "Run day-stratified and late-day-only audits; test structural->calcium "
                "and metabolic endpoint reversals."
            ),
            "status": "strong_candidate",
        },
        {
            "hypothesis": "C_single_cell_noise_collapses_cross_axis_signal",
            "current_evidence": (
                "Strengthened: calcium/electrophysiology rises from cell-level AUC "
                "0.571 to pseudo-bulk AUC 0.626, but the rescue is fragile "
                "(bootstrap pass rate about 0.60; leave-individual min AUC 0.542)."
            ),
            "next_test": (
                "Run donor/collection-held-out pseudo-bulk and compare sample-level, "
                "collection-level, and annotation-free aggregation contracts."
            ),
            "status": "strong_candidate",
        },
        {
            "hypothesis": "D_time_and_trajectory_channels_dominate",
            "current_evidence": (
                "Strong: in GSE175634, day and pseudotime beat all allowed biology "
                "panels at cell level, and pseudo-bulk aggregation strengthens "
                "forbidden channels even more (pseudotime AUC 0.942; annotation AUC 0.947)."
            ),
            "next_test": (
                "Evaluate day-held-out, pseudotime-withheld, and reconstruction-free "
                "contracts across additional scRNA maturation datasets."
            ),
            "status": "strong_candidate",
        },
    ]


def write_report(
    path: Path,
    rows: list[dict[str, Any]],
    hypothesis_rows: list[dict[str, Any]],
    plot_path: Path,
) -> None:
    g201, g175, g175_pb = rows
    lines = [
        "# LAMP-Bio Cross-Dataset Contrast: GSE201437 vs GSE175634",
        "",
        "The interesting question is no longer `where does LAMP find PASS?`.",
        "The stronger question is why one iPSC-CM dataset admits a fragile",
        "disjoint biological signal while another collapses under a stricter",
        "single-cell count-matrix contract.",
        "",
        "## Main Contrast",
        "",
        "| Dataset | Resolution | Allowed biology AUC | Best shortcut AUC | Oracle AUC | Diagnosis |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {dataset} | {resolution} | {allowed:.3f} | {shortcut:.3f} | {oracle:.3f} | {diagnosis} |".format(
                dataset=row["dataset"],
                resolution=row["resolution"],
                allowed=float(row["allowed_biology_auc"]),
                shortcut=float(row["best_forbidden_shortcut_auc"]),
                oracle=float(row["oracle_auc"]),
                diagnosis=row["diagnosis"],
            )
        )
    lines.extend(
        [
            "",
            "## Dataset-Level Reading",
            "",
            f"- **GSE201437**: {g201['interpretation']} {g201['fragility_evidence']}.",
            f"- **GSE175634**: {g175['interpretation']} {g175['fragility_evidence']}.",
            f"- **GSE175634 pseudo-bulk**: {g175_pb['interpretation']} {g175_pb['fragility_evidence']}.",
            "",
            "The contrast is the result. LAMP is not mechanically saying all biology",
            "fails, and it is not rewarding every high-AUC biological score. It separates",
            "a small fragile sample-level signal, a cell-level scRNA collapse, and a",
            "partial pseudo-bulk rescue where shortcut/trajectory channels strengthen",
            "even more than the allowed biology axis.",
            "",
            "## Why Published Annotation AUC 0.654 Matters",
            "",
            "The published CM annotation in GSE175634 is predictive but far from an oracle",
            "for the strict structural endpoint. That means at least one of three things",
            "is true: the annotation is not identical to structural maturation, the",
            "structural endpoint is narrower than the cell-type label, or the dataset",
            "contains many transitional cells. All three interpretations are biologically",
            "interesting and argue against treating annotation, pseudotime, or day as",
            "clean latent-state evidence.",
            "",
            "## Working Formulation",
            "",
            "> In a large real-world hiPSC differentiation dataset, independent biological",
            "> axes failed at cell level but showed a fragile calcium/electrophysiology",
            "> pseudo-bulk rescue. Temporal, annotation, and trajectory-derived channels",
            "> strengthened more than the allowed biology axis. This suggests that",
            "> apparent maturation performance can be dominated by timepoint and",
            "> reconstruction structure even when some independent biology is recoverable",
            "> after aggregation.",
            "",
            "## Hypotheses",
            "",
            "| Hypothesis | Evidence now | Next test | Status |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in hypothesis_rows:
        lines.append(
            "| {hypothesis} | {current_evidence} | {next_test} | {status} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Figure",
            "",
            f"![Allowed biology vs shortcut AUC](figures/{plot_path.name})",
            "",
            "## Files",
            "",
            f"- Summary CSV: `{relpath(OUT / 'gse201437_vs_gse175634_contrast_summary.csv')}`",
            f"- Hypotheses CSV: `{relpath(OUT / 'gse201437_vs_gse175634_hypotheses.csv')}`",
            f"- Figure: `{relpath(plot_path)}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_allowed_vs_shortcut(rows: list[dict[str, Any]], path: Path) -> None:
    labels = [row["dataset"] for row in rows]
    allowed = [float(row["allowed_biology_auc"]) for row in rows]
    shortcut = [float(row["best_forbidden_shortcut_auc"]) for row in rows]
    oracle = [float(row["oracle_auc"]) for row in rows]
    x = range(len(labels))
    width = 0.24
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([i - width for i in x], allowed, width=width, label="Allowed biology", color="#222222")
    ax.bar(list(x), shortcut, width=width, label="Best shortcut", color="#777777")
    ax.bar([i + width for i in x], oracle, width=width, label="Oracle", color="#bbbbbb", edgecolor="black")
    ax.axhline(0.60, linestyle="--", linewidth=1.0, color="black")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("AUC")
    ax.set_title("LAMP-Bio contrast: fragile signal vs shortcut-dominated collapse")
    ax.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


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
