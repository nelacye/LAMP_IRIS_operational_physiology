# LAMP CLI scientific run: PhysioNet/CinC 2019 sepsis v3 5k

This report re-runs the installable `lamp audit` CLI on the frozen v3 5k score table, separately for 6, 12, and 18 hour horizons.

| horizon_h | n | n_positive | valid_auc | future_auc | oracle_auc | noise_auc | score_perm_auc | label_perm_auc | matched_delta | audit_pass | output_classes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---|
| 6 | 4869 | 280 | 0.641621 | 0.630712 | 1.000000 | 0.499970 | 0.500518 | 0.500966 | 0.029066 | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| 12 | 4836 | 247 | 0.632763 | 0.644646 | 1.000000 | 0.499750 | 0.500588 | 0.498182 | 0.028062 | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| 18 | 4812 | 223 | 0.624875 | 0.656924 | 1.000000 | 0.501511 | 0.499681 | 0.501071 | 0.024776 | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |

## Claim boundary

Survives LAMP does not mean clinically valid. In this benchmark it means the frozen early-warning score survived the configured failure-mode audit and earns prospective testing.
