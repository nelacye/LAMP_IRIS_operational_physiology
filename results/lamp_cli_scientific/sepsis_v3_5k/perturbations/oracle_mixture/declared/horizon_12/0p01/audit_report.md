# LAMP audit report: PhysioNet sepsis oracle mixture h12 lambda 0.01

## Executive summary

- Primary score: `mixed_score`
- Primary AUC: `0.6666`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `anchor_idx`
- Frozen before holdout: `public PhysioNet training_setA source table`, `horizons 6, 12, and 18 hours`, `pre-anchor feature extraction`, `valid early-warning score formula`, `future-physiology sentinel formula`, `oracle-label sentinel formula`, `visible-state matching variables`, `null-control seed and permutation count`, `LAMP thresholds`

Temporal violations:
- `oracle_label_sentinel_score` latest_offset_h=1

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `future_physiology_sentinel_score`, `oracle_label_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `oracle_label_sentinel_score`

## Negative controls

- noise_auc_mean: `0.4979`
- score_permutation_auc_mean: `0.5016`
- label_permutation_auc_mean: `0.4982`

## Sentinels

- `future_physiology` (future_physiology): column `future_physiology_sentinel_score`, AUC `0.6446`, expected `invalid post-anchor physiology comparator`
- `oracle_label` (oracle_label): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling label-adjacent leakage comparator`

## Sentinel relations

- `future_physiology`: gap `-0.0219`, proximity `2.8470`, Pearson `0.5411`, alert `False`
- `oracle_label`: gap `0.3334`, proximity `0.0921`, Pearson `0.0985`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0436`
- Matched rows: `4633`
- Matched strata: `231`

## Threshold sensitivity

- Fragile: `False`
- threshold `1.5000`: selected `0.3435`, enrichment `0.0344`
- threshold `2.5000`: selected `0.1040`, enrichment `0.0523`
- threshold `3.5000`: selected `0.0343`, enrichment `0.0634`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
