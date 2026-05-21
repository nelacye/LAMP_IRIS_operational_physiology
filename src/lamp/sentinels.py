"""Sentinel score diagnostics."""

from __future__ import annotations

import math
from typing import Any

from .controls import as_float, auc_score, labels_and_scores


def declared_sentinel_columns(config: dict[str, Any]) -> list[str]:
    columns: list[str] = []
    for _, spec in _iter_sentinel_specs(config):
        column = spec.get("column")
        if column:
            columns.append(column)
    return columns


def evaluate_sentinels(
    rows: list[dict[str, Any]],
    label_col: str,
    positive_value: Any,
    config: dict[str, Any],
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name, spec in _iter_sentinel_specs(config):
        column = spec.get("column")
        if not column:
            results[name] = {"evaluated": False, "reason": "missing column in config"}
            continue
        labels, scores = labels_and_scores(rows, label_col, column, positive_value)
        auc = auc_score(labels, scores)
        results[name] = {
            "evaluated": auc is not None,
            "column": column,
            "role": spec.get("role", name),
            "expected_signature": spec.get("expected_signature"),
            "auc": auc,
            "n": len(labels),
            "n_positive": sum(labels),
            "n_negative": len(labels) - sum(labels),
        }
    return results


def evaluate_sentinel_relations(
    rows: list[dict[str, Any]],
    label_col: str,
    positive_value: Any,
    primary_score_col: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    proximity_cfg = config.get("leakage_proximity", {}) or {}
    baseline_col = proximity_cfg.get("baseline_score")
    alert_min = float(proximity_cfg.get("oracle_proximity_alert_min", 0.01))

    results: dict[str, Any] = {}
    for name, spec in _iter_sentinel_specs(config):
        sentinel_col = spec.get("column")
        if not sentinel_col:
            continue

        labels: list[int] = []
        primary_scores: list[float] = []
        sentinel_scores: list[float] = []
        baseline_scores: list[float] = []
        positive_text = str(positive_value)

        for row in rows:
            primary = as_float(row.get(primary_score_col))
            sentinel = as_float(row.get(sentinel_col))
            if primary is None or sentinel is None:
                continue
            labels.append(1 if str(row.get(label_col)) == positive_text else 0)
            primary_scores.append(primary)
            sentinel_scores.append(sentinel)
            if baseline_col:
                baseline = as_float(row.get(baseline_col))
                baseline_scores.append(primary if baseline is None else baseline)

        primary_auc = auc_score(labels, primary_scores)
        sentinel_auc = auc_score(labels, sentinel_scores)
        relation = {
            "column": sentinel_col,
            "role": spec.get("role", name),
            "n": len(labels),
            "primary_auc": primary_auc,
            "sentinel_auc": sentinel_auc,
            "sentinel_minus_primary_auc": _safe_subtract(sentinel_auc, primary_auc),
            "primary_sentinel_pearson": _pearson(primary_scores, sentinel_scores),
            "primary_sentinel_spearman": _pearson(
                _ranks(primary_scores),
                _ranks(sentinel_scores),
            ),
        }

        if baseline_col:
            baseline_auc = auc_score(labels, baseline_scores)
            proximity = _leakage_proximity(primary_auc, baseline_auc, sentinel_auc)
            relation.update(
                {
                    "baseline_score_column": baseline_col,
                    "baseline_auc": baseline_auc,
                    "auc_leakage_proximity": proximity,
                    "oracle_proximity_alert_min": alert_min,
                    "oracle_proximity_alert": _is_oracle(name, spec)
                    and proximity is not None
                    and proximity >= alert_min,
                }
            )
        else:
            relation["oracle_proximity_alert"] = False

        results[name] = relation
    return results


def _iter_sentinel_specs(config: dict[str, Any]):
    sentinels = config.get("sentinels", {}) or {}
    for name, spec in sentinels.items():
        if isinstance(spec, str):
            yield name, {"column": spec}
        else:
            yield name, spec or {}


def _safe_subtract(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return float(a - b)


def _leakage_proximity(
    primary_auc: float | None,
    baseline_auc: float | None,
    sentinel_auc: float | None,
) -> float | None:
    if primary_auc is None or baseline_auc is None or sentinel_auc is None:
        return None
    denom = sentinel_auc - baseline_auc
    if abs(denom) < 1e-12:
        return None
    return float((primary_auc - baseline_auc) / denom)


def _is_oracle(name: str, spec: dict[str, Any]) -> bool:
    role = str(spec.get("role", name)).lower()
    return "oracle" in role or "oracle" in name.lower()


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    lx = [float(x) for x in left if x is not None]
    ry = [float(y) for y in right if y is not None]
    if len(lx) != len(left) or len(ry) != len(right):
        return None
    mean_l = sum(left) / len(left)
    mean_r = sum(right) / len(right)
    num = sum((x - mean_l) * (y - mean_r) for x, y in zip(left, right))
    den_l = math.sqrt(sum((x - mean_l) ** 2 for x in left))
    den_r = math.sqrt(sum((y - mean_r) ** 2 for y in right))
    if den_l == 0 or den_r == 0:
        return None
    return float(num / (den_l * den_r))


def _ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[ordered[k][0]] = avg_rank
        i = j
    return ranks
