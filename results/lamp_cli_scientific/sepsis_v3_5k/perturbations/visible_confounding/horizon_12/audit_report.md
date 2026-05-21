# LAMP audit report: PhysioNet sepsis visible-only score h12

## Executive summary

- Primary score: `visible_only_score`
- Primary AUC: `0.5777`
- Audit-pass candidate: `False`
- Output classes: `null_or_destroyed_signal`, `oracle_label_leakage_sentinel`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_idx`
- Frozen before holdout: `public PhysioNet training_setA source table`, `horizons 6, 12, and 18 hours`, `pre-anchor feature extraction`, `valid early-warning score formula`, `future-physiology sentinel formula`, `oracle-label sentinel formula`, `visible-state matching variables`, `null-control seed and permutation count`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `future_physiology_sentinel_score`, `oracle_label_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.4979`
- score_permutation_auc_mean: `0.5013`
- label_permutation_auc_mean: `0.4986`

## Sentinels

- `future_physiology` (future_physiology): column `future_physiology_sentinel_score`, AUC `0.6446`, expected `invalid post-anchor physiology comparator`
- `oracle_label` (oracle_label): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling label-adjacent leakage comparator`

## Sentinel relations

- `future_physiology`: gap `0.0670`, proximity `-4.6368`, Pearson `0.2310`, alert `False`
- `oracle_label`: gap `0.4223`, proximity `-0.1500`, Pearson `0.0549`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0022`
- Matched rows: `4460`
- Matched strata: `223`

## Threshold sensitivity

- Fragile: `False`
- threshold `1.5000`: selected `0.9599`, enrichment `0.0008`
- threshold `2.5000`: selected `0.8925`, enrichment `0.0018`
- threshold `3.5000`: selected `0.7603`, enrichment `0.0030`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
