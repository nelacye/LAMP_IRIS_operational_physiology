"""Discovery-oriented interpretation layer for LAMP audit results."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml

from .audit import load_csv
from .config import load_audit_config
from .controls import as_float, auc_score, labels_and_scores
from .sentinels import evaluate_sentinel_relations, evaluate_sentinels


MECHANISM_LIBRARY = {
    "future_folding_execution": {
        "mechanism": (
            "The score is close to post-anchor folding/proteostasis state. This "
            "can be an invalid future channel, but the localized feature can also "
            "define a time-lagged biological hypothesis."
        ),
        "experiment": (
            "Run a time-course perturbation with early kinase modulation and "
            "measure folding/proteostasis markers at 15, 30, 60, and 120 minutes."
        ),
    },
    "oracle_label": {
        "mechanism": (
            "The monitor is too close to an endpoint or answer-key channel. Treat "
            "the score as label-adjacent until disjoint evidence is demonstrated."
        ),
        "experiment": (
            "Repeat with endpoint markers hidden during scoring and use a disjoint "
            "readout panel for the biological endpoint."
        ),
    },
    "protocol_shortcut": {
        "mechanism": (
            "The monitor is reading intervention, timing, donor, batch, or run "
            "structure rather than the declared latent biology."
        ),
        "experiment": (
            "Use a balanced factorial plate with protocol, donor, and batch crossed "
            "against the perturbation of interest."
        ),
    },
    "donor_batch_shortcut": {
        "mechanism": (
            "The localized signal may be driven by donor, batch, plate, or run "
            "identity. This is useful as a QC discovery, but not a latent-state "
            "claim by itself."
        ),
        "experiment": (
            "Repeat with donor-held-out and batch-held-out splits, then rebalance "
            "or randomize plate/run assignments."
        ),
    },
}


KINASE_HINTS = {
    "akt": "AKT/mTOR axis",
    "mtor": "AKT/mTOR axis",
    "gsk3": "GSK3/CDK balance",
    "cdk": "GSK3/CDK balance",
    "mapk": "MAPK/ERK axis",
    "erk": "MAPK/ERK axis",
    "stress": "stress-kinase persistence",
    "ampk": "AMPK/stress-energy axis",
}

FOLDING_HINTS = {
    "chaperone": "chaperone buffering",
    "hsp": "chaperone buffering",
    "upr": "unfolded-protein response",
    "autophagy": "autophagy/proteasome axis",
    "aggregate": "aggregate burden",
    "folding": "folding execution",
}


def run_discovery(
    audit_summary_path: Path,
    config_path: Path,
    data_path: Path,
    out_dir: Path,
    contract_path: Path | None = None,
    top_n: int = 12,
) -> dict[str, Any]:
    """Build a discovery dossier from an audit result and its source table."""

    out_dir.mkdir(parents=True, exist_ok=True)
    audit_summary = _load_json(audit_summary_path)
    config_model = load_audit_config(config_path)
    config = config_model.to_runtime_dict()
    rows, table_columns = load_csv(data_path)
    contract = _load_yaml(contract_path) if contract_path else None

    columns = config.get("columns", {}) or {}
    label_col = columns.get("label", "label")
    score_col = columns.get("score", "score")
    positive_value = columns.get("positive_value", 1)

    candidates = feature_candidates(config, table_columns, score_col)
    sentinels = evaluate_sentinels(rows, label_col, positive_value, config)
    relations = evaluate_sentinel_relations(rows, label_col, positive_value, score_col, config)
    failure = infer_failure_type(audit_summary, sentinels, relations)
    localized = localize_features(rows, label_col, positive_value, score_col, candidates, top_n * 3)
    localized = rank_localized_for_failure(localized, failure)[:top_n]
    hypotheses = build_hypotheses(failure, localized, sentinels, relations, contract)
    experiment = design_followup_experiment(failure, hypotheses, contract)

    dossier = {
        "schema_version": "lamp.discovery_dossier/v1",
        "audit_summary_path": str(audit_summary_path),
        "config_path": str(config_path),
        "data_path": str(data_path),
        "contract_path": str(contract_path) if contract_path else None,
        "monitor": {
            "score_column": score_col,
            "label_column": label_col,
            "primary_auc": (audit_summary.get("primary_score", {}) or {}).get("auc"),
            "audit_pass_candidate": (
                audit_summary.get("failure_mode_dossier", {}) or {}
            ).get("audit_pass_candidate"),
        },
        "failure_localization": failure,
        "localized_features": localized,
        "mechanism_hypotheses": hypotheses,
        "experiment_design": experiment,
    }

    json_path = out_dir / "discovery_dossier.json"
    report_path = out_dir / "discovery_report.md"
    json_path.write_text(json.dumps(dossier, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(render_discovery_report(dossier), encoding="utf-8")
    dossier["outputs"] = {"json": str(json_path), "report_md": str(report_path)}
    return dossier


def feature_candidates(
    config: dict[str, Any],
    table_columns: list[str],
    score_col: str,
) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}

    for item in (config.get("temporal_isolation", {}) or {}).get("valid_score_features", []) or []:
        name = item.get("name") if isinstance(item, dict) else str(item)
        if name:
            candidates[name] = {"feature": name, "source": "declared_score_feature"}

    for name, spec in (config.get("sentinels", {}) or {}).items():
        if isinstance(spec, str):
            column = spec
            role = name
        else:
            column = spec.get("column")
            role = spec.get("role", name)
        if column:
            candidates[column] = {
                "feature": column,
                "source": "sentinel",
                "sentinel": name,
                "role": role,
            }

    forbidden = (config.get("forbidden_features", {}) or {}).get("columns", []) or []
    for feature in forbidden:
        if feature:
            candidates.setdefault(
                feature,
                {"feature": feature, "source": "forbidden_feature"},
            )

    for feature in table_columns:
        if feature == score_col or feature in candidates:
            continue
        lowered = feature.lower()
        if any(token in lowered for token in ["kinase", "phospho", "fold", "hsp", "upr", "autophagy", "aggregate"]):
            candidates[feature] = {"feature": feature, "source": "molecular_axis_scan"}

    return list(candidates.values())


def localize_features(
    rows: list[dict[str, Any]],
    label_col: str,
    positive_value: Any,
    score_col: str,
    candidates: list[dict[str, Any]],
    top_n: int,
) -> list[dict[str, Any]]:
    labels, primary_scores = labels_and_scores(rows, label_col, score_col, positive_value)
    localized = []
    for candidate in candidates:
        feature = candidate["feature"]
        if feature not in rows[0]:
            continue
        feature_labels, feature_scores = labels_and_scores(rows, label_col, feature, positive_value)
        feature_auc = auc_score(feature_labels, feature_scores)
        paired_primary = []
        paired_feature = []
        for row in rows:
            primary = as_float(row.get(score_col))
            value = as_float(row.get(feature))
            if primary is None or value is None:
                continue
            paired_primary.append(primary)
            paired_feature.append(value)
        item = {
            **candidate,
            "auc": feature_auc,
            "inverted_auc": None if feature_auc is None else 1.0 - feature_auc,
            "absolute_auc_distance_from_null": (
                None if feature_auc is None else abs(feature_auc - 0.5)
            ),
            "primary_feature_pearson": pearson(paired_primary, paired_feature),
            "axis_hint": axis_hint(feature),
        }
        localized.append(item)

    localized.sort(
        key=lambda item: (
            item.get("absolute_auc_distance_from_null") or 0.0,
            abs(item.get("primary_feature_pearson") or 0.0),
        ),
        reverse=True,
    )
    return localized[:top_n]


def infer_failure_type(
    audit_summary: dict[str, Any],
    sentinels: dict[str, Any],
    relations: dict[str, Any],
) -> dict[str, Any]:
    dossier = audit_summary.get("failure_mode_dossier", {}) or {}
    classes = set(dossier.get("output_classes", []) or [])
    forbidden = audit_summary.get("forbidden_feature_screen", {}) or {}
    temporal = audit_summary.get("temporal_isolation", {}) or {}

    audit_pass = bool(dossier.get("audit_pass_candidate"))
    violations = forbidden.get("valid_score_feature_violations", []) or []
    violation_text = " ".join(str(value).lower() for value in violations)

    if audit_pass:
        failure_type = "audit_pass_discovery"
    elif not temporal.get("passed") and any(
        "future" in str(item.get("role", "")).lower() for item in sentinels.values()
    ):
        failure_type = "future_folding"
    elif not forbidden.get("passed"):
        if any(
            token in violation_text
            for token in ["protocol", "stressor", "dose", "day", "batch", "donor"]
        ):
            failure_type = "protocol_shortcut"
        elif any(token in violation_text for token in ["oracle", "label", "endpoint"]):
            failure_type = "oracle_or_endpoint_adjacent"
        else:
            failure_type = "forbidden_feature"
    elif "oracle_leakage_proximity_shift" in classes:
        failure_type = "oracle_or_endpoint_adjacent"
    elif "visible_state_confounding" in classes:
        failure_type = "visible_state_shortcut"
    elif dossier.get("audit_pass_candidate"):
        failure_type = "audit_pass_discovery"
    else:
        failure_type = "unresolved_failure"

    evidence = []
    for name, relation in relations.items():
        role = str(relation.get("role", name))
        sentinel_auc = relation.get("sentinel_auc")
        if sentinel_auc is None:
            continue
        if abs(float(sentinel_auc) - 0.5) >= 0.10:
            evidence.append(
                {
                    "sentinel": name,
                    "role": role,
                    "sentinel_auc": sentinel_auc,
                    "sentinel_minus_primary_auc": relation.get("sentinel_minus_primary_auc"),
                    "primary_sentinel_spearman": relation.get("primary_sentinel_spearman"),
                }
            )
    evidence.sort(key=lambda item: abs(float(item["sentinel_auc"]) - 0.5), reverse=True)
    return {
        "failure_type": failure_type,
        "output_classes": sorted(classes),
        "temporal_passed": temporal.get("passed"),
        "forbidden_passed": forbidden.get("passed"),
        "valid_score_feature_violations": forbidden.get("valid_score_feature_violations", []) or [],
        "sentinel_evidence": evidence[:6],
    }


def rank_localized_for_failure(
    localized: list[dict[str, Any]],
    failure: dict[str, Any],
) -> list[dict[str, Any]]:
    failure_type = failure.get("failure_type")
    violations = set(failure.get("valid_score_feature_violations", []) or [])

    def relevance(item: dict[str, Any]) -> float:
        feature = str(item.get("feature", "")).lower()
        role = str(item.get("role", "")).lower()
        source = str(item.get("source", "")).lower()
        axis = str(item.get("axis_hint", "")).lower()
        base = abs(float(item.get("primary_feature_pearson") or 0.0))
        auc_signal = float(item.get("absolute_auc_distance_from_null") or 0.0)
        score = 2.0 * base + auc_signal

        if item.get("feature") in violations:
            score += 100.0
        if failure_type == "audit_pass_discovery":
            if source == "declared_score_feature" or "early" in feature:
                score += 50.0
            if any(token in feature or token in role for token in ["oracle", "label", "future"]):
                score -= 80.0
        elif failure_type == "protocol_shortcut":
            if any(
                token in feature or token in role or token in axis
                for token in ["protocol", "stressor", "dose", "day", "batch", "donor", "run"]
            ):
                score += 60.0
            if any(token in feature or token in role for token in ["oracle", "label"]):
                score -= 50.0
        elif failure_type == "future_folding":
            if any(token in role or token in feature for token in ["future", "folding", "aggregate"]):
                score += 60.0
            if any(token in feature or token in role for token in ["oracle", "label"]):
                score -= 35.0
            if any(token in axis for token in ["mapk", "akt", "gsk", "stress", "autophagy", "chaperone", "upr"]):
                score += 20.0
        elif failure_type == "oracle_or_endpoint_adjacent":
            if any(token in feature or token in role for token in ["oracle", "label", "endpoint"]):
                score += 60.0
        return score

    return sorted(localized, key=relevance, reverse=True)


def build_hypotheses(
    failure: dict[str, Any],
    localized: list[dict[str, Any]],
    sentinels: dict[str, Any],
    relations: dict[str, Any],
    contract: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    failure_type = failure["failure_type"]
    top = localized[:8]
    hypotheses = []

    if failure_type == "future_folding":
        feature = first_future_feature(top) or first_axis(top, "folding") or (top[0] if top else {})
        kinase = first_axis(top, "kinase")
        hypotheses.append(
            {
                "title": "Time-lagged kinase-to-folding coupling",
                "confidence": "hypothesis_generating",
                "localized_features": compact_features([item for item in [kinase, feature] if item]),
                "mechanism": (
                    "The monitor is invalid as an early predictor because it uses "
                    "post-anchor folding state, but the same localized channel can "
                    "suggest a causal time-lag: early kinase dynamics may precede "
                    "later proteostasis/folding execution."
                ),
                "testable_prediction": (
                    "Modulating the localized kinase axis should alter the localized "
                    "folding/proteostasis readout at later 15/30/60/120 minute windows."
                ),
            }
        )
    elif failure_type == "protocol_shortcut":
        hypotheses.append(
            {
                "title": "Protocol-conditioned biology rather than latent-state inference",
                "confidence": "actionable_qc",
                "localized_features": compact_features(top),
                "mechanism": (
                    "The monitor reads protocol or stressor assignment. The shortcut "
                    "may still be biologically informative, but it cannot support the "
                    "declared hidden-state claim without a balanced perturbation design."
                ),
                "testable_prediction": (
                    "After crossing protocol arms across donors and batches, the shortcut "
                    "score should collapse while a genuine molecular-code signal remains."
                ),
            }
        )
    elif failure_type == "oracle_or_endpoint_adjacent":
        hypotheses.append(
            {
                "title": "Endpoint-adjacent channel masquerading as early signal",
                "confidence": "audit_failure",
                "localized_features": compact_features(top),
                "mechanism": (
                    "The score is near an endpoint label or endpoint-marker sentinel. "
                    "This is not discovery until endpoint features are excluded from "
                    "the monitor and used only as held-out readouts."
                ),
                "testable_prediction": (
                    "A disjoint early panel should lose the endpoint-level AUC but keep "
                    "some matched-state signal if the biology is real."
                ),
            }
        )
    elif failure_type == "audit_pass_discovery":
        hypotheses.append(
            {
                "title": "Candidate latent-state signal",
                "confidence": "requires_prospective_test",
                "localized_features": compact_features(top),
                "mechanism": (
                    "The monitor survived the configured failure-mode tests. The top "
                    "localized features are candidates for prospective perturbation."
                ),
                "testable_prediction": (
                    "Perturbing the localized kinase/proteostasis axis should shift "
                    "the held-out folding endpoint without relying on protocol labels."
                ),
            }
        )
    else:
        hypotheses.append(
            {
                "title": "Unresolved information-contract failure",
                "confidence": "low",
                "localized_features": compact_features(top),
                "mechanism": "The audit failed, but the current localization is insufficient.",
                "testable_prediction": "Add richer sentinels and group-held-out splits.",
            }
        )

    hypotheses.extend(generic_hypotheses_from_sentinels(sentinels, relations))
    return hypotheses[:4]


def first_future_feature(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in items:
        role = str(item.get("role", "")).lower()
        feature = str(item.get("feature", "")).lower()
        if "future" in role or "future" in feature or "aggregate" in feature:
            return item
    return None


def design_followup_experiment(
    failure: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    contract: dict[str, Any] | None,
) -> dict[str, Any]:
    primary = hypotheses[0] if hypotheses else {}
    failure_type = failure["failure_type"]
    if failure_type in {"future_folding", "audit_pass_discovery"}:
        perturbations = ["AKT/mTOR inhibitor", "GSK3/CDK modulation", "HSP90 chaperone modulation", "vehicle control"]
        readouts = ["phospho-kinase panel", "HSP90/HSPA5 chaperone panel", "UPR/autophagy panel", "aggregate/folding endpoint panel"]
    elif failure_type == "protocol_shortcut":
        perturbations = ["protocol arm A", "protocol arm B", "stressor low", "stressor high"]
        readouts = ["declared early kinase/proteostasis panel", "held-out folding endpoint panel", "batch/donor sentinel panel"]
    else:
        perturbations = ["clean early-panel score", "endpoint-hidden score", "vehicle control"]
        readouts = ["disjoint early probe panel", "held-out endpoint panel"]

    return {
        "goal": primary.get("testable_prediction", "Prospectively test the localized signal."),
        "format": "96-well balanced time-course sketch",
        "timepoints_min": [0, 15, 30, 60, 120],
        "perturbations": perturbations,
        "readouts": readouts,
        "controls": [
            "vehicle controls in every plate quadrant",
            "donor-balanced wells",
            "batch/run randomized acquisition order",
            "endpoint markers hidden from monitor scoring",
        ],
        "opentrons_sketch": {
            "plate": "96-well flat-bottom plate",
            "replicates_per_condition": 4,
            "liquid_classes": ["vehicle", "kinase_modulator", "stressor", "lysis_or_fixation_buffer"],
            "notes": (
                "This is a design sketch, not a wet-lab protocol. Volumes, cell "
                "density, compound identity, and biosafety constraints must be set "
                "by the experimental team."
            ),
        },
    }


def render_discovery_report(dossier: dict[str, Any]) -> str:
    monitor = dossier["monitor"]
    failure = dossier["failure_localization"]
    lines = [
        "# LAMP Discovery Dossier",
        "",
        "This report turns a LAMP audit result into discovery-oriented hypotheses.",
        "It does not convert an audit failure into validation; it converts the",
        "failure into localized, testable next experiments.",
        "",
        "## Monitor",
        "",
        f"- Score column: `{monitor['score_column']}`",
        f"- Primary AUC: {fmt(monitor.get('primary_auc'))}",
        f"- Audit pass candidate: `{monitor.get('audit_pass_candidate')}`",
        "",
        "## Failure Localization",
        "",
        f"- Failure type: `{failure['failure_type']}`",
        f"- Temporal passed: `{failure.get('temporal_passed')}`",
        f"- Forbidden passed: `{failure.get('forbidden_passed')}`",
        f"- Valid score feature violations: `{failure.get('valid_score_feature_violations')}`",
        "",
        "## Top Localized Features",
        "",
        "| Feature | Source | Role/Axis | AUC | Inverted AUC | Corr(score) |",
        "|---|---|---|---:|---:|---:|",
    ]
    for item in dossier["localized_features"][:10]:
        role = item.get("role") or item.get("axis_hint") or ""
        lines.append(
            f"| `{item['feature']}` | {item.get('source')} | {role} | "
            f"{fmt(item.get('auc'))} | {fmt(item.get('inverted_auc'))} | "
            f"{fmt(item.get('primary_feature_pearson'))} |"
        )

    lines.extend(["", "## Mechanism Hypotheses", ""])
    for idx, hypothesis in enumerate(dossier["mechanism_hypotheses"], start=1):
        lines.extend(
            [
                f"### H{idx}. {hypothesis['title']}",
                "",
                f"- Confidence: `{hypothesis['confidence']}`",
                f"- Localized features: `{hypothesis.get('localized_features', [])}`",
                f"- Mechanism: {hypothesis['mechanism']}",
                f"- Testable prediction: {hypothesis['testable_prediction']}",
                "",
            ]
        )

    experiment = dossier["experiment_design"]
    lines.extend(
        [
            "## Follow-Up Experiment Sketch",
            "",
            f"- Goal: {experiment['goal']}",
            f"- Format: {experiment['format']}",
            f"- Timepoints (min): `{experiment['timepoints_min']}`",
            f"- Perturbations: `{experiment['perturbations']}`",
            f"- Readouts: `{experiment['readouts']}`",
            f"- Controls: `{experiment['controls']}`",
            "",
            "### Opentrons-Oriented Sketch",
            "",
            f"- Plate: {experiment['opentrons_sketch']['plate']}",
            f"- Replicates per condition: {experiment['opentrons_sketch']['replicates_per_condition']}",
            f"- Liquid classes: `{experiment['opentrons_sketch']['liquid_classes']}`",
            f"- Note: {experiment['opentrons_sketch']['notes']}",
            "",
        ]
    )
    return "\n".join(lines)


def generic_hypotheses_from_sentinels(
    sentinels: dict[str, Any],
    relations: dict[str, Any],
) -> list[dict[str, Any]]:
    hypotheses = []
    for name, item in sentinels.items():
        role = str(item.get("role", name)).lower()
        auc = item.get("auc")
        if auc is None or abs(float(auc) - 0.5) < 0.15:
            continue
        key = "future_folding_execution" if "future" in role else role
        library_item = next(
            (value for token, value in MECHANISM_LIBRARY.items() if token in key),
            None,
        )
        if not library_item:
            continue
        hypotheses.append(
            {
                "title": f"Sentinel-driven hypothesis: {name}",
                "confidence": "sentinel_supported",
                "localized_features": [{"feature": item.get("column"), "auc": auc, "role": role}],
                "mechanism": library_item["mechanism"],
                "testable_prediction": library_item["experiment"],
            }
        )
    return hypotheses


def first_axis(items: list[dict[str, Any]], axis_token: str) -> dict[str, Any] | None:
    for item in items:
        hint = str(item.get("axis_hint", "")).lower()
        if axis_token in hint or (
            axis_token == "kinase"
            and any(token in hint for token in ["mapk", "akt", "gsk", "cdk", "stress-kinase"])
        ):
            return item
    for item in items:
        feature = item["feature"].lower()
        if (axis_token in feature or (axis_token == "kinase" and "phospho" in feature)) and not feature.endswith("_score"):
            return item
    for item in items:
        if axis_token in item["feature"].lower():
            return item
    return None


def compact_features(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for item in items:
        compact.append(
            {
                "feature": item.get("feature"),
                "auc": item.get("auc"),
                "axis_hint": item.get("axis_hint"),
                "source": item.get("source"),
            }
        )
    return compact


def axis_hint(feature: str) -> str | None:
    lowered = feature.lower()
    for token, hint in KINASE_HINTS.items():
        if token in lowered:
            return hint
    for token, hint in FOLDING_HINTS.items():
        if token in lowered:
            return hint
    if any(token in lowered for token in ["protocol", "dose", "day", "batch", "donor", "run", "stressor"]):
        return "protocol/batch structure"
    return None


def pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    num = sum((x - mean_left) * (y - mean_right) for x, y in zip(left, right))
    den_left = sum((x - mean_left) ** 2 for x in left) ** 0.5
    den_right = sum((y - mean_right) ** 2 for y in right) ** 0.5
    if den_left == 0 or den_right == 0:
        return None
    return float(num / (den_left * den_right))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else None


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)
