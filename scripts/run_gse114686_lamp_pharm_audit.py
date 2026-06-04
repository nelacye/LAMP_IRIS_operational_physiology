#!/usr/bin/env python3
"""GSE114686 LAMP-Pharm cardiotoxicity shortcut audit.

This artifact asks whether a pharmacology monitor is detecting cardiotoxic
biology or experimental structure. It uses public processed RNA-seq from
hiPSC-derived cardiomyocytes treated with tyrosine kinase inhibitors (TKIs).

The deliberately narrow endpoint is severe/high-dose cardiotoxic TKI exposure:
Sorafenib or Sunitinib at >=3 uM. LAMP compares a signed cardiotoxic-response
expression panel against shortcut sentinels for drug identity, dose, exposure
time, and direct endpoint-adjacent leakage.
"""

from __future__ import annotations

import csv
import gzip
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402


ACCESSION = "GSE114686"
GEO_RECORD = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={ACCESSION}"
PROCESSED_URL = (
    "https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE114686&file="
    "GSE114686_ProcessedData.csv.gz&format=file"
)
DATA_DIR = ROOT / "data" / "raw" / ACCESSION.lower()
RAW_EXPR = DATA_DIR / "GSE114686_ProcessedData.csv.gz"
OUT = ROOT / "results" / "lamp_pharm" / "gse114686_tki_cardiotoxicity"
SEED = 20260604

DRUG_MAP = {
    "D": "DMSO",
    "E": "Erlotinib",
    "L": "Lapatinib",
    "S": "Sorafenib",
    "U": "Sunitinib",
}
TIME_MAP = {"1": 6, "2": 24, "3": 72, "4": 168}
DOSE_MAP = {"A": 0.001, "B": 1.0, "C": 3.0, "D": 10.0}
SEVERE_TKI = {"Sorafenib", "Sunitinib"}

STRESS_GENES = [
    "NPPB",
    "NPPA",
    "HSPA1A",
    "HSPA1B",
    "ATF3",
    "DDIT3",
    "JUN",
    "FOS",
    "EGR1",
    "HMOX1",
    "TXNIP",
    "BAX",
    "CDKN1A",
    "GADD45A",
]
APOPTOSIS_GENES = [
    "BAX",
    "BBC3",
    "PMAIP1",
    "CASP3",
    "CASP7",
    "CDKN1A",
    "MDM2",
    "GADD45A",
    "DDIT3",
]
CARDIAC_PROGRAM_GENES = [
    "TNNT2",
    "TNNI3",
    "MYH6",
    "MYH7",
    "MYL2",
    "MYL7",
    "ACTN2",
    "TTN",
    "ATP2A2",
    "PLN",
    "RYR2",
    "CACNA1C",
    "SCN5A",
    "KCNH2",
]

