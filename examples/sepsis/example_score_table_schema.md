# PhysioNet/CinC 2019 Sepsis Score Table Schema

This benchmark should be exported as a locked score table before running LAMP.
The audit table is not the raw ICU time series; it is the frozen prediction table
plus audit comparators.

Required columns:

- `patient_id`: stable patient identifier.
- `anchor_hour`: prediction anchor hour. Valid features must be computed at or before this hour.
- `sepsis_within_horizon`: binary label for the frozen horizon.
- `valid_early_warning_score`: score produced only from declared pre-anchor features.
- `future_physiology_sentinel_score`: comparator using post-anchor physiology. This is deliberately invalid and must be declared as a sentinel.
- `oracle_label_sentinel_score`: comparator using label-adjacent future information. This is deliberately invalid and must be declared as a sentinel.
- `age`, `pre_anchor_hr_summary`, `pre_anchor_rr_summary`, `pre_anchor_spo2_summary`, `pre_anchor_sbp_summary`, `missingness_burden_pre_anchor`: visible-state matching variables.

Locked-design requirements:

- State exactly which public training partition is the design cohort and which is the locked holdout cohort.
- Freeze horizons, features, score construction, matching variables, sentinels, forbidden-feature rules, and thresholds before holdout evaluation.
- The oracle sentinel is not leakage in the valid model. It is an audit comparator and is only a violation if the valid score uses `oracle_label_sentinel_score`, `onset_distance_hours`, or equivalent label-adjacent features.
- The future-physiology sentinel is not leakage in the valid model. It is an invalid comparator and is only a violation if the valid score uses post-anchor physiology.
- The valid score must not use post-anchor physiology.
