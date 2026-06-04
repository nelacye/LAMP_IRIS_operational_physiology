#!/usr/bin/env python3
"""Stress-test LAMP under incomplete contracts and partially observed structure."""

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402
from lamp.controls import auc_score, labels_and_scores  # noqa: E402
from lamp.matching import matched_cohort_delta  # noqa: E402


OUT_DIR = ROOT / "results/lamp_contract_uncertainty"
FIG_DIR = OUT_DIR / "figures"
AUDIT_DIR = OUT_DIR / "audits"
TABLE_DIR = OUT_DIR / "tables"

LAMBDA_GRID = [0.0, 0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02]
BIO_NOISE_GRID = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40]
CONFOUNDER_OBS_GRID = [0.0, 0.25, 0.50, 0.75, 1.0]


def main() -> int:
    for path in [OUT_DIR, FIG_DIR, AUDIT_DIR, TABLE_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    provenance_rows = run_provenance_stress()
    bio_rows = run_bio_contract_noise_stress()
    confounding_rows = run_partial_confounding_stress()

    provenance_df = pd.DataFrame(provenance_rows)
    bio_df = pd.DataFrame(bio_rows)
    confounding_df = pd.DataFrame(confounding_rows)

    provenance_path = OUT_DIR / "provenance_uncertainty.csv"
    bio_path = OUT_DIR / "biological_contract_noise.csv"
    confounding_path = OUT_DIR / "partial_confounding.csv"
    summary_path = OUT_DIR / "contract_uncertainty_summary.csv"

    provenance_df.to_csv(provenance_path, index=False)
    bio_df.to_csv(bio_path, index=False)
    confounding_df.to_csv(confounding_path, index=False)

    summary = pd.concat(
        [
            summarize_block(provenance_df, "incomplete_provenance"),
            summarize_block(bio_df, "noisy_biological_contract"),
            summarize_block(confounding_df, "partially_observed_confounding"),
        ],
        ignore_index=True,
    )
    summary.to_csv(summary_path, index=False)

    plot_provenance(provenance_df, FIG_DIR / "provenance_uncertainty.png")
    plot_bio_noise(bio_df, FIG_DIR / "biological_contract_noise.png")
    plot_partial_confounding(
        confounding_df,
        FIG_DIR / "partial_confounding.png",
    )

    report_path = OUT_DIR / "contract_uncertainty_report.md"
    write_report(report_path, provenance_df, bio_df, confounding_df)

    manifest = {
        "summary": relpath(summary_path),
        "provenance_uncertainty": relpath(provenance_path),
        "biological_contract_noise": relpath(bio_path),
        "partial_confounding": relpath(confounding_path),
        "report": relpath(report_path),
        "figures": [
            relpath(FIG_DIR / "provenance_uncertainty.png"),
            relpath(FIG_DIR / "biological_contract_noise.png"),
            relpath(FIG_DIR / "partial_confounding.png"),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(report_path)
    return 0


def run_provenance_stress() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base = make_provenance_table()
    for lam in LAMBDA_GRID:
        df = base.copy()
        df["score"] = zscore(
            ((1.0 - lam) * df["valid_score_z"]) + (lam * df["oracle_score_z"])
        )
        table_path = TABLE_DIR / f"provenance_lambda_{tag(lam)}.csv"
        df.to_csv(table_path, index=False)
        clean_auc = auc(df["outcome"], df["valid_score_z"])

        for mode in ["complete_declared", "sentinel_only", "score_only"]:
            config = base_config(score_col="score")
            config["dataset"]["name"] = f"Provenance uncertainty lambda={lam:g}"
            config["dataset"]["role"] = mode
            config["leakage_proximity"] = {
                "baseline_score": "valid_score_z",
                "oracle_proximity_alert_min": 0.001,
            }
            if mode == "complete_declared" and lam > 0:
                config["temporal_isolation"]["valid_score_features"].append(
                    {"name": "oracle_score", "latest_offset_h": 1}
                )
                config["forbidden_features"]["valid_score_features"].append(
                    "oracle_score"
                )
            if mode == "score_only":
                config["sentinels"] = {}
                config["forbidden_features"]["columns"] = []
                config.pop("leakage_proximity", None)

            result = run_one_audit(config, table_path, f"provenance_{mode}_{tag(lam)}")
            rows.append(
                flatten_result(
                    scenario="incomplete_provenance",
                    condition=mode,
                    dose=lam,
                    clean_auc=clean_auc,
                    result=result,
                    ground_truth_invalid=lam > 0,
                    extra={
                        "interpretation": provenance_interpretation(mode, lam, result),
                    },
                )
            )
    return rows


def run_bio_contract_noise_stress() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for noise in BIO_NOISE_GRID:
        df = make_bio_contract_table(noise)
        table_path = TABLE_DIR / f"bio_contract_noise_{tag(noise)}.csv"
        df.to_csv(table_path, index=False)
        config = base_config(score_col="calcium_probe_score")
        config["dataset"]["name"] = f"Noisy biological contract noise={noise:g}"
        config["dataset"]["task"] = "iPSC-CM disjoint-axis contract stress"
        config["dataset"]["role"] = "endpoint-axis-noise"
        config["sentinels"]["protocol_shortcut"] = {
            "column": "protocol_sentinel_score",
            "role": "protocol_shortcut",
            "expected_signature": "protocol or batch comparator",
        }
        config["thresholds"]["valid_auc_min"] = 0.60
        config["visible_state_matching"]["columns"] = ["early_morphology", "donor_proxy"]
        config["early_window_sensitivity"] = {
            "score_columns": ["weak_marker_panel_score"],
        }

        result = run_one_audit(config, table_path, f"bio_noise_{tag(noise)}")
        labels, scores = labels_and_scores(
            df.to_dict("records"),
            "outcome",
            "calcium_probe_score",
            1,
        )
        stability = bootstrap_stability_rate(
            df,
            score_col="calcium_probe_score",
            match_columns=["early_morphology", "donor_proxy"],
            seed=int(noise * 1000) + 101,
        )
        rows.append(
            flatten_result(
                scenario="noisy_biological_contract",
                condition="endpoint_axis_label_noise",
                dose=noise,
                clean_auc=auc_score(labels, scores),
                result=result,
                ground_truth_invalid=False,
                extra={
                    "bootstrap_stability_rate": stability,
                    "interpretation": bio_noise_interpretation(noise, result, stability),
                },
            )
        )
    return rows


def run_partial_confounding_stress() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for observed_fraction in CONFOUNDER_OBS_GRID:
        df = make_confounding_table(observed_fraction)
        table_path = TABLE_DIR / f"partial_confounding_obs_{tag(observed_fraction)}.csv"
        df.to_csv(table_path, index=False)
        config = base_config(score_col="shortcut_score")
        config["dataset"]["name"] = (
            f"Partially observed confounding observed_fraction={observed_fraction:g}"
        )
        config["dataset"]["task"] = "visible shortcut with incomplete matching proxy"
        config["dataset"]["role"] = "partial-confounding"
        config["visible_state_matching"]["columns"] = ["observed_confounder_proxy"]
        config["visible_state_matching"]["n_bins"] = 3
        config["sentinels"]["true_confounder_sentinel"] = {
            "column": "true_confounder_sentinel",
            "role": "protocol_batch_or_donor_shortcut",
            "expected_signature": "unavailable true confounder comparator",
        }
        result = run_one_audit(
            config,
            table_path,
            f"partial_confounding_{tag(observed_fraction)}",
        )
        labels, scores = labels_and_scores(
            df.to_dict("records"),
            "outcome",
            "shortcut_score",
            1,
        )
        rows.append(
            flatten_result(
                scenario="partially_observed_confounding",
                condition="observed_confounder_fraction",
                dose=observed_fraction,
                clean_auc=auc_score(labels, scores),
                result=result,
                ground_truth_invalid=True,
                extra={
                    "true_confounder_auc": auc(
                        df["outcome"],
                        df["true_confounder_sentinel"],
                    ),
                    "interpretation": partial_confounding_interpretation(
                        observed_fraction,
                        result,
                    ),
                },
            )
        )
    return rows


def make_provenance_table(seed: int = 410, n: int = 1400) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    latent = rng.normal(size=n)
    visible = rng.normal(size=n)
    donor = rng.normal(size=n)
    logit = 1.15 * latent + 0.25 * visible + rng.normal(scale=0.65, size=n)
    outcome = (logit > np.quantile(logit, 0.55)).astype(int)
    valid = zscore(0.95 * latent + 0.25 * visible + rng.normal(scale=0.75, size=n))
    oracle = zscore(outcome + rng.normal(scale=0.04, size=n))
    future = zscore(0.55 * latent + 0.85 * outcome + rng.normal(scale=0.4, size=n))
    return pd.DataFrame(
        {
            "subject_id": [f"P{i:04d}" for i in range(n)],
            "anchor_time_h": 0,
            "outcome": outcome,
            "valid_score_z": valid,
            "oracle_score_z": oracle,
            "score": valid,
            "oracle_score": oracle,
            "future_score": future,
            "early_signal": latent + rng.normal(scale=0.2, size=n),
            "visible_state": visible,
            "donor_proxy": donor,
        }
    )


def make_bio_contract_table(noise: float, seed: int = 510, n: int = 900) -> pd.DataFrame:
    rng = np.random.default_rng(seed + int(noise * 1000))
    latent_maturation = rng.normal(size=n)
    protocol = rng.binomial(1, 0.5, size=n)
    donor = rng.normal(size=n)
    early_morphology = 0.45 * latent_maturation + 0.35 * donor + rng.normal(size=n)

    true_logit = 1.1 * latent_maturation + 0.25 * protocol + rng.normal(scale=0.75, size=n)
    true_outcome = (true_logit > np.quantile(true_logit, 0.55)).astype(int)
    flips = rng.binomial(1, noise, size=n)
    observed_outcome = np.where(flips == 1, 1 - true_outcome, true_outcome)

    calcium_probe = zscore(
        0.9 * latent_maturation + 0.1 * protocol + rng.normal(scale=0.85 + noise, size=n)
    )
    weak_marker_panel = zscore(
        0.45 * latent_maturation + rng.normal(scale=1.15 + noise, size=n)
    )
    protocol_score = zscore(protocol + rng.normal(scale=0.25, size=n))
    oracle = zscore(observed_outcome + rng.normal(scale=0.04, size=n))
    future = zscore(0.65 * latent_maturation + 0.65 * observed_outcome + rng.normal(size=n))

    return pd.DataFrame(
        {
            "subject_id": [f"B{i:04d}" for i in range(n)],
            "anchor_time_h": 0,
            "outcome": observed_outcome,
            "calcium_probe_score": calcium_probe,
            "weak_marker_panel_score": weak_marker_panel,
            "protocol_sentinel_score": protocol_score,
            "oracle_score": oracle,
            "future_score": future,
            "early_signal": latent_maturation + rng.normal(scale=0.25, size=n),
            "visible_state": early_morphology,
            "early_morphology": early_morphology,
            "donor_proxy": donor,
        }
    )


def make_confounding_table(
    observed_fraction: float,
    seed: int = 610,
    n: int = 1200,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + int(observed_fraction * 1000))
    true_group = rng.integers(0, 3, size=n)
    latent_noise = rng.normal(size=n)
    outcome_prob = np.array([0.18, 0.48, 0.82])[true_group]
    outcome = rng.binomial(1, outcome_prob)
    shortcut_score = zscore(true_group + rng.normal(scale=0.03, size=n))

    random_proxy = rng.integers(0, 3, size=n)
    use_true = rng.binomial(1, observed_fraction, size=n).astype(bool)
    observed_proxy = np.where(use_true, true_group, random_proxy)
    observed_proxy = observed_proxy + rng.normal(scale=0.02, size=n)

    return pd.DataFrame(
        {
            "subject_id": [f"C{i:04d}" for i in range(n)],
            "anchor_time_h": 0,
            "outcome": outcome,
            "shortcut_score": shortcut_score,
            "oracle_score": zscore(outcome + rng.normal(scale=0.04, size=n)),
            "future_score": zscore(outcome + 0.3 * true_group + rng.normal(scale=0.4, size=n)),
            "true_confounder_sentinel": zscore(true_group),
            "early_signal": latent_noise,
            "visible_state": observed_proxy,
            "observed_confounder_proxy": observed_proxy,
            "donor_proxy": rng.normal(size=n),
        }
    )


def base_config(score_col: str) -> dict[str, Any]:
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": "Contract uncertainty stress test",
            "task": "hidden-state monitor uncertainty analysis",
            "role": "synthetic stress test",
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
                "score formula",
                "sentinel formula",
                "matching columns",
            ],
            "valid_score_features": [
                {"name": "early_signal", "latest_offset_h": 0},
                {"name": "visible_state", "latest_offset_h": 0},
            ],
        },
        "forbidden_features": {
            "columns": ["future_score", "oracle_score"],
            "valid_score_features": ["early_signal", "visible_state"],
        },
        "sentinels": {
            "future_physiology": {
                "column": "future_score",
                "role": "future_physiology",
                "expected_signature": "post-anchor comparator",
            },
            "oracle_label": {
                "column": "oracle_score",
                "role": "oracle_label",
                "expected_signature": "ceiling label-adjacent comparator",
            },
        },
        "negative_controls": {"n_permutations": 50, "seed": 51},
        "visible_state_matching": {
            "columns": ["visible_state", "donor_proxy"],
            "n_bins": 3,
            "min_bin_size": 12,
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.02,
            "matched_collapse_max": 0.01,
            "score_thresholds": [-1.0, 0.0, 1.0],
        },
    }


