from lamp.controls import forbidden_feature_screen
from lamp.sentinels import declared_sentinel_columns, evaluate_sentinels


def test_declared_sentinel_columns_are_not_forbidden_violations():
    config = {
        "forbidden_features": {
            "columns": ["future_score", "oracle_score", "onset_distance_hours"],
            "valid_score_features": ["baseline_hr", "baseline_spo2"],
        },
        "sentinels": {
            "future_physiology": {"column": "future_score", "role": "future"},
            "oracle_label": {"column": "oracle_score", "role": "oracle"},
        },
    }
    table_columns = ["label", "valid_score", "future_score", "oracle_score"]

    screen = forbidden_feature_screen(
        config,
        table_columns,
        declared_sentinel_columns(config),
    )

    assert screen["passed"]
    assert screen["declared_sentinel_columns_present"] == [
        "future_score",
        "oracle_score",
    ]
    assert screen["unexpected_forbidden_columns_present"] == []


def test_oracle_sentinel_reaches_ceiling_without_being_valid_model_leakage():
    rows = [
        {"label": "0", "oracle_score": "0"},
        {"label": "0", "oracle_score": "0"},
        {"label": "1", "oracle_score": "1"},
        {"label": "1", "oracle_score": "1"},
    ]
    config = {
        "sentinels": {
            "oracle_label": {"column": "oracle_score", "role": "oracle_label"}
        }
    }

    sentinels = evaluate_sentinels(rows, "label", 1, config)

    assert sentinels["oracle_label"]["auc"] == 1.0
