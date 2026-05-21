# LAMP-CriticalCare Battery

Benchmark A is the existing PhysioNet/CinC 2019 sepsis v3_5k audit.
Cardiac-arrest-risk and GIB cohorts are included when the credentialed Clinical Trajectory Flow ICU CSV files are present locally.

| benchmark | window_h | n | n_positive | valid_auc | future_sentinel_auc | oracle_auc | matched_delta | audit_pass | output_classes |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|---|
| physionet_cinc_2019_sepsis | 6 | 4869 | 280 | 0.641621 | 0.630712 | 1.000000 | 0.029066 | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| physionet_cinc_2019_sepsis | 12 | 4836 | 247 | 0.632763 | 0.644646 | 1.000000 | 0.028062 | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| physionet_cinc_2019_sepsis | 18 | 4812 | 223 | 0.624875 | 0.656924 | 1.000000 | 0.024776 | True | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |

## Access Note

Clinical Trajectory Flow ICU is PhysioNet credentialed access, not open access. It requires CITI Data or Specimens Only Research training and a signed DUA.

## Interpretation Boundary

These audits test failure-mode separation, not clinical deployment readiness.
