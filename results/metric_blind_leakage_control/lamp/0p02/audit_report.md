# LAMP audit report: Metric-blind leakage synthetic control lambda=0.02

## Executive summary

- Primary score: `mixed_score_l0p02`
- Primary AUC: `0.8425`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `anchor_time_h`
- Frozen before holdout: `synthetic data-generating process`, `valid score`, `oracle mixture grid`, `LAMP thresholds`

Temporal violations:
- `oracle_score` latest_offset_h=999.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `future_score`, `oracle_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `oracle_score`

## Negative controls

- noise_auc_mean: `0.5000`
- score_permutation_auc_mean: `0.4994`
- label_permutation_auc_mean: `0.5001`

## Sentinels

- `future_physiology` (future_physiology): column `future_score`, AUC `0.8731`, expected `invalid post-anchor comparator`
- `oracle_label` (oracle_label): column `oracle_score`, AUC `1.0000`, expected `known ceiling label-adjacent leakage`

## Sentinel relations

- `future_physiology`: gap `0.0306`, proximity `0.2914`, Pearson `0.7217`, alert `False`
- `oracle_label`: gap `0.1575`, proximity `0.0741`, Pearson `0.5918`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.3310`
- Matched rows: `20000`
- Matched strata: `16`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2500`: selected `0.7037`, enrichment `0.1507`
- threshold `0.5000`: selected `0.4978`, enrichment `0.2574`
- threshold `0.7500`: selected `0.2933`, enrichment `0.3679`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
