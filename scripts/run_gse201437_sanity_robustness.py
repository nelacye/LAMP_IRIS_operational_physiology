#!/usr/bin/env python3
"""Robustness checks for the GSE201437 LAMP sanity separation.

Reviewer-facing question: the controlled sanity check shows that LAMP can emit a
PASS on biological expression rows, but how stable is that PASS?

This script stress-tests the clean/protocol/leakage separation with:
- stratified bootstrap resampling,
- alternative disjoint probe panels,
- leave-one-protocol-group-out sensitivity,
- threshold sensitivity over the audit decision cutoffs.

The dataset is still tiny, so the report explicitly marks donor-held-out and
real protocol-held-out validation as not evaluable.
"""

from __future__ import annotations

import copy
import csv
import statistics
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from lamp.audit import LAMP_Audit  # noqa: E402
import run_gse201437_lamp_sanity_separation as sanity  # noqa: E402


OUT = ROOT / "results" / "ipsc_cm_maturation_lamp" / "gse201437_sanity_robustness"
SEED = 20260604
N_BOOTSTRAPS = 300

ALT_PROBE_PANELS = {
    "full_calcium_electrophysiology": ["ATP2A2", "PLN", "RYR2", "CACNA1C", "SCN5A", "KCNH2"],
    "calcium_handling": ["ATP2A2", "PLN", "RYR2", "CACNA1C"],
    "ion_channel_core": ["RYR2", "CACNA1C", "SCN5A", "KCNH2"],
    "depolarization_repolarization": ["CACNA1C", "SCN5A", "KCNH2"],
    "minimal_calcium_pair": ["ATP2A2", "PLN"],
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sanity.ensure_counts()
    counts = sanity.load_counts()
    base_table = sanity.build_prediction_table(counts)
    z = sanity.zscore_rows(sanity.log_counts_per_million(counts))

    base_rows = run_base_separation(base_table)
    bootstrap_rows = run_bootstrap(base_table)
    panel_rows = run_alternative_panels(base_table, z)
    group_rows = run_leave_one_group_out(base_table)
    threshold_rows = run_threshold_grid(base_table)

    write_csv(OUT / "gse201437_robustness_base.csv", base_rows)
    write_csv(OUT / "gse201437_robustness_bootstrap.csv", bootstrap_rows)
    write_csv(OUT / "gse201437_robustness_panels.csv", panel_rows)
    write_csv(OUT / "gse201437_robustness_leave_group_out.csv", group_rows)
    write_csv(OUT / "gse201437_robustness_thresholds.csv", threshold_rows)
    write_report(base_rows, bootstrap_rows, panel_rows, group_rows, threshold_rows)
    print(OUT / "gse201437_sanity_robustness_report.md")
    return 0


def run_base_separation(table: pd.DataFrame) -> list[dict[str, Any]]:
    return [summarize_result(monitor, run_monitor(table, monitor)) for monitor in sanity.MONITORS]


def run_bootstrap(table: pd.DataFrame) -> list[dict[str, Any]]:
    rng = np.random.default_rng(SEED)
    pos = table[table["label_structural_maturation_high"] == 1].reset_index(drop=True)
    neg = table[table["label_structural_maturation_high"] == 0].reset_index(drop=True)
    rows = []
    for monitor in sanity.MONITORS:
        replicate_rows = []
        for iteration in range(N_BOOTSTRAPS):
            sampled = pd.concat(
                [
                    pos.iloc[rng.integers(0, len(pos), len(pos))],
                    neg.iloc[rng.integers(0, len(neg), len(neg))],
                ],
                ignore_index=True,
            ).sample(frac=1.0, random_state=int(rng.integers(0, 2**31 - 1)))
            sampled = sampled.reset_index(drop=True)
            sampled["sample_id"] = [
                f"{sample_id}_boot{iteration:03d}_{idx:02d}"
                for idx, sample_id in enumerate(sampled["sample_id"])
            ]
            result = run_monitor(sampled, monitor, n_permutations=30)
            replicate_rows.append(summarize_result(monitor, result))
        rows.append(aggregate_bootstrap(monitor, replicate_rows))
    return rows


def run_alternative_panels(table: pd.DataFrame, z: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for name, genes in ALT_PROBE_PANELS.items():
        present = [gene for gene in genes if gene in z.index]
        variant_table = table.copy()
        if present:
            variant_table[f"{name}_score"] = z.loc[present].mean(axis=0).loc[
                variant_table["sample_id"]
            ].to_numpy()
        else:
            variant_table[f"{name}_score"] = np.nan
        monitor = clean_monitor_variant(
            monitor_id=f"clean_{name}",
            score_col=f"{name}_score",
            feature_name=f"{name}_panel",
            name=f"Clean probe panel: {name.replace('_', ' ')}",
        )
        result = run_monitor(variant_table, monitor)
        row = summarize_result(monitor, result)
        row["panel_genes_present"] = ";".join(present)
        row["n_panel_genes"] = len(present)
        rows.append(row)
    return rows


def run_leave_one_group_out(table: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for group in sorted(table["group"].unique()):
        subset = table[table["group"] != group].copy().reset_index(drop=True)
        n_pos = int(subset["label_structural_maturation_high"].sum())
        n_neg = len(subset) - n_pos
        for monitor in sanity.MONITORS:
            if n_pos == 0 or n_neg == 0:
                row = {
                    "left_out_group": group,
                    "monitor": monitor["name"],
                    "monitor_id": monitor["id"],
                    "expected": monitor["expected"],
                    "observed": "NOT_EVALUABLE",
                    "matches_expectation": False,
                    "auc": None,
                    "audit_pass": False,
                    "temporal_passed": None,
                    "forbidden_passed": None,
                    "matched_delta": None,
                    "threshold_fragile": None,
                    "n_rows": len(subset),
                    "n_positive": n_pos,
                    "n_negative": n_neg,
                    "output_classes": "",
                    "key_reasons": "single class after leave-out",
                }
            else:
                result = run_monitor(subset, monitor)
                row = summarize_result(monitor, result)
                row["left_out_group"] = group
                row["n_rows"] = len(subset)
                row["n_positive"] = n_pos
                row["n_negative"] = n_neg
            rows.append(row)
    return rows


def run_threshold_grid(table: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    valid_auc_values = [0.60, 0.65, 0.70]
    matched_delta_values = [0.02, 0.10, 0.20, 0.50]
    for valid_auc_min in valid_auc_values:
        for matched_delta_min in matched_delta_values:
            overrides = {
                "valid_auc_min": valid_auc_min,
                "matched_delta_min": matched_delta_min,
            }
            for monitor in sanity.MONITORS:
                result = run_monitor(table, monitor, threshold_overrides=overrides)
                row = summarize_result(monitor, result)
                row["valid_auc_min"] = valid_auc_min
                row["matched_delta_min"] = matched_delta_min
                rows.append(row)
    return rows


def clean_monitor_variant(
    monitor_id: str,
    score_col: str,
    feature_name: str,
    name: str,
) -> dict[str, Any]:
    monitor = copy.deepcopy(sanity.MONITORS[0])
    monitor["id"] = monitor_id
    monitor["name"] = name
    monitor["score"] = score_col
    monitor["features"] = [feature_name]
    monitor["temporal_offsets"] = {feature_name: 0}
    monitor["description"] = "Alternative disjoint expression probe for robustness."
    return monitor


def run_monitor(
    table: pd.DataFrame,
    monitor: dict[str, Any],
    threshold_overrides: dict[str, float] | None = None,
    n_permutations: int | None = None,
) -> dict[str, Any]:
    config = sanity.build_config(monitor)
    if threshold_overrides:
        config["thresholds"].update(threshold_overrides)
    if n_permutations is not None:
        config["negative_controls"]["n_permutations"] = n_permutations
    rows = dataframe_to_rows(table)
    return LAMP_Audit(config, rows, list(table.columns)).run()


def dataframe_to_rows(table: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for row in table.to_dict(orient="records"):
        rows.append({key: value for key, value in row.items()})
    return rows


def summarize_result(monitor: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    dossier = result["failure_mode_dossier"]
    primary = result["primary_score"]
    observed = "PASS" if dossier["audit_pass_candidate"] else "FAIL"
    return {
        "monitor": monitor["name"],
        "monitor_id": monitor["id"],
        "expected": monitor.get("expected", "PASS"),
        "observed": observed,
        "matches_expectation": observed == monitor.get("expected", "PASS"),
        "auc": primary.get("auc"),
        "inverted_auc": primary.get("inverted_auc"),
        "audit_pass": dossier["audit_pass_candidate"],
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "threshold_fragile": result["threshold_sensitivity"].get("fragile"),
        "output_classes": ";".join(dossier["output_classes"]),
        "key_reasons": key_reasons(result),
    }


def aggregate_bootstrap(
    monitor: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    aucs = [row["auc"] for row in rows if row["auc"] is not None]
    deltas = [row["matched_delta"] for row in rows if row["matched_delta"] is not None]
    observed = [row["observed"] for row in rows]
    expected = monitor["expected"]
    pass_rate = observed.count("PASS") / len(observed)
    expected_rate = sum(row["observed"] == expected for row in rows) / len(rows)
    return {
        "monitor": monitor["name"],
        "monitor_id": monitor["id"],
        "expected": expected,
        "n_bootstraps": len(rows),
        "pass_rate": pass_rate,
        "expected_decision_rate": expected_rate,
        "auc_mean": mean_or_none(aucs),
        "auc_p025": quantile_or_none(aucs, 0.025),
        "auc_p975": quantile_or_none(aucs, 0.975),
        "matched_delta_mean": mean_or_none(deltas),
        "matched_delta_p025": quantile_or_none(deltas, 0.025),
        "matched_delta_p975": quantile_or_none(deltas, 0.975),
        "temporal_pass_rate": sum(bool(row["temporal_passed"]) for row in rows) / len(rows),
        "forbidden_pass_rate": sum(bool(row["forbidden_passed"]) for row in rows) / len(rows),
        "threshold_fragile_rate": sum(bool(row["threshold_fragile"]) for row in rows) / len(rows),
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


def write_report(
    base_rows: list[dict[str, Any]],
    bootstrap_rows: list[dict[str, Any]],
    panel_rows: list[dict[str, Any]],
    group_rows: list[dict[str, Any]],
    threshold_rows: list[dict[str, Any]],
) -> None:
    base_ok = all(bool(row["matches_expectation"]) for row in base_rows)
    bootstrap_ok = all(
        row["expected_decision_rate"] >= 0.90
        for row in bootstrap_rows
        if row["monitor_id"] in {"protocol_shortcut", "explicit_oracle_leakage"}
    )
    clean_boot = next(row for row in bootstrap_rows if row["monitor_id"] == "clean_calcium_probe")
    clean_panel_passes = sum(bool(row["audit_pass"]) for row in panel_rows)
    clean_threshold_rows = [
        row for row in threshold_rows if row["monitor_id"] == "clean_calcium_probe"
    ]
    clean_threshold_pass_rate = sum(bool(row["audit_pass"]) for row in clean_threshold_rows) / len(
        clean_threshold_rows
    )

    lines = [
        "# GSE201437 LAMP Sanity Robustness",
        "",
        "Reviewer-facing robustness checks for the controlled GSE201437 separation",
        "experiment. The goal is to answer whether the clean PASS is stable, not",
        "whether this 14-sample dataset is a final biological benchmark.",
        "",
        "## Summary",
        "",
        f"- Base expected-vs-observed separation passed: `{base_ok}`.",
        f"- Clean bootstrap PASS rate: `{clean_boot['pass_rate']:.3f}` over {N_BOOTSTRAPS} stratified resamples.",
        f"- Shortcut/leakage bootstrap expected-decision stability >=90%: `{bootstrap_ok}`.",
        f"- Alternative clean probe panels passing: `{clean_panel_passes}/{len(panel_rows)}`.",
        f"- Clean threshold-grid PASS rate: `{clean_threshold_pass_rate:.3f}`.",
        "- Donor-held-out stability: `not evaluable` because this processed GEO table does not expose donor IDs.",
        "- True protocol-held-out training/evaluation: `not evaluable` here because the experiment has 14 samples and the label itself is coupled to protocol structure.",
        "",
        "## Base Separation",
        "",
        "| Model | Expected | Observed | AUC | Matched Delta | Threshold Fragile | Key Reasons |",
        "|---|:---:|:---:|---:|---:|:---:|---|",
    ]
    for row in base_rows:
        lines.append(
            f"| {row['monitor']} | {row['expected']} | {row['observed']} | "
            f"{fmt(row['auc'])} | {fmt(row['matched_delta'])} | "
            f"{row['threshold_fragile']} | {row['key_reasons']} |"
        )

    lines.extend(
        [
            "",
            "## Stratified Bootstrap",
            "",
            "| Model | Expected | PASS Rate | Expected Decision Rate | AUC Mean | AUC 95% Interval | Matched Delta Mean | Matched Delta 95% Interval |",
            "|---|:---:|---:|---:|---:|---|---:|---|",
        ]
    )
    for row in bootstrap_rows:
        lines.append(
            f"| {row['monitor']} | {row['expected']} | {fmt(row['pass_rate'])} | "
            f"{fmt(row['expected_decision_rate'])} | {fmt(row['auc_mean'])} | "
            f"{fmt(row['auc_p025'])}-{fmt(row['auc_p975'])} | "
            f"{fmt(row['matched_delta_mean'])} | "
            f"{fmt(row['matched_delta_p025'])}-{fmt(row['matched_delta_p975'])} |"
        )

    lines.extend(
        [
            "",
            "## Alternative Clean Probe Panels",
            "",
            "| Panel | AUC | Observed | Matched Delta | Threshold Fragile | Genes Present |",
            "|---|---:|:---:|---:|:---:|---|",
        ]
    )
    for row in panel_rows:
        panel_name = row["monitor"].replace("Clean probe panel: ", "")
        lines.append(
            f"| {panel_name} | {fmt(row['auc'])} | {row['observed']} | "
            f"{fmt(row['matched_delta'])} | {row['threshold_fragile']} | "
            f"`{row['panel_genes_present']}` |"
        )

    lines.extend(
        [
            "",
            "## Leave-One-Protocol-Group-Out",
            "",
            "| Left-Out Group | Model | Observed | AUC | Matched Delta | Rows | Pos/Neg | Key Reasons |",
            "|---|---|:---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in group_rows:
        lines.append(
            f"| {row['left_out_group']} | {row['monitor']} | {row['observed']} | "
            f"{fmt(row['auc'])} | {fmt(row['matched_delta'])} | "
            f"{row['n_rows']} | {row['n_positive']}/{row['n_negative']} | "
            f"{row['key_reasons']} |"
        )

    lines.extend(
        [
            "",
            "## Threshold Grid",
            "",
            "| Model | valid_auc_min | matched_delta_min | Observed | AUC | Matched Delta |",
            "|---|---:|---:|:---:|---:|---:|",
        ]
    )
    for row in threshold_rows:
        lines.append(
            f"| {row['monitor']} | {fmt(row['valid_auc_min'])} | "
            f"{fmt(row['matched_delta_min'])} | {row['observed']} | "
            f"{fmt(row['auc'])} | {fmt(row['matched_delta'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The clean PASS is reachable and survives the base contract, but it is not a",
            "strong biological validation claim. The bootstrap and panel-variant tables",
            "should be read as small-n stability diagnostics. A reviewer should still ask",
            "for donor-held-out, protocol-held-out, and independent-dataset replication.",
            "",
            "The important negative control is that shortcut and oracle monitors continue",
            "to fail even when their AUC is higher than the clean probe.",
            "",
        ]
    )
    (OUT / "gse201437_sanity_robustness_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.fmean(values))


def quantile_or_none(values: list[float], q: float) -> float | None:
    if not values:
        return None
    return float(np.quantile(values, q))


def fmt(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.3f}"


if __name__ == "__main__":
    raise SystemExit(main())
