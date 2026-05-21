"""Top-level LAMP audit orchestration."""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AuditConfig, load_audit_config
from .controls import (
    auc_score,
    forbidden_feature_screen,
    labels_and_scores,
    negative_controls,
    temporal_isolation_check,
    threshold_sensitivity,
)
from .matching import matched_cohort_delta
from .reports import write_outputs
from .sentinels import (
    declared_sentinel_columns,
    evaluate_sentinel_relations,
    evaluate_sentinels,
)

LOGGER = logging.getLogger(__name__)


class LAMP_Audit:
    """Executable LAMP failure-mode audit.

    The class keeps each audit component as a named method so the protocol is
    inspectable, testable, and reusable outside the CLI.
    """

    def __init__(
        self,
        config: AuditConfig | dict[str, Any],
        rows: list[dict[str, str]],
        table_columns: list[str],
        config_path: Path | None = None,
        input_path: Path | None = None,
    ) -> None:
        self.config_model = (
            config if isinstance(config, AuditConfig) else AuditConfig.model_validate(config)
        )
        self.config = self.config_model.to_runtime_dict()
        self.rows = rows
        self.table_columns = table_columns
        self.config_path = config_path
        self.input_path = input_path

        columns = self.config.get("columns", {}) or {}
        self.label_col = columns.get("label", "label")
        self.score_col = columns.get("score", "score")
        self.subject_col = columns.get("subject_id", columns.get("id", "subject_id"))
        self.positive_value = columns.get("positive_value", 1)

    @classmethod
    def from_files(cls, config_path: Path, input_path: Path) -> "LAMP_Audit":
        config = load_audit_config(config_path)
        rows, table_columns = load_csv(input_path)
        return cls(
            config=config,
            rows=rows,
            table_columns=table_columns,
            config_path=config_path,
            input_path=input_path,
        )

    def run(self, out_dir: Path | None = None) -> dict[str, Any]:
        LOGGER.info("Starting LAMP audit")
        self.validate_required_columns()
        labels, scores = self.labels_and_scores()

        primary = self.evaluate_primary_score(labels, scores)
        temporal = self.evaluate_temporal_isolation()
        forbidden = self.evaluate_forbidden_features()
        controls = self.evaluate_negative_controls(labels, scores)
        match = self.evaluate_matched_observed_state_cohorts()
        sentinels = self.evaluate_leaky_sentinel_predictors()
        sentinel_relations = self.evaluate_sentinel_geometry()
        early_windows = self.evaluate_early_window_sensitivity()
        thresh = self.evaluate_threshold_robustness(labels, scores)
        dossier = self.build_failure_mode_dossier(
            primary=primary,
            forbidden=forbidden,
            temporal=temporal,
            controls=controls,
            match=match,
            sentinels=sentinels,
            sentinel_relations=sentinel_relations,
            threshold_sensitivity_result=thresh,
        )

        input_path = self.input_path or Path("<in-memory>")
        result = {
            "schema_version": "lamp.audit_summary/v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset": self.config.get("dataset", {"name": input_path.stem}),
            "input": {
                "config_path": str(self.config_path) if self.config_path else None,
                "input_path": str(self.input_path) if self.input_path else None,
                "n_rows": len(self.rows),
                "n_subjects": _n_subjects(self.rows, self.subject_col),
                "columns": sorted(self.table_columns),
            },
            "primary_score": primary,
            "temporal_isolation": temporal,
            "forbidden_feature_screen": forbidden,
            "negative_controls": controls,
            "sentinels": sentinels,
            "sentinel_relations": sentinel_relations,
            "visible_state_matching": match,
            "early_window_sensitivity": early_windows,
            "threshold_sensitivity": thresh,
            "failure_mode_dossier": dossier,
        }

        if out_dir is not None:
            result["outputs"] = write_outputs(result, out_dir)
        LOGGER.info("Finished LAMP audit")
        return result

    def validate_required_columns(self) -> None:
        required = [self.label_col, self.score_col]
        missing = [col for col in required if col not in self.table_columns]
        if missing:
            raise ValueError(f"Input table is missing required columns: {missing}")

    def labels_and_scores(self) -> tuple[list[int], list[float]]:
        return labels_and_scores(
            self.rows,
            self.label_col,
            self.score_col,
            self.positive_value,
        )

    def evaluate_primary_score(
        self,
        labels: list[int],
        scores: list[float],
    ) -> dict[str, Any]:
        primary_auc = auc_score(labels, scores)
        return {
            "column": self.score_col,
            "auc": primary_auc,
            "n": len(labels),
            "n_positive": sum(labels),
            "n_negative": len(labels) - sum(labels),
        }

    def evaluate_temporal_isolation(self) -> dict[str, Any]:
        return temporal_isolation_check(self.config)

    def evaluate_forbidden_features(self) -> dict[str, Any]:
        sentinel_columns = declared_sentinel_columns(self.config)
        return forbidden_feature_screen(self.config, self.table_columns, sentinel_columns)

    def evaluate_negative_controls(
        self,
        labels: list[int],
        scores: list[float],
    ) -> dict[str, Any]:
        control_cfg = self.config.get("negative_controls", {}) or {}
        return negative_controls(
            labels,
            scores,
            n_permutations=int(control_cfg.get("n_permutations", 100)),
            seed=int(control_cfg.get("seed", 17)),
        )

    def evaluate_matched_observed_state_cohorts(self) -> dict[str, Any]:
        matching_cfg = self.config.get("visible_state_matching", {}) or self.config.get(
            "matching", {}
        ) or {}
        return matched_cohort_delta(
            rows=self.rows,
            label_col=self.label_col,
            score_col=self.score_col,
            match_columns=list(matching_cfg.get("columns", []) or []),
            positive_value=self.positive_value,
            n_bins=int(matching_cfg.get("n_bins", 4)),
            min_bin_size=int(matching_cfg.get("min_bin_size", 8)),
        )

    def evaluate_leaky_sentinel_predictors(self) -> dict[str, Any]:
        return evaluate_sentinels(
            self.rows,
            self.label_col,
            self.positive_value,
            self.config,
        )

    def evaluate_sentinel_geometry(self) -> dict[str, Any]:
        return evaluate_sentinel_relations(
            self.rows,
            self.label_col,
            self.positive_value,
            self.score_col,
            self.config,
        )

    def evaluate_early_window_sensitivity(self) -> dict[str, Any]:
        cfg = self.config.get("early_window_sensitivity", {}) or {}
        score_columns = list(cfg.get("score_columns", []) or cfg.get("columns", []) or [])
        rows = []
        for column in score_columns:
            if column not in self.table_columns:
                rows.append({"column": column, "evaluated": False, "reason": "missing"})
                continue
            labels, scores = labels_and_scores(
                self.rows,
                self.label_col,
                column,
                self.positive_value,
            )
            rows.append(
                {
                    "column": column,
                    "evaluated": True,
                    "auc": auc_score(labels, scores),
                    "n": len(labels),
                    "n_positive": sum(labels),
                }
            )
        if not rows:
            return {
                "evaluated": False,
                "reason": "no early-window sensitivity score columns configured",
            }
        return {"evaluated": True, "score_columns": rows}

    def evaluate_threshold_robustness(
        self,
        labels: list[int],
        scores: list[float],
    ) -> dict[str, Any]:
        threshold_cfg = self.config.get("thresholds", {}) or {}
        return threshold_sensitivity(labels, scores, threshold_cfg.get("score_thresholds"))

    def build_failure_mode_dossier(
        self,
        primary: dict[str, Any],
        forbidden: dict[str, Any],
        temporal: dict[str, Any],
        controls: dict[str, Any],
        match: dict[str, Any],
        sentinels: dict[str, Any],
        sentinel_relations: dict[str, Any],
        threshold_sensitivity_result: dict[str, Any],
    ) -> dict[str, Any]:
        threshold_cfg = self.config.get("thresholds", {}) or {}
        return classify_failure_modes(
            primary=primary,
            forbidden=forbidden,
            temporal=temporal,
            controls=controls,
            match=match,
            sentinels=sentinels,
            sentinel_relations=sentinel_relations,
            threshold_sensitivity_result=threshold_sensitivity_result,
            thresholds=threshold_cfg,
        )


