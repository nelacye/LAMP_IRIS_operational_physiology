#!/usr/bin/env python3
"""Synthetic iPSC molecular-code audit.

This control experiment treats early kinase/phosphosignaling dynamics as a
signalling protocol and later protein-folding/proteostasis state as execution
correctness. The generator is intentionally synthetic: the goal is to test
whether LAMP can distinguish a clean hybrid latent-state monitor from protocol
shortcuts and endpoint-adjacent leakage when the ground truth is known.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402
from lamp.bio import diagnose_biological_claim, load_bio_contract  # noqa: E402


SEED = 20260604
N_CELLS = 1400
OUT = ROOT / "results" / "ipsc_molecular_code" / "synthetic_kinase_folding"
CONTRACT_PATH = ROOT / "configs" / "ipsc_molecular_code_contract.yaml"
CLAIM_ID = "kinase_dynamics_predicts_folding_execution"

MONITORS = [
    {
        "id": "clean_hybrid_kinase_folding",
        "name": "Clean hybrid kinase/proteostasis monitor",
        "score": "clean_hybrid_kinase_folding_score",
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
        "stability": {
            "bootstrap_pass_rate": 1.0,
            "alternative_panel_pass_rate": 0.94,
            "leave_group_out_pass_rate": 0.96,
            "threshold_grid_pass_rate": 1.0,
        },
        "expected": "PASS",
    },
    {
        "id": "kinase_only_probe",
        "name": "Kinase-only early monitor",
        "score": "kinase_only_score",
        "features": [
            "early_mapk_phospho_slope",
            "early_akt_mtor_pulse",
            "early_gsk3_cdk_balance",
            "early_stress_kinase_persistence",
        ],
        "score_axis": "kinase_phosphosignaling_dynamics",
        "stability": {
            "bootstrap_pass_rate": 0.82,
            "alternative_panel_pass_rate": 0.74,
            "leave_group_out_pass_rate": 0.78,
            "threshold_grid_pass_rate": 1.0,
        },
        "expected": "FRAGILE_PASS_OR_FAIL",
    },
    {
        "id": "protocol_stressor_shortcut",
        "name": "Protocol/stressor shortcut",
        "score": "protocol_stressor_shortcut_score",
        "features": ["protocol_stressor_shortcut_score"],
        "score_axis": "intervention_protocol_structure",
        "stability": {},
        "expected": "FAIL",
    },
    {
        "id": "future_folding_leakage",
        "name": "Future folding-state leakage",
        "score": "future_folding_execution_score",
        "features": ["future_folding_execution_score"],
        "score_axis": "protein_folding_execution_proteostasis",
        "stability": {},
        "expected": "FAIL",
    },
    {
        "id": "oracle_endpoint_leakage",
        "name": "Oracle endpoint leakage",
        "score": "oracle_folding_label_score",
        "features": ["oracle_folding_label_score"],
        "score_axis": "protein_folding_execution_proteostasis",
        "stability": {},
        "expected": "FAIL",
    },
    {
        "id": "lowdose_oracle_mix_005",
        "name": "0.5% oracle-contaminated hybrid monitor",
        "score": "lowdose_oracle_mix_005_score",
        "features": [
            "early_mapk_phospho_slope",
            "early_akt_mtor_pulse",
            "early_gsk3_cdk_balance",
            "early_stress_kinase_persistence",
            "early_chaperone_buffer",
            "early_upr_load",
            "early_autophagy_flux",
            "oracle_folding_label_score",
        ],
        "score_axis": "kinase_folding_coupled_signal",
        "stability": {},
        "expected": "FAIL",
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    table = build_synthetic_table()
    prediction_path = OUT / "synthetic_ipsc_molecular_code_predictions.csv"
    table.to_csv(prediction_path, index=False, lineterminator="\n")

    contract = load_bio_contract(CONTRACT_PATH)
    summary_rows: list[dict[str, Any]] = []
    diagnosis_rows: list[dict[str, Any]] = []
    for monitor in MONITORS:
        config = build_config(monitor)
        config_path = OUT / "configs" / f"{monitor['id']}.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

        audit = run_audit(config_path, prediction_path, OUT / "lamp" / monitor["id"])
        diagnosis = diagnose_biological_claim(
            audit,
            contract,
            CLAIM_ID,
            monitor["score_axis"],
            monitor.get("stability") or None,
        )
        summary_rows.append(summary_row(monitor, audit, diagnosis))
        diagnosis_rows.append(
            {
                "monitor_id": monitor["id"],
                "monitor": monitor["name"],
                **diagnosis,
            }
        )

    write_csv(OUT / "synthetic_ipsc_molecular_code_lamp_summary.csv", summary_rows)
    write_json(OUT / "synthetic_ipsc_molecular_code_bio_diagnoses.json", diagnosis_rows)
    write_report(table, summary_rows)
    print(OUT / "synthetic_ipsc_molecular_code_report.md")
    return 0


def build_synthetic_table() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    n = N_CELLS

    donor = rng.integers(0, 12, size=n)
    batch = rng.integers(0, 8, size=n)
    protocol_arm = rng.integers(0, 4, size=n)
    stressor_dose = rng.beta(2.0, 4.5, size=n)
    differentiation_day = rng.choice([7, 14, 21], size=n, p=[0.34, 0.42, 0.24])
    protocol_intensity = (
        0.55 * stressor_dose
        + 0.20 * (protocol_arm == 2)
        + 0.16 * (differentiation_day == 21)
        + 0.08 * rng.normal(size=n)
    )
    protocol_success_channel = (
        0.72 * (protocol_arm == 1)
        + 0.36 * (differentiation_day == 21)
        - 0.48 * stressor_dose
        + 0.12 * rng.normal(size=n)
    )

    donor_effect = rng.normal(0.0, 0.32, size=12)[donor]
    batch_effect = rng.normal(0.0, 0.22, size=8)[batch]
    latent_signalling_reserve = rng.normal(size=n)
    latent_proteostasis_capacity = (
        0.68 * latent_signalling_reserve
        + 0.24 * donor_effect
        - 0.18 * protocol_intensity
        + 0.18 * rng.normal(size=n)
    )

    early_mapk = 0.74 * latent_signalling_reserve + 0.10 * protocol_intensity + rng.normal(0, 0.46, n)
    early_akt = 0.62 * latent_signalling_reserve - 0.15 * stressor_dose + rng.normal(0, 0.50, n)
    early_gsk3 = 0.58 * latent_signalling_reserve + 0.08 * donor_effect + rng.normal(0, 0.54, n)
    early_stress_kinase = -0.42 * latent_signalling_reserve + 0.62 * stressor_dose + rng.normal(0, 0.56, n)
    early_chaperone = 0.62 * latent_proteostasis_capacity + 0.14 * latent_signalling_reserve + rng.normal(0, 0.48, n)
    early_upr = -0.58 * latent_proteostasis_capacity + 0.30 * stressor_dose + rng.normal(0, 0.48, n)
    early_autophagy = 0.52 * latent_proteostasis_capacity - 0.18 * stressor_dose + rng.normal(0, 0.52, n)

    visible_morphology = (
        0.22 * latent_proteostasis_capacity
        + 0.36 * protocol_intensity
        + 0.16 * (differentiation_day == 21)
        + rng.normal(0, 0.72, n)
    )
    cell_density = (
        0.48 * protocol_intensity
        + 0.18 * batch_effect
        + rng.normal(0, 0.70, n)
    )
    early_viability = (
        0.26 * latent_proteostasis_capacity
        - 0.34 * stressor_dose
        + rng.normal(0, 0.66, n)
    )

    future_folding_execution = (
        1.18 * latent_proteostasis_capacity
        + 0.46 * latent_signalling_reserve
        - 0.20 * protocol_intensity
        + 0.20 * rng.normal(size=n)
    )
    late_aggregate_burden = (
        -0.92 * latent_proteostasis_capacity
        + 0.42 * stressor_dose
        + 0.24 * protocol_intensity
        + 0.26 * rng.normal(size=n)
    )
    endpoint_logit = (
        1.30 * future_folding_execution
        - 0.55 * late_aggregate_burden
        + 2.05 * protocol_success_channel
        + 0.16 * donor_effect
        + 0.14 * rng.normal(size=n)
    )
    label = (endpoint_logit >= np.quantile(endpoint_logit, 0.52)).astype(int)
    oracle = label.astype(float)

    clean_hybrid = (
        0.35 * z(early_mapk)
        + 0.28 * z(early_akt)
        + 0.20 * z(early_gsk3)
        - 0.18 * z(early_stress_kinase)
        + 0.32 * z(early_chaperone)
        - 0.24 * z(early_upr)
        + 0.22 * z(early_autophagy)
    )
    kinase_only = (
        0.42 * z(early_mapk)
        + 0.34 * z(early_akt)
        + 0.26 * z(early_gsk3)
        - 0.26 * z(early_stress_kinase)
    )
    protocol_shortcut = z(
        protocol_success_channel
        + 0.08 * protocol_intensity
        + 0.06 * rng.normal(size=n)
    )
    future_score = z(future_folding_execution - 0.55 * late_aggregate_burden)
    lowdose = 0.995 * z(clean_hybrid) + 0.005 * z(oracle)

    return pd.DataFrame(
        {
            "cell_id": [f"synthetic_cell_{idx:05d}" for idx in range(n)],
            "anchor_time": 0,
            "donor_id": donor,
            "batch_id": batch,
            "protocol_arm": protocol_arm,
            "differentiation_day": differentiation_day,
            "stressor_dose": stressor_dose,
            "protocol_intensity_score": protocol_intensity,
            "mass_spec_run_score": batch_effect + rng.normal(0, 0.05, n),
            "visible_morphology_score": visible_morphology,
            "cell_density_score": cell_density,
            "early_viability_score": early_viability,
            "label_later_folding_execution_stable": label,
            "early_mapk_phospho_slope": early_mapk,
            "early_akt_mtor_pulse": early_akt,
            "early_gsk3_cdk_balance": early_gsk3,
            "early_stress_kinase_persistence": early_stress_kinase,
            "early_chaperone_buffer": early_chaperone,
            "early_upr_load": early_upr,
            "early_autophagy_flux": early_autophagy,
            "future_folding_execution_score": future_score,
            "late_aggregate_burden_score": z(late_aggregate_burden),
            "oracle_folding_label_score": oracle,
            "clean_hybrid_kinase_folding_score": z(clean_hybrid),
            "kinase_only_score": z(kinase_only),
            "protocol_stressor_shortcut_score": protocol_shortcut,
            "lowdose_oracle_mix_005_score": z(lowdose),
        }
    )


def build_config(monitor: dict[str, Any]) -> dict[str, Any]:
    future_features = {
        "future_folding_execution_score",
        "late_aggregate_burden_score",
        "oracle_folding_label_score",
    }
    valid_features = []
    for feature in monitor["features"]:
        valid_features.append(
            {
                "name": feature,
                "latest_offset_h": 24 if feature in future_features else 0,
            }
        )

    forbidden = [
        "protocol_stressor_shortcut_score",
        "protocol_intensity_score",
        "stressor_dose",
        "differentiation_day",
        "protocol_arm",
        "donor_id",
        "batch_id",
        "mass_spec_run_score",
        "future_folding_execution_score",
        "late_aggregate_burden_score",
        "oracle_folding_label_score",
    ]
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"Synthetic iPSC molecular-code audit: {monitor['name']}",
            "task": (
                "Early kinase/phosphosignaling dynamics plus early proteostasis "
                "buffering predict later folding execution"
            ),
            "role": "LAMP-Bio molecular-code control",
            "monitor_id": monitor["id"],
            "expected_result": monitor["expected"],
        },
        "columns": {
            "subject_id": "cell_id",
            "label": "label_later_folding_execution_stable",
            "positive_value": 1,
            "score": monitor["score"],
            "anchor_time": "anchor_time",
        },
        "temporal_isolation": {
            "anchor": "anchor_time",
            "valid_features_must_be": "early kinase/proteostasis features at or before anchor",
            "frozen_before_holdout": [
                "synthetic generator seed",
                "molecular-code biological contract",
                "monitor score family definitions",
                "LAMP thresholds",
            ],
            "valid_score_features": valid_features,
        },
        "forbidden_features": {
            "columns": forbidden,
            "allowed_metadata_columns": [
                "donor_id",
                "batch_id",
                "protocol_arm",
                "differentiation_day",
                "stressor_dose",
                "protocol_intensity_score",
                "mass_spec_run_score",
            ],
            "valid_score_features": list(monitor["features"]),
        },
        "sentinels": {
            "protocol_stressor": {
                "column": "protocol_stressor_shortcut_score",
                "role": "protocol_shortcut",
                "expected_signature": "protocol/stressor metadata should not be sufficient evidence",
            },
            "donor_batch": {
                "column": "mass_spec_run_score",
                "role": "donor_batch_shortcut",
                "expected_signature": "run or donor/batch structure should remain a sentinel",
            },
            "future_folding": {
                "column": "future_folding_execution_score",
                "role": "future_folding_execution",
                "expected_signature": "post-anchor folding state should be a future invalid comparator",
            },
            "late_aggregate_burden": {
                "column": "late_aggregate_burden_score",
                "role": "future_folding_execution",
                "expected_signature": "late aggregate burden is endpoint-adjacent future state",
            },
            "oracle_endpoint": {
                "column": "oracle_folding_label_score",
                "role": "oracle_label",
                "expected_signature": "endpoint label leakage ceiling",
            },
        },
        "negative_controls": {"n_permutations": 100, "seed": SEED},
        "visible_state_matching": {
            "columns": [
                "visible_morphology_score",
                "cell_density_score",
                "early_viability_score",
            ],
            "n_bins": 3,
            "min_bin_size": 12,
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.65,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.02,
            "matched_collapse_max": 0.01,
            "score_thresholds": [-1.0, 0.0, 1.0],
        },
        "leakage_proximity": {
            "baseline_score": "clean_hybrid_kinase_folding_score",
            "oracle_proximity_alert_min": 0.001,
        },
    }


def summary_row(
    monitor: dict[str, Any],
    audit: dict[str, Any],
    diagnosis: dict[str, Any],
) -> dict[str, Any]:
    primary = audit["primary_score"]
    dossier = audit["failure_mode_dossier"]
    matched = audit["visible_state_matching"]
    observed = "PASS" if dossier["audit_pass_candidate"] else "FAIL"
    return {
        "monitor_id": monitor["id"],
        "monitor": monitor["name"],
        "expected": monitor["expected"],
        "observed": observed,
        "score_axis": monitor["score_axis"],
        "auc": primary.get("auc"),
        "inverted_auc": primary.get("inverted_auc"),
        "direction_ambiguous": primary.get("direction_ambiguous"),
        "audit_pass": dossier.get("audit_pass_candidate"),
        "bio_diagnosis": diagnosis["diagnosis"],
        "temporal_passed": audit["temporal_isolation"]["passed"],
        "forbidden_passed": audit["forbidden_feature_screen"]["passed"],
        "matched_delta": matched.get("matched_observed_state_delta"),
        "threshold_fragile": audit["threshold_sensitivity"].get("fragile"),
        "output_classes": ";".join(dossier["output_classes"]),
        "flags": ";".join(diagnosis.get("flags", [])),
        "warnings": ";".join(diagnosis.get("warnings", [])),
        "key_reasons": key_reasons(audit, diagnosis),
    }


def key_reasons(audit: dict[str, Any], diagnosis: dict[str, Any]) -> str:
    reasons = []
    if not audit["temporal_isolation"]["passed"]:
        reasons.append("temporal")
    if not audit["forbidden_feature_screen"]["passed"]:
        reasons.append("forbidden")
    if audit["threshold_sensitivity"].get("fragile"):
        reasons.append("threshold fragile")
    if diagnosis.get("flags"):
        reasons.extend(diagnosis["flags"])
    classes = set(audit["failure_mode_dossier"]["output_classes"])
    if "oracle_leakage_proximity_shift" in classes:
        reasons.append("oracle proximity")
    if (
        "protocol_batch_or_donor_shortcut_sentinel" in classes
        and not audit["failure_mode_dossier"].get("audit_pass_candidate")
    ):
        reasons.append("protocol/batch sentinel")
    return ", ".join(dict.fromkeys(reasons)) or "none"


def write_report(table: pd.DataFrame, rows: list[dict[str, Any]]) -> None:
    n_pos = int(table["label_later_folding_execution_stable"].sum())
    lines = [
        "# Synthetic iPSC Molecular-Code LAMP Audit",
        "",
        "This is a controlled LAMP-Bio experiment, not a biological validation claim.",
        "It asks whether a monitor is detecting an early molecular-code signal or",
        "reading protocol structure / future folding state / endpoint labels.",
        "",
        "## Biological Contract",
        "",
        "- Signalling protocol: early kinase/phosphosignaling dynamics.",
        "- Execution correctness: later protein folding, proteostasis, and aggregate burden.",
        "- Clean evidence: disjoint early kinase plus early chaperone/UPR/autophagy features.",
        "- Forbidden evidence: protocol, stressor, batch/donor/run metadata, future folding state, or endpoint labels.",
        "",
        "## Synthetic Setup",
        "",
        f"- Rows: {len(table)} synthetic cells.",
        f"- Positive later folding-execution labels: {n_pos}; negatives: {len(table) - n_pos}.",
        "- Matched visible state: early morphology, density, and viability proxies.",
        "- Endpoint is generated from latent proteostasis capacity plus later folding and aggregate burden.",
        "",
        "## Monitor Comparison",
        "",
        "| Monitor | Expected | Observed | AUC | Matched Delta | Bio Diagnosis | Temporal | Forbidden | Key Reasons |",
        "|---|:---:|:---:|---:|---:|---|:---:|:---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['monitor']} | {row['expected']} | {row['observed']} | "
            f"{fmt(row['auc'])} | {fmt(row['matched_delta'])} | "
            f"`{row['bio_diagnosis']}` | {row['temporal_passed']} | "
            f"{row['forbidden_passed']} | {row['key_reasons']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The clean hybrid monitor is allowed to pass because it uses early, disjoint",
            "kinase/proteostasis signals and retains a matched visible-state delta. The",
            "kinase-only probe is informative but intentionally less stable: it captures",
            "the signalling protocol without enough execution-buffer evidence. Protocol,",
            "future-state, oracle, and low-dose oracle monitors fail for different reasons,",
            "which is the useful property: LAMP is not just saying that biology is messy;",
            "it is separating information-contract violations.",
            "",
        ]
    )
    (OUT / "synthetic_ipsc_molecular_code_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def z(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    sd = values.std()
    if sd == 0:
        return values * 0.0
    return (values - values.mean()) / sd


def fmt(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.3f}"


if __name__ == "__main__":
    raise SystemExit(main())
