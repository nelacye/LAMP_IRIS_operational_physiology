#!/usr/bin/env python3
"""Build discovery dossiers for the synthetic iPSC molecular-code battery."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.discovery import run_discovery  # noqa: E402


BASE = ROOT / "results" / "ipsc_molecular_code" / "synthetic_kinase_folding"
CONTRACT = ROOT / "configs" / "ipsc_molecular_code_contract.yaml"
DATA = BASE / "synthetic_ipsc_molecular_code_predictions.csv"
MONITORS = [
    "clean_hybrid_kinase_folding",
    "protocol_stressor_shortcut",
    "future_folding_leakage",
    "lowdose_oracle_mix_005",
]


def main() -> int:
    rows = []
    for monitor_id in MONITORS:
        config = BASE / "configs" / f"{monitor_id}.yaml"
        audit_summary = BASE / "lamp" / monitor_id / "audit_summary.json"
        out_dir = BASE / "discovery" / monitor_id
        dossier = run_discovery(
            audit_summary_path=audit_summary,
            config_path=config,
            data_path=DATA,
            out_dir=out_dir,
            contract_path=CONTRACT,
            top_n=12,
        )
        rows.append(summary_row(monitor_id, dossier))

    write_csv(BASE / "synthetic_ipsc_molecular_code_discovery_summary.csv", rows)
    write_summary_report(rows)
    print(BASE / "synthetic_ipsc_molecular_code_discovery_report.md")
    return 0


def summary_row(monitor_id: str, dossier: dict[str, Any]) -> dict[str, Any]:
    failure = dossier["failure_localization"]
    hypothesis = (dossier.get("mechanism_hypotheses") or [{}])[0]
    top_feature = (dossier.get("localized_features") or [{}])[0]
    return {
        "monitor_id": monitor_id,
        "primary_auc": dossier["monitor"].get("primary_auc"),
        "audit_pass": dossier["monitor"].get("audit_pass_candidate"),
        "failure_type": failure.get("failure_type"),
        "top_feature": top_feature.get("feature"),
        "top_feature_auc": top_feature.get("auc"),
        "top_feature_axis": top_feature.get("axis_hint") or top_feature.get("role"),
        "hypothesis": hypothesis.get("title"),
        "testable_prediction": hypothesis.get("testable_prediction"),
    }


def write_summary_report(rows: list[dict[str, Any]]) -> None:
    lines = [
        "# iPSC Molecular-Code Discovery Summary",
        "",
        "This report is the first LAMP-Discovery emulator artifact. It treats audit",
        "outcomes as entry points for localized hypotheses and prospective experiment",
        "design, not only PASS/FAIL labels.",
        "",
        "| Monitor | AUC | Audit Pass | Discovery Class | Top Localized Feature | Hypothesis |",
        "|---|---:|:---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['monitor_id']}` | {fmt(row['primary_auc'])} | "
            f"{row['audit_pass']} | `{row['failure_type']}` | "
            f"`{row['top_feature']}` ({fmt(row['top_feature_auc'])}) | "
            f"{row['hypothesis']} |"
        )
    lines.extend(
        [
            "",
            "## What Changed",
            "",
            "The audit layer says whether the declared information contract survived.",
            "The discovery layer asks what the failure is made of: the suspected",
            "feature/channel, the biological mechanism hypothesis, and a concrete",
            "time-course plate sketch for the next experiment.",
            "",
            "The important design constraint remains intact: a leakage channel does not",
            "become validation. It becomes a hypothesis only after being moved out of",
            "the monitor and into a prospective perturbation/readout design.",
            "",
        ]
    )
    (BASE / "synthetic_ipsc_molecular_code_discovery_report.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
