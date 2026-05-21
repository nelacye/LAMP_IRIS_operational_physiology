# LAMP perturbation benchmark: PhysioNet/CinC 2019 sepsis v3 5k

## Oracle low-dose mixture

Score definition: `mixed_score = (1 - lambda) * valid_score + lambda * oracle_score`.

| horizon | lambda | provenance | AUC | distance_to_oracle | oracle_proximity | temporal | forbidden | audit_pass | output_classes |
|---:|---:|---|---:|---:|---:|:---:|:---:|:---:|---|
| 6 | 0 | undeclared | 0.641618 | 0.358382 | -0.000009 | True | True | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| 6 | 0 | declared | 0.641618 | 0.358382 | -0.000009 | True | True | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| 6 | 0.005 | undeclared | 0.658573 | 0.341427 | 0.047300 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 6 | 0.005 | declared | 0.658573 | 0.341427 | 0.047300 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 6 | 0.01 | undeclared | 0.675462 | 0.324538 | 0.094426 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 6 | 0.01 | declared | 0.675462 | 0.324538 | 0.094426 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 6 | 0.02 | undeclared | 0.708014 | 0.291986 | 0.185258 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 6 | 0.02 | declared | 0.708014 | 0.291986 | 0.185258 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 6 | 0.05 | undeclared | 0.793965 | 0.206035 | 0.425090 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 6 | 0.05 | declared | 0.793965 | 0.206035 | 0.425090 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 6 | 0.1 | undeclared | 0.895347 | 0.104653 | 0.707982 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 6 | 0.1 | declared | 0.895347 | 0.104653 | 0.707982 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 12 | 0 | undeclared | 0.632762 | 0.367238 | -0.000005 | True | True | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| 12 | 0 | declared | 0.632762 | 0.367238 | -0.000005 | True | True | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| 12 | 0.005 | undeclared | 0.649762 | 0.350238 | 0.046288 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 12 | 0.005 | declared | 0.649762 | 0.350238 | 0.046288 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 12 | 0.01 | undeclared | 0.666592 | 0.333408 | 0.092117 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 12 | 0.01 | declared | 0.666592 | 0.333408 | 0.092117 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 12 | 0.02 | undeclared | 0.699367 | 0.300633 | 0.181365 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 12 | 0.02 | declared | 0.699367 | 0.300633 | 0.181365 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 12 | 0.05 | undeclared | 0.787301 | 0.212699 | 0.420811 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 12 | 0.05 | declared | 0.787301 | 0.212699 | 0.420811 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 12 | 0.1 | undeclared | 0.891339 | 0.108661 | 0.704113 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 12 | 0.1 | declared | 0.891339 | 0.108661 | 0.704113 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 18 | 0 | undeclared | 0.624873 | 0.375127 | -0.000005 | True | True | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| 18 | 0 | declared | 0.624873 | 0.375127 | -0.000005 | True | True | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| 18 | 0.005 | undeclared | 0.642135 | 0.357865 | 0.046011 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 18 | 0.005 | declared | 0.642135 | 0.357865 | 0.046011 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 18 | 0.01 | undeclared | 0.659291 | 0.340709 | 0.091744 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 18 | 0.01 | declared | 0.659291 | 0.340709 | 0.091744 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 18 | 0.02 | undeclared | 0.692667 | 0.307333 | 0.180719 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 18 | 0.02 | declared | 0.692667 | 0.307333 | 0.180719 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 18 | 0.05 | undeclared | 0.781883 | 0.218117 | 0.418549 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 18 | 0.05 | declared | 0.781883 | 0.218117 | 0.418549 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| 18 | 0.1 | undeclared | 0.888442 | 0.111558 | 0.702610 | True | True | False | `leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;valid_early_hidden_state_signal` |
| 18 | 0.1 | declared | 0.888442 | 0.111558 | 0.702610 | False | False | False | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |

## Visible-confounding collapse

| horizon | visible_only_auc | baseline_valid_auc | auc_delta | matched_delta | audit_pass | output_classes |
|---:|---:|---:|---:|---:|:---:|---|
| 6 | 0.581585 | 0.641621 | -0.060036 | -0.007235 | False | `oracle_label_leakage_sentinel` |
| 12 | 0.577667 | 0.632763 | -0.055097 | 0.002152 | False | `null_or_destroyed_signal;oracle_label_leakage_sentinel` |
| 18 | 0.562384 | 0.624875 | -0.062492 | -0.006479 | False | `null_or_destroyed_signal;oracle_label_leakage_sentinel;threshold_fragile_claim` |

## Interpretation boundary

This perturbation benchmark tests audit behavior under controlled score contamination.
It does not establish clinical validity. Surviving LAMP earns prospective testing.
