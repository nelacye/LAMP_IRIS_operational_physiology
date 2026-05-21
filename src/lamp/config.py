"""Typed YAML configuration models for LAMP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LAMPModel(BaseModel):
    """Base model that preserves forward-compatible config fields."""

    model_config = ConfigDict(extra="allow")


class DatasetConfig(LAMPModel):
    name: str | None = None
    task: str | None = None
    role: str | None = None


class ColumnsConfig(LAMPModel):
    subject_id: str = "subject_id"
    id: str | None = None
    label: str = "label"
    positive_value: str | int | float = 1
    score: str = "score"
    anchor_time: str | None = None


class TemporalFeature(LAMPModel):
    name: str
    latest_offset_h: float | None = None


class TemporalIsolationConfig(LAMPModel):
    anchor: str = "prediction_time"
    valid_features_must_be: str = "at_or_before_anchor"
    frozen_before_holdout: list[str] = Field(default_factory=list)
    valid_score_features: list[TemporalFeature] = Field(default_factory=list)

    @field_validator("valid_score_features", mode="before")
    @classmethod
    def _coerce_features(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        coerced = []
        for item in value:
            if isinstance(item, str):
                coerced.append({"name": item})
            else:
                coerced.append(item)
        return coerced


class ForbiddenFeaturesConfig(LAMPModel):
    columns: list[str] = Field(default_factory=list)
    allowed_metadata_columns: list[str] = Field(default_factory=list)
    valid_score_features: list[str] = Field(default_factory=list)


class SentinelConfig(LAMPModel):
    column: str | None = None
    role: str | None = None
    expected_signature: str | None = None


class NegativeControlsConfig(LAMPModel):
    n_permutations: int = 100
    seed: int = 17


class VisibleStateMatchingConfig(LAMPModel):
    columns: list[str] = Field(default_factory=list)
    n_bins: int = 4
    min_bin_size: int = 8


class ThresholdConfig(LAMPModel):
    null_auc_max: float = 0.58
    valid_auc_min: float = 0.60
    oracle_auc_min: float = 0.95
    leakage_auc_gap: float = 0.10
    matched_delta_min: float = 0.02
    matched_collapse_max: float = 0.01
    score_thresholds: list[float] | None = None


class EarlyWindowSensitivityConfig(LAMPModel):
    score_columns: list[str] = Field(default_factory=list)


class AuditConfig(LAMPModel):
    schema_version: str = "lamp.audit_config/v1"
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    columns: ColumnsConfig = Field(default_factory=ColumnsConfig)
    temporal_isolation: TemporalIsolationConfig = Field(
        default_factory=TemporalIsolationConfig
    )
    forbidden_features: ForbiddenFeaturesConfig = Field(
        default_factory=ForbiddenFeaturesConfig
    )
    sentinels: dict[str, SentinelConfig | str] = Field(default_factory=dict)
    negative_controls: NegativeControlsConfig = Field(
        default_factory=NegativeControlsConfig
    )
    visible_state_matching: VisibleStateMatchingConfig = Field(
        default_factory=VisibleStateMatchingConfig
    )
    matching: VisibleStateMatchingConfig | None = None
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    early_window_sensitivity: EarlyWindowSensitivityConfig = Field(
        default_factory=EarlyWindowSensitivityConfig
    )
    leakage_proximity: dict[str, Any] = Field(default_factory=dict)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


def load_audit_config(path: Path) -> AuditConfig:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("LAMP config must be a YAML mapping")
    return AuditConfig.model_validate(data)
