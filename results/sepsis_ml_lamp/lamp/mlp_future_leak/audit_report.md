# LAMP audit report: MLP future-window contaminated model

## Executive summary

- Primary score: `mlp_future_leak_score`
- Primary AUC: `0.8431`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `oracle_label_leakage_sentinel`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `horizon_h`
- Frozen before holdout: `patient-level split`, `horizon list`, `model family`, `feature groups`, `contamination definitions`, `LAMP thresholds`, `random seed`

Temporal violations:
- `future_HR_last` latest_offset_h=1.0
- `future_HR_recent_mean` latest_offset_h=1.0
- `future_HR_recent_slope` latest_offset_h=1.0
- `future_O2Sat_last` latest_offset_h=1.0
- `future_O2Sat_recent_mean` latest_offset_h=1.0
- `future_O2Sat_recent_slope` latest_offset_h=1.0
- `future_Temp_last` latest_offset_h=1.0
- `future_Temp_recent_mean` latest_offset_h=1.0
- `future_Temp_recent_slope` latest_offset_h=1.0
- `future_SBP_last` latest_offset_h=1.0
- `future_SBP_recent_mean` latest_offset_h=1.0
- `future_SBP_recent_slope` latest_offset_h=1.0
- `future_MAP_last` latest_offset_h=1.0
- `future_MAP_recent_mean` latest_offset_h=1.0
- `future_MAP_recent_slope` latest_offset_h=1.0
- `future_DBP_last` latest_offset_h=1.0
- `future_DBP_recent_mean` latest_offset_h=1.0
- `future_DBP_recent_slope` latest_offset_h=1.0
- `future_Resp_last` latest_offset_h=1.0
- `future_Resp_recent_mean` latest_offset_h=1.0
- `future_Resp_recent_slope` latest_offset_h=1.0
- `future_Lactate_last` latest_offset_h=1.0
- `future_Lactate_recent_mean` latest_offset_h=1.0
- `future_Lactate_recent_slope` latest_offset_h=1.0
- `future_WBC_last` latest_offset_h=1.0
- `future_WBC_recent_mean` latest_offset_h=1.0
- `future_WBC_recent_slope` latest_offset_h=1.0
- `future_Creatinine_last` latest_offset_h=1.0
- `future_Creatinine_recent_mean` latest_offset_h=1.0
- `future_Creatinine_recent_slope` latest_offset_h=1.0
- `future_BUN_last` latest_offset_h=1.0
- `future_BUN_recent_mean` latest_offset_h=1.0
- `future_BUN_recent_slope` latest_offset_h=1.0
- `future_Platelets_last` latest_offset_h=1.0
- `future_Platelets_recent_mean` latest_offset_h=1.0
- `future_Platelets_recent_slope` latest_offset_h=1.0
- `future_Bilirubin_total_last` latest_offset_h=1.0
- `future_Bilirubin_total_recent_mean` latest_offset_h=1.0
- `future_Bilirubin_total_recent_slope` latest_offset_h=1.0
- `future_Age` latest_offset_h=1.0
- `future_Gender` latest_offset_h=1.0
- `future_HospAdmTime` latest_offset_h=1.0
- `future_ICULOS` latest_offset_h=1.0
- `future_vital_missing_rate` latest_offset_h=1.0
- `future_lab_missing_rate` latest_offset_h=1.0
- `future_n_hours_used` latest_offset_h=1.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `future_physiology_sentinel_score`, `oracle_label_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `future_Age`, `future_BUN_last`, `future_BUN_recent_mean`, `future_BUN_recent_slope`, `future_Bilirubin_total_last`, `future_Bilirubin_total_recent_mean`, `future_Bilirubin_total_recent_slope`, `future_Creatinine_last`, `future_Creatinine_recent_mean`, `future_Creatinine_recent_slope`, `future_DBP_last`, `future_DBP_recent_mean`, `future_DBP_recent_slope`, `future_Gender`, `future_HR_last`, `future_HR_recent_mean`, `future_HR_recent_slope`, `future_HospAdmTime`, `future_ICULOS`, `future_Lactate_last`, `future_Lactate_recent_mean`, `future_Lactate_recent_slope`, `future_MAP_last`, `future_MAP_recent_mean`, `future_MAP_recent_slope`, `future_O2Sat_last`, `future_O2Sat_recent_mean`, `future_O2Sat_recent_slope`, `future_Platelets_last`, `future_Platelets_recent_mean`, `future_Platelets_recent_slope`, `future_Resp_last`, `future_Resp_recent_mean`, `future_Resp_recent_slope`, `future_SBP_last`, `future_SBP_recent_mean`, `future_SBP_recent_slope`, `future_Temp_last`, `future_Temp_recent_mean`, `future_Temp_recent_slope`, `future_WBC_last`, `future_WBC_recent_mean`, `future_WBC_recent_slope`, `future_lab_missing_rate`, `future_n_hours_used`, `future_vital_missing_rate`

## Negative controls

- noise_auc_mean: `0.5000`
- score_permutation_auc_mean: `0.4999`
- label_permutation_auc_mean: `0.4991`

## Sentinels

- `future_physiology` (future_physiology): column `future_physiology_sentinel_score`, AUC `0.6846`, expected `post-anchor physiology comparator`
- `oracle_label` (oracle_label): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling label leakage comparator`

## Sentinel relations

- `future_physiology`: gap `-0.1585`, proximity `0.0724`, Pearson `0.1427`, alert `False`
- `oracle_label`: gap `0.1569`, proximity `-0.0856`, Pearson `0.3903`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0749`
- Matched rows: `4958`
- Matched strata: `234`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.4857`, enrichment `0.0416`
- threshold `0.4000`: selected `0.2203`, enrichment `0.1136`
- threshold `0.6000`: selected `0.0711`, enrichment `0.3128`
- threshold `0.8000`: selected `0.0300`, enrichment `0.6210`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
