# Sepsis ML LAMP Benchmark

This benchmark trains lightweight ML monitors on the available PhysioNet/CinC
2019 v3_5k patient-level score table. Valid models use early-window summary
features only. Contaminated variants deliberately use future-window features
or low-dose oracle information.

Raw hourly `.psv` trajectories are not present in this checkout, so this is a
real clinical feature-table ML benchmark rather than a raw-sequence LSTM/TFT run.

| monitor | score | auc | audit_pass | temporal | forbidden | oracle proximity | output_classes |
|---|---|---:|:---:|:---:|:---:|:---:|---|
| Existing locked early score | `existing_valid_early_warning_score` | 0.6145 | False | True | True | False | `oracle_label_leakage_sentinel` |
| MLP early-window model | `mlp_early_score` | 0.8555 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| Gradient-boosted early-window model | `gb_early_score` | 0.9906 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| Linear sequential-feature model | `linear_sequence_score` | 0.9669 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| Linear probe on MLP hidden activation | `mlp_hidden_probe_score` | 0.8632 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| MLP future-window contaminated model | `mlp_future_leak_score` | 0.8431 | False | False | False | False | `forbidden_feature_contamination;oracle_label_leakage_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| Gradient-boosted future-window contaminated model | `gb_future_leak_score` | 0.9889 | False | False | False | False | `forbidden_feature_contamination;oracle_label_leakage_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| MLP low-dose oracle mixture | `mlp_oracle_mix_score` | 0.9902 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| Hidden-activation probe with oracle contamination | `mlp_hidden_oracle_probe_score` | 0.9852 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |

## Per-Horizon AUC

| horizon_h | score | auc | n | n_positive |
|---:|---|---:|---:|---:|
| 6 | `mlp_early_score` | 0.7913 | 1705 | 98 |
| 6 | `gb_early_score` | 0.9616 | 1705 | 98 |
| 6 | `linear_sequence_score` | 0.8338 | 1705 | 98 |
| 6 | `mlp_hidden_probe_score` | 0.7909 | 1705 | 98 |
| 6 | `mlp_future_leak_score` | 0.7676 | 1705 | 98 |
| 6 | `gb_future_leak_score` | 0.9485 | 1705 | 98 |
| 6 | `mlp_oracle_mix_score` | 0.9837 | 1705 | 98 |
| 6 | `mlp_hidden_oracle_probe_score` | 0.9741 | 1705 | 98 |
| 12 | `mlp_early_score` | 0.8187 | 1691 | 84 |
| 12 | `gb_early_score` | 0.9982 | 1691 | 84 |
| 12 | `linear_sequence_score` | 0.9945 | 1691 | 84 |
| 12 | `mlp_hidden_probe_score` | 0.8289 | 1691 | 84 |
| 12 | `mlp_future_leak_score` | 0.8249 | 1691 | 84 |
| 12 | `gb_future_leak_score` | 0.9988 | 1691 | 84 |
| 12 | `mlp_oracle_mix_score` | 0.9859 | 1691 | 84 |
| 12 | `mlp_hidden_oracle_probe_score` | 0.9799 | 1691 | 84 |
| 18 | `mlp_early_score` | 0.9239 | 1679 | 72 |
| 18 | `gb_early_score` | 0.9986 | 1679 | 72 |
| 18 | `linear_sequence_score` | 0.9990 | 1679 | 72 |
| 18 | `mlp_hidden_probe_score` | 0.9324 | 1679 | 72 |
| 18 | `mlp_future_leak_score` | 0.9078 | 1679 | 72 |
| 18 | `gb_future_leak_score` | 0.9993 | 1679 | 72 |
| 18 | `mlp_oracle_mix_score` | 0.9990 | 1679 | 72 |
| 18 | `mlp_hidden_oracle_probe_score` | 0.9983 | 1679 | 72 |

## Interpretation

LAMP is applied to predictions, not just to data tables: the same audit
flags future-window contamination, low-dose oracle mixtures, and
representation-level oracle contamination even when AUC improves.