def run_one_audit(config: dict[str, Any], table_path: Path, name: str) -> dict[str, Any]:
    run_dir = AUDIT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)
    config_path = run_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return run_audit(config_path, table_path, run_dir)


def flatten_result(
    scenario: str,
    condition: str,
    dose: float,
    clean_auc: float | None,
    result: dict[str, Any],
    ground_truth_invalid: bool,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    primary = result["primary_score"]
    dossier = result["failure_mode_dossier"]
    oracle_rel = result["sentinel_relations"].get("oracle_label", {})
    row = {
        "scenario": scenario,
        "condition": condition,
        "dose": dose,
        "ground_truth_invalid": ground_truth_invalid,
        "auc": primary.get("auc"),
        "clean_or_reference_auc": clean_auc,
        "auc_delta": (
            primary.get("auc") - clean_auc
            if primary.get("auc") is not None and clean_auc is not None
            else None
        ),
        "matched_delta": result["visible_state_matching"].get(
            "matched_observed_state_delta"
        ),
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "oracle_proximity": oracle_rel.get("auc_leakage_proximity"),
        "oracle_proximity_alert": oracle_rel.get("oracle_proximity_alert"),
        "audit_pass_candidate": dossier["audit_pass_candidate"],
        "output_classes": ";".join(dossier["output_classes"]),
    }
    if extra:
        row.update(extra)
    return row


def bootstrap_stability_rate(
    df: pd.DataFrame,
    score_col: str,
    match_columns: list[str],
    seed: int,
    n_bootstrap: int = 80,
) -> float:
    rng = np.random.default_rng(seed)
    records = df.to_dict("records")
    passes = 0
    for _ in range(n_bootstrap):
        idx = rng.integers(0, len(records), size=len(records))
        sample = [records[i] for i in idx]
        labels, scores = labels_and_scores(sample, "outcome", score_col, 1)
        sample_auc = auc_score(labels, scores)
        match = matched_cohort_delta(
            sample,
            "outcome",
            score_col,
            match_columns,
            positive_value=1,
            n_bins=3,
            min_bin_size=12,
        )
        if (
            sample_auc is not None
            and sample_auc >= 0.60
            and match.get("evaluated")
            and (match.get("matched_observed_state_delta") or 0.0) >= 0.02
        ):
            passes += 1
    return passes / n_bootstrap


def summarize_block(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
    rows = []
    for condition, group in df.groupby("condition"):
        rows.append(
            {
                "scenario": scenario,
                "condition": condition,
                "n_rows": len(group),
                "mean_auc": group["auc"].mean(),
                "mean_matched_delta": group["matched_delta"].mean(),
                "audit_pass_rate": group["audit_pass_candidate"].mean(),
                "oracle_proximity_alert_rate": group.get(
                    "oracle_proximity_alert",
                    pd.Series(dtype=float),
                ).fillna(False).mean(),
            }
        )
    return pd.DataFrame(rows)


def plot_provenance(df: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    for condition, group in df.groupby("condition"):
        group = group.sort_values("dose")
        axes[0].plot(
            group["dose"] * 100,
            group["auc_delta"],
            marker="o",
            linewidth=1.5,
            label=condition,
        )
        axes[1].plot(
            group["dose"] * 100,
            (~group["audit_pass_candidate"]).astype(int),
            marker="o",
            linewidth=1.5,
            label=condition,
        )
    axes[0].axhline(0.01, color="#999999", linestyle=":", linewidth=1)
    axes[0].set_ylabel("AUC delta vs clean")
    axes[0].grid(alpha=0.18)
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].set_xscale("symlog", linthresh=0.01)
    axes[1].set_yticks([0, 1])
    axes[1].set_yticklabels(["PASS", "FAIL"])
    axes[1].set_xlabel("Oracle dose (%)")
    axes[1].set_ylabel("LAMP decision")
    axes[1].grid(alpha=0.18)
    fig.suptitle("Incomplete provenance specification")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_bio_noise(df: pd.DataFrame, path: Path) -> None:
    group = df.sort_values("dose")
    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(group["dose"] * 100, group["auc"], marker="o", label="AUC")
    ax1.plot(
        group["dose"] * 100,
        group["matched_delta"],
        marker="s",
        label="matched delta",
    )
    ax1.set_xlabel("Endpoint/contract label noise (%)")
    ax1.set_ylabel("AUC / matched delta")
    ax1.grid(alpha=0.18)
    ax2 = ax1.twinx()
    ax2.plot(
        group["dose"] * 100,
        group["bootstrap_stability_rate"],
        color="#555555",
        marker="^",
        linestyle="--",
        label="bootstrap stability",
    )
    ax2.set_ylabel("bootstrap stability rate")
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, frameon=False, loc="lower left")
    fig.suptitle("Noisy biological contract")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_partial_confounding(df: pd.DataFrame, path: Path) -> None:
    group = df.sort_values("dose")
    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(group["dose"] * 100, group["auc"], marker="o", label="shortcut AUC")
    ax1.plot(
        group["dose"] * 100,
        group["matched_delta"],
        marker="s",
        label="matched delta after observed proxy",
    )
    ax1.axhline(0.02, color="#999999", linestyle=":", linewidth=1)
    ax1.set_xlabel("True confounder observed by matching proxy (%)")
    ax1.set_ylabel("AUC / matched delta")
    ax1.grid(alpha=0.18)
    ax2 = ax1.twinx()
    ax2.plot(
        group["dose"] * 100,
        group["audit_pass_candidate"].astype(int),
        color="#555555",
        linestyle="--",
        marker="^",
        label="audit pass",
    )
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(["FAIL", "PASS"])
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, frameon=False, loc="upper right")
    fig.suptitle("Partially observed confounding")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_report(
    path: Path,
    provenance: pd.DataFrame,
    bio: pd.DataFrame,
    confounding: pd.DataFrame,
) -> None:
    lines: list[str] = []
    lines.append("# LAMP Contract-Uncertainty Analysis")
    lines.append("")
    lines.append(
        "This stress analysis asks what happens when the audit contract is not "
        "ideal: provenance is incompletely specified, biological contracts are "
        "noisy, or confounding is only partially observed."
    )
    lines.append("")
    lines.append("## 1. Incomplete Provenance Specification")
    lines.append("")
    lines.append(
        "Known oracle contamination was injected into an otherwise valid score. "
        "Three audit modes were compared: complete declared provenance, sentinel-only "
        "provenance, and score-only provenance with no oracle sentinel."
    )
    lines.append("")
    lines.append("| Mode | First detected nonzero dose | Pass at 0.5%? | Main interpretation |")
    lines.append("| --- | ---: | :---: | --- |")
    for mode in ["complete_declared", "sentinel_only", "score_only"]:
        group = provenance[(provenance["condition"] == mode) & (provenance["dose"] > 0)]
        detected = group[~group["audit_pass_candidate"]].sort_values("dose")
        first = detected.iloc[0]["dose"] if not detected.empty else None
        row_005 = provenance[
            (provenance["condition"] == mode) & (provenance["dose"] == 0.005)
        ].iloc[0]
        lines.append(
            "| {mode} | {first} | {pass_005} | {interp} |".format(
                mode=mode,
                first="not detected" if first is None else f"{first * 100:.4g}%",
                pass_005="yes" if row_005["audit_pass_candidate"] else "no",
                interp=row_005["interpretation"],
            )
        )
    lines.append("")
    lines.append(
        "**Conclusion:** LAMP is strongest when provenance is declared. With an "
        "oracle sentinel but no declared score feature, geometry can still detect "
        "movement toward the sentinel. With neither declared provenance nor a "
        "sentinel, the same contaminated score can pass. That is not a bug; it is "
        "the limit of auditing an unspecified information boundary."
    )
    lines.append("")
    lines.append("## 2. Noisy Biological Contracts")
    lines.append("")
    lines.append(
        "The biological stress test flips a fraction of endpoint-axis labels while "
        "keeping the allowed disjoint calcium/electrophysiology-style probe fixed."
    )
    lines.append("")
    lines.append("| Endpoint noise | AUC | Matched delta | Bootstrap stability | LAMP |")
    lines.append("| ---: | ---: | ---: | ---: | --- |")
    for _, row in bio.sort_values("dose").iterrows():
        lines.append(
            "| {noise:.0f}% | {auc_v:.3f} | {delta:.3f} | {stab:.3f} | {decision} |".format(
                noise=row["dose"] * 100,
                auc_v=row["auc"],
                delta=row["matched_delta"],
                stab=row["bootstrap_stability_rate"],
                decision="PASS" if row["audit_pass_candidate"] else "FAIL",
            )
        )
    lines.append("")
    lines.append(
        "**Conclusion:** noisy biological contracts do not behave like leakage. "
        "They mostly erode AUC, matched-cohort signal, and bootstrap stability. "
        "The right diagnosis is usually fragile or not biologically interpretable, "
        "not contamination, unless endpoint-adjacent features are explicitly used."
    )
    lines.append("")
    lines.append("## 3. Partially Observed Confounding")
    lines.append("")
    lines.append(
        "The confounding stress test creates a score that is only a shortcut through "
        "a true confounder. Matching sees only a noisy proxy for that confounder."
    )
    lines.append("")
    lines.append("| Confounder observed | Shortcut AUC | Matched delta | Audit pass? | Interpretation |")
    lines.append("| ---: | ---: | ---: | :---: | --- |")
    for _, row in confounding.sort_values("dose").iterrows():
        lines.append(
            "| {obs:.0f}% | {auc_v:.3f} | {delta:.3f} | {passed} | {interp} |".format(
                obs=row["dose"] * 100,
                auc_v=row["auc"],
                delta=row["matched_delta"],
                passed="yes" if row["audit_pass_candidate"] else "no",
                interp=row["interpretation"],
            )
        )
    lines.append("")
    lines.append(
        "**Conclusion:** partially observed confounding is the most dangerous case. "
        "If the matching variables do not capture the true shortcut structure, "
        "the matched delta can remain positive and LAMP may pass a shortcut. "
        "The audit should therefore report observed-confounder coverage and run "
        "additional donor/protocol/batch sentinels whenever possible."
    )
    lines.append("")
    lines.append("## Practical Rule")
    lines.append("")
    lines.append(
        "LAMP should not be read as `PASS means true`. It should be read as: "
        "`PASS under this declared contract and this observed confounder set`. "
        "Incomplete provenance creates false-pass risk; noisy biological contracts "
        "create fragility/interpretability risk; partially observed confounding "
        "creates the strongest shortcut risk."
    )
    lines.append("")
    lines.append("## Figures")
    lines.append("")
    lines.append("- `figures/provenance_uncertainty.png`")
    lines.append("- `figures/biological_contract_noise.png`")
    lines.append("- `figures/partial_confounding.png`")
    path.write_text("\n".join(lines), encoding="utf-8")