def run_audit(
    config_path: Path,
    input_path: Path,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    return LAMP_Audit.from_files(config_path, input_path).run(out_dir)


def load_config(path: Path) -> dict[str, Any]:
    return load_audit_config(path).to_runtime_dict()


def load_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        rows = [dict(row) for row in reader]
        return rows, list(reader.fieldnames)


def classify_failure_modes(
    primary: dict[str, Any],
    forbidden: dict[str, Any],
    temporal: dict[str, Any],
    controls: dict[str, Any],
    match: dict[str, Any],
    sentinels: dict[str, Any],
    sentinel_relations: dict[str, Any],
    threshold_sensitivity_result: dict[str, Any],
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    null_auc_max = float(thresholds.get("null_auc_max", 0.58))
    valid_auc_min = float(thresholds.get("valid_auc_min", 0.60))
    oracle_auc_min = float(thresholds.get("oracle_auc_min", 0.95))
    leakage_auc_gap = float(thresholds.get("leakage_auc_gap", 0.10))
    matched_delta_min = float(thresholds.get("matched_delta_min", 0.02))
    matched_collapse_max = float(thresholds.get("matched_collapse_max", 0.01))

    auc = primary.get("auc")
    output_classes: list[str] = []
    notes: list[str] = []

    if auc is None or auc <= null_auc_max:
        output_classes.append("null_or_destroyed_signal")

    if not temporal.get("passed"):
        output_classes.append("temporal_isolation_incomplete")

    if not forbidden.get("passed"):
        output_classes.append("forbidden_feature_contamination")

    if match.get("evaluated"):
        matched_delta = match.get("matched_observed_state_delta") or 0.0
        if auc is not None and auc >= valid_auc_min and abs(matched_delta) <= matched_collapse_max:
            output_classes.append("visible_state_confounding")
        if auc is not None and auc >= valid_auc_min and matched_delta >= matched_delta_min:
            output_classes.append("valid_early_hidden_state_signal")
    else:
        notes.append("Visible-state matching was not evaluable.")

    for name, item in sentinels.items():
        sentinel_auc = item.get("auc")
        if sentinel_auc is None:
            continue
        role = str(item.get("role", name)).lower()
        if "oracle" in role or "oracle" in name.lower():
            if sentinel_auc >= oracle_auc_min:
                output_classes.append("oracle_label_leakage_sentinel")
        if "future" in role or "future" in name.lower():
            if auc is not None and sentinel_auc >= auc + leakage_auc_gap:
                output_classes.append("future_physiology_invalid_comparator")

    if threshold_sensitivity_result.get("fragile"):
        output_classes.append("threshold_fragile_claim")

    oracle_proximity_alert = any(
        item.get("oracle_proximity_alert") for item in sentinel_relations.values()
    )
    if oracle_proximity_alert:
        output_classes.append("oracle_leakage_proximity_shift")
        output_classes.append("leakage_contaminated_candidate")

    controls_near_null = _controls_near_null(controls, null_auc_max)
    audit_pass = (
        auc is not None
        and auc >= valid_auc_min
        and temporal.get("passed")
        and forbidden.get("passed")
        and controls_near_null
        and match.get("evaluated")
        and (match.get("matched_observed_state_delta") or 0.0) >= matched_delta_min
        and not threshold_sensitivity_result.get("fragile")
        and not oracle_proximity_alert
    )
    if audit_pass:
        output_classes.append("audit_pass_candidate")

    return {
        "audit_pass_candidate": audit_pass,
        "output_classes": sorted(set(output_classes)),
        "thresholds": {
            "null_auc_max": null_auc_max,
            "valid_auc_min": valid_auc_min,
            "oracle_auc_min": oracle_auc_min,
            "leakage_auc_gap": leakage_auc_gap,
            "matched_delta_min": matched_delta_min,
            "matched_collapse_max": matched_collapse_max,
        },
        "controls_near_null": controls_near_null,
        "notes": notes,
    }


def _controls_near_null(controls: dict[str, Any], null_auc_max: float) -> bool:
    values = [
        controls.get("noise_auc_mean"),
        controls.get("score_permutation_auc_mean"),
        controls.get("label_permutation_auc_mean"),
    ]
    return all(value is not None and value <= null_auc_max for value in values)


def _n_subjects(rows: list[dict[str, Any]], subject_col: str) -> int | None:
    if not rows or subject_col not in rows[0]:
        return None
    return len({row.get(subject_col) for row in rows})
