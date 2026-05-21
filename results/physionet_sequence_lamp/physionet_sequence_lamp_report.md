# PhysioNet/CinC 2019 Raw Sequence LAMP Benchmark

This run builds examples directly from raw `.psv` files, creates early-window
and future-window splits, trains valid and intentionally contaminated monitors,
and applies LAMP to the resulting prediction table.

- Source examples: 7245
- Held-out predictions: 2529
- Max patients: 3000
- Horizons: 6,12,18
- Early window: 12 hours
- PyTorch available: True

## LAMP Diagnoses

| monitor | score | auc | audit_pass | temporal | forbidden | oracle proximity | output_classes |
|---|---|---:|:---:|:---:|:---:|:---:|---|
| MLP hand-crafted valid | `mlp_probe_valid_score` | 0.6749 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| MLP hand-crafted leaky | `mlp_probe_leaky_score` | 0.8200 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| MLP low-dose oracle mix | `mlp_lowdose_oracle_score` | 0.6824 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| LSTM valid sequence | `lstm_valid_score` | 0.5759 | False | True | True | False | `null_or_destroyed_signal;oracle_label_leakage_sentinel` |
| LSTM future-window leaky sequence | `lstm_future_leaky_score` | 0.6180 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| GRU valid sequence | `gru_valid_score` | 0.5690 | False | True | True | False | `null_or_destroyed_signal;oracle_label_leakage_sentinel;threshold_fragile_claim` |
| GRU future-window leaky sequence | `gru_future_leaky_score` | 0.6164 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| TRANSFORMER valid sequence | `transformer_valid_score` | 0.5827 | False | True | True | False | `oracle_label_leakage_sentinel` |
| TRANSFORMER future-window leaky sequence | `transformer_future_leaky_score` | 0.5916 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete` |

## Per-Horizon Metrics

| horizon_h | score | auc | n | n_positive |
|---:|---|---:|---:|---:|
| 6 | `mlp_probe_valid_score` | 0.6668 | 989 | 50 |
| 6 | `mlp_probe_leaky_score` | 0.8914 | 989 | 50 |
| 6 | `mlp_lowdose_oracle_score` | 0.6939 | 989 | 50 |
| 6 | `lstm_valid_score` | 0.5894 | 989 | 50 |
| 6 | `lstm_future_leaky_score` | 0.6208 | 989 | 50 |
| 6 | `gru_valid_score` | 0.5731 | 989 | 50 |
| 6 | `gru_future_leaky_score` | 0.6232 | 989 | 50 |
| 6 | `transformer_valid_score` | 0.6125 | 989 | 50 |
| 6 | `transformer_future_leaky_score` | 0.6074 | 989 | 50 |
| 12 | `mlp_probe_valid_score` | 0.6635 | 830 | 43 |
| 12 | `mlp_probe_leaky_score` | 0.8883 | 830 | 43 |
| 12 | `mlp_lowdose_oracle_score` | 0.6700 | 830 | 43 |
| 12 | `lstm_valid_score` | 0.5851 | 830 | 43 |
| 12 | `lstm_future_leaky_score` | 0.6280 | 830 | 43 |
| 12 | `gru_valid_score` | 0.6019 | 830 | 43 |
| 12 | `gru_future_leaky_score` | 0.6175 | 830 | 43 |
| 12 | `transformer_valid_score` | 0.5814 | 830 | 43 |
| 12 | `transformer_future_leaky_score` | 0.5839 | 830 | 43 |
| 18 | `mlp_probe_valid_score` | 0.7591 | 710 | 36 |
| 18 | `mlp_probe_leaky_score` | 0.7986 | 710 | 36 |
| 18 | `mlp_lowdose_oracle_score` | 0.7627 | 710 | 36 |
| 18 | `lstm_valid_score` | 0.5457 | 710 | 36 |
| 18 | `lstm_future_leaky_score` | 0.6022 | 710 | 36 |
| 18 | `gru_valid_score` | 0.5251 | 710 | 36 |
| 18 | `gru_future_leaky_score` | 0.6124 | 710 | 36 |
| 18 | `transformer_valid_score` | 0.5460 | 710 | 36 |
| 18 | `transformer_future_leaky_score` | 0.5715 | 710 | 36 |

## Notes

Valid monitors only receive pre-anchor windows. Leaky monitors are trained
with post-anchor physiology and/or oracle onset information so LAMP can
separate performance from validity.
