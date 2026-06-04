#!/usr/bin/env python3
"""Apply the iPSC-CM biological contract to existing LAMP-Bio outputs."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.bio import diagnose_biological_claim, load_audit_summary, load_bio_contract  # noqa: E402


CONTRACT_PATH = ROOT / "configs" / "ipsc_cm_maturation_contract.yaml"
SANITY_DIR = ROOT / "results" / "ipsc_cm_maturation_lamp" / "gse201437_sanity_separation"
ROBUSTNESS_DIR = ROOT / "results" / "ipsc_cm_maturation_lamp" / "gse201437_sanity_robustness"
OUT = ROOT / "results" / "ipsc_cm_maturation_lamp" / "bio_contract_diagnosis"


MODELS = [
    {
        "model_id": "clean_calcium_probe",
        "name": "Clean calcium/electrophysiology probe",
        "audit_summary": SANITY_DIR / "lamp" / "clean_calcium_probe" / "audit_summary.json",
        "score_axis": "calcium_handling_electrophysiology",
        "include_stability": True,
    },
    {
        "model_id": "protocol_shortcut",
        "name": "High-calcium protocol shortcut",
        "audit_summary": SANITY_DIR / "lamp" / "protocol_shortcut" / "audit_summary.json",
        "score_axis": "intervention_protocol_structure",
        "include_stability": False,
    },
    {
        "model_id": "explicit_oracle_leakage",
        "name": "Explicit oracle leakage",
        "audit_summary": SANITY_DIR / "lamp" / "explicit_oracle_leakage" / "audit_summary.json",
        "score_axis": "structural_maturation",
        "include_stability": False,
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = load_bio_contract(CONTRACT_PATH)
    stability = load_clean_stability()

    diagnoses = []
    for model in MODELS:
        audit_summary = load_audit_summary(model["audit_summary"])
        model_stability = stability if model["include_stability"] else {}
        diagnosis = diagnose_biological_claim(
            audit_summary=audit_summary,
            contract=contract,
            claim_id="structural_endpoint_calcium_probe",
            score_axis=model["score_axis"],
            stability=model_stability,
        )
        diagnosis["model_id"] = model["model_id"]
        diagnosis["model_name"] = model["name"]
        diagnoses.append(diagnosis)

    (OUT / "ipsc_cm_bio_contract_diagnosis.json").write_text(
        json.dumps(diagnoses, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_csv(OUT / "ipsc_cm_bio_contract_diagnosis.csv", diagnoses)
    write_report(diagnoses, stability)
    print(OUT / "ipsc_cm_bio_contract_diagnosis.md")
    return 0


def load_clean_stability() -> dict[str, Any]:
    bootstrap = pd.read_csv(ROBUSTNESS_DIR / "gse201437_robustness_bootstrap.csv")
    panels = pd.read_csv(ROBUSTNESS_DIR / "gse201437_robustness_panels.csv")
    groups = pd.read_csv(ROBUSTNESS_DIR / "gse201437_robustness_leave_group_out.csv")
    thresholds = pd.read_csv(ROBUSTNESS_DIR / "gse201437_robustness_thresholds.csv")

    clean_boot = bootstrap[bootstrap["monitor_id"] == "clean_calcium_probe"].iloc[0]
    clean_panels = panels[panels["monitor_id"].astype(str).str.startswith("clean_")]
    clean_groups = groups[groups["monitor_id"] == "clean_calcium_probe"]
    clean_thresholds = thresholds[thresholds["monitor_id"] == "clean_calcium_probe"]
    return {
        "bootstrap_pass_rate": float(clean_boot["pass_rate"]),
        "bootstrap_auc_mean": float(clean_boot["auc_mean"]),
        "bootstrap_auc_p025": float(clean_boot["auc_p025"]),
        "bootstrap_auc_p975": float(clean_boot["auc_p975"]),
        "alternative_panel_pass_rate": float(clean_panels["audit_pass"].astype(bool).mean()),
        "leave_group_out_pass_rate": float((clean_groups["observed"] == "PASS").mean()),
        "threshold_grid_pass_rate": float(clean_thresholds["audit_pass"].astype(bool).mean()),
        "donor_heldout_status": "not_evaluable",
        "protocol_heldout_status": "not_evaluable",
    }


def write_csv(path: Path, diagnoses: list[dict[str, Any]]) -> None:
    rows = []
    for item in diagnoses:
        rows.append(
            {
                "model_id": item["model_id"],
                "model_name": item["model_name"],
                "diagnosis": item["diagnosis"],
                "primary_auc": item["primary_auc"],
                "audit_pass_candidate": item["audit_pass_candidate"],
                "endpoint_axis": item["endpoint_axis"],
                "score_axis": item["score_axis"],
                "protocol_sentinel_dominance": item["protocol_sentinel_dominance"],
                "flags": ";".join(item["flags"]),
                "warnings": ";".join(item["warnings"]),
                "interpretation": item["interpretation"],
            }
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(diagnoses: list[dict[str, Any]], stability: dict[str, Any]) -> None:
    lines = [
        "# iPSC-CM Biological Contract Diagnosis",
        "",
        "This report applies `configs/ipsc_cm_maturation_contract.yaml` to the",
        "controlled GSE201437 LAMP sanity outputs. It translates raw audit classes",
        "into biological maturation interpretation levels.",
        "",
        "## Claim Contract",
        "",
        "- Claim: disjoint calcium/electrophysiology evidence predicts structural maturation state.",
        "- Endpoint axis: structural maturation.",
        "- Allowed evidence axis: calcium-handling / electrophysiology maturation.",
        "- Forbidden axis: day/protocol/intervention/batch/donor/drug/dose/replicate structure.",
        "- Required sentinels: protocol, timepoint, endpoint-marker/oracle, donor/batch, score-direction sanity.",
        "",
        "## Diagnosis Table",
        "",
        "| Model | AUC | Audit Pass | Biological Diagnosis | Flags | Warnings |",
        "|---|---:|:---:|---|---|---|",
    ]
    for item in diagnoses:
        lines.append(
            f"| {item['model_name']} | {fmt(item['primary_auc'])} | "
            f"{item['audit_pass_candidate']} | `{item['diagnosis']}` | "
            f"{join_or_none(item['flags'])} | {join_or_none(item['warnings'])} |"
        )

    clean = next(item for item in diagnoses if item["model_id"] == "clean_calcium_probe")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            clean["interpretation"],
            "",
            "For the current GSE201437 clean probe, the correct biological reading is:",
            "",
            "> A disjoint calcium/electrophysiology probe supports a biologically plausible",
            "> structural maturation signal, but the interpretation is fragile. Bootstrap",
            "> PASS rate is approximately 0.503, leave-one-HCRP-out fails, and donor-held-out",
            "> stability is not evaluable from the processed GEO table.",
            "",
            "Protocol and oracle monitors are still rejected, so this is not evidence that",
            "LAMP mechanically fails every biological dataset. It is evidence that the",
            "current tiny biological PASS should be treated as a fragile sanity check, not",
            "as a mature iPSC-CM validation claim.",
            "",
            "## Stability Inputs",
            "",
            f"- Bootstrap PASS rate: {fmt(stability['bootstrap_pass_rate'])}.",
            f"- Bootstrap AUC mean: {fmt(stability['bootstrap_auc_mean'])} "
            f"({fmt(stability['bootstrap_auc_p025'])}-{fmt(stability['bootstrap_auc_p975'])}).",
            f"- Alternative panel PASS rate: {fmt(stability['alternative_panel_pass_rate'])}.",
            f"- Leave-group-out PASS rate: {fmt(stability['leave_group_out_pass_rate'])}.",
            f"- Threshold-grid PASS rate: {fmt(stability['threshold_grid_pass_rate'])}.",
            "- Donor-held-out: not evaluable.",
            "- Protocol-held-out: not evaluable for this tiny protocol-coupled sanity table.",
            "",
        ]
    )
    (OUT / "ipsc_cm_bio_contract_diagnosis.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def join_or_none(items: list[str]) -> str:
    if not items:
        return "`none`"
    return ", ".join(f"`{item}`" for item in items)


def fmt(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.3f}"


if __name__ == "__main__":
    raise SystemExit(main())
