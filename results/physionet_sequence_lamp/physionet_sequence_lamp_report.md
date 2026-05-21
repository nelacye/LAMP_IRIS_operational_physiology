# PhysioNet/CinC 2019 Raw Sequence LAMP Benchmark

This run builds examples directly from raw `.psv` files, creates early-window
and future-window splits, trains valid and intentionally contaminated monitors,
and applies LAMP to the resulting prediction table.

- Source examples: 19508
- Held-out predictions: 6856
- Max patients: 8000
- Horizons: 6,12,18
- Early window: 12 hours
- Leakage lambdas: 0.01,0.05,0.10
- PyTorch available: True
- XGBoost available: True

## LAMP Diagnoses

| monitor | score | auc | audit_pass | temporal | forbidden | oracle proximity | output_classes |
|---|---|---:|:---:|:---:|:---:|:---:|---|
| MLP hand-crafted valid | `mlp_probe_valid_score` | 0.7792 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| mlp_probe oracle mix 1pct | `mlp_probe_valid_score_oracle_mix_1pct` | 0.7802 | False | False | False | False | `forbidden_feature_contamination;oracle_label_leakage_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| mlp_probe oracle mix 5pct | `mlp_probe_valid_score_oracle_mix_5pct` | 0.7840 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| mlp_probe oracle mix 10pct | `mlp_probe_valid_score_oracle_mix_10pct` | 0.7892 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| MLP hand-crafted leaky | `mlp_probe_leaky_score` | 0.9844 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| Oracle label leakage ceiling | `oracle_leakage_ceiling_score` | 1.0000 | False | False | False | False | `forbidden_feature_contamination;oracle_label_leakage_sentinel;temporal_isolation_incomplete;visible_state_confounding` |
| Random Forest valid | `rf_valid_score` | 0.8188 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| Random Forest oracle mix 1pct | `rf_valid_score_oracle_mix_1pct` | 0.8231 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| Random Forest oracle mix 5pct | `rf_valid_score_oracle_mix_5pct` | 0.8281 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| Random Forest oracle mix 10pct | `rf_valid_score_oracle_mix_10pct` | 0.8408 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| Random Forest future/oracle leaky | `rf_future_leaky_score` | 0.9986 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| HistGradientBoosting valid | `histgb_valid_score` | 0.8620 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| HistGradientBoosting oracle mix 1pct | `histgb_valid_score_oracle_mix_1pct` | 0.8694 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| HistGradientBoosting oracle mix 5pct | `histgb_valid_score_oracle_mix_5pct` | 0.8925 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| HistGradientBoosting oracle mix 10pct | `histgb_valid_score_oracle_mix_10pct` | 0.9117 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| HistGradientBoosting future/oracle leaky | `histgb_future_leaky_score` | 1.0000 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| XGBoost valid | `xgb_valid_score` | 0.8409 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| XGBoost oracle mix 1pct | `xgb_valid_score_oracle_mix_1pct` | 0.8421 | False | False | False | False | `forbidden_feature_contamination;oracle_label_leakage_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| XGBoost oracle mix 5pct | `xgb_valid_score_oracle_mix_5pct` | 0.8464 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| XGBoost oracle mix 10pct | `xgb_valid_score_oracle_mix_10pct` | 0.8510 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| XGBoost future/oracle leaky | `xgb_future_leaky_score` | 1.0000 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| LSTM valid sequence | `lstm_valid_score` | 0.6612 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| LSTM future-window leaky sequence | `lstm_future_leaky_score` | 0.6864 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| LSTM oracle mix 1pct | `lstm_valid_score_oracle_mix_1pct` | 0.6634 | False | False | False | False | `forbidden_feature_contamination;oracle_label_leakage_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| LSTM oracle mix 5pct | `lstm_valid_score_oracle_mix_5pct` | 0.6727 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| LSTM oracle mix 10pct | `lstm_valid_score_oracle_mix_10pct` | 0.6854 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| LSTM hidden-state probe | `lstm_hidden_probe_score` | 0.6488 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| LSTM future hidden-state probe | `lstm_future_hidden_probe_score` | 0.6797 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| GRU valid sequence | `gru_valid_score` | 0.6458 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| GRU future-window leaky sequence | `gru_future_leaky_score` | 0.6694 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| GRU oracle mix 1pct | `gru_valid_score_oracle_mix_1pct` | 0.6484 | False | False | False | False | `forbidden_feature_contamination;oracle_label_leakage_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| GRU oracle mix 5pct | `gru_valid_score_oracle_mix_5pct` | 0.6589 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| GRU oracle mix 10pct | `gru_valid_score_oracle_mix_10pct` | 0.6730 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| TRANSFORMER valid sequence | `transformer_valid_score` | 0.6490 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| TRANSFORMER future-window leaky sequence | `transformer_future_leaky_score` | 0.6917 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| TRANSFORMER oracle mix 1pct | `transformer_valid_score_oracle_mix_1pct` | 0.6513 | False | False | False | False | `forbidden_feature_contamination;oracle_label_leakage_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| TRANSFORMER oracle mix 5pct | `transformer_valid_score_oracle_mix_5pct` | 0.6609 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| TRANSFORMER oracle mix 10pct | `transformer_valid_score_oracle_mix_10pct` | 0.6739 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| TRANSFORMER hidden-state probe | `transformer_hidden_probe_score` | 0.6716 | True | True | True | False | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| TRANSFORMER future hidden-state probe | `transformer_future_hidden_probe_score` | 0.7056 | False | False | False | True | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |

## Per-Horizon Metrics

| horizon_h | score | auc | n | n_positive |
|---:|---|---:|---:|---:|
| 6 | `mlp_probe_valid_score` | 0.7798 | 2645 | 136 |
| 6 | `mlp_probe_leaky_score` | 0.9840 | 2645 | 136 |
| 6 | `mlp_probe_valid_score_oracle_mix_1pct` | 0.7813 | 2645 | 136 |
| 6 | `mlp_probe_valid_score_oracle_mix_5pct` | 0.7874 | 2645 | 136 |
| 6 | `mlp_probe_valid_score_oracle_mix_10pct` | 0.7957 | 2645 | 136 |
| 6 | `oracle_leakage_ceiling_score` | 1.0000 | 2645 | 136 |
| 6 | `rf_valid_score` | 0.8034 | 2645 | 136 |
| 6 | `rf_valid_score_oracle_mix_1pct` | 0.8077 | 2645 | 136 |
| 6 | `rf_valid_score_oracle_mix_5pct` | 0.8179 | 2645 | 136 |
| 6 | `rf_valid_score_oracle_mix_10pct` | 0.8372 | 2645 | 136 |
| 6 | `rf_future_leaky_score` | 0.9983 | 2645 | 136 |
| 6 | `histgb_valid_score` | 0.8622 | 2645 | 136 |
| 6 | `histgb_valid_score_oracle_mix_1pct` | 0.8721 | 2645 | 136 |
| 6 | `histgb_valid_score_oracle_mix_5pct` | 0.9023 | 2645 | 136 |
| 6 | `histgb_valid_score_oracle_mix_10pct` | 0.9237 | 2645 | 136 |
| 6 | `histgb_future_leaky_score` | 1.0000 | 2645 | 136 |
| 6 | `xgb_valid_score` | 0.8406 | 2645 | 136 |
| 6 | `xgb_valid_score_oracle_mix_1pct` | 0.8425 | 2645 | 136 |
| 6 | `xgb_valid_score_oracle_mix_5pct` | 0.8489 | 2645 | 136 |
| 6 | `xgb_valid_score_oracle_mix_10pct` | 0.8549 | 2645 | 136 |
| 6 | `xgb_future_leaky_score` | 1.0000 | 2645 | 136 |
| 6 | `lstm_valid_score` | 0.6907 | 2645 | 136 |
| 6 | `lstm_future_leaky_score` | 0.6873 | 2645 | 136 |
| 6 | `lstm_valid_score_oracle_mix_1pct` | 0.6941 | 2645 | 136 |
| 6 | `lstm_valid_score_oracle_mix_5pct` | 0.7073 | 2645 | 136 |
| 6 | `lstm_valid_score_oracle_mix_10pct` | 0.7248 | 2645 | 136 |
| 6 | `lstm_hidden_probe_score` | 0.6696 | 2645 | 136 |
| 6 | `lstm_future_hidden_probe_score` | 0.6908 | 2645 | 136 |
| 6 | `gru_valid_score` | 0.6733 | 2645 | 136 |
| 6 | `gru_future_leaky_score` | 0.6731 | 2645 | 136 |
| 6 | `gru_valid_score_oracle_mix_1pct` | 0.6768 | 2645 | 136 |
| 6 | `gru_valid_score_oracle_mix_5pct` | 0.6916 | 2645 | 136 |
| 6 | `gru_valid_score_oracle_mix_10pct` | 0.7110 | 2645 | 136 |
| 6 | `transformer_valid_score` | 0.6685 | 2645 | 136 |
| 6 | `transformer_future_leaky_score` | 0.7035 | 2645 | 136 |
| 6 | `transformer_valid_score_oracle_mix_1pct` | 0.6721 | 2645 | 136 |
| 6 | `transformer_valid_score_oracle_mix_5pct` | 0.6871 | 2645 | 136 |
| 6 | `transformer_valid_score_oracle_mix_10pct` | 0.7071 | 2645 | 136 |
| 6 | `transformer_hidden_probe_score` | 0.6868 | 2645 | 136 |
| 6 | `transformer_future_hidden_probe_score` | 0.7221 | 2645 | 136 |
| 12 | `mlp_probe_valid_score` | 0.8000 | 2254 | 123 |
| 12 | `mlp_probe_leaky_score` | 0.9897 | 2254 | 123 |
| 12 | `mlp_probe_valid_score_oracle_mix_1pct` | 0.8008 | 2254 | 123 |
| 12 | `mlp_probe_valid_score_oracle_mix_5pct` | 0.8037 | 2254 | 123 |
| 12 | `mlp_probe_valid_score_oracle_mix_10pct` | 0.8080 | 2254 | 123 |
| 12 | `oracle_leakage_ceiling_score` | 1.0000 | 2254 | 123 |
| 12 | `rf_valid_score` | 0.8221 | 2254 | 123 |
| 12 | `rf_valid_score_oracle_mix_1pct` | 0.8280 | 2254 | 123 |
| 12 | `rf_valid_score_oracle_mix_5pct` | 0.8290 | 2254 | 123 |
| 12 | `rf_valid_score_oracle_mix_10pct` | 0.8396 | 2254 | 123 |
| 12 | `rf_future_leaky_score` | 0.9989 | 2254 | 123 |
| 12 | `histgb_valid_score` | 0.8537 | 2254 | 123 |
| 12 | `histgb_valid_score_oracle_mix_1pct` | 0.8603 | 2254 | 123 |
| 12 | `histgb_valid_score_oracle_mix_5pct` | 0.8825 | 2254 | 123 |
| 12 | `histgb_valid_score_oracle_mix_10pct` | 0.9031 | 2254 | 123 |
| 12 | `histgb_future_leaky_score` | 1.0000 | 2254 | 123 |
| 12 | `xgb_valid_score` | 0.8299 | 2254 | 123 |
| 12 | `xgb_valid_score_oracle_mix_1pct` | 0.8307 | 2254 | 123 |
| 12 | `xgb_valid_score_oracle_mix_5pct` | 0.8341 | 2254 | 123 |
| 12 | `xgb_valid_score_oracle_mix_10pct` | 0.8381 | 2254 | 123 |
| 12 | `xgb_future_leaky_score` | 1.0000 | 2254 | 123 |
| 12 | `lstm_valid_score` | 0.6337 | 2254 | 123 |
| 12 | `lstm_future_leaky_score` | 0.6893 | 2254 | 123 |
| 12 | `lstm_valid_score_oracle_mix_1pct` | 0.6355 | 2254 | 123 |
| 12 | `lstm_valid_score_oracle_mix_5pct` | 0.6434 | 2254 | 123 |
| 12 | `lstm_valid_score_oracle_mix_10pct` | 0.6537 | 2254 | 123 |
| 12 | `lstm_hidden_probe_score` | 0.6109 | 2254 | 123 |
| 12 | `lstm_future_hidden_probe_score` | 0.6831 | 2254 | 123 |
| 12 | `gru_valid_score` | 0.6344 | 2254 | 123 |
| 12 | `gru_future_leaky_score` | 0.6698 | 2254 | 123 |
| 12 | `gru_valid_score_oracle_mix_1pct` | 0.6364 | 2254 | 123 |
| 12 | `gru_valid_score_oracle_mix_5pct` | 0.6448 | 2254 | 123 |
| 12 | `gru_valid_score_oracle_mix_10pct` | 0.6562 | 2254 | 123 |
| 12 | `transformer_valid_score` | 0.6590 | 2254 | 123 |
| 12 | `transformer_future_leaky_score` | 0.6832 | 2254 | 123 |
| 12 | `transformer_valid_score_oracle_mix_1pct` | 0.6607 | 2254 | 123 |
| 12 | `transformer_valid_score_oracle_mix_5pct` | 0.6681 | 2254 | 123 |
| 12 | `transformer_valid_score_oracle_mix_10pct` | 0.6782 | 2254 | 123 |
| 12 | `transformer_hidden_probe_score` | 0.6709 | 2254 | 123 |
| 12 | `transformer_future_hidden_probe_score` | 0.7051 | 2254 | 123 |
| 18 | `mlp_probe_valid_score` | 0.7812 | 1957 | 111 |
| 18 | `mlp_probe_leaky_score` | 0.9797 | 1957 | 111 |
| 18 | `mlp_probe_valid_score_oracle_mix_1pct` | 0.7818 | 1957 | 111 |
| 18 | `mlp_probe_valid_score_oracle_mix_5pct` | 0.7841 | 1957 | 111 |
| 18 | `mlp_probe_valid_score_oracle_mix_10pct` | 0.7871 | 1957 | 111 |
| 18 | `oracle_leakage_ceiling_score` | 1.0000 | 1957 | 111 |
| 18 | `rf_valid_score` | 0.8332 | 1957 | 111 |
| 18 | `rf_valid_score_oracle_mix_1pct` | 0.8366 | 1957 | 111 |
| 18 | `rf_valid_score_oracle_mix_5pct` | 0.8384 | 1957 | 111 |
| 18 | `rf_valid_score_oracle_mix_10pct` | 0.8466 | 1957 | 111 |
| 18 | `rf_future_leaky_score` | 0.9986 | 1957 | 111 |
| 18 | `histgb_valid_score` | 0.8748 | 1957 | 111 |
| 18 | `histgb_valid_score_oracle_mix_1pct` | 0.8796 | 1957 | 111 |
| 18 | `histgb_valid_score_oracle_mix_5pct` | 0.8974 | 1957 | 111 |
| 18 | `histgb_valid_score_oracle_mix_10pct` | 0.9145 | 1957 | 111 |
| 18 | `histgb_future_leaky_score` | 1.0000 | 1957 | 111 |
| 18 | `xgb_valid_score` | 0.8573 | 1957 | 111 |
| 18 | `xgb_valid_score_oracle_mix_1pct` | 0.8580 | 1957 | 111 |
| 18 | `xgb_valid_score_oracle_mix_5pct` | 0.8612 | 1957 | 111 |
| 18 | `xgb_valid_score_oracle_mix_10pct` | 0.8652 | 1957 | 111 |
| 18 | `xgb_future_leaky_score` | 1.0000 | 1957 | 111 |
| 18 | `lstm_valid_score` | 0.6662 | 1957 | 111 |
| 18 | `lstm_future_leaky_score` | 0.6818 | 1957 | 111 |
| 18 | `lstm_valid_score_oracle_mix_1pct` | 0.6678 | 1957 | 111 |
| 18 | `lstm_valid_score_oracle_mix_5pct` | 0.6747 | 1957 | 111 |
| 18 | `lstm_valid_score_oracle_mix_10pct` | 0.6841 | 1957 | 111 |
| 18 | `lstm_hidden_probe_score` | 0.6698 | 1957 | 111 |
| 18 | `lstm_future_hidden_probe_score` | 0.6601 | 1957 | 111 |
| 18 | `gru_valid_score` | 0.6276 | 1957 | 111 |
| 18 | `gru_future_leaky_score` | 0.6663 | 1957 | 111 |
| 18 | `gru_valid_score_oracle_mix_1pct` | 0.6295 | 1957 | 111 |
| 18 | `gru_valid_score_oracle_mix_5pct` | 0.6373 | 1957 | 111 |
| 18 | `gru_valid_score_oracle_mix_10pct` | 0.6475 | 1957 | 111 |
| 18 | `transformer_valid_score` | 0.6218 | 1957 | 111 |
| 18 | `transformer_future_leaky_score` | 0.6906 | 1957 | 111 |
| 18 | `transformer_valid_score_oracle_mix_1pct` | 0.6232 | 1957 | 111 |
| 18 | `transformer_valid_score_oracle_mix_5pct` | 0.6290 | 1957 | 111 |
| 18 | `transformer_valid_score_oracle_mix_10pct` | 0.6371 | 1957 | 111 |
| 18 | `transformer_hidden_probe_score` | 0.6533 | 1957 | 111 |
| 18 | `transformer_future_hidden_probe_score` | 0.6855 | 1957 | 111 |

## Notes

Valid monitors only receive pre-anchor windows. Leaky monitors are trained
with post-anchor physiology and/or oracle onset information so LAMP can
separate performance from validity.
