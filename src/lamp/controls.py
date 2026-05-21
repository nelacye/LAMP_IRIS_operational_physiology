"""Negative controls, leakage screens, and threshold diagnostics."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable
from typing import Any


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(float(value)):
            return None
        return float(value)
    text = str(value).strip()
    if text == "" or text.lower() in {"na", "nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def labels_and_scores(
    rows: Iterable[dict[str, Any]],
    label_col: str,
    score_col: str,
    positive_value: Any = 1,
) -> tuple[list[int], list[float]]:
    labels: list[int] = []
    scores: list[float] = []
    positive_text = str(positive_value)
    for row in rows:
        score = as_float(row.get(score_col))
        if score is None:
            continue
        label_raw = row.get(label_col)
        label = 1 if str(label_raw) == positive_text else 0
        labels.append(label)
        scores.append(score)
    return labels, scores


def auc_score(labels: list[int], scores: list[float]) -> float | None:
    """Rank-based ROC AUC with average ranks for ties."""
    if len(labels) != len(scores):
        raise ValueError("labels and scores must have equal length")
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None

    ordered = sorted(enumerate(scores), key=lambda item: item[1])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[ordered[k][0]] = avg_rank
        i = j

    pos_rank_sum = sum(rank for rank, label in zip(ranks, labels) if label == 1)
    auc = (pos_rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def negative_controls(
    labels: list[int],
    scores: list[float],
    n_permutations: int = 100,
    seed: int = 17,
) -> dict[str, Any]:
    rng = random.Random(seed)
    n = len(labels)
    if n == 0:
        return {
            "n": 0,
            "noise_auc_mean": None,
            "score_permutation_auc_mean": None,
            "label_permutation_auc_mean": None,
        }

    noise_aucs: list[float] = []
    score_perm_aucs: list[float] = []
    label_perm_aucs: list[float] = []
    for _ in range(max(1, int(n_permutations))):
        noise = [rng.random() for _ in range(n)]
        noise_auc = auc_score(labels, noise)
        if noise_auc is not None:
            noise_aucs.append(noise_auc)

        perm_scores = list(scores)
        rng.shuffle(perm_scores)
        score_auc = auc_score(labels, perm_scores)
        if score_auc is not None:
            score_perm_aucs.append(score_auc)

        perm_labels = list(labels)
        rng.shuffle(perm_labels)
        label_auc = auc_score(perm_labels, scores)
        if label_auc is not None:
            label_perm_aucs.append(label_auc)

    return {
        "n": n,
        "n_permutations": max(1, int(n_permutations)),
        "noise_auc_mean": _mean(noise_aucs),
        "noise_auc_sd": _sd(noise_aucs),
        "score_permutation_auc_mean": _mean(score_perm_aucs),
        "score_permutation_auc_sd": _sd(score_perm_aucs),
        "label_permutation_auc_mean": _mean(label_perm_aucs),
        "label_permutation_auc_sd": _sd(label_perm_aucs),
    }


def forbidden_feature_screen(
    config: dict[str, Any],
    table_columns: Iterable[str],
    declared_sentinel_columns: Iterable[str],
) -> dict[str, Any]:
    spec = config.get("forbidden_features", {}) or {}
    forbidden = set(spec.get("columns", []) or [])
    valid_score_features = set(spec.get("valid_score_features", []) or [])
    allowed_metadata = set(spec.get("allowed_metadata_columns", []) or [])
    declared_sentinels = set(declared_sentinel_columns)
    table_cols = set(table_columns)

    present_forbidden = forbidden & table_cols
    declared_sentinel_hits = sorted(present_forbidden & declared_sentinels)
    unexpected_table_hits = sorted(
        present_forbidden - declared_sentinels - allowed_metadata
    )
    valid_feature_hits = sorted(forbidden & valid_score_features)

    return {
        "passed": not unexpected_table_hits and not valid_feature_hits,
        "forbidden_columns_declared": sorted(forbidden),
        "declared_sentinel_columns_present": declared_sentinel_hits,
        "unexpected_forbidden_columns_present": unexpected_table_hits,
        "valid_score_feature_violations": valid_feature_hits,
        "interpretation": (
            "Declared sentinel columns are audit comparators, not leakage in the "
            "valid model unless they appear in valid_score_features."
        ),
    }


def temporal_isolation_check(config: dict[str, Any]) -> dict[str, Any]:
    spec = config.get("temporal_isolation", {}) or {}
    valid_features = spec.get("valid_score_features", []) or []
    violations: list[dict[str, Any]] = []
    declared: list[dict[str, Any]] = []

    for item in valid_features:
        if isinstance(item, str):
            declared.append({"name": item, "latest_offset_h": None})
            continue
        name = item.get("name")
        latest_offset = item.get("latest_offset_h")
        declared.append({"name": name, "latest_offset_h": latest_offset})
        if latest_offset is not None and float(latest_offset) > 0:
            violations.append({"name": name, "latest_offset_h": latest_offset})

    return {
        "declared": bool(spec),
        "passed": bool(spec) and not violations,
        "anchor": spec.get("anchor", "prediction_time"),
        "valid_features_must_be": spec.get(
            "valid_features_must_be", "at_or_before_anchor"
        ),
        "valid_score_features": declared,
        "violations": violations,
        "frozen_before_holdout": spec.get("frozen_before_holdout", []) or [],
    }


def threshold_sensitivity(
    labels: list[int],
    scores: list[float],
    thresholds: list[float] | None = None,
) -> dict[str, Any]:
    if not labels:
        return {"evaluated": False, "thresholds": []}
    if thresholds is None:
        thresholds = [0.25, 0.5, 0.75]

    baseline = sum(labels) / len(labels)
    rows: list[dict[str, float]] = []
    enrichments: list[float] = []
    for threshold in thresholds:
        selected = [label for label, score in zip(labels, scores) if score >= threshold]
        if not selected:
            rows.append(
                {
                    "threshold": float(threshold),
                    "selected_fraction": 0.0,
                    "positive_rate": None,
                    "enrichment_over_baseline": None,
                }
            )
            continue
        rate = sum(selected) / len(selected)
        enrichment = rate - baseline
        enrichments.append(enrichment)
        rows.append(
            {
                "threshold": float(threshold),
                "selected_fraction": len(selected) / len(labels),
                "positive_rate": rate,
                "enrichment_over_baseline": enrichment,
            }
        )

    signs = {1 if value > 0 else -1 if value < 0 else 0 for value in enrichments}
    fragile = len(signs - {0}) > 1
    return {
        "evaluated": True,
        "baseline_positive_rate": baseline,
        "thresholds": rows,
        "fragile": fragile,
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _sd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    var = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return float(math.sqrt(var))
