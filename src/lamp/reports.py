"""Report writers for LAMP audit outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_outputs(result: dict[str, Any], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "audit_summary.json"
    report_path = out_dir / "audit_report.md"
    outputs = {
        "summary_json": str(summary_path),
        "report_md": str(report_path),
    }
    result["outputs"] = outputs

    summary_path.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    report_path.write_text(render_markdown(result), encoding="utf-8")
    return outputs


def render_markdown(result: dict[str, Any]) -> str:
    dataset = result.get("dataset", {})
    primary = result.get("primary_score", {})
    classes = result.get("failure_mode_dossier", {}).get("output_classes", [])
    audit_pass = result.get("failure_mode_dossier", {}).get("audit_pass_candidate")

    lines = [
        f"# LAMP audit report: {dataset.get('name', 'unnamed dataset')}",
        "",
        "## Executive summary",
        "",
        f"- Primary score: `{primary.get('column')}`",
        f"- Primary AUC: {_fmt(primary.get('auc'))}",
        f"- Audit-pass candidate: `{audit_pass}`",
        f"- Output classes: {', '.join(f'`{item}`' for item in classes) if classes else '`none`'}",
        "",
        "Passing LAMP does not establish clinical validity. It means the score survived",
        "the configured failure-mode audit and earned prospective testing.",
        "",
        "## Temporal isolation",
        "",
    ]

    temporal = result.get("temporal_isolation", {})
    lines.extend(
        [
            f"- Declared: `{temporal.get('declared')}`",
            f"- Passed: `{temporal.get('passed')}`",
            f"- Anchor: `{temporal.get('anchor')}`",
            f"- Frozen before holdout: {', '.join(f'`{x}`' for x in temporal.get('frozen_before_holdout', [])) or '`none declared`'}",
            "",
        ]
    )
    if temporal.get("violations"):
        lines.append("Temporal violations:")
        for violation in temporal["violations"]:
            lines.append(
                f"- `{violation.get('name')}` latest_offset_h={violation.get('latest_offset_h')}"
            )
        lines.append("")

    forbidden = result.get("forbidden_feature_screen", {})
    lines.extend(
        [
            "## Forbidden-feature screen",
            "",
            f"- Passed: `{forbidden.get('passed')}`",
            f"- Declared sentinels present: {_join_code(forbidden.get('declared_sentinel_columns_present'))}",
            f"- Unexpected forbidden columns: {_join_code(forbidden.get('unexpected_forbidden_columns_present'))}",
            f"- Valid-score feature violations: {_join_code(forbidden.get('valid_score_feature_violations'))}",
            "",
        ]
    )

    lines.extend(["## Negative controls", ""])
    controls = result.get("negative_controls", {})
    for key in [
        "noise_auc_mean",
        "score_permutation_auc_mean",
        "label_permutation_auc_mean",
    ]:
        lines.append(f"- {key}: {_fmt(controls.get(key))}")
    lines.append("")

    lines.extend(["## Sentinels", ""])
    sentinels = result.get("sentinels", {})
    if not sentinels:
        lines.append("No sentinels configured.")
    for name, item in sentinels.items():
        lines.append(
            f"- `{name}` ({item.get('role')}): column `{item.get('column')}`, AUC {_fmt(item.get('auc'))}, expected `{item.get('expected_signature')}`"
        )
    lines.append("")

    relations = result.get("sentinel_relations", {})
    if relations:
        lines.extend(["## Sentinel relations", ""])
        for name, item in relations.items():
            lines.append(
                f"- `{name}`: gap {_fmt(item.get('sentinel_minus_primary_auc'))}, proximity {_fmt(item.get('auc_leakage_proximity'))}, Pearson {_fmt(item.get('primary_sentinel_pearson'))}, alert `{item.get('oracle_proximity_alert')}`"
            )
        lines.append("")

    match = result.get("visible_state_matching", {})
    lines.extend(
        [
            "## Visible-state matching",
            "",
            f"- Evaluated: `{match.get('evaluated')}`",
            f"- Matched observed-state delta: {_fmt(match.get('matched_observed_state_delta'))}",
            f"- Matched rows: `{match.get('matched_rows')}`",
            f"- Matched strata: `{match.get('matched_strata')}`",
            "",
        ]
    )

    early = result.get("early_window_sensitivity", {})
    lines.extend(["## Early-window sensitivity", ""])
    lines.append(f"- Evaluated: `{early.get('evaluated')}`")
    for row in early.get("score_columns", []):
        lines.append(
            f"- `{row.get('column')}`: evaluated `{row.get('evaluated')}`, AUC {_fmt(row.get('auc'))}"
        )
    lines.append("")

    lines.extend(["## Threshold sensitivity", ""])
    threshold = result.get("threshold_sensitivity", {})
    lines.append(f"- Fragile: `{threshold.get('fragile')}`")
    for row in threshold.get("thresholds", []):
        lines.append(
            f"- threshold {_fmt(row.get('threshold'))}: selected {_fmt(row.get('selected_fraction'))}, enrichment {_fmt(row.get('enrichment_over_baseline'))}"
        )
    lines.append("")

    lines.extend(
        [
            "## Interpretation boundary",
            "",
            "LAMP is a failure-mode audit, not a substitute for prospective clinical",
            "validation, deployment monitoring, safety review, or causal proof. A surviving",
            "score should be described as an audit-pass candidate for prospective testing.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "`NA`"
    if isinstance(value, float):
        return f"`{value:.4f}`"
    return f"`{value}`"


def _join_code(values: list[Any] | None) -> str:
    if not values:
        return "`none`"
    return ", ".join(f"`{value}`" for value in values)
