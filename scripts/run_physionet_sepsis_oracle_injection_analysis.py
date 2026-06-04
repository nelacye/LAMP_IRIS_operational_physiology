#!/usr/bin/env python3
"""Known-truth oracle leakage injection on the real PhysioNet sepsis table."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import auc, confusion_matrix, roc_curve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402


BASE_TABLE = ROOT / "results/sepsis_external/v3_5k/tables/sepsis_patient_scores.csv"
BASE_CONFIG = ROOT / "examples/sepsis/physionet_v3_5k_existing_results_config.yaml"
OUT_DIR = ROOT / "results/physionet_sepsis_oracle_injection"
FIG_DIR = OUT_DIR / "figures"
TABLE_DIR = OUT_DIR / "tables"
AUDIT_DIR = OUT_DIR / "audits"

HORIZONS = [6, 12, 18]
LAMBDAS = [
    0.0,
    0.00001,
    0.00005,
    0.0001,
    0.0005,
    0.001,
    0.002,
    0.005,
    0.01,
    0.02,
    0.05,
    0.10,
]
MODES = ["strict_declared", "geometry_only"]
PRIMARY_LAMBDA = 0.005


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    base_df = pd.read_csv(BASE_TABLE)
    base_config = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))

    summary_rows: list[dict[str, Any]] = []
    roc_payload: dict[int, dict[str, Any]] = {}
    audit_payloads: dict[tuple[int, float, str], dict[str, Any]] = {}

    for horizon in HORIZONS:
        horizon_df = prepare_horizon_df(base_df, horizon)
        labels = horizon_df["label_future_sepsis"].astype(int).to_numpy()
        clean_scores = horizon_df["valid_score_z"].to_numpy()
        oracle_scores = horizon_df["oracle_score_z"].to_numpy()
        clean_auc = float(auc(*roc_curve(labels, clean_scores)[:2]))

        roc_payload[horizon] = {
            "labels": labels,
            "clean_scores": clean_scores,
            "clean_auc": clean_auc,
            "primary_scores": None,
            "primary_auc": None,
        }

        for lam in LAMBDAS:
            run_df = horizon_df.copy()
            mixed = ((1.0 - lam) * run_df["valid_score_z"]) + (
                lam * run_df["oracle_score_z"]
            )
            run_df["mixed_score"] = zscore(mixed)
            run_df["known_oracle_leakage_lambda"] = lam

            table_path = TABLE_DIR / f"physionet_h{horizon}_oracle_l{lambda_tag(lam)}.csv"
            run_df.to_csv(table_path, index=False)

            if lam == PRIMARY_LAMBDA:
                primary_scores = run_df["mixed_score"].to_numpy()
                roc_payload[horizon]["primary_scores"] = primary_scores
                roc_payload[horizon]["primary_auc"] = float(
                    auc(*roc_curve(labels, primary_scores)[:2])
                )

            for mode in MODES:
                run_dir = AUDIT_DIR / f"{mode}_h{horizon}_l{lambda_tag(lam)}"
                run_dir.mkdir(parents=True, exist_ok=True)
                config = oracle_injection_config(base_config, horizon, lam, mode)
                config_path = run_dir / "config.yaml"
                config_path.write_text(
                    yaml.safe_dump(config, sort_keys=False),
                    encoding="utf-8",
                )

                audit = run_audit(config_path, table_path, run_dir)
                audit_payloads[(horizon, lam, mode)] = audit
                summary_rows.append(
                    flatten_audit_result(
                        horizon=horizon,
                        lam=lam,
                        mode=mode,
                        clean_auc=clean_auc,
                        audit=audit,
                    )
                )
                print(f"PhysioNet oracle injection h={horizon} lambda={lam:g} {mode}")

    summary_df = pd.DataFrame(summary_rows)
    summary_path = OUT_DIR / "real_physionet_oracle_injection_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    primary_rows = summary_df[summary_df["lambda"] == PRIMARY_LAMBDA].copy()
    primary_path = OUT_DIR / "real_physionet_oracle_0p5pct_rows.csv"
    primary_rows.to_csv(primary_path, index=False)

    confusion_rows = compute_confusion_rows(summary_df)
    confusion_path = OUT_DIR / "real_physionet_oracle_injection_confusion.csv"
    pd.DataFrame(confusion_rows).to_csv(confusion_path, index=False)

    plot_roc_overlay(roc_payload, FIG_DIR / "physionet_roc_clean_vs_0p5pct_oracle.png")
    plot_sensitivity(
        summary_df,
        FIG_DIR / "physionet_oracle_leakage_sensitivity.png",
    )
    plot_confusion_matrices(
        summary_df,
        FIG_DIR / "physionet_lamp_vs_known_leakage_confusion.png",
    )

    report_path = OUT_DIR / "real_physionet_oracle_injection_report.md"
    write_report(
        report_path=report_path,
        summary_df=summary_df,
        confusion_rows=confusion_rows,
        primary_rows=primary_rows,
    )

    manifest = {
        "source_table": relpath(BASE_TABLE),
        "source_config": relpath(BASE_CONFIG),
        "summary": relpath(summary_path),
        "primary_0p5pct_rows": relpath(primary_path),
        "confusion": relpath(confusion_path),
        "report": relpath(report_path),
        "figures": [
            relpath(FIG_DIR / "physionet_roc_clean_vs_0p5pct_oracle.png"),
            relpath(FIG_DIR / "physionet_oracle_leakage_sensitivity.png"),
            relpath(FIG_DIR / "physionet_lamp_vs_known_leakage_confusion.png"),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(summary_path)
    print(report_path)
    return 0


def prepare_horizon_df(base_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    df = base_df[base_df["horizon_h"].astype(int) == horizon].copy()
    df["label_future_sepsis"] = df["label_future_sepsis"].astype(int)
    df["valid_score_z"] = zscore(df["valid_early_warning_score"])
    df["oracle_score_z"] = zscore(df["oracle_label_sentinel_score"])
    return df


def oracle_injection_config(
    base_config: dict[str, Any],
    horizon: int,
    lam: float,
    mode: str,
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    config["dataset"] = {
        "name": "PhysioNet/CinC 2019 sepsis known-truth oracle injection",
        "task": "real-data oracle leakage sensitivity",
        "role": mode,
        "horizon_h": horizon,
        "oracle_leakage_lambda": lam,
        "ground_truth_leakage": lam > 0,
        "source_table": "results/sepsis_external/v3_5k/tables/sepsis_patient_scores.csv",
    }
    config["columns"]["score"] = "mixed_score"
    config["negative_controls"]["n_permutations"] = 200
    config["thresholds"]["score_thresholds"] = [-1.0, 0.0, 1.0]
    config["leakage_proximity"] = {
        "baseline_score": "valid_score_z",
        "oracle_proximity_alert_min": 0.001,
    }
    config["early_window_sensitivity"] = {
        "score_columns": ["valid_score_z"],
    }

    if mode == "strict_declared" and lam > 0:
        config["forbidden_features"]["valid_score_features"] = list(
            config["forbidden_features"].get("valid_score_features", [])
        ) + ["oracle_label_sentinel_score"]
        config["temporal_isolation"]["valid_score_features"] = list(
            config["temporal_isolation"].get("valid_score_features", [])
        ) + [{"name": "oracle_label_sentinel_score", "latest_offset_h": 1}]

    return config


def flatten_audit_result(
    horizon: int,
    lam: float,
    mode: str,
    clean_auc: float,
    audit: dict[str, Any],
) -> dict[str, Any]:
    primary = audit["primary_score"]
    dossier = audit["failure_mode_dossier"]
    oracle_rel = audit["sentinel_relations"].get("oracle_label", {})
    future_rel = audit["sentinel_relations"].get("future_physiology", {})
    auc_delta = (
        primary["auc"] - clean_auc
        if primary.get("auc") is not None and clean_auc is not None
        else None
    )
    return {
        "horizon_h": horizon,
        "lambda": lam,
        "lambda_percent": lam * 100.0,
        "mode": mode,
        "ground_truth_leakage": lam > 0,
        "n": primary.get("n"),
        "n_positive": primary.get("n_positive"),
        "clean_auc": clean_auc,
        "mixed_auc": primary.get("auc"),
        "auc_delta": auc_delta,
        "auc_delta_ge_0p01": auc_delta is not None and abs(auc_delta) >= 0.01,
        "oracle_auc": oracle_rel.get("sentinel_auc"),
        "distance_to_oracle_auc": oracle_rel.get("sentinel_minus_primary_auc"),
        "oracle_proximity": oracle_rel.get("auc_leakage_proximity"),
        "oracle_proximity_alert": oracle_rel.get("oracle_proximity_alert"),
        "future_auc": future_rel.get("sentinel_auc"),
        "matched_delta": audit["visible_state_matching"].get(
            "matched_observed_state_delta"
        ),
        "temporal_passed": audit["temporal_isolation"]["passed"],
        "forbidden_passed": audit["forbidden_feature_screen"]["passed"],
        "threshold_fragile": audit["threshold_sensitivity"].get("fragile"),
        "audit_pass_candidate": dossier["audit_pass_candidate"],
        "lamp_detected_leakage": not dossier["audit_pass_candidate"],
        "output_classes": ";".join(dossier["output_classes"]),
        "forbidden_valid_feature_violations": ";".join(
            audit["forbidden_feature_screen"]["valid_score_feature_violations"]
        ),
    }


def compute_confusion_rows(summary_df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mode, group in summary_df.groupby("mode"):
        y_true = group["ground_truth_leakage"].astype(int).to_numpy()
        y_pred = group["lamp_detected_leakage"].astype(int).to_numpy()
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        rows.append(
            {
                "mode": mode,
                "scope": "full_lambda_sweep",
                "true_negative": int(tn),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_positive": int(tp),
                "sensitivity": safe_div(tp, tp + fn),
                "specificity": safe_div(tn, tn + fp),
            }
        )

        canonical = group[group["lambda"].isin([0.0, PRIMARY_LAMBDA])]
        y_true = canonical["ground_truth_leakage"].astype(int).to_numpy()
        y_pred = canonical["lamp_detected_leakage"].astype(int).to_numpy()
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        rows.append(
            {
                "mode": mode,
                "scope": "clean_vs_0p5pct",
                "true_negative": int(tn),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_positive": int(tp),
                "sensitivity": safe_div(tp, tp + fn),
                "specificity": safe_div(tn, tn + fp),
            }
        )
    return rows


def plot_roc_overlay(roc_payload: dict[int, dict[str, Any]], path: Path) -> None:
    fig, axes = plt.subplots(1, len(HORIZONS), figsize=(12, 3.8), sharex=True, sharey=True)
    for ax, horizon in zip(axes, HORIZONS):
        payload = roc_payload[horizon]
        labels = payload["labels"]
        clean_scores = payload["clean_scores"]
        primary_scores = payload["primary_scores"]
        if primary_scores is None:
            continue
        fpr_clean, tpr_clean, _ = roc_curve(labels, clean_scores)
        fpr_mix, tpr_mix, _ = roc_curve(labels, primary_scores)
        ax.plot(
            fpr_clean,
            tpr_clean,
            color="#111111",
            linewidth=2.0,
            label=f"clean AUC {payload['clean_auc']:.3f}",
        )
        ax.plot(
            fpr_mix,
            tpr_mix,
            color="#666666",
            linewidth=1.8,
            linestyle="--",
            label=f"0.5% oracle AUC {payload['primary_auc']:.3f}",
        )
        ax.plot([0, 1], [0, 1], color="#bbbbbb", linewidth=1.0)
        ax.set_title(f"{horizon}h horizon")
        ax.set_xlabel("False positive rate")
        ax.grid(alpha=0.18)
        ax.legend(frameon=False, fontsize=8, loc="lower right")
    axes[0].set_ylabel("True positive rate")
    fig.suptitle("PhysioNet sepsis: clean ROC vs 0.5% known oracle injection", y=1.03)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_sensitivity(summary_df: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    for horizon in HORIZONS:
        geom = summary_df[
            (summary_df["mode"] == "geometry_only")
            & (summary_df["horizon_h"] == horizon)
        ].sort_values("lambda")
        strict = summary_df[
            (summary_df["mode"] == "strict_declared")
            & (summary_df["horizon_h"] == horizon)
        ].sort_values("lambda")
        x = np.where(geom["lambda"].to_numpy() == 0, np.nan, geom["lambda"].to_numpy())
        axes[0].plot(
            geom["lambda_percent"],
            geom["auc_delta"],
            marker="o",
            linewidth=1.5,
            label=f"{horizon}h",
        )
        axes[1].plot(
            geom["lambda_percent"],
            geom["lamp_detected_leakage"].astype(int),
            marker="o",
            linewidth=1.5,
            label=f"{horizon}h geometry",
        )
        axes[1].plot(
            strict["lambda_percent"],
            strict["lamp_detected_leakage"].astype(int),
            marker="x",
            linewidth=1.2,
            linestyle="--",
            label=f"{horizon}h declared",
        )
        _ = x

    axes[0].axhline(0.01, color="#999999", linestyle=":", linewidth=1.2)
    axes[0].text(
        0.001,
        0.0105,
        "0.01 AUC-delta alert",
        color="#555555",
        fontsize=8,
    )
    axes[0].set_ylabel("AUC delta vs clean")
    axes[0].grid(alpha=0.18)
    axes[0].legend(frameon=False, fontsize=8, ncol=3)

    axes[1].set_xscale("symlog", linthresh=0.001)
    axes[1].set_yticks([0, 1])
    axes[1].set_yticklabels(["PASS", "FAIL"])
    axes[1].set_xlabel("Injected oracle dose (%)")
    axes[1].set_ylabel("LAMP decision")
    axes[1].grid(alpha=0.18)
    axes[1].legend(frameon=False, fontsize=8, ncol=2)

    fig.suptitle("Known-truth oracle injection sensitivity on real sepsis rows", y=1.02)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_confusion_matrices(summary_df: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4))
    for ax, mode in zip(axes, MODES):
        group = summary_df[
            (summary_df["mode"] == mode)
            & (summary_df["lambda"].isin([0.0, PRIMARY_LAMBDA]))
        ]
        y_true = group["ground_truth_leakage"].astype(int).to_numpy()
        y_pred = group["lamp_detected_leakage"].astype(int).to_numpy()
        matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
        ax.imshow(matrix, cmap="Greys", vmin=0, vmax=max(1, matrix.max()))
        for i in range(2):
            for j in range(2):
                ax.text(
                    j,
                    i,
                    str(matrix[i, j]),
                    ha="center",
                    va="center",
                    color="white" if matrix[i, j] > matrix.max() / 2 else "black",
                    fontsize=12,
                    fontweight="bold",
                )
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["PASS", "FAIL"])
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["clean", "0.5% leak"])
        ax.set_xlabel("LAMP decision")
        ax.set_title(mode.replace("_", " "))
    axes[0].set_ylabel("Known ground truth")
    fig.suptitle("LAMP vs known oracle leakage on real PhysioNet rows", y=1.04)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_report(
    report_path: Path,
    summary_df: pd.DataFrame,
    confusion_rows: list[dict[str, Any]],
    primary_rows: pd.DataFrame,
) -> None:
    lines: list[str] = []
    lines.append("# Real PhysioNet Oracle-Injection Control")
    lines.append("")
    lines.append(
        "This artifact uses the real PhysioNet/CinC 2019 sepsis v3_5k score table "
        "already integrated in LAMP, then injects a known oracle-label component into "
        "the monitor score by construction."
    )
    lines.append("")
    lines.append("```text")
    lines.append("mixed_score = z((1 - lambda) * z(valid_score) + lambda * z(oracle_score))")
    lines.append("primary test lambda = 0.005 (0.5% oracle injection)")
    lines.append("```")
    lines.append("")
    lines.append(
        "Ground truth is therefore known: lambda = 0 is clean; every nonzero lambda "
        "contains oracle leakage. The strict-declared mode checks the stated "
        "information contract. The geometry-only mode does not declare the oracle "
        "as a score feature and instead uses LAMP's sentinel proximity relation."
    )
    lines.append("")
    lines.append("## 0.5% Oracle Injection Rows")
    lines.append("")
    lines.append("| Horizon | Mode | Clean AUC | 0.5% AUC | Delta | AUC delta >= 0.01 | LAMP decision | Key classes |")
    lines.append("| --- | --- | ---: | ---: | ---: | --- | --- | --- |")
    for _, row in primary_rows.sort_values(["horizon_h", "mode"]).iterrows():
        decision = "FAIL" if row["lamp_detected_leakage"] else "PASS"
        lines.append(
            "| {horizon}h | {mode} | {clean:.4f} | {mixed:.4f} | {delta:.4f} | {alert} | {decision} | {classes} |".format(
                horizon=int(row["horizon_h"]),
                mode=row["mode"],
                clean=row["clean_auc"],
                mixed=row["mixed_auc"],
                delta=row["auc_delta"],
                alert=str(bool(row["auc_delta_ge_0p01"])),
                decision=decision,
                classes=str(row["output_classes"]).replace(";", ", "),
            )
        )
    lines.append("")
    lines.append("## LAMP vs Known Ground Truth")
    lines.append("")
    lines.append("| Mode | Scope | TN | FP | FN | TP | Sensitivity | Specificity |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in confusion_rows:
        lines.append(
            "| {mode} | {scope} | {tn} | {fp} | {fn} | {tp} | {sens:.3f} | {spec:.3f} |".format(
                mode=row["mode"],
                scope=row["scope"],
                tn=row["true_negative"],
                fp=row["false_positive"],
                fn=row["false_negative"],
                tp=row["true_positive"],
                sens=row["sensitivity"],
                spec=row["specificity"],
            )
        )
    lines.append("")
    lines.append("## Sensitivity Floor")
    lines.append("")
    for mode in MODES:
        lines.append(f"### {mode}")
        mode_rows = summary_df[(summary_df["mode"] == mode) & (summary_df["lambda"] > 0)]
        for horizon in HORIZONS:
            h_rows = mode_rows[mode_rows["horizon_h"] == horizon].sort_values("lambda")
            detected = h_rows[h_rows["lamp_detected_leakage"]]
            first = detected.iloc[0] if not detected.empty else None
            if first is None:
                lines.append(f"- {horizon}h: no nonzero dose detected in this sweep.")
            else:
                lines.append(
                    "- {horizon}h: first detected dose = {pct:.4g}% "
                    "(lambda={lam:g}, AUC delta={delta:.5f}).".format(
                        horizon=horizon,
                        pct=first["lambda_percent"],
                        lam=first["lambda"],
                        delta=first["auc_delta"],
                    )
                )
        lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The 0.5% oracle-injected ROC curves are visually close to the clean curves, "
        "and the AUC deltas remain below a simple 0.01 metric-change alert across "
        "all horizons. LAMP still fails the contaminated scores because the "
        "information contract is broken by construction; in geometry-only mode it "
        "also detects the score's movement toward the oracle sentinel."
    )
    lines.append("")
    lines.append("## Figures")
    lines.append("")
    lines.append("- `figures/physionet_roc_clean_vs_0p5pct_oracle.png`")
    lines.append("- `figures/physionet_oracle_leakage_sensitivity.png`")
    lines.append("- `figures/physionet_lamp_vs_known_leakage_confusion.png`")
    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def zscore(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    mean = numeric.mean()
    std = numeric.std(ddof=0)
    if not np.isfinite(std) or std == 0:
        return numeric - mean
    return (numeric - mean) / std


def lambda_tag(lam: float) -> str:
    return f"{int(round(lam * 1_000_000)):06d}ppm"


def safe_div(num: int, den: int) -> float:
    return float(num / den) if den else float("nan")


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
