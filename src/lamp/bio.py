"""Biological interpretation contracts for LAMP-Bio."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_bio_contract(path: Path) -> dict[str, Any]:
    """Load a LAMP-Bio biological contract YAML file."""

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("LAMP-Bio contract must be a YAML mapping")
    if data.get("schema_version") != "lamp.bio_contract/v1":
        raise ValueError("Unsupported LAMP-Bio contract schema")
    return data


def load_audit_summary(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def diagnose_biological_claim(
    audit_summary: dict[str, Any],
    contract: dict[str, Any],
    claim_id: str,
    score_axis: str,
    stability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a LAMP audit result into a biological diagnosis level.

    The diagnosis is intentionally separate from the raw LAMP PASS/FAIL state.
    For example, a score can be an audit-pass candidate while still receiving a
    protocol-sentinel-dominance warning or a fragile-stability diagnosis.
    """

    stability = stability or {}
    claim = _claim(contract, claim_id)
    thresholds = (contract.get("diagnosis_rules", {}) or {}).get("thresholds", {}) or {}
    primary = audit_summary.get("primary_score", {}) or {}
    dossier = audit_summary.get("failure_mode_dossier", {}) or {}
    classes = set(dossier.get("output_classes", []) or [])
    temporal = audit_summary.get("temporal_isolation", {}) or {}
    forbidden = audit_summary.get("forbidden_feature_screen", {}) or {}
    sentinels = audit_summary.get("sentinels", {}) or {}
    sentinel_relations = audit_summary.get("sentinel_relations", {}) or {}

    audit_pass = bool(dossier.get("audit_pass_candidate"))
    primary_auc = _as_float(primary.get("auc"))
    allowed_axes = set(claim.get("allowed_probe_axes", []) or [])
    endpoint_axis = str(claim.get("endpoint_axis", ""))
    flags: list[str] = []
    warnings: list[str] = []

    if score_axis == endpoint_axis:
        flags.append("endpoint_axis_reused_as_score_axis")
    if score_axis not in allowed_axes:
        flags.append("score_axis_not_declared_as_allowed_probe")

    protocol_dominance = _protocol_sentinel_dominance(
        primary_auc,
        sentinels,
        sentinel_relations,
        float(thresholds.get("protocol_sentinel_dominance_auc_gap", 0.0)),
    )
    if protocol_dominance:
        warnings.append("protocol_sentinel_dominance_present")

    if _has_oracle_sentinel(sentinels):
        warnings.append("oracle_sentinel_present")
    if primary.get("direction_ambiguous"):
        flags.append("score_direction_ambiguous")
    if stability.get("donor_heldout_status") == "not_evaluable":
        warnings.append("donor_heldout_not_evaluable")
    if stability.get("protocol_heldout_status") == "not_evaluable":
        warnings.append("protocol_heldout_not_evaluable")

    stability_status = _stability_status(stability, thresholds)
    if stability_status:
        warnings.extend(stability_status["warnings"])

    if not temporal.get("passed"):
        diagnosis = "endpoint_adjacent_contamination"
        flags.append("temporal_isolation_failed")
    elif not forbidden.get("passed"):
        if _valid_feature_uses_oracle_or_endpoint(forbidden):
            diagnosis = "endpoint_adjacent_contamination"
            flags.append("endpoint_or_oracle_feature_used_by_score")
        else:
            diagnosis = "protocol_confounded_signal"
            flags.append("forbidden_protocol_feature_used_by_score")
    elif flags and "score_axis_not_declared_as_allowed_probe" in flags:
        diagnosis = "not_biologically_interpretable"
    elif audit_pass:
        if _stable_enough(stability_status, protocol_dominance):
            diagnosis = "valid_biological_signal_stable"
        else:
            diagnosis = "valid_biological_signal_fragile"
    elif primary_auc is not None and primary_auc >= 0.60:
        diagnosis = "protocol_confounded_signal" if protocol_dominance else "not_biologically_interpretable"
    else:
        diagnosis = "not_biologically_interpretable"

    return {
        "schema_version": "lamp.bio_diagnosis/v1",
        "claim_id": claim_id,
        "claim": claim.get("claim"),
        "endpoint_axis": endpoint_axis,
        "score_axis": score_axis,
        "allowed_probe_axes": sorted(allowed_axes),
        "diagnosis": diagnosis,
        "audit_pass_candidate": audit_pass,
        "primary_auc": primary_auc,
        "output_classes": sorted(classes),
        "flags": sorted(set(flags)),
        "warnings": sorted(set(warnings)),
        "protocol_sentinel_dominance": protocol_dominance,
        "stability": stability,
        "interpretation": _interpretation(diagnosis, flags, warnings),
    }


