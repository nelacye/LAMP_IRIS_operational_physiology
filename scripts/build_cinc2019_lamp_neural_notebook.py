#!/usr/bin/env python3
"""Build the CinC 2019 neural LAMP audit notebook and figures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import RocCurveDisplay, auc, roc_curve


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/physionet_sequence_lamp"
NOTEBOOK = ROOT / "notebooks/cinc2019_lamp_neural_audit.ipynb"
FIG_DIR = ROOT / "notebooks/figures"


KEY_SCORES = [
    "mlp_probe_valid_score",
    "mlp_probe_leaky_score",
    "mlp_probe_valid_score_oracle_mix_1pct",
    "rf_valid_score",
    "rf_future_leaky_score",
    "xgb_valid_score",
    "xgb_future_leaky_score",
    "lstm_valid_score",
    "lstm_future_leaky_score",
    "transformer_valid_score",
    "transformer_future_leaky_score",
    "transformer_hidden_probe_score",
    "transformer_future_hidden_probe_score",
]


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(RESULTS / "physionet_sequence_lamp_summary.csv")
    metrics = pd.read_csv(RESULTS / "physionet_sequence_metrics.csv")
    registry = pd.read_csv(RESULTS / "model_registry.csv")
    predictions = pd.read_csv(RESULTS / "physionet_sequence_predictions.csv")
    report_text = (RESULTS / "physionet_sequence_lamp_report.md").read_text(encoding="utf-8")

    joined = (
        summary.merge(registry, on="score", how="left")
        .assign(key_failures=lambda df: df.apply(key_failures, axis=1))
        .sort_values(["audit_pass", "auc"], ascending=[False, False])
    )

    figure_paths = build_figures(summary, metrics, registry, predictions)
    notebook = build_notebook(joined, metrics, figure_paths, report_text)
    NOTEBOOK.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
    print(json.dumps({"notebook": str(NOTEBOOK), "figures": figure_paths}, indent=2))
    return 0


def build_figures(
    summary: pd.DataFrame,
    metrics: pd.DataFrame,
    registry: pd.DataFrame,
    predictions: pd.DataFrame,
) -> dict[str, str]:
    paths = {}
    paths["auc_bar"] = save_auc_bar(summary, registry)
    paths["roc"] = save_roc_curves(predictions)
    paths["leakage_dose"] = save_leakage_dose(metrics, registry)
    paths["horizon_arch"] = save_horizon_architecture(metrics, registry)
    paths["timeline"] = save_timeline_schema()
    paths["empirical_timeline"] = save_empirical_timeline(predictions)
    paths["audit_gates"] = save_audit_gates(summary, registry)
    return paths


def save_auc_bar(summary: pd.DataFrame, registry: pd.DataFrame) -> str:
    df = summary.merge(registry, on="score", how="left")
    keep = df[df["score"].isin(KEY_SCORES)].copy()
    keep["label"] = keep["name"].fillna(keep["monitor"])
    keep = keep.sort_values("auc")

    fig, ax = plt.subplots(figsize=(11, 7))
    colors = keep["audit_pass"].map({True: "#2E7D32", False: "#B23A48"}).fillna("#555")
    ax.barh(keep["label"], keep["auc"], color=colors)
    ax.axvline(0.60, color="#333", linestyle="--", linewidth=1, label="valid_auc_min")
    ax.set_xlabel("Pooled held-out AUC")
    ax.set_title("LAMP separates performance from audit validity")
    ax.set_xlim(0.45, 1.02)
    ax.legend(loc="lower right")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    return savefig(fig, "cinc2019_auc_bar.png")


def save_roc_curves(predictions: pd.DataFrame) -> str:
    scores = [
        ("MLP valid", "mlp_probe_valid_score"),
        ("MLP leaky", "mlp_probe_leaky_score"),
        ("XGBoost valid", "xgb_valid_score"),
        ("XGBoost leaky", "xgb_future_leaky_score"),
        ("LSTM valid", "lstm_valid_score"),
        ("LSTM leaky", "lstm_future_leaky_score"),
        ("Transformer hidden probe", "transformer_hidden_probe_score"),
        ("Transformer future probe", "transformer_future_hidden_probe_score"),
    ]
    y = predictions["label_future_sepsis"].astype(int).to_numpy()

    fig, ax = plt.subplots(figsize=(8, 7))
    for label, col in scores:
        if col not in predictions:
            continue
        fpr, tpr, _ = roc_curve(y, predictions[col].to_numpy())
        RocCurveDisplay(fpr=fpr, tpr=tpr, roc_auc=auc(fpr, tpr), name=label).plot(ax=ax)
    ax.plot([0, 1], [0, 1], color="#777", linestyle="--", linewidth=1)
    ax.set_title("ROC curves: valid vs leaky monitors")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    return savefig(fig, "cinc2019_roc_curves.png")


def save_leakage_dose(metrics: pd.DataFrame, registry: pd.DataFrame) -> str:
    df = metrics.merge(registry, on="score", how="left")
    dose = df[df["type"].eq("low-dose leakage")].copy()
    dose = dose[dose["family"].isin(["mlp_probe", "Random Forest", "XGBoost", "LSTM", "TRANSFORMER"])]
    valid = df[df["type"].eq("valid")][["horizon_h", "family", "auc"]].rename(columns={"auc": "valid_auc"})
    dose = dose.merge(valid, on=["horizon_h", "family"], how="left")
    dose["auc_lift"] = dose["auc"] - dose["valid_auc"]
    dose["lambda_pct"] = pd.to_numeric(dose["leakage_lambda"], errors="coerce") * 100

    fig, ax = plt.subplots(figsize=(10, 6))
    for family, group in dose.groupby("family"):
        by_lambda = group.groupby("lambda_pct")["auc_lift"].mean().reset_index()
        ax.plot(by_lambda["lambda_pct"], by_lambda["auc_lift"], marker="o", label=family)
    ax.axhline(0, color="#333", linewidth=1)
    ax.set_xlabel("Oracle leakage dose (%)")
    ax.set_ylabel("Mean AUC lift over valid score")
    ax.set_title("Low-dose leakage raises AUC while LAMP flags invalid feature use")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    return savefig(fig, "cinc2019_leakage_dose_auc_lift.png")


def save_horizon_architecture(metrics: pd.DataFrame, registry: pd.DataFrame) -> str:
    df = metrics.merge(registry, on="score", how="left")
    valid = df[df["type"].eq("valid")].copy()
    valid = valid[valid["family"].isin(["MLP probe", "Random Forest", "XGBoost", "LSTM", "GRU", "TRANSFORMER"])]

    fig, ax = plt.subplots(figsize=(11, 6))
    for family, group in valid.groupby("family"):
        group = group.sort_values("horizon_h")
        ax.plot(group["horizon_h"], group["auc"], marker="o", label=family)
    ax.set_xlabel("Prediction horizon (hours)")
    ax.set_ylabel("Held-out AUC")
    ax.set_title("Architecture and horizon ablation")
    ax.set_xticks(sorted(valid["horizon_h"].unique()))
    ax.grid(alpha=0.25)
    ax.legend(ncol=2)
    fig.tight_layout()
    return savefig(fig, "cinc2019_horizon_architecture_ablation.png")


def save_timeline_schema() -> str:
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.axvspan(-12, 0, color="#D6EAF8", alpha=0.9, label="allowed early window")
    ax.axvspan(0, 18, color="#FADBD8", alpha=0.85, label="forbidden future window")
    for horizon in [6, 12, 18]:
        ax.axvline(horizon, color="#922B21", linestyle="--", linewidth=1)
        ax.text(horizon, 0.62, f"{horizon}h label/onset", rotation=90, va="center", ha="right")
    ax.axvline(0, color="#111", linewidth=2)
    ax.text(0, 0.95, "anchor", ha="center", va="top")
    ax.annotate(
        "valid monitor reads here",
        xy=(-6, 0.35),
        xytext=(-11.5, 0.15),
        arrowprops={"arrowstyle": "->", "color": "#1F618D"},
        color="#1F618D",
    )
    ax.annotate(
        "leaky monitor reads here -> LAMP temporal/forbidden gate fails",
        xy=(7, 0.35),
        xytext=(1, 0.08),
        arrowprops={"arrowstyle": "->", "color": "#922B21"},
        color="#922B21",
    )
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xlim(-13, 19)
    ax.set_xlabel("Hours relative to prediction anchor")
    ax.set_title("Timeline: where leakage enters the evaluation")
    ax.legend(loc="upper left", ncol=2)
    fig.tight_layout()
    return savefig(fig, "cinc2019_leakage_timeline_schema.png")


def save_empirical_timeline(predictions: pd.DataFrame) -> str:
    cols = [
        ("MLP valid", "mlp_probe_valid_score"),
        ("MLP leaky", "mlp_probe_leaky_score"),
        ("MLP 5% oracle mix", "mlp_probe_valid_score_oracle_mix_5pct"),
        ("Oracle", "oracle_leakage_ceiling_score"),
    ]
    positive = predictions[predictions["label_future_sepsis"].eq(1)].copy()
    positive["hours_to_onset"] = pd.to_numeric(positive["hours_to_onset"], errors="coerce")

    fig, ax = plt.subplots(figsize=(9, 6))
    for label, col in cols:
        if col not in positive:
            continue
        grouped = positive.groupby("hours_to_onset")[col].median().reset_index()
        ax.plot(grouped["hours_to_onset"], grouped[col], marker="o", label=label)
    ax.invert_xaxis()
    ax.set_xlabel("Hours before onset / label")
    ax.set_ylabel("Median score among positives")
    ax.set_title("Empirical timeline: leaky scores track future/oracle information")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    return savefig(fig, "cinc2019_empirical_leakage_timeline.png")


def save_audit_gates(summary: pd.DataFrame, registry: pd.DataFrame) -> str:
    df = summary.merge(registry, on="score", how="left")
    keep = df[df["score"].isin(KEY_SCORES + ["rf_future_leaky_score", "xgb_future_leaky_score"])].copy()
    keep["label"] = keep["name"].fillna(keep["monitor"])
    gate_matrix = pd.DataFrame(
        {
            "audit pass": keep["audit_pass"].astype(bool),
            "temporal clean": keep["temporal_passed"].astype(bool),
            "forbidden clean": keep["forbidden_passed"].astype(bool),
            "oracle proximity absent": ~keep["oracle_proximity_shift"].astype(bool),
        }
    )
    matrix = gate_matrix.astype(int).to_numpy()

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(gate_matrix.columns)))
    ax.set_xticklabels(gate_matrix.columns, rotation=25, ha="right")
    ax.set_yticks(np.arange(len(keep)))
    ax.set_yticklabels(keep["label"])
    ax.set_title("Audit gates by model")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, "pass" if matrix[i, j] else "fail", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    fig.tight_layout()
    return savefig(fig, "cinc2019_audit_gates.png")


def savefig(fig, filename: str) -> str:
    path = FIG_DIR / filename
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return str(path.relative_to(ROOT)).replace("\\", "/")


def build_notebook(
    joined: pd.DataFrame,
    metrics: pd.DataFrame,
    figure_paths: dict[str, str],
    report_text: str,
) -> dict[str, Any]:
    comparison = comparison_table(joined)
    valid_leaky = valid_leaky_table(joined)
    probe_table = probe_summary_table(joined)
    dose_table = leakage_dose_table(joined)
    horizon_table = horizon_table_md(metrics)
    run_summary = extract_run_summary(report_text)
    figure_paths = {key: notebook_relative_path(path) for key, path in figure_paths.items()}

    cells = [
        md(
            "# CinC 2019 LAMP Neural Audit\n\n"
            "**Goal.** Audit neural and classical early-warning monitors trained on raw "
            "PhysioNet/CinC 2019 `.psv` trajectories, and show that higher AUC can be "
            "caused by evaluation gaming rather than valid early hidden-state inference.\n\n"
            f"{run_summary}"
        ),
        md(
            "## Executive Result\n\n"
            "LAMP distinguishes monitors with similar biomedical framing but different "
            "information contracts. Valid early-window models can pass the audit, while "
            "future-window and oracle-contaminated variants are flagged even when their "
            "AUC improves only modestly.\n\n"
            f"{valid_leaky}"
        ),
        code(
            "from pathlib import Path\n"
            "import pandas as pd\n"
            "from sklearn.metrics import roc_curve, auc\n\n"
            "ROOT = Path('..').resolve()\n"
            "RESULTS = ROOT / 'results' / 'physionet_sequence_lamp'\n"
            "summary = pd.read_csv(RESULTS / 'physionet_sequence_lamp_summary.csv')\n"
            "metrics = pd.read_csv(RESULTS / 'physionet_sequence_metrics.csv')\n"
            "registry = pd.read_csv(RESULTS / 'model_registry.csv')\n"
            "predictions = pd.read_csv(RESULTS / 'physionet_sequence_predictions.csv')\n"
            "summary.merge(registry, on='score', how='left').head()"
        ),
        md(
            "## Model Comparison\n\n"
            "The key table for the paper is not just `Model -> AUC`; it is "
            "`Model -> AUC -> Audit Status -> Failure Mode`.\n\n"
            f"{comparison}"
        ),
        md(
            "## ROC Curves\n\n"
            f"![ROC curves]({figure_paths['roc']})"
        ),
        md(
            "## Leakage-Dose Ablation\n\n"
            "Low-dose oracle contamination is intentionally subtle: the AUC lift can be "
            "small, but LAMP still marks the score as using forbidden/oracle-adjacent "
            "information once the configured leakage-proximity geometry shifts.\n\n"
            f"{dose_table}\n\n"
            f"![Leakage dose]({figure_paths['leakage_dose']})"
        ),
        md(
            "## Architecture and Horizon Ablation\n\n"
            "The same audit contract is applied across horizons (6/12/18h), classical "
            "models, neural sequence models, and internal-representation probes.\n\n"
            f"{horizon_table}\n\n"
            f"![Horizon architecture ablation]({figure_paths['horizon_arch']})"
        ),
        md(
            "## LAMP Gate Map\n\n"
            "Green does not mean high AUC; green means the score survived the configured "
            "temporal, forbidden-feature, negative-control, matched-state, sentinel, and "
            "threshold gates.\n\n"
            f"![Audit gates]({figure_paths['audit_gates']})"
        ),
        md(
            "## Internal-State Probes\n\n"
            "This is the alignment-native part: LAMP can audit not only final task scores "
            "but also probe outputs trained on model representations. Future-window "
            "hidden probes fail for the same reason a future-reading task model fails: "
            "the information contract has been broken.\n\n"
            f"{probe_table}"
        ),
        md(
            "## Timeline: Where Leakage Enters\n\n"
            "The audit does not wait for clinical deployment to discover that a model has "
            "read forbidden information. The temporal contract is violated at the moment "
            "a score uses post-anchor physiology or label/onset-derived features.\n\n"
            f"![Timeline schema]({figure_paths['timeline']})\n\n"
            f"![Empirical timeline]({figure_paths['empirical_timeline']})"
        ),
        md(
            "## Interpretation for Evaluation Gaming\n\n"
            "A neural early-warning system can look better under ordinary validation "
            "because it quietly learns from future physiology, oracle-like event "
            "proximity, or contaminated internal traces. LAMP reframes the result: "
            "performance is not validity. A model that passes LAMP has not proven "
            "clinical safety or alignment safety, but it has earned the right to more "
            "expensive prospective evaluation.\n\n"
            "For AI alignment, the direct analogy is a latent monitor for deception or "
            "situational awareness. If the monitor wins by reading evaluation artifacts, "
            "post-hoc labels, privileged scratchpads, or hidden routing signals, it can "
            "obtain impressive AUC while failing the audit."
        ),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def comparison_table(joined: pd.DataFrame) -> str:
    rows = joined[
        joined["score"].isin(
            [
                "mlp_probe_valid_score",
                "mlp_probe_leaky_score",
                "rf_valid_score",
                "rf_future_leaky_score",
                "xgb_valid_score",
                "xgb_future_leaky_score",
                "lstm_valid_score",
                "lstm_future_leaky_score",
                "transformer_valid_score",
                "transformer_future_leaky_score",
                "transformer_hidden_probe_score",
                "transformer_future_hidden_probe_score",
            ]
        )
    ].copy()
    rows = rows.sort_values(["family", "type"])
    return to_md_table(
        rows,
        ["name", "type", "auc", "audit_pass", "key_failures"],
        ["Model", "Type", "AUC", "Audit Status", "Key Failures"],
    )


def valid_leaky_table(joined: pd.DataFrame) -> str:
    rows = joined[
        joined["score"].isin(
            [
                "mlp_probe_valid_score",
                "mlp_probe_leaky_score",
                "xgb_valid_score",
                "xgb_future_leaky_score",
                "lstm_valid_score",
                "lstm_future_leaky_score",
                "transformer_hidden_probe_score",
                "transformer_future_hidden_probe_score",
            ]
        )
    ].copy()
    return to_md_table(
        rows,
        ["name", "auc", "audit_pass", "key_failures"],
        ["Monitor", "AUC", "Audit Status", "Key Failures"],
    )


def probe_summary_table(joined: pd.DataFrame) -> str:
    rows = joined[joined["type"].astype(str).str.contains("hidden probe", na=False)].copy()
    return to_md_table(
        rows,
        ["name", "auc", "audit_pass", "key_failures"],
        ["Probe", "AUC", "Audit Status", "Key Failures"],
    )


def leakage_dose_table(joined: pd.DataFrame) -> str:
    rows = joined[joined["type"].eq("low-dose leakage")].copy()
    rows = rows[rows["family"].isin(["mlp_probe", "Random Forest", "XGBoost", "LSTM", "TRANSFORMER"])]
    rows = rows.sort_values(["family", "leakage_lambda"])
    return to_md_table(
        rows.head(20),
        ["family", "leakage_level", "auc", "audit_pass", "key_failures"],
        ["Family", "Leakage Dose", "AUC", "Audit Status", "Key Failures"],
    )


def horizon_table_md(metrics: pd.DataFrame) -> str:
    keep = metrics[
        metrics["score"].isin(
            [
                "mlp_probe_valid_score",
                "rf_valid_score",
                "xgb_valid_score",
                "lstm_valid_score",
                "gru_valid_score",
                "transformer_valid_score",
            ]
        )
    ].copy()
    pivot = keep.pivot_table(index="score", columns="horizon_h", values="auc", aggfunc="mean")
    pivot = pivot.reset_index().rename(columns={"score": "Score"})
    for col in pivot.columns:
        if col != "Score":
            pivot[col] = pivot[col].map(lambda x: f"{x:.3f}")
    return markdown_table(pivot.astype(str).values.tolist(), [str(col) for col in pivot.columns])


def to_md_table(df: pd.DataFrame, columns: list[str], headers: list[str]) -> str:
    out = df[columns].copy()
    for col in out.columns:
        if col == "auc":
            out[col] = out[col].map(lambda x: f"{float(x):.3f}")
        elif col == "audit_pass":
            out[col] = out[col].map(lambda x: "PASS" if bool(x) else "FAIL")
        else:
            out[col] = out[col].fillna("").astype(str)
    out.columns = headers
    return markdown_table(out.values.tolist(), headers)


def markdown_table(rows: list[list[Any]], headers: list[str]) -> str:
    if not rows:
        return "_No rows._"
    values = [[str(value) for value in row] for row in rows]
    widths = [
        max(len(str(headers[idx])), *(len(row[idx]) for row in values))
        for idx in range(len(headers))
    ]
    header = "| " + " | ".join(str(headers[idx]).ljust(widths[idx]) for idx in range(len(headers))) + " |"
    sep = "| " + " | ".join("-" * widths[idx] for idx in range(len(headers))) + " |"
    body = [
        "| " + " | ".join(row[idx].ljust(widths[idx]) for idx in range(len(headers))) + " |"
        for row in values
    ]
    return "\n".join([header, sep, *body])


def notebook_relative_path(path: str) -> str:
    figure_path = Path(path)
    try:
        return str(figure_path.relative_to("notebooks")).replace("\\", "/")
    except ValueError:
        return f"../{path}"


def key_failures(row: pd.Series) -> str:
    if bool(row.get("audit_pass")):
        return "none"
    failures = []
    if not bool(row.get("temporal_passed")):
        failures.append("temporal")
    if not bool(row.get("forbidden_passed")):
        failures.append("forbidden")
    if bool(row.get("oracle_proximity_shift")):
        failures.append("oracle proximity")
    classes = str(row.get("output_classes", ""))
    if "threshold_fragile_claim" in classes:
        failures.append("threshold fragile")
    if "visible_state_confounding" in classes:
        failures.append("visible confounding")
    if "null_or_destroyed_signal" in classes:
        failures.append("null/destroyed")
    return ", ".join(dict.fromkeys(failures)) or "sentinel/classifier warning"


def extract_run_summary(report_text: str) -> str:
    lines = []
    for line in report_text.splitlines():
        if line.startswith("- Source examples") or line.startswith("- Held-out predictions"):
            lines.append(line)
        if line.startswith("- Max patients") or line.startswith("- Horizons") or line.startswith("- Early window"):
            lines.append(line)
    return "\n".join(lines)


def md(text: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


if __name__ == "__main__":
    raise SystemExit(main())