MONITORS = [
    {
        "id": "signed_cardiotoxic_response_score",
        "name": "Signed cardiotoxic-response expression score",
        "score": "signed_cardiotoxic_response_score",
        "features": ["signed_cardiotoxic_response_panel"],
        "temporal_offsets": {"signed_cardiotoxic_response_panel": 0},
        "description": "Stress/apoptosis activation minus cardiac-program expression.",
    },
    {
        "id": "severe_tki_identity_shortcut_score",
        "name": "Severe-TKI drug-identity shortcut score",
        "score": "severe_tki_identity_shortcut_score",
        "features": ["severe_tki_identity"],
        "temporal_offsets": {"severe_tki_identity": 0},
        "description": "Uses Sorafenib/Sunitinib identity as a shortcut.",
    },
    {
        "id": "dose_shortcut_score",
        "name": "Dose shortcut score",
        "score": "dose_shortcut_score",
        "features": ["dose_uM"],
        "temporal_offsets": {"dose_uM": 0},
        "description": "Uses administered dose rather than expression response biology.",
    },
    {
        "id": "exposure_time_shortcut_score",
        "name": "Exposure-time shortcut score",
        "score": "exposure_time_shortcut_score",
        "features": ["exposure_time_h"],
        "temporal_offsets": {"exposure_time_h": 0},
        "description": "Uses exposure duration as a workflow/protocol shortcut.",
    },
    {
        "id": "combined_drug_dose_shortcut_score",
        "name": "Combined drug-dose shortcut score",
        "score": "combined_drug_dose_shortcut_score",
        "features": ["combined_drug_dose_shortcut_score"],
        "temporal_offsets": {"combined_drug_dose_shortcut_score": 0},
        "description": "Uses the exact severe-TKI-at-high-dose endpoint rule.",
    },
    {
        "id": "endpoint_adjacent_marker_score",
        "name": "Endpoint-adjacent marker-selection score",
        "score": "endpoint_adjacent_marker_score",
        "features": ["endpoint_adjacent_marker_score"],
        "temporal_offsets": {"endpoint_adjacent_marker_score": 999},
        "description": "Top genes selected against the endpoint on the same table.",
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ensure_expression()
    expr, gene_ids = load_expression()
    table, endpoint_genes, panel_genes = build_prediction_table(expr, gene_ids)
    prediction_path = OUT / "gse114686_lamp_pharm_prediction_table.csv"
    table.to_csv(prediction_path, index=False, lineterminator="\n")

    summary_rows = []
    for monitor in MONITORS:
        config = build_config(monitor)
        config_path = OUT / "configs" / f"{monitor['id']}.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        result = run_audit(config_path, prediction_path, OUT / "lamp" / monitor["id"])
        summary_rows.append(summary_row(monitor, result))

    write_csv(OUT / "gse114686_lamp_pharm_summary.csv", summary_rows)
    write_report(table, summary_rows, endpoint_genes, panel_genes)
    print(OUT / "gse114686_lamp_pharm_report.md")
    return 0


def ensure_expression() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_EXPR.exists() and RAW_EXPR.stat().st_size > 100_000:
        return
    print(f"Downloading {ACCESSION} processed expression table from GEO")
    request = urllib.request.Request(PROCESSED_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        RAW_EXPR.write_bytes(response.read())


def load_expression() -> tuple[pd.DataFrame, dict[str, str]]:
    with gzip.open(RAW_EXPR, "rt", encoding="utf-8") as handle:
        frame = pd.read_csv(handle)
    sample_cols = [
        col
        for col in frame.columns
        if col not in {"ensembl_gene_id", "external_gene_name"}
    ]
    expr = frame.set_index("external_gene_name")[sample_cols].astype(float)
    gene_ids = frame.set_index("external_gene_name")["ensembl_gene_id"].astype(str).to_dict()
    return expr, gene_ids


def build_prediction_table(
    expr: pd.DataFrame,
    gene_ids: dict[str, str],
) -> tuple[pd.DataFrame, list[str], dict[str, list[str]]]:
    z = zscore_rows(np.log1p(expr))
    sample_ids = list(z.columns)
    panel = {
        "stress_apoptosis": unique_present(STRESS_GENES + APOPTOSIS_GENES, z.index),
        "cardiac_program": unique_present(CARDIAC_PROGRAM_GENES, z.index),
    }
    if len(panel["stress_apoptosis"]) < 5 or len(panel["cardiac_program"]) < 5:
        raise RuntimeError(f"Too few panel genes found in {ACCESSION}: {panel}")

    labels: dict[str, int] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for sample_id in sample_ids:
        parsed = parse_sample_id(sample_id)
        severe_identity = int(parsed["drug"] in SEVERE_TKI)
        high_dose = int(parsed["dose_uM"] >= 3.0)
        labels[sample_id] = int(severe_identity and high_dose)
        metadata[sample_id] = {
            **parsed,
            "severe_tki_identity": severe_identity,
            "high_dose_ge3": high_dose,
        }

    endpoint_genes = select_endpoint_adjacent_genes(z, labels)
    endpoint_gene_names = [gene for gene, _ in endpoint_genes]
    endpoint_gene_signs = pd.Series(
        {gene: 1.0 if effect >= 0.0 else -1.0 for gene, effect in endpoint_genes}
    )

    rows = []
    for sample_id in sample_ids:
        item = metadata[sample_id]
        stress_apoptosis = float(z.loc[panel["stress_apoptosis"], sample_id].mean())
        cardiac_program = float(z.loc[panel["cardiac_program"], sample_id].mean())
        signed_response = stress_apoptosis - cardiac_program
        endpoint_score = float(
            z.loc[endpoint_gene_names, sample_id].mul(endpoint_gene_signs).mean()
        )
        rows.append(
            {
                "sample_id": sample_id,
                "anchor_time": 0,
                "drug": item["drug"],
                "drug_code": item["drug_code"],
                "dose_code": item["dose_code"],
                "time_code": item["time_code"],
                "replicate": item["replicate"],
                "dose_uM": item["dose_uM"],
                "exposure_time_h": item["exposure_time_h"],
                "severe_tki_identity": item["severe_tki_identity"],
                "high_dose_ge3": item["high_dose_ge3"],
                "label_severe_highdose_tki": labels[sample_id],
                "stress_apoptosis_panel_score": stress_apoptosis,
                "cardiac_program_panel_score": cardiac_program,
                "signed_cardiotoxic_response_score": signed_response,
                "severe_tki_identity_shortcut_score": float(item["severe_tki_identity"]),
                "dose_shortcut_score": float(np.log10(item["dose_uM"] + 0.01)),
                "exposure_time_shortcut_score": float(np.log1p(item["exposure_time_h"])),
                "combined_drug_dose_shortcut_score": float(labels[sample_id]),
                "oracle_severe_highdose_tki_score": float(labels[sample_id]),
                "endpoint_adjacent_marker_score": endpoint_score,
                "sample_mean_expression": float(expr[sample_id].mean()),
                "detected_gene_count": int((expr[sample_id] > 0).sum()),
            }
        )

    table = pd.DataFrame(rows).sort_values(
        ["drug", "dose_uM", "exposure_time_h", "replicate"]
    ).reset_index(drop=True)
    endpoint_items = []
    for gene, effect in endpoint_genes:
        ensembl = gene_ids.get(gene, "")
        endpoint_items.append(f"{gene}/{ensembl}:{effect:.3f}")
    return table, endpoint_items, panel


def parse_sample_id(sample_id: str) -> dict[str, Any]:
    match = re.fullmatch(r"([DELSU])(\d)([ABCD])(\d)", sample_id)
    if not match:
        raise ValueError(f"Could not parse GSE114686 sample id: {sample_id}")
    drug_code, time_code, dose_code, replicate_text = match.groups()
    return {
        "drug_code": drug_code,
        "drug": DRUG_MAP[drug_code],
        "time_code": time_code,
        "exposure_time_h": TIME_MAP[time_code],
        "dose_code": dose_code,
        "dose_uM": DOSE_MAP[dose_code],
        "replicate": int(replicate_text),
    }


def zscore_rows(frame: pd.DataFrame) -> pd.DataFrame:
    mean = frame.mean(axis=1)
    sd = frame.std(axis=1).replace(0, np.nan)
    return frame.sub(mean, axis=0).divide(sd, axis=0).fillna(0.0)


def unique_present(genes: list[str], available: pd.Index) -> list[str]:
    seen = set()
    present = []
    for gene in genes:
        if gene in available and gene not in seen:
            seen.add(gene)
            present.append(gene)
    return present


def select_endpoint_adjacent_genes(
    z: pd.DataFrame,
    labels: dict[str, int],
    n_genes: int = 20,
) -> list[tuple[str, float]]:
    positive_samples = [sample for sample, label in labels.items() if label == 1]
    negative_samples = [sample for sample, label in labels.items() if label == 0]
    effects = z[positive_samples].mean(axis=1) - z[negative_samples].mean(axis=1)
    selected = effects.abs().sort_values(ascending=False).head(n_genes)
    return [(gene, float(effects.loc[gene])) for gene in selected.index]


def build_config(monitor: dict[str, Any]) -> dict[str, Any]:
    temporal_offsets = monitor.get("temporal_offsets", {})
    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"{ACCESSION} LAMP-Pharm audit: {monitor['name']}",
            "task": "Audit cardiotoxic drug-response claim vs dose/drug/time shortcuts",
            "role": "LAMP-Pharm public hiPSC-CM cardiotoxicity artifact",
            "source": GEO_RECORD,
            "processed_data_url": PROCESSED_URL,
            "monitor_id": monitor["id"],
            "monitor_description": monitor["description"],
        },
        "columns": {
            "subject_id": "sample_id",
            "label": "label_severe_highdose_tki",
            "positive_value": 1,
            "score": monitor["score"],
            "anchor_time": "anchor_time",
        },
        "temporal_isolation": {
            "anchor": "anchor_time",
            "valid_features_must_be": "expression response features only; drug/dose/time codes are sentinels",
            "frozen_before_holdout": [
                "GSE114686 accession",
                "processed RNA-seq table",
                "sample ID parser",
                "signed cardiotoxic-response panel",
                "drug/dose/time sentinel definitions",
                "LAMP thresholds",
            ],
            "valid_score_features": [
                {"name": feature, "latest_offset_h": temporal_offsets.get(feature, 0)}
                for feature in monitor["features"]
            ],
        },
        "forbidden_features": {
            "columns": [
                "severe_tki_identity",
                "dose_uM",
                "exposure_time_h",
                "high_dose_ge3",
                "combined_drug_dose_shortcut_score",
                "oracle_severe_highdose_tki_score",
                "endpoint_adjacent_marker_score",
            ],
            "allowed_metadata_columns": [
                "severe_tki_identity",
                "dose_uM",
                "exposure_time_h",
                "high_dose_ge3",
            ],
            "valid_score_features": list(monitor["features"]),
        },
        "sentinels": {
            "severe_tki_identity": {
                "column": "severe_tki_identity_shortcut_score",
                "role": "protocol_drug_identity_shortcut",
                "expected_signature": "drug identity should not substitute for response biology",
            },
            "dose": {
                "column": "dose_shortcut_score",
                "role": "protocol_dose_shortcut",
                "expected_signature": "administered dose is experimental structure",
            },
            "exposure_time": {
                "column": "exposure_time_shortcut_score",
                "role": "protocol_time_shortcut",
                "expected_signature": "exposure duration is experimental structure",
            },
            "combined_drug_dose": {
                "column": "combined_drug_dose_shortcut_score",
                "role": "protocol_shortcut",
                "expected_signature": "exact endpoint rule encoded as drug+dose structure",
            },
            "oracle_endpoint": {
                "column": "oracle_severe_highdose_tki_score",
                "role": "oracle_label",
                "expected_signature": "ceiling endpoint comparator",
            },
            "endpoint_adjacent_markers": {
                "column": "endpoint_adjacent_marker_score",
                "role": "oracle_label",
                "expected_signature": "genes selected against endpoint on same table",
            },
        },
        "negative_controls": {"n_permutations": 100, "seed": SEED},
        "visible_state_matching": {
            "columns": ["sample_mean_expression", "detected_gene_count"],
            "n_bins": 4,
            "min_bin_size": 4,
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.02,
            "matched_collapse_max": 0.005,
            "score_thresholds": [-1.0, 0.0, 1.0],
        },
    }


def summary_row(monitor: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    dossier = result["failure_mode_dossier"]
    primary = result["primary_score"]
    return {
        "monitor": monitor["name"],
        "monitor_id": monitor["id"],
        "score": monitor["score"],
        "auc": primary.get("auc"),
        "inverted_auc": primary.get("inverted_auc"),
        "direction_ambiguous": primary.get("direction_ambiguous"),
        "audit_pass": dossier["audit_pass_candidate"],
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "output_classes": ";".join(dossier["output_classes"]),
        "key_warnings": key_warnings(result),
    }


def key_warnings(result: dict[str, Any]) -> str:
    warnings = []
    if result["primary_score"].get("direction_ambiguous"):
        warnings.append("score direction")
    if not result["temporal_isolation"]["passed"]:
        warnings.append("temporal")
    if not result["forbidden_feature_screen"]["passed"]:
        warnings.append("forbidden")
    classes = set(result["failure_mode_dossier"]["output_classes"])
    if "protocol_batch_or_donor_shortcut_sentinel" in classes:
        warnings.append("drug/dose/time sentinel")
    if "oracle_label_leakage_sentinel" in classes:
        warnings.append("oracle sentinel")
    return ", ".join(dict.fromkeys(warnings)) or "none"


def write_report(
    table: pd.DataFrame,
    summary_rows: list[dict[str, Any]],
    endpoint_genes: list[str],
    panel_genes: dict[str, list[str]],
) -> None:
    positives = int(table["label_severe_highdose_tki"].sum())
    drug_counts = table["drug"].value_counts().sort_index().to_dict()
    lines = [
        "# GSE114686 LAMP-Pharm Cardiotoxicity Shortcut Audit",
        "",
        "Public-data LAMP-Pharm artifact asking whether a monitor detects",
        "pharmacological cardiotoxic response biology or experimental structure.",
        "",
        "## Source",
        "",
        f"- GEO accession: `{ACCESSION}`",
        f"- GEO record: {GEO_RECORD}",
        "- Study: hiPSC-derived cardiomyocytes treated with four tyrosine kinase inhibitors and DMSO controls.",
        "- Design used here: 80 processed RNA-seq samples across drug, dose, exposure time, and biological replicate/experiment codes.",
        f"- Endpoint: Sorafenib or Sunitinib at dose >= 3 uM ({positives} positives, {len(table) - positives} controls).",
        f"- Drug counts: {', '.join(f'{key}={value}' for key, value in drug_counts.items())}.",
        "",
        "## LAMP Setup",
        "",
        "- Candidate biology score: stress/apoptosis activation minus cardiac-program expression.",
        "- Drug/dose/time sentinels: severe-TKI identity, administered dose, exposure time, and exact drug-dose endpoint code.",
        "- Oracle sentinels: endpoint label and endpoint-adjacent genes selected on this table.",
        "- Matching variables: sample mean expression and detected gene count.",
        "",
        "## Audit Summary",
        "",
        "| Monitor | AUC | Inverted AUC | Direction? | Audit Pass | Temporal | Forbidden | Matched Delta | Key Warnings | Output Classes |",
        "|---|---:|---:|:---:|:---:|:---:|:---:|---:|---|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['monitor']} | {fmt(row['auc'])} | {fmt(row['inverted_auc'])} | "
            f"{row['direction_ambiguous']} | {row['audit_pass']} | {row['temporal_passed']} | "
            f"{row['forbidden_passed']} | {fmt(row['matched_delta'])} | {row['key_warnings']} | "
            f"`{row['output_classes']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This artifact should not be read as a high-performance cardiotoxicity model.",
            "The signed biology panel is intentionally transparent and modest. The point is",
            "that drug identity and dose structure are stronger than the candidate biology",
            "score, while the exact drug-dose rule and endpoint-selected genes reach oracle",
            "performance. LAMP-Pharm therefore turns a pharmacology claim into the explicit",
            "question: response biology, or experimental structure?",
            "",
            "A serious follow-up should use held-out drugs, held-out doses, held-out batches,",
            "and perturbation-matched controls, ideally in iPSC-CM cardiotoxicity, CiPA/MEA,",
            "LINCS/L1000, or organoid drug-response datasets.",
            "",
            "## Signed Biology Panel",
            "",
            f"- Stress/apoptosis genes present: {', '.join(panel_genes['stress_apoptosis'])}.",
            f"- Cardiac-program genes present: {', '.join(panel_genes['cardiac_program'])}.",
            "",
            "## Endpoint-Adjacent Genes",
            "",
            "These genes were selected against the severe/high-dose TKI endpoint on the same",
            "table and are treated only as oracle/leaky sentinels:",
            "",
        ]
    )
    for item in endpoint_genes:
        lines.append(f"- `{item}`")
    lines.append("")
    (OUT / "gse114686_lamp_pharm_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.3f}"


if __name__ == "__main__":
    raise SystemExit(main())
