from pathlib import Path

from lamp.bio import diagnose_biological_claim, load_bio_contract


def _contract():
    return {
        "schema_version": "lamp.bio_contract/v1",
        "claim_contracts": {
            "structural_endpoint_calcium_probe": {
                "claim": "clean calcium probe predicts structural maturation",
                "endpoint_axis": "structural_maturation",
                "allowed_probe_axes": ["calcium_handling_electrophysiology"],
            }
        },
        "diagnosis_rules": {
            "thresholds": {
                "stable_bootstrap_pass_rate_min": 0.90,
                "stable_leave_group_pass_rate_min": 0.90,
                "stable_alt_panel_pass_rate_min": 0.80,
                "protocol_sentinel_dominance_auc_gap": 0.0,
            }
        },
    }


def _audit_summary(audit_pass=True, temporal=True, forbidden=True):
    return {
        "primary_score": {"auc": 0.70, "direction_ambiguous": False},
        "failure_mode_dossier": {
            "audit_pass_candidate": audit_pass,
            "output_classes": ["audit_pass_candidate"] if audit_pass else [],
        },
        "temporal_isolation": {"passed": temporal},
        "forbidden_feature_screen": {
            "passed": forbidden,
            "valid_score_feature_violations": [],
        },
        "sentinels": {
            "high_calcium": {"role": "protocol_shortcut", "auc": 0.65},
            "oracle": {"role": "oracle_label", "auc": 1.0},
        },
        "sentinel_relations": {},
    }


def test_clean_bio_signal_can_be_fragile():
    diagnosis = diagnose_biological_claim(
        _audit_summary(),
        _contract(),
        "structural_endpoint_calcium_probe",
        "calcium_handling_electrophysiology",
        {
            "bootstrap_pass_rate": 0.50,
            "alternative_panel_pass_rate": 0.80,
            "leave_group_out_pass_rate": 0.75,
            "threshold_grid_pass_rate": 0.67,
            "donor_heldout_status": "not_evaluable",
        },
    )

    assert diagnosis["diagnosis"] == "valid_biological_signal_fragile"
    assert "bootstrap_pass_rate_below_stable_threshold" in diagnosis["warnings"]


def test_protocol_feature_failure_is_protocol_confounded():
    summary = _audit_summary(audit_pass=False, forbidden=False)
    summary["forbidden_feature_screen"]["valid_score_feature_violations"] = [
        "high_calcium_shortcut_score"
    ]

    diagnosis = diagnose_biological_claim(
        summary,
        _contract(),
        "structural_endpoint_calcium_probe",
        "intervention_protocol_structure",
    )

    assert diagnosis["diagnosis"] == "protocol_confounded_signal"
    assert "forbidden_protocol_feature_used_by_score" in diagnosis["flags"]


def test_temporal_failure_is_endpoint_adjacent_contamination():
    diagnosis = diagnose_biological_claim(
        _audit_summary(audit_pass=False, temporal=False, forbidden=False),
        _contract(),
        "structural_endpoint_calcium_probe",
        "structural_maturation",
    )

    assert diagnosis["diagnosis"] == "endpoint_adjacent_contamination"


def test_molecular_code_contract_loads():
    contract = load_bio_contract(Path("configs/ipsc_molecular_code_contract.yaml"))
    claim = contract["claim_contracts"]["kinase_dynamics_predicts_folding_execution"]

    assert claim["endpoint_axis"] == "protein_folding_execution_proteostasis"
    assert "kinase_folding_coupled_signal" in claim["allowed_probe_axes"]
    assert "future_folding_sentinel" in claim["required_sentinels"]
