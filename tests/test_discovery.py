from lamp.discovery import infer_failure_type


def test_discovery_prioritizes_audit_pass_over_oracle_sentinel():
    audit_summary = {
        "failure_mode_dossier": {
            "audit_pass_candidate": True,
            "output_classes": ["audit_pass_candidate", "oracle_label_leakage_sentinel"],
        },
        "temporal_isolation": {"passed": True},
        "forbidden_feature_screen": {
            "passed": True,
            "valid_score_feature_violations": [],
        },
    }
    sentinels = {"oracle": {"role": "oracle_label", "auc": 1.0}}

    failure = infer_failure_type(audit_summary, sentinels, {})

    assert failure["failure_type"] == "audit_pass_discovery"


def test_discovery_prioritizes_protocol_violation_before_oracle_sentinel():
    audit_summary = {
        "failure_mode_dossier": {
            "audit_pass_candidate": False,
            "output_classes": ["oracle_label_leakage_sentinel"],
        },
        "temporal_isolation": {"passed": True},
        "forbidden_feature_screen": {
            "passed": False,
            "valid_score_feature_violations": ["protocol_stressor_shortcut_score"],
        },
    }
    sentinels = {
        "oracle": {"role": "oracle_label", "auc": 1.0},
        "protocol": {"role": "protocol_shortcut", "auc": 0.7},
    }

    failure = infer_failure_type(audit_summary, sentinels, {})

    assert failure["failure_type"] == "protocol_shortcut"


def test_discovery_detects_future_folding_temporal_failure():
    audit_summary = {
        "failure_mode_dossier": {
            "audit_pass_candidate": False,
            "output_classes": ["temporal_isolation_incomplete"],
        },
        "temporal_isolation": {"passed": False},
        "forbidden_feature_screen": {
            "passed": False,
            "valid_score_feature_violations": ["future_folding_execution_score"],
        },
    }
    sentinels = {
        "future_folding": {"role": "future_folding_execution", "auc": 0.95},
    }

    failure = infer_failure_type(audit_summary, sentinels, {})

    assert failure["failure_type"] == "future_folding"