def _claim(contract: dict[str, Any], claim_id: str) -> dict[str, Any]:
    claims = contract.get("claim_contracts", {}) or {}
    if claim_id not in claims:
        raise KeyError(f"Unknown biological claim contract: {claim_id}")
    return claims[claim_id] or {}


def _protocol_sentinel_dominance(
    primary_auc: float | None,
    sentinels: dict[str, Any],
    sentinel_relations: dict[str, Any],
    dominance_gap: float,
) -> bool:
    if primary_auc is None:
        return False
    for name, item in sentinels.items():
        role = str(item.get("role", name)).lower()
        if not _is_protocol_role(role):
            continue
        sentinel_auc = _as_float(item.get("auc"))
        if sentinel_auc is not None and sentinel_auc >= primary_auc + dominance_gap:
            return True
    for name, item in sentinel_relations.items():
        role = str(item.get("role", name)).lower()
        if not _is_protocol_role(role):
            continue
        sentinel_auc = _as_float(item.get("sentinel_auc"))
        if sentinel_auc is not None and sentinel_auc >= primary_auc + dominance_gap:
            return True
    return False


def _is_protocol_role(role: str) -> bool:
    return any(
        token in role
        for token in ["protocol", "batch", "donor", "timepoint", "dose", "drug", "intervention"]
    )


def _has_oracle_sentinel(sentinels: dict[str, Any]) -> bool:
    for name, item in sentinels.items():
        role = str(item.get("role", name)).lower()
        if "oracle" in role or "oracle" in name.lower():
            return True
    return False


def _valid_feature_uses_oracle_or_endpoint(forbidden: dict[str, Any]) -> bool:
    for item in forbidden.get("valid_score_feature_violations", []) or []:
        text = str(item).lower()
        if "oracle" in text or "endpoint" in text or "label" in text:
            return True
    return False


def _stability_status(
    stability: dict[str, Any],
    thresholds: dict[str, Any],
) -> dict[str, Any] | None:
    if not stability:
        return None
    warnings = []
    bootstrap = _as_float(stability.get("bootstrap_pass_rate"))
    alt_panel = _as_float(stability.get("alternative_panel_pass_rate"))
    leave_group = _as_float(stability.get("leave_group_out_pass_rate"))
    threshold_grid = _as_float(stability.get("threshold_grid_pass_rate"))

    if bootstrap is not None and bootstrap < float(
        thresholds.get("stable_bootstrap_pass_rate_min", 0.90)
    ):
        warnings.append("bootstrap_pass_rate_below_stable_threshold")
    if alt_panel is not None and alt_panel < float(
        thresholds.get("stable_alt_panel_pass_rate_min", 0.80)
    ):
        warnings.append("alternative_panel_pass_rate_below_stable_threshold")
    if leave_group is not None and leave_group < float(
        thresholds.get("stable_leave_group_pass_rate_min", 0.90)
    ):
        warnings.append("leave_group_out_pass_rate_below_stable_threshold")
    if threshold_grid is not None and threshold_grid < 1.0:
        warnings.append("threshold_grid_not_fully_stable")

    return {
        "bootstrap_pass_rate": bootstrap,
        "alternative_panel_pass_rate": alt_panel,
        "leave_group_out_pass_rate": leave_group,
        "threshold_grid_pass_rate": threshold_grid,
        "warnings": warnings,
    }


def _stable_enough(
    stability_status: dict[str, Any] | None,
    protocol_dominance: bool,
) -> bool:
    if protocol_dominance:
        return False
    if stability_status is None:
        return False
    return not stability_status["warnings"]


def _interpretation(
    diagnosis: str,
    flags: list[str],
    warnings: list[str],
) -> str:
    if diagnosis == "valid_biological_signal_stable":
        return "The claim has a disjoint biological signal with stable audit support."
    if diagnosis == "valid_biological_signal_fragile":
        return (
            "The claim has a plausible disjoint biological signal, but robustness "
            "or sentinel-dominance warnings limit interpretation."
        )
    if diagnosis == "protocol_confounded_signal":
        return "The signal is not cleanly separable from protocol or intervention structure."
    if diagnosis == "endpoint_adjacent_contamination":
        return "The score violates endpoint, oracle, or temporal isolation."
    if flags or warnings:
        return "The numerical result is not sufficient for biological interpretation."
    return "No interpretable biological signal was established."


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
