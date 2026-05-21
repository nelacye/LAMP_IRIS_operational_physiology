# BIDSleep LAMP benchmark: HR plus EEG labels

Open wearable sleep benchmark using Apple Watch instantaneous HR and Dreem 2 expert EEG labels.

## Main Audit

| n | n_positive | valid_auc | future_hr_auc | oracle_auc | matched_delta | audit_pass | output_classes |
|---:|---:|---:|---:|---:|---:|:---:|---|
| 252 | 77 | 0.567124 | 0.611206 | 1.000000 | 0.049971 | False | `null_or_destroyed_signal;oracle_label_leakage_sentinel` |

## Low-Dose Oracle Mixture

| lambda | provenance | auc | oracle_proximity | temporal | forbidden | audit_pass | output_classes |
|---:|---|---:|---:|:---:|:---:|:---:|---|
| 0 | undeclared | 0.567124 | 0.000000 | True | True | False | `null_or_destroyed_signal;oracle_label_leakage_sentinel` |
| 0 | declared | 0.567124 | 0.000000 | True | True | False | `null_or_destroyed_signal;oracle_label_leakage_sentinel` |
| 0.005 | undeclared | 0.572022 | 0.011315 | True | True | False | `leakage_contaminated_candidate;null_or_destroyed_signal;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift` |
| 0.005 | declared | 0.572022 | 0.011315 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;null_or_destroyed_signal;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete` |
| 0.01 | undeclared | 0.577588 | 0.024173 | True | True | False | `leakage_contaminated_candidate;null_or_destroyed_signal;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift` |
| 0.01 | declared | 0.577588 | 0.024173 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;null_or_destroyed_signal;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete` |
| 0.02 | undeclared | 0.588571 | 0.049546 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;threshold_fragile_claim` |
| 0.02 | declared | 0.588571 | 0.049546 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;threshold_fragile_claim` |
| 0.05 | undeclared | 0.621299 | 0.125150 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 0.05 | declared | 0.621299 | 0.125150 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 0.1 | undeclared | 0.674286 | 0.247557 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 0.1 | declared | 0.674286 | 0.247557 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |

## Visible-State Shortcut

| visible_auc | baseline_valid_auc | matched_delta | audit_pass | output_classes |
|---:|---:|---:|:---:|---|
| 0.605974 | 0.567124 | 0.000000 | False | `oracle_label_leakage_sentinel;visible_state_confounding` |

## Claim Boundary

This is an open wearable-domain LAMP transfer benchmark. It is not a clinical sleep-device validation study.