def provenance_interpretation(mode: str, lam: float, result: dict[str, Any]) -> str:
    if mode == "complete_declared":
        return "contract violation is directly auditable from declared provenance"
    if mode == "sentinel_only":
        return "detectable only after score geometry moves toward oracle sentinel"
    if lam > 0 and result["failure_mode_dossier"]["audit_pass_candidate"]:
        return "false-pass risk: score provenance and oracle sentinel are both missing"
    return "no oracle provenance available to LAMP"


def bio_noise_interpretation(
    noise: float,
    result: dict[str, Any],
    stability: float,
) -> str:
    if result["failure_mode_dossier"]["audit_pass_candidate"] and stability >= 0.8:
        return "stable disjoint biological signal"
    if result["failure_mode_dossier"]["audit_pass_candidate"]:
        return "fragile but plausible disjoint biological signal"
    if noise >= 0.3:
        return "contract too noisy for a stable maturation claim"
    return "weak or threshold-sensitive biological support"


def partial_confounding_interpretation(
    observed_fraction: float,
    result: dict[str, Any],
) -> str:
    if result["failure_mode_dossier"]["audit_pass_candidate"]:
        return "false-pass risk if unobserved confounder is not represented in matching"
    if observed_fraction >= 0.75:
        return "shortcut collapses once matching observes the confounder"
    return "partial proxy weakens but does not fully identify shortcut"


def zscore(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    sd = arr.std()
    if sd == 0:
        return arr - arr.mean()
    return (arr - arr.mean()) / sd


def auc(labels: Any, scores: Any) -> float | None:
    return auc_score([int(x) for x in labels], [float(x) for x in scores])


def tag(value: float) -> str:
    return f"{int(round(value * 1_000_000)):06d}ppm"


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
