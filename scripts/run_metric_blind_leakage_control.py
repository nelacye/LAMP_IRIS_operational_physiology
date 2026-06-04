#!/usr/bin/env python3
"""Controlled synthetic test for metric-blind oracle leakage.

The experiment keeps the synthetic population and valid score fixed, then mixes
in a known oracle score at increasing doses. It records both ordinary AUC deltas
and LAMP's information-contract decision.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from lamp.audit import LAMP_Audit


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "metric_blind_leakage_control"
SEED = 20260531
N = 20_000
LAMBDAS = [0.0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10]
AUC_DELTA_ALERT = 0.01
WRITE_INPUT_TABLE = False


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = generate_rows()
    table_columns = list(rows[0])

    audit_rows = []
    baseline_auc = None
    for lam in LAMBDAS:
        score_col = lambda_column(lam)
        result = LAMP_Audit(
            config=build_config(score_col=score_col, lam=lam),
            rows=rows,
            table_columns=table_columns,
        ).run(OUT_DIR / "lamp" / lambda_slug(lam))

        auc = result["primary_score"]["auc"]
        if lam == 0:
            baseline_auc = auc
        assert baseline_auc is not None

        dossier = result["failure_mode_dossier"]
        relations = result["sentinel_relations"].get("oracle_label", {})
        temporal = result["temporal_isolation"]
        forbidden = result["forbidden_feature_screen"]
        auc_delta = auc - baseline_auc

        audit_rows.append(
            {
                "lambda": lam,
                "score_column": score_col,
                "auc": auc,
                "delta_auc": auc_delta,
                "auc_delta_alert_0p01": abs(auc_delta) >= AUC_DELTA_ALERT,
                "audit_pass": dossier["audit_pass_candidate"],
                "temporal_passed": temporal["passed"],
                "forbidden_passed": forbidden["passed"],
                "oracle_proximity": relations.get("auc_leakage_proximity"),
                "oracle_proximity_alert": relations.get("oracle_proximity_alert"),
                "output_classes": ";".join(dossier["output_classes"]),
            }
        )

    if WRITE_INPUT_TABLE:
        write_input_table(rows)
    write_summary_csv(audit_rows)
    write_report(audit_rows)
    write_figure(audit_rows)
    print(OUT_DIR / "metric_blind_leakage_report.md")
    return 0


def generate_rows() -> list[dict[str, Any]]:
    rng = np.random.default_rng(SEED)
    latent_reserve = rng.normal(size=N)
    visible_severity = 0.75 * latent_reserve + rng.normal(scale=0.90, size=N)
    age_z = rng.normal(size=N)
    workflow_noise = rng.normal(size=N)

    label_prob = sigmoid(1.60 * latent_reserve + 0.30 * visible_severity + 0.05 * age_z)
    outcome = rng.binomial(1, label_prob)
    valid_score = sigmoid(
        1.60 * latent_reserve
        + 0.35 * visible_severity
        + 0.08 * age_z
        + rng.normal(scale=0.70, size=N)
    )
    oracle_score = outcome.astype(float)
    future_score = sigmoid(
        1.00 * latent_reserve
        + 0.80 * outcome
        + 0.20 * workflow_noise
        + rng.normal(scale=0.90, size=N)
    )

    rows: list[dict[str, Any]] = []
    for idx in range(N):
        row: dict[str, Any] = {
            "subject_id": f"synthetic_{idx:05d}",
            "anchor_time_h": 0,
            "outcome": int(outcome[idx]),
            "latent_reserve_probe": float(latent_reserve[idx]),
            "visible_severity": float(visible_severity[idx]),
            "age_z": float(age_z[idx]),
            "workflow_noise": float(workflow_noise[idx]),
            "valid_score": float(valid_score[idx]),
            "oracle_score": float(oracle_score[idx]),
            "future_score": float(future_score[idx]),
        }
        for lam in LAMBDAS:
            row[lambda_column(lam)] = float((1.0 - lam) * valid_score[idx] + lam * oracle_score[idx])
        rows.append(row)
    return rows


def build_config(score_col: str, lam: float) -> dict[str, Any]:
    valid_feature_names = ["latent_reserve_probe", "visible_severity", "age_z"]
    temporal_features: list[dict[str, Any]] = [
        {"name": "latent_reserve_probe", "latest_offset_h": 0},
        {"name": "visible_severity", "latest_offset_h": 0},
        {"name": "age_z", "latest_offset_h": 0},
    ]
    if lam > 0:
        valid_feature_names.append("oracle_score")
        temporal_features.append({"name": "oracle_score", "latest_offset_h": 999})

    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"Metric-blind leakage synthetic control lambda={lam:g}",
            "task": "controlled oracle-mixture validity audit",
            "role": "synthetic control experiment",
        },
        "columns": {
            "subject_id": "subject_id",
            "label": "outcome",
            "positive_value": 1,
            "score": score_col,
            "anchor_time": "anchor_time_h",
        },
        "temporal_isolation": {
            "anchor": "anchor_time_h",
            "valid_features_must_be": "at_or_before_anchor",
            "frozen_before_holdout": [
                "synthetic data-generating process",
                "valid score",
                "oracle mixture grid",
                "LAMP thresholds",
            ],
            "valid_score_features": temporal_features,
        },
        "forbidden_features": {
            "columns": ["oracle_score", "future_score"],
            "valid_score_features": valid_feature_names,
        },
        "sentinels": {
            "future_physiology": {
                "column": "future_score",
                "role": "future_physiology",
                "expected_signature": "invalid post-anchor comparator",
            },
            "oracle_label": {
                "column": "oracle_score",
                "role": "oracle_label",
                "expected_signature": "known ceiling label-adjacent leakage",
            },
        },
        "leakage_proximity": {
            "baseline_score": "valid_score",
            "oracle_proximity_alert_min": 0.01,
        },
        "negative_controls": {
            "n_permutations": 100,
            "seed": 31,
        },
        "visible_state_matching": {
            "columns": ["visible_severity", "age_z"],
            "n_bins": 4,
            "min_bin_size": 30,
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.02,
            "matched_collapse_max": 0.005,
            "score_thresholds": [0.25, 0.50, 0.75],
        },
    }


def write_input_table(rows: list[dict[str, Any]]) -> None:
    with (OUT_DIR / "synthetic_metric_blind_input.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_summary_csv(rows: list[dict[str, Any]]) -> None:
    with (OUT_DIR / "metric_blind_leakage_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows: list[dict[str, Any]]) -> None:
    baseline = rows[0]
    first_blind = next(row for row in rows if row["lambda"] > 0 and not row["auc_delta_alert_0p01"])
    lines = [
        "# Metric-Blind Leakage Synthetic Control",
        "",
        "This control keeps the data-generating process and valid score fixed, then",
        "adds a known oracle-label score at dose lambda:",
        "",
        "`mixed_score = (1 - lambda) * valid_score + lambda * oracle_score`",
        "",
        "The purpose is to test whether metric-blind leakage is a structural failure",
        "mode rather than an artifact of a particular clinical or LLM benchmark.",
        "",
        "## Key Result",
        "",
        (
            f"Baseline valid AUC is {baseline['auc']:.4f}. At lambda={first_blind['lambda']:.3g}, "
            f"AUC is {first_blind['auc']:.4f} (delta={first_blind['delta_auc']:.4f}), below "
            f"the conventional {AUC_DELTA_ALERT:.2f} AUC-delta alert used here. LAMP still fails "
            "the monitor because the information contract is already broken."
        ),
        "",
        "In other words, performance can remain statistically boring while validity has already collapsed.",
        "",
        "## Summary",
        "",
        "| lambda | AUC | delta AUC | AUC-delta alert | LAMP pass | temporal | forbidden | oracle proximity | oracle alert |",
        "|---:|---:|---:|:---:|:---:|:---:|:---:|---:|:---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['lambda']:.3g} | "
            f"{row['auc']:.4f} | "
            f"{row['delta_auc']:.4f} | "
            f"{bool(row['auc_delta_alert_0p01'])} | "
            f"{bool(row['audit_pass'])} | "
            f"{bool(row['temporal_passed'])} | "
            f"{bool(row['forbidden_passed'])} | "
            f"{format_optional(row['oracle_proximity'])} | "
            f"{bool(row['oracle_proximity_alert'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "AUC answers whether rank discrimination changed. LAMP answers whether the",
            "score was allowed to know what made it discriminate. The first nonzero",
            "oracle dose already violates the declared temporal and forbidden-feature",
            "contract, even when the AUC movement is smaller than a simple metric-delta",
            "screen would treat as noteworthy.",
            "",
            "This is the controlled synthetic version of the empirical observation from",
            "the PhysioNet/CinC 2019 neural audit: RF valid AUC 0.8188 versus 1% oracle",
            "mixture AUC 0.8231. Small metric movement does not imply preserved validity.",
            "",
            "![AUC versus LAMP decision](metric_blind_leakage_curve.png)",
            "",
        ]
    )
    (OUT_DIR / "metric_blind_leakage_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_figure(rows: list[dict[str, Any]]) -> None:
    lambdas = [row["lambda"] for row in rows]
    aucs = [row["auc"] for row in rows]
    pass_status = [row["audit_pass"] for row in rows]
    auc_flags = [row["auc_delta_alert_0p01"] for row in rows]

    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=180)
    ax.plot(lambdas, aucs, color="black", linewidth=1.8, marker="o", label="AUC")
    for lam, auc, passed, metric_flag in zip(lambdas, aucs, pass_status, auc_flags):
        if passed:
            ax.scatter([lam], [auc], marker="s", s=70, edgecolor="black", facecolor="white", zorder=3)
        elif metric_flag:
            ax.scatter([lam], [auc], marker="o", s=70, edgecolor="black", facecolor="black", zorder=3)
        else:
            ax.scatter([lam], [auc], marker="x", s=70, color="black", zorder=3)
    ax.axhline(aucs[0] + AUC_DELTA_ALERT, color="black", linestyle=":", linewidth=1.0)
    ax.text(
        lambdas[-1],
        aucs[0] + AUC_DELTA_ALERT + 0.002,
        "AUC + 0.01",
        ha="right",
        va="bottom",
        fontsize=9,
    )
    ax.set_xlabel("Oracle leakage dose (lambda)")
    ax.set_ylabel("ROC AUC")
    ax.set_title("Metric-blind leakage: small AUC movement, broken contract")
    ax.set_xlim(-0.002, max(lambdas) + 0.005)
    ax.grid(axis="y", color="0.85", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "metric_blind_leakage_curve.png")
    plt.close(fig)


def lambda_column(lam: float) -> str:
    return f"mixed_score_l{lambda_slug(lam)}"


def lambda_slug(lam: float) -> str:
    return str(lam).replace(".", "p")


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def format_optional(value: Any) -> str:
    if value is None:
        return "NA"
    return f"{float(value):.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
