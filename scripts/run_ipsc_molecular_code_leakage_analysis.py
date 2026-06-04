#!/usr/bin/env python3
"""ROC, confusion-matrix, and leakage-sensitivity analysis for iPSC molecular code."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import auc as sklearn_auc
from sklearn.metrics import roc_curve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from lamp.audit import run_audit  # noqa: E402
from lamp.bio import diagnose_biological_claim, load_bio_contract  # noqa: E402
from run_synthetic_ipsc_molecular_code_audit import (  # noqa: E402
    CLAIM_ID,
    CONTRACT_PATH,
    MONITORS,
    OUT,
    SEED,
    build_config,
    z,
)


BASE = OUT
PREDICTIONS = BASE / "synthetic_ipsc_molecular_code_predictions.csv"
ANALYSIS = BASE / "leakage_sensitivity"
FIGURES = ANALYSIS / "figures"
LAMBDA_VALUES = [
    0.0,
    0.00001,  # 0.001%
    0.00005,  # 0.005%
    0.00010,  # 0.01%
    0.00050,  # 0.05%
    0.00100,  # 0.1%
    0.00200,  # 0.2%
    0.00500,  # 0.5%
    0.01000,  # 1%
    0.02000,  # 2%
    0.05000,  # 5%
    0.10000,  # 10%
]


def main() -> int:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(PREDICTIONS)

    plot_roc_overlay(table)
    canonical_rows = canonical_confusion_rows()
    strict_rows, geometry_rows, sweep_table = run_lambda_sweep(table)

    write_csv(ANALYSIS / "canonical_lamp_confusion_table.csv", canonical_rows)
    write_csv(ANALYSIS / "oracle_leakage_sensitivity_strict.csv", strict_rows)
    write_csv(ANALYSIS / "oracle_leakage_sensitivity_geometry_only.csv", geometry_rows)
    sweep_table.to_csv(ANALYSIS / "oracle_leakage_sensitivity_predictions.csv", index=False)

    plot_confusion_matrix(canonical_rows)
    plot_sensitivity(strict_rows, geometry_rows)
    write_report(canonical_rows, strict_rows, geometry_rows)
    print(ANALYSIS / "ipsc_molecular_code_leakage_analysis_report.md")
    return 0


def plot_roc_overlay(table: pd.DataFrame) -> None:
    y = table["label_later_folding_execution_stable"].astype(int).to_numpy()
    series = [
        ("Clean hybrid", "clean_hybrid_kinase_folding_score", "#111111", "-"),
        ("0.5% oracle mix", "lowdose_oracle_mix_005_score", "#666666", "--"),
        ("Oracle ceiling", "oracle_folding_label_score", "#000000", ":"),
    ]
    plt.figure(figsize=(7.0, 5.8))
    for label, column, color, linestyle in series:
        fpr, tpr, _ = roc_curve(y, table[column].to_numpy(dtype=float))
        roc_auc = sklearn_auc(fpr, tpr)
        plt.plot(
            fpr,
            tpr,
            color=color,
            linestyle=linestyle,
            linewidth=2.2,
            label=f"{label} AUC={roc_auc:.4f}",
        )
    plt.plot([0, 1], [0, 1], color="#999999", linewidth=1.0, linestyle="-")
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title("Clean vs 0.5% oracle-contaminated ROC")
    plt.legend(loc="lower right", frameon=False)
    plt.tight_layout()
    plt.savefig(FIGURES / "roc_clean_vs_oracle_005.png", dpi=220)
    plt.close()


def canonical_confusion_rows() -> list[dict[str, Any]]:
    contract = load_bio_contract(CONTRACT_PATH)
    rows = []
    truth = {
        "clean_hybrid_kinase_folding": "valid",
        "kinase_only_probe": "valid",
        "protocol_stressor_shortcut": "invalid",
        "future_folding_leakage": "invalid",
        "oracle_endpoint_leakage": "invalid",
        "lowdose_oracle_mix_005": "invalid",
    }
    for monitor in MONITORS:
        monitor_id = monitor["id"]
        audit_path = BASE / "lamp" / monitor_id / "audit_summary.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        diagnosis = diagnose_biological_claim(
            audit,
            contract,
            CLAIM_ID,
            monitor["score_axis"],
            monitor.get("stability") or None,
        )
        expected = truth[monitor_id]
        predicted = "valid" if audit["failure_mode_dossier"]["audit_pass_candidate"] else "invalid"
        rows.append(
            {
                "monitor_id": monitor_id,
                "ground_truth_contract": expected,
                "lamp_decision": predicted,
                "correct": expected == predicted,
                "auc": audit["primary_score"]["auc"],
                "matched_delta": audit["visible_state_matching"].get("matched_observed_state_delta"),
                "bio_diagnosis": diagnosis["diagnosis"],
            }
        )
    return rows


def run_lambda_sweep(
    table: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], pd.DataFrame]:
    sweep_table = table.copy()
    clean = z(sweep_table["clean_hybrid_kinase_folding_score"].to_numpy(dtype=float))
    oracle = z(sweep_table["oracle_folding_label_score"].to_numpy(dtype=float))
    strict_rows = []
    geometry_rows = []

    for lam in LAMBDA_VALUES:
        column = lambda_column(lam)
        sweep_table[column] = z((1.0 - lam) * clean + lam * oracle)

    prediction_path = ANALYSIS / "oracle_leakage_sensitivity_prediction_table.csv"
    sweep_table.to_csv(prediction_path, index=False, lineterminator="\n")

    for lam in LAMBDA_VALUES:
        strict_rows.append(run_lambda_audit(sweep_table, prediction_path, lam, mode="strict_declared"))
        geometry_rows.append(run_lambda_audit(sweep_table, prediction_path, lam, mode="geometry_only"))
    return strict_rows, geometry_rows, sweep_table


def run_lambda_audit(
    table: pd.DataFrame,
    prediction_path: Path,
    lam: float,
    mode: str,
) -> dict[str, Any]:
    monitor = {
        "id": f"oracle_mix_{mode}_{lambda_id(lam)}",
        "name": f"{mode} oracle mixture lambda={lam:g}",
        "score": lambda_column(lam),
        "features": [
            "early_mapk_phospho_slope",
            "early_akt_mtor_pulse",
            "early_gsk3_cdk_balance",
            "early_stress_kinase_persistence",
            "early_chaperone_buffer",
            "early_upr_load",
            "early_autophagy_flux",
        ],
        "score_axis": "kinase_folding_coupled_signal",
        "expected": "PASS" if lam == 0 else "FAIL",
    }
    if mode == "strict_declared" and lam > 0:
        monitor["features"] = [*monitor["features"], "oracle_folding_label_score"]

    config = build_config(monitor)
    config["dataset"]["leakage_lambda"] = lam
    config["dataset"]["leakage_percent"] = 100.0 * lam
    config["dataset"]["sensitivity_mode"] = mode
    if mode == "geometry_only":
        config["temporal_isolation"]["valid_features_must_be"] = (
            "provenance-blind geometry-only run: score internals are not declared"
        )
    config_path = ANALYSIS / "configs" / mode / f"{lambda_id(lam)}.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    audit = run_audit(config_path, prediction_path, ANALYSIS / "lamp" / mode / lambda_id(lam))
    primary_auc = audit["primary_score"]["auc"]
    clean_auc = canonical_auc("clean_hybrid_kinase_folding")
    output_classes = audit["failure_mode_dossier"]["output_classes"]
    oracle_relation = audit["sentinel_relations"].get("oracle_endpoint", {})
    return {
        "mode": mode,
        "lambda": lam,
        "leakage_percent": 100.0 * lam,
        "score_column": lambda_column(lam),
        "ground_truth_contract": "valid" if lam == 0 else "invalid",
        "lamp_decision": "valid"
        if audit["failure_mode_dossier"]["audit_pass_candidate"]
        else "invalid",
        "detected": bool(not audit["failure_mode_dossier"]["audit_pass_candidate"]),
        "auc": primary_auc,
        "delta_auc_vs_clean": None if primary_auc is None else primary_auc - clean_auc,
        "temporal_passed": audit["temporal_isolation"]["passed"],
        "forbidden_passed": audit["forbidden_feature_screen"]["passed"],
        "oracle_proximity": oracle_relation.get("auc_leakage_proximity"),
        "oracle_proximity_alert": oracle_relation.get("oracle_proximity_alert"),
        "output_classes": ";".join(output_classes),
    }


def canonical_auc(monitor_id: str) -> float:
    audit = json.loads((BASE / "lamp" / monitor_id / "audit_summary.json").read_text(encoding="utf-8"))
    return float(audit["primary_score"]["auc"])


def plot_confusion_matrix(rows: list[dict[str, Any]]) -> None:
    labels = ["valid", "invalid"]
    matrix = np.zeros((2, 2), dtype=int)
    for row in rows:
        matrix[labels.index(row["ground_truth_contract"]), labels.index(row["lamp_decision"])] += 1

    plt.figure(figsize=(5.6, 4.8))
    plt.imshow(matrix, cmap="Greys", vmin=0)
    plt.xticks([0, 1], ["LAMP valid", "LAMP invalid"])
    plt.yticks([0, 1], ["Truth valid", "Truth invalid"])
    for i in range(2):
        for j in range(2):
            color = "white" if matrix[i, j] > matrix.max() / 2 else "black"
            plt.text(j, i, str(matrix[i, j]), ha="center", va="center", color=color, fontsize=16)
    plt.title("LAMP decision vs known synthetic contract")
    plt.tight_layout()
    plt.savefig(FIGURES / "lamp_confusion_matrix.png", dpi=220)
    plt.close()


def plot_sensitivity(
    strict_rows: list[dict[str, Any]],
    geometry_rows: list[dict[str, Any]],
) -> None:
    fig, (ax_auc, ax_decision) = plt.subplots(
        2,
        1,
        figsize=(7.4, 7.0),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )
    nonzero = [row for row in geometry_rows if row["leakage_percent"] > 0]
    x = [row["leakage_percent"] for row in nonzero]
    y = [row["delta_auc_vs_clean"] for row in nonzero]
    ax_auc.plot(x, y, color="#111111", marker="o", linewidth=1.9, label="AUC lift")
    ax_auc.axhline(0.0, color="#999999", linewidth=1.0)
    ax_auc.axvline(0.5, color="#bbbbbb", linewidth=1.0, linestyle="--")
    ax_auc.text(0.0011, 0.00035, "0% clean baseline: delta AUC = 0", fontsize=10)
    ax_auc.set_ylabel("AUC lift vs clean")
    ax_auc.set_title("Leakage dose sensitivity")
    ax_auc.legend(frameon=False, loc="upper left")

    for rows, label, color, marker, offset in [
        (strict_rows, "strict declared", "#111111", "o", 0.03),
        (geometry_rows, "geometry only", "#666666", "s", -0.03),
    ]:
        nonzero_rows = [row for row in rows if row["leakage_percent"] > 0]
        decision_x = [row["leakage_percent"] for row in nonzero_rows]
        decision_y = [(1.0 if row["detected"] else 0.0) + offset for row in nonzero_rows]
        ax_decision.step(
            decision_x,
            decision_y,
            where="post",
            color=color,
            linewidth=1.8,
            label=label,
        )
        ax_decision.scatter(decision_x, decision_y, color=color, marker=marker, s=36)

    ax_decision.set_xscale("log")
    ax_decision.set_ylim(-0.18, 1.18)
    ax_decision.set_yticks([0, 1])
    ax_decision.set_yticklabels(["not detected", "detected"])
    ax_decision.set_xlabel("Oracle leakage dose (%)")
    ax_decision.set_ylabel("LAMP")
    ax_decision.legend(frameon=False, loc="center left")
    ax_decision.grid(axis="y", color="#dddddd", linewidth=0.8)
    plt.tight_layout()
    fig.savefig(FIGURES / "oracle_leakage_sensitivity.png", dpi=220)
    plt.close()


def write_report(
    canonical_rows: list[dict[str, Any]],
    strict_rows: list[dict[str, Any]],
    geometry_rows: list[dict[str, Any]],
) -> None:
    cm = confusion_metrics(canonical_rows)
    strict_first = first_detected(strict_rows)
    geometry_first = first_detected(geometry_rows)
    clean_auc = canonical_auc("clean_hybrid_kinase_folding")
    lowdose_auc = canonical_auc("lowdose_oracle_mix_005")
    lines = [
        "# iPSC Molecular-Code Leakage Analysis",
        "",
        "This analysis adds ROC overlays, a known-truth confusion matrix, and",
        "oracle-leakage sensitivity curves to the synthetic molecular-code audit.",
        "",
        "## ROC Overlay",
        "",
        f"- Clean hybrid AUC: `{clean_auc:.4f}`.",
        f"- 0.5% oracle mix AUC: `{lowdose_auc:.4f}`.",
        f"- Delta AUC: `{lowdose_auc - clean_auc:.4f}`.",
        f"- Figure: `figures/roc_clean_vs_oracle_005.png`.",
        "",
        "## LAMP vs Known Synthetic Contract",
        "",
        f"- True positives (invalid detected): `{cm['tp']}`.",
        f"- True negatives (valid accepted): `{cm['tn']}`.",
        f"- False positives: `{cm['fp']}`.",
        f"- False negatives: `{cm['fn']}`.",
        f"- Sensitivity: `{cm['sensitivity']:.3f}`.",
        f"- Specificity: `{cm['specificity']:.3f}`.",
        f"- Figure: `figures/lamp_confusion_matrix.png`.",
        "",
        "## Leakage Sensitivity",
        "",
        f"- Strict declared provenance first detects leakage at `{strict_first['leakage_percent']:.4g}%`.",
        f"- Geometry-only first detects leakage at `{geometry_first['leakage_percent']:.4g}%`.",
        f"- Figure: `figures/oracle_leakage_sensitivity.png`.",
        "",
        "| Lambda | Leakage % | Strict AUC | Strict Decision | Geometry AUC | Geometry Decision | Geometry Proximity |",
        "|---:|---:|---:|---|---:|---|---:|",
    ]
    by_lambda = {row["lambda"]: row for row in geometry_rows}
    for strict in strict_rows:
        geom = by_lambda[strict["lambda"]]
        lines.append(
            f"| {strict['lambda']:.5g} | {strict['leakage_percent']:.4g} | "
            f"{fmt(strict['auc'])} | {strict['lamp_decision']} | "
            f"{fmt(geom['auc'])} | {geom['lamp_decision']} | "
            f"{fmt(geom['oracle_proximity'])} |"
        )
    lines.extend(
        [
            "",
            "Interpretation: strict provenance mode is a hard information-contract test.",
            "If the score is known to include any endpoint/oracle channel, any nonzero",
            "lambda is invalid. Geometry-only mode is weaker but still detects tiny",
            "rank-geometry shifts once the oracle proximity exceeds the configured",
            "threshold.",
            "",
        ]
    )
    (ANALYSIS / "ipsc_molecular_code_leakage_analysis_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def confusion_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(row["ground_truth_contract"] == "invalid" and row["lamp_decision"] == "invalid" for row in rows)
    tn = sum(row["ground_truth_contract"] == "valid" and row["lamp_decision"] == "valid" for row in rows)
    fp = sum(row["ground_truth_contract"] == "valid" and row["lamp_decision"] == "invalid" for row in rows)
    fn = sum(row["ground_truth_contract"] == "invalid" and row["lamp_decision"] == "valid" for row in rows)
    sensitivity = tp / (tp + fn) if tp + fn else float("nan")
    specificity = tn / (tn + fp) if tn + fp else float("nan")
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "sensitivity": sensitivity, "specificity": specificity}


def first_detected(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row["lambda"] > 0 and row["lamp_decision"] == "invalid":
            return row
    return {"leakage_percent": float("nan")}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def lambda_id(lam: float) -> str:
    return f"lambda_{lam:.5f}".replace(".", "p")


def lambda_column(lam: float) -> str:
    return f"oracle_mix_{lambda_id(lam)}_score"


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
