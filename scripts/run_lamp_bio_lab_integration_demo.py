#!/usr/bin/env python3
"""Synthetic LAMP-Bio lab integration demo.

This demo turns five common lab bottlenecks into auditable artifacts:
single-cell QC decisions, cluster annotation, experimental context integration,
cross-modal evidence, and hypothesis generation.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
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


OUT_DIR = ROOT / "results/lamp_bio_lab_integration"
FIG_DIR = OUT_DIR / "figures"
LAMP_DIR = OUT_DIR / "lamp_audit"
CONTRACT_PATH = ROOT / "configs/lamp_bio_lab_integration_contract.yaml"


def main() -> int:
    for path in [OUT_DIR, FIG_DIR, LAMP_DIR]:
        path.mkdir(parents=True, exist_ok=True)

    wells, cells = generate_synthetic_lab_bundle()
    qc_decisions = apply_qc_policy(cells)
    annotation = annotate_clusters(qc_decisions)
    context_audit = audit_context(wells)
    sample_table = build_cross_modal_sample_table(wells, qc_decisions, annotation)
    hypothesis = generate_hypotheses(sample_table, annotation, context_audit)

    qc_path = OUT_DIR / "qc_decisions.csv"
    annotation_path = OUT_DIR / "cluster_annotation.csv"
    context_path = OUT_DIR / "context_manifest_audit.csv"
    sample_path = OUT_DIR / "cross_modal_sample_table.csv"
    hypothesis_path = OUT_DIR / "hypothesis_dossier.csv"

    qc_decisions.to_csv(qc_path, index=False)
    annotation.to_csv(annotation_path, index=False)
    context_audit.to_csv(context_path, index=False)
    sample_table.to_csv(sample_path, index=False)
    hypothesis.to_csv(hypothesis_path, index=False)

    audit_config = make_lamp_config()
    config_path = OUT_DIR / "lamp_bio_lab_audit_config.yaml"
    config_path.write_text(yaml.safe_dump(audit_config, sort_keys=False), encoding="utf-8")
    audit_result = run_audit(config_path, sample_path, LAMP_DIR)

    plot_qc_summary(qc_decisions, FIG_DIR / "qc_decision_summary.png")
    plot_hypothesis_summary(hypothesis, FIG_DIR / "hypothesis_support.png")

    report_path = OUT_DIR / "lamp_bio_lab_integration_report.md"
    write_report(
        report_path,
        qc_decisions,
        annotation,
        context_audit,
        sample_table,
        hypothesis,
        audit_result,
    )

    manifest = {
        "contract": relpath(CONTRACT_PATH),
        "report": relpath(report_path),
        "qc_decisions": relpath(qc_path),
        "cluster_annotation": relpath(annotation_path),
        "context_manifest_audit": relpath(context_path),
        "cross_modal_sample_table": relpath(sample_path),
        "hypothesis_dossier": relpath(hypothesis_path),
        "lamp_audit_summary": relpath(LAMP_DIR / "audit_summary.json"),
        "lamp_audit_report": relpath(LAMP_DIR / "audit_report.md"),
        "figures": [
            relpath(FIG_DIR / "qc_decision_summary.png"),
            relpath(FIG_DIR / "hypothesis_support.png"),
        ],
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(report_path)
    return 0


def generate_synthetic_lab_bundle(
    seed: int = 703,
    n_wells: int = 180,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    donors = [f"D{i}" for i in range(1, 7)]
    batches = [f"B{i}" for i in range(1, 4)]
    plates = [f"P{i}" for i in range(1, 7)]
    protocols = ["baseline", "high_calcium", "ramp_pacing"]
    media = ["standard", "fatty_acid", "lactate_selection"]
    stimulations = ["none", "electrical", "drug_pulse"]

    well_rows: list[dict[str, Any]] = []
    cell_rows: list[dict[str, Any]] = []

    donor_effect = {donor: rng.normal(scale=0.35) for donor in donors}
    batch_effect = {batch: rng.normal(scale=0.25) for batch in batches}

    for idx in range(n_wells):
        donor = donors[idx % len(donors)]
        batch = batches[(idx // 12) % len(batches)]
        plate = plates[(idx // 6) % len(plates)]
        # Mild protocol/batch entanglement: realistic enough to be a sentinel.
        if batch == "B1":
            protocol = rng.choice(protocols, p=[0.50, 0.35, 0.15])
        elif batch == "B2":
            protocol = rng.choice(protocols, p=[0.25, 0.50, 0.25])
        else:
            protocol = rng.choice(protocols, p=[0.20, 0.25, 0.55])
        medium = rng.choice(media, p=[0.45, 0.35, 0.20])
        stimulation = rng.choice(stimulations, p=[0.45, 0.40, 0.15])
        passage = int(rng.integers(18, 34))

        protocol_effect = {"baseline": -0.25, "high_calcium": 0.25, "ramp_pacing": 0.45}[
            protocol
        ]
        medium_effect = {"standard": -0.10, "fatty_acid": 0.20, "lactate_selection": 0.35}[
            medium
        ]
        stimulation_effect = {"none": -0.15, "electrical": 0.30, "drug_pulse": -0.05}[
            stimulation
        ]
        latent_maturation = (
            rng.normal()
            + donor_effect[donor]
            + batch_effect[batch]
            + protocol_effect
            + medium_effect
            + stimulation_effect
        )
        qc_pressure = sigmoid(-0.45 * latent_maturation + 0.25 * (passage - 24) / 8)
        readiness_logit = 1.15 * latent_maturation - 0.45 * qc_pressure + rng.normal(scale=0.65)
        functional_readiness = int(readiness_logit > 0.15)

        well_id = f"W{idx:04d}"
        well_rows.append(
            {
                "well_id": well_id,
                "donor_id": donor,
                "batch_id": batch,
                "protocol": protocol,
                "plate_id": plate,
                "passage": passage,
                "medium": medium,
                "stimulation": stimulation,
                "timepoint": "day_30",
                "replicate": (idx % 3) + 1,
                "latent_maturation": latent_maturation,
                "qc_pressure": qc_pressure,
                "functional_readiness": functional_readiness,
            }
        )

        n_cells = int(rng.integers(45, 80))
        for cell_idx in range(n_cells):
            cell_latent = latent_maturation + rng.normal(scale=0.65)
            stress = sigmoid(qc_pressure + rng.normal(scale=0.55))
            fibroblast_probability = sigmoid(-1.3 * cell_latent + 0.9 * stress - 1.1)
            stressed_probability = sigmoid(0.8 * stress - 0.7)
            if rng.random() < fibroblast_probability * 0.55:
                true_cell_type = "fibroblast_contamination"
                cluster_id = 5
            elif rng.random() < stressed_probability * 0.45:
                true_cell_type = "stressed_cm"
                cluster_id = 4
            elif cell_latent > 0.9:
                true_cell_type = "ventricular_cm"
                cluster_id = rng.choice([2, 3])
            elif cell_latent > 0.15:
                true_cell_type = "immature_cm"
                cluster_id = rng.choice([1, 2])
            else:
                true_cell_type = "immature_cm"
                cluster_id = rng.choice([0, 1])

            n_genes = max(120, int(rng.normal(2600 + 450 * cell_latent - 800 * stress, 420)))
            n_counts = max(350, int(rng.normal(8000 + 1400 * cell_latent - 1800 * stress, 1100)))
            pct_mito = max(1.0, rng.normal(7.5 + 12.0 * stress - 2.0 * cell_latent, 3.0))
            doublet_score = min(1.0, max(0.0, rng.beta(1.5, 8.0) + 0.15 * (n_counts > 10500)))
            ambient_score = min(1.0, max(0.0, rng.beta(1.4, 9.0) + 0.25 * stress))

            cell_rows.append(
                {
                    "cell_id": f"{well_id}_C{cell_idx:03d}",
                    "well_id": well_id,
                    "cluster_id": int(cluster_id),
                    "true_cell_type": true_cell_type,
                    "n_genes": n_genes,
                    "n_counts": n_counts,
                    "pct_mito": pct_mito,
                    "doublet_score": doublet_score,
                    "ambient_rna_score": ambient_score,
                    "stress_signature_score": zlike(stress),
                    "structural_marker_score": cell_latent + rng.normal(scale=0.7),
                    "calcium_marker_score": 0.8 * cell_latent + rng.normal(scale=0.75),
                    "fibroblast_marker_score": (true_cell_type == "fibroblast_contamination")
                    + rng.normal(scale=0.35),
                    "stress_marker_score": stress + rng.normal(scale=0.35),
                    "cell_cycle_marker_score": -0.35 * cell_latent + rng.normal(scale=0.8),
                }
            )

    return pd.DataFrame(well_rows), pd.DataFrame(cell_rows)


def apply_qc_policy(cells: pd.DataFrame) -> pd.DataFrame:
    df = cells.copy()
    decisions = []
    reasons = []
    near = []
    for _, row in df.iterrows():
        hard_reasons = []
        review_reasons = []
        if row["n_genes"] < 500:
            hard_reasons.append("low_genes")
        elif row["n_genes"] < 650:
            review_reasons.append("near_low_genes")
        if row["n_genes"] > 6500:
            hard_reasons.append("high_genes")
        if row["pct_mito"] > 20.0:
            hard_reasons.append("high_mito")
        elif row["pct_mito"] > 18.0:
            review_reasons.append("near_high_mito")
        if row["doublet_score"] > 0.35:
            hard_reasons.append("doublet")
        elif row["doublet_score"] > 0.315:
            review_reasons.append("near_doublet")
        if row["ambient_rna_score"] > 0.25:
            hard_reasons.append("ambient_rna")
        elif row["ambient_rna_score"] > 0.225:
            review_reasons.append("near_ambient")
        if row["stress_signature_score"] > 2.5:
            review_reasons.append("high_stress_signature")

        if hard_reasons:
            decisions.append("drop")
            reasons.append(";".join(hard_reasons))
        elif review_reasons:
            decisions.append("review")
            reasons.append(";".join(review_reasons))
        else:
            decisions.append("keep")
            reasons.append("pass")
        near.append(bool(review_reasons))

    df["qc_decision"] = decisions
    df["qc_reason"] = reasons
    df["qc_near_threshold"] = near
    return df


def annotate_clusters(qc: pd.DataFrame) -> pd.DataFrame:
    kept = qc[qc["qc_decision"] != "drop"].copy()
    rows = []
    for cluster_id, group in kept.groupby("cluster_id"):
        scores = {
            "immature_cm": 0.55 * group["structural_marker_score"].mean()
            - 0.45 * group["cell_cycle_marker_score"].mean(),
            "ventricular_cm": group["structural_marker_score"].mean()
            + 0.45 * group["calcium_marker_score"].mean(),
            "stressed_cm": group["stress_marker_score"].mean() + 0.25 * group["pct_mito"].mean() / 10,
            "fibroblast_contamination": group["fibroblast_marker_score"].mean(),
        }
        probabilities = softmax(scores)
        ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
        label, confidence = ranked[0]
        second_label, second_confidence = ranked[1]
        margin = confidence - second_confidence
        ambiguous = confidence < 0.55 or margin < 0.12
        contamination = label == "fibroblast_contamination" or probabilities[
            "fibroblast_contamination"
        ] > 0.30
        rows.append(
            {
                "cluster_id": cluster_id,
                "n_cells_kept_or_review": len(group),
                "label": "unknown_or_mixed" if ambiguous else label,
                "top_label": label,
                "confidence": confidence,
                "second_best_label": second_label,
                "second_best_confidence": second_confidence,
                "top_minus_second_margin": margin,
                "ambiguity_flag": ambiguous,
                "contamination_flag": contamination,
                "mean_structural_marker_score": group["structural_marker_score"].mean(),
                "mean_calcium_marker_score": group["calcium_marker_score"].mean(),
                "mean_stress_marker_score": group["stress_marker_score"].mean(),
                "mean_fibroblast_marker_score": group["fibroblast_marker_score"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values("cluster_id")


def audit_context(wells: pd.DataFrame) -> pd.DataFrame:
    required = [
        "donor_id",
        "batch_id",
        "protocol",
        "plate_id",
        "passage",
        "medium",
        "stimulation",
        "timepoint",
        "replicate",
    ]
    rows = []
    for _, row in wells.iterrows():
        missing = [field for field in required if pd.isna(row.get(field))]
        rows.append(
            {
                "well_id": row["well_id"],
                "context_completeness": 1.0 - (len(missing) / len(required)),
                "missing_context_fields": ";".join(missing) if missing else "none",
                "donor_id": row["donor_id"],
                "batch_id": row["batch_id"],
                "protocol": row["protocol"],
                "plate_id": row["plate_id"],
                "passage": row["passage"],
                "medium": row["medium"],
                "stimulation": row["stimulation"],
            }
        )
    audit = pd.DataFrame(rows)
    audit["batch_protocol_pair"] = audit["batch_id"] + "::" + audit["protocol"]
    pair_counts = audit["batch_protocol_pair"].map(audit["batch_protocol_pair"].value_counts())
    audit["batch_protocol_entanglement_score"] = pair_counts / pair_counts.max()
    return audit


def build_cross_modal_sample_table(
    wells: pd.DataFrame,
    qc: pd.DataFrame,
    annotation: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    annotation_map = annotation.set_index("cluster_id").to_dict("index")
    protocol_code = {"baseline": -0.5, "high_calcium": 0.35, "ramp_pacing": 0.75}
    medium_code = {"standard": -0.35, "fatty_acid": 0.25, "lactate_selection": 0.45}
    stimulation_code = {"none": -0.4, "electrical": 0.45, "drug_pulse": -0.1}

    for _, well in wells.iterrows():
        cells = qc[qc["well_id"] == well["well_id"]]
        retained = cells[cells["qc_decision"] == "keep"]
        used = retained if len(retained) >= 8 else cells[cells["qc_decision"] != "drop"]
        qc_burden = 1.0 - (len(retained) / max(1, len(cells)))
        review_rate = (cells["qc_decision"] == "review").mean()
        drop_rate = (cells["qc_decision"] == "drop").mean()
        fibroblast_fraction = (
            used["cluster_id"].map(
                lambda cluster: bool(
                    annotation_map.get(cluster, {}).get("contamination_flag", False)
                )
            )
        ).mean()
        stressed_fraction = (
            used["cluster_id"].map(
                lambda cluster: annotation_map.get(cluster, {}).get("top_label")
                == "stressed_cm"
            )
        ).mean()

        early_rna_calcium = used["calcium_marker_score"].mean()
        early_rna_structural = used["structural_marker_score"].mean()
        phospho_kinase = (
            0.65 * well["latent_maturation"]
            + 0.35 * protocol_code[well["protocol"]]
            + np.random.default_rng(int(well["well_id"][1:]) + 41).normal(scale=0.55)
        )
        morphology_sarcomere = (
            0.75 * well["latent_maturation"]
            - 0.25 * qc_burden
            + np.random.default_rng(int(well["well_id"][1:]) + 91).normal(scale=0.65)
        )
        future_calcium = (
            1.15 * well["functional_readiness"]
            + 0.35 * well["latent_maturation"]
            + np.random.default_rng(int(well["well_id"][1:]) + 131).normal(scale=0.35)
        )
        protocol_sentinel = (
            protocol_code[well["protocol"]]
            + 0.25 * medium_code[well["medium"]]
            + 0.2 * stimulation_code[well["stimulation"]]
        )
        cross_modal = (
            0.34 * early_rna_calcium
            + 0.24 * early_rna_structural
            + 0.24 * phospho_kinase
            + 0.24 * morphology_sarcomere
            - 0.55 * qc_burden
            - 0.25 * fibroblast_fraction
        )
        rows.append(
            {
                "subject_id": well["well_id"],
                "anchor_time_h": 0,
                "outcome": int(well["functional_readiness"]),
                "cross_modal_maturation_score": cross_modal,
                "early_rna_calcium_axis": early_rna_calcium,
                "early_rna_structural_axis": early_rna_structural,
                "early_phospho_kinase_axis": phospho_kinase,
                "early_morphology_sarcomere_axis": morphology_sarcomere,
                "qc_burden_sentinel_score": qc_burden,
                "annotation_contamination_sentinel_score": fibroblast_fraction,
                "stressed_cm_fraction": stressed_fraction,
                "review_rate": review_rate,
                "drop_rate": drop_rate,
                "protocol_context_sentinel_score": protocol_sentinel,
                "future_calcium_trace_score": future_calcium,
                "endpoint_oracle_score": well["functional_readiness"]
                + np.random.default_rng(int(well["well_id"][1:]) + 171).normal(scale=0.04),
                "donor_id": well["donor_id"],
                "batch_id": well["batch_id"],
                "protocol": well["protocol"],
                "plate_id": well["plate_id"],
                "passage": well["passage"],
                "medium": well["medium"],
                "stimulation": well["stimulation"],
            }
        )

    table = pd.DataFrame(rows)
    numeric_cols = [
        "cross_modal_maturation_score",
        "early_rna_calcium_axis",
        "early_rna_structural_axis",
        "early_phospho_kinase_axis",
        "early_morphology_sarcomere_axis",
        "qc_burden_sentinel_score",
        "annotation_contamination_sentinel_score",
        "protocol_context_sentinel_score",
        "future_calcium_trace_score",
        "endpoint_oracle_score",
    ]
    for col in numeric_cols:
        table[col] = zscore(table[col])
    return table


def generate_hypotheses(
    sample_table: pd.DataFrame,
    annotation: pd.DataFrame,
    context: pd.DataFrame,
) -> pd.DataFrame:
    labels = sample_table["outcome"].astype(int).tolist()
    hypotheses = []
    feature_sets = {
        "calcium_handling_maturation": [
            "early_rna_calcium_axis",
            "early_phospho_kinase_axis",
            "early_morphology_sarcomere_axis",
        ],
        "stress_or_qc_artifact": ["qc_burden_sentinel_score", "review_rate", "drop_rate"],
        "protocol_or_batch_shortcut": ["protocol_context_sentinel_score"],
        "contamination_composition_shift": [
            "annotation_contamination_sentinel_score",
            "stressed_cm_fraction",
        ],
        "future_endpoint_leakage": ["future_calcium_trace_score", "endpoint_oracle_score"],
    }
    tests = {
        "calcium_handling_maturation": (
            "Hold out future calcium traces, perturb early kinase/calcium axes, "
            "and retest a disjoint structural or electrophysiology endpoint."
        ),
        "stress_or_qc_artifact": (
            "Match QC burden, perturb QC thresholds, run ambient-RNA correction, "
            "and check whether the signal survives."
        ),
        "protocol_or_batch_shortcut": (
            "Cross donor, batch, protocol, plate, medium, and stimulation in a "
            "balanced design; require protocol-heldout performance."
        ),
        "contamination_composition_shift": (
            "Match or purify cell-type composition and retest after removing "
            "fibroblast/stressed-cell composition from the score."
        ),
        "future_endpoint_leakage": (
            "Remove endpoint-adjacent and future trace channels from the monitor "
            "and repeat with a frozen pre-anchor feature set."
        ),
    }
    for name, features in feature_sets.items():
        aucs = [
            auc_score(labels, sample_table[feature].astype(float).tolist())
            for feature in features
            if feature in sample_table
        ]
        aucs = [value for value in aucs if value is not None]
        support = float(np.mean([abs(value - 0.5) * 2.0 for value in aucs])) if aucs else 0.0
        top_feature = features[int(np.argmax([abs((value or 0.5) - 0.5) for value in aucs]))] if aucs else ""
        hypotheses.append(
            {
                "category": hypothesis_category(name),
                "hypothesis": name,
                "support_score": support,
                "top_feature_or_axis": top_feature,
                "evidence_features": ";".join(features),
                "alternative_explanation": alternative_explanation(name),
                "prospective_test": tests[name],
            }
        )

    out = pd.DataFrame(hypotheses)
    category_order = {
        "biological_hypothesis": 0,
        "alternative_shortcut": 1,
        "sentinel_control": 2,
    }
    out["category_order"] = out["category"].map(category_order)
    out = out.sort_values(["category_order", "support_score"], ascending=[True, False])
    out["rank"] = range(1, len(out) + 1)
    return out[
        [
            "rank",
            "category",
            "hypothesis",
            "support_score",
            "top_feature_or_axis",
            "evidence_features",
            "alternative_explanation",
            "prospective_test",
        ]
    ]


def make_lamp_config() -> dict[str, Any]:
    context_metadata = [
        "donor_id",
        "batch_id",
        "protocol",
        "plate_id",
        "passage",
        "medium",
        "stimulation",
    ]
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": "Synthetic LAMP-Bio lab integration demo",
            "task": "early multimodal iPSC-CM readiness audit",
            "role": "lab-facing integration artifact",
        },
        "columns": {
            "subject_id": "subject_id",
            "label": "outcome",
            "positive_value": 1,
            "score": "cross_modal_maturation_score",
            "anchor_time": "anchor_time_h",
        },
        "temporal_isolation": {
            "anchor": "anchor_time_h",
            "valid_features_must_be": "at_or_before_anchor",
            "frozen_before_holdout": [
                "QC policy",
                "annotation policy",
                "context manifest fields",
                "cross-modal score formula",
                "sentinel definitions",
            ],
            "valid_score_features": [
                {"name": "early_rna_calcium_axis", "latest_offset_h": 0},
                {"name": "early_rna_structural_axis", "latest_offset_h": 0},
                {"name": "early_phospho_kinase_axis", "latest_offset_h": 0},
                {"name": "early_morphology_sarcomere_axis", "latest_offset_h": 0},
            ],
        },
        "forbidden_features": {
            "columns": [
                "future_calcium_trace_score",
                "endpoint_oracle_score",
                "protocol_context_sentinel_score",
                "qc_burden_sentinel_score",
                "annotation_contamination_sentinel_score",
            ],
            "allowed_metadata_columns": context_metadata,
            "valid_score_features": [
                "early_rna_calcium_axis",
                "early_rna_structural_axis",
                "early_phospho_kinase_axis",
                "early_morphology_sarcomere_axis",
            ],
        },
        "sentinels": {
            "future_calcium_trace": {
                "column": "future_calcium_trace_score",
                "role": "future_physiology",
                "expected_signature": "future functional calcium comparator",
            },
            "endpoint_oracle": {
                "column": "endpoint_oracle_score",
                "role": "oracle_label",
                "expected_signature": "endpoint-adjacent readiness comparator",
            },
            "protocol_context": {
                "column": "protocol_context_sentinel_score",
                "role": "protocol_shortcut",
                "expected_signature": "protocol, medium, stimulation context comparator",
            },
            "qc_burden": {
                "column": "qc_burden_sentinel_score",
                "role": "qc_artifact_shortcut",
                "expected_signature": "QC filtering and low-quality-cell comparator",
            },
            "annotation_contamination": {
                "column": "annotation_contamination_sentinel_score",
                "role": "annotation_contamination_shortcut",
                "expected_signature": "fibroblast/stressed-cell composition comparator",
            },
        },
        "negative_controls": {"n_permutations": 100, "seed": 703},
        "visible_state_matching": {
            "columns": [
                "early_rna_structural_axis",
                "qc_burden_sentinel_score",
                "annotation_contamination_sentinel_score",
            ],
            "n_bins": 3,
            "min_bin_size": 8,
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
        "early_window_sensitivity": {
            "score_columns": [
                "early_rna_calcium_axis",
                "early_phospho_kinase_axis",
                "early_morphology_sarcomere_axis",
            ]
        },
    }


def write_report(
    path: Path,
    qc: pd.DataFrame,
    annotation: pd.DataFrame,
    context: pd.DataFrame,
    sample_table: pd.DataFrame,
    hypotheses: pd.DataFrame,
    audit: dict[str, Any],
) -> None:
    qc_counts = qc["qc_decision"].value_counts().to_dict()
    top_qc_reasons = Counter(
        reason for value in qc["qc_reason"] for reason in str(value).split(";") if reason
    ).most_common(6)
    primary = audit["primary_score"]
    dossier = audit["failure_mode_dossier"]
    sentinels = audit["sentinels"]
    match = audit["visible_state_matching"]
    biological = hypotheses[hypotheses["category"] == "biological_hypothesis"]
    sentinel_controls = hypotheses[hypotheses["category"] == "sentinel_control"]
    top_hypothesis = biological.iloc[0] if not biological.empty else hypotheses.iloc[0]
    top_sentinel = sentinel_controls.iloc[0] if not sentinel_controls.empty else None
    ambiguous_clusters = int(annotation["ambiguity_flag"].sum())
    contaminated_clusters = int(annotation["contamination_flag"].sum())
    context_complete = context["context_completeness"].mean()

    lines = []
    lines.append("# LAMP-Bio Lab Integration Demo")
    lines.append("")
    lines.append(
        "This synthetic artifact integrates five lab-facing decision layers into "
        "a LAMP-Bio audit: single-cell QC, biological annotation, experimental "
        "context, cross-modal evidence, and hypothesis generation."
    )
    lines.append("")
    lines.append("## 1. QC Decisions")
    lines.append("")
    lines.append(f"- Cells audited: `{len(qc)}`")
    lines.append(
        "- Decisions: "
        + ", ".join(f"`{key}`={value}" for key, value in sorted(qc_counts.items()))
    )
    lines.append(
        "- Top QC reasons: "
        + ", ".join(f"`{reason}`={count}" for reason, count in top_qc_reasons)
    )
    lines.append(
        f"- Mean review/drop burden by well is encoded as `qc_burden_sentinel_score`."
    )
    lines.append("")
    lines.append("## 2. Biological Annotation")
    lines.append("")
    lines.append(f"- Clusters annotated: `{len(annotation)}`")
    lines.append(f"- Ambiguous clusters: `{ambiguous_clusters}`")
    lines.append(f"- Contamination-flagged clusters: `{contaminated_clusters}`")
    lines.append("")
    lines.append("| Cluster | Label | Confidence | Second Best | Ambiguous | Contamination |")
    lines.append("| ---: | --- | ---: | --- | --- | --- |")
    for _, row in annotation.iterrows():
        lines.append(
            "| {cluster} | {label} | {conf:.3f} | {second} | {amb} | {contam} |".format(
                cluster=int(row["cluster_id"]),
                label=row["label"],
                conf=row["confidence"],
                second=row["second_best_label"],
                amb=str(bool(row["ambiguity_flag"])),
                contam=str(bool(row["contamination_flag"])),
            )
        )
    lines.append("")
    lines.append("## 3. Experimental Context")
    lines.append("")
    lines.append(f"- Wells/samples: `{len(context)}`")
    lines.append(f"- Mean context completeness: `{context_complete:.3f}`")
    lines.append(
        "- Context fields are retained as metadata/sentinels, not valid biological "
        "score evidence."
    )
    lines.append("")
    lines.append("## 4. Cross-Modal LAMP Audit")
    lines.append("")
    lines.append(f"- Cross-modal score AUC: `{primary['auc']:.3f}`")
    lines.append(
        f"- Matched observed-state delta: `{match.get('matched_observed_state_delta'):.3f}`"
    )
    lines.append(
        f"- Audit pass candidate: `{dossier['audit_pass_candidate']}`"
    )
    lines.append(
        "- Output classes: "
        + ", ".join(f"`{value}`" for value in dossier["output_classes"])
    )
    lines.append("")
    lines.append("| Sentinel | Role | AUC |")
    lines.append("| --- | --- | ---: |")
    for name, item in sentinels.items():
        lines.append(
            "| {name} | {role} | {auc_value} |".format(
                name=name,
                role=item.get("role"),
                auc_value=(
                    "NA" if item.get("auc") is None else f"{item.get('auc'):.3f}"
                ),
            )
        )
    lines.append("")
    lines.append("## 5. Hypothesis Generation")
    lines.append("")
    lines.append(
        "Top biological hypothesis: `{}` with support `{:.3f}`.".format(
            top_hypothesis["hypothesis"],
            top_hypothesis["support_score"],
        )
    )
    if top_sentinel is not None:
        lines.append(
            "Strongest sentinel/control channel: `{}` with support `{:.3f}`. "
            "This is not a valid biological hypothesis; it is the channel to "
            "remove, hide, or hold out before validation.".format(
                top_sentinel["hypothesis"],
                top_sentinel["support_score"],
            )
        )
    lines.append("")
    lines.append("| Rank | Category | Hypothesis | Support | Top Feature / Axis | Prospective Test |")
    lines.append("| ---: | --- | --- | ---: | --- | --- |")
    for _, row in hypotheses.iterrows():
        lines.append(
            "| {rank} | {category} | {hypothesis} | {support:.3f} | {feature} | {test} |".format(
                rank=int(row["rank"]),
                category=row["category"],
                hypothesis=row["hypothesis"],
                support=row["support_score"],
                feature=row["top_feature_or_axis"],
                test=row["prospective_test"],
            )
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The demo does not claim biological discovery. It shows the intended "
        "LAMP-Bio behavior: QC decisions, annotation ambiguity, and context fields "
        "are first-class audit objects; cross-modal evidence is interpreted only "
        "after sentinels and matched cohorts are checked; hypotheses are emitted "
        "as prospective tests, not validation."
    )
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("- `qc_decisions.csv`")
    lines.append("- `cluster_annotation.csv`")
    lines.append("- `context_manifest_audit.csv`")
    lines.append("- `cross_modal_sample_table.csv`")
    lines.append("- `hypothesis_dossier.csv`")
    lines.append("- `lamp_audit/audit_summary.json`")
    lines.append("- `figures/qc_decision_summary.png`")
    lines.append("- `figures/hypothesis_support.png`")
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_qc_summary(qc: pd.DataFrame, path: Path) -> None:
    counts = qc["qc_decision"].value_counts().reindex(["keep", "review", "drop"]).fillna(0)
    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    ax.bar(counts.index, counts.values, color=["#222222", "#777777", "#bbbbbb"])
    ax.set_ylabel("cells")
    ax.set_title("Single-cell QC decisions")
    ax.grid(axis="y", alpha=0.18)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_hypothesis_summary(hypotheses: pd.DataFrame, path: Path) -> None:
    ordered = hypotheses.sort_values("rank", ascending=True)
    colors = ordered["category"].map(
        {
            "biological_hypothesis": "#222222",
            "alternative_shortcut": "#777777",
            "sentinel_control": "#bbbbbb",
        }
    )
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    ax.barh(ordered["hypothesis"], ordered["support_score"], color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("support score")
    ax.set_title("Generated hypotheses and sentinel controls")
    ax.grid(axis="x", alpha=0.18)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def softmax(scores: dict[str, float]) -> dict[str, float]:
    keys = list(scores)
    values = np.array([scores[key] for key in keys], dtype=float)
    values = values - values.max()
    exp = np.exp(values)
    probs = exp / exp.sum()
    return {key: float(prob) for key, prob in zip(keys, probs)}


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-float(value)))


def zscore(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    sd = arr.std()
    if sd == 0:
        return arr - arr.mean()
    return (arr - arr.mean()) / sd


def zlike(value: float) -> float:
    return (float(value) - 0.5) * 4.0


def alternative_explanation(name: str) -> str:
    return {
        "calcium_handling_maturation": "could still be protocol or future-trace leakage",
        "stress_or_qc_artifact": "could explain signal via filtering/stress rather than maturation",
        "protocol_or_batch_shortcut": "could reconstruct outcome from experimental structure",
        "contamination_composition_shift": "could reflect cell-type composition rather than state",
        "future_endpoint_leakage": "invalid as validation, useful only as sentinel",
    }[name]


def hypothesis_category(name: str) -> str:
    if name == "calcium_handling_maturation":
        return "biological_hypothesis"
    if name == "future_endpoint_leakage":
        return "sentinel_control"
    return "alternative_shortcut"


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
