from lamp.datasets.framing_audit import build_eval_awareness_frame
from lamp.monitors.eval_awareness import MONITORS, build_monitor_config


def test_eval_awareness_frame_has_three_framing_conditions():
    rows = build_eval_awareness_frame(repetitions_per_task_condition=2)
    conditions = {row["condition"] for row in rows}

    assert conditions == {"evaluation", "deployment", "neutral"}
    assert {0, 1}.issubset({row["label_sandbagging"] for row in rows})


def test_eval_awareness_leaky_monitor_config_marks_forbidden_feature():
    monitor = next(item for item in MONITORS if item["id"] == "answer_key_leak")
    config = build_monitor_config(monitor)

    assert "answer_key_oracle_feature" in config["forbidden_features"]["columns"]
    assert "answer_key_oracle_feature" in config["forbidden_features"]["valid_score_features"]
    assert config["temporal_isolation"]["valid_score_features"][0]["latest_offset_h"] == 1.0

