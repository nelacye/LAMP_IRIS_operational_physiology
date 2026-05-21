"""Visible-state matching diagnostics for LAMP."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .controls import as_float


def matched_cohort_delta(
    rows: list[dict[str, Any]],
    label_col: str,
    score_col: str,
    match_columns: list[str],
    positive_value: Any = 1,
    n_bins: int = 4,
    min_bin_size: int = 8,
) -> dict[str, Any]:
    if not match_columns:
        return {"evaluated": False, "reason": "no match columns configured"}

    complete_rows: list[dict[str, Any]] = []
    for row in rows:
        if as_float(row.get(score_col)) is None:
            continue
        if any(as_float(row.get(col)) is None for col in match_columns):
            continue
        complete_rows.append(row)

    if len(complete_rows) < min_bin_size:
        return {
            "evaluated": False,
            "reason": "too few complete rows for matching",
            "complete_rows": len(complete_rows),
        }

    bin_maps: dict[str, dict[int, int]] = {}
    for col in match_columns:
        values = [(as_float(row.get(col)), idx) for idx, row in enumerate(complete_rows)]
        values = [(value, idx) for value, idx in values if value is not None]
        ordered = sorted(values, key=lambda item: item[0])
        col_bins: dict[int, int] = {}
        total = len(ordered)
        for position, (_, idx) in enumerate(ordered):
            col_bins[idx] = min(int(position * n_bins / total), n_bins - 1)
        bin_maps[col] = col_bins

    strata: dict[tuple[int, ...], list[dict[str, Any]]] = defaultdict(list)
    for idx, row in enumerate(complete_rows):
        key = tuple(bin_maps[col][idx] for col in match_columns)
        strata[key].append(row)

    deltas: list[float] = []
    weights: list[int] = []
    used_strata = 0
    used_rows = 0
    for stratum_rows in strata.values():
        if len(stratum_rows) < min_bin_size:
            continue
        scored = [(as_float(row.get(score_col)), row) for row in stratum_rows]
        scored = [(score, row) for score, row in scored if score is not None]
        if len(scored) < min_bin_size:
            continue
        if len({score for score, _ in scored}) < 2:
            deltas.append(0.0)
            weights.append(len(scored))
            used_strata += 1
            used_rows += len(scored)
            continue
        median_score = sorted(score for score, _ in scored)[len(scored) // 2]
        low = [row for score, row in scored if score < median_score]
        high = [row for score, row in scored if score >= median_score]
        if not low or not high:
            continue

        low_rate = _positive_rate(low, label_col, positive_value)
        high_rate = _positive_rate(high, label_col, positive_value)
        deltas.append(high_rate - low_rate)
        weights.append(len(scored))
        used_strata += 1
        used_rows += len(scored)

    if not deltas:
        return {
            "evaluated": False,
            "reason": "no strata met min_bin_size",
            "complete_rows": len(complete_rows),
            "candidate_strata": len(strata),
        }

    weighted_delta = sum(delta * weight for delta, weight in zip(deltas, weights)) / sum(
        weights
    )
    return {
        "evaluated": True,
        "match_columns": match_columns,
        "n_bins": n_bins,
        "min_bin_size": min_bin_size,
        "candidate_strata": len(strata),
        "matched_strata": used_strata,
        "matched_rows": used_rows,
        "matched_observed_state_delta": float(weighted_delta),
        "absolute_matched_observed_state_delta": float(abs(weighted_delta)),
    }


def _positive_rate(
    rows: list[dict[str, Any]],
    label_col: str,
    positive_value: Any,
) -> float:
    if not rows:
        return 0.0
    positive_text = str(positive_value)
    return sum(1 for row in rows if str(row.get(label_col)) == positive_text) / len(rows)
