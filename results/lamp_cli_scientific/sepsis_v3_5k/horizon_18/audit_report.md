# LAMP audit report: PhysioNet/CinC 2019 sepsis v3 5k existing score table

## Executive summary

- Primary score: `valid_early_warning_score`
- Primary AUC: `0.6249`
- Audit-pass candidate: `True`
- Output classes: `audit_pass_candidate`, `oracle_label_leakage_sentinel`, `valid_early_hidden_state_signal`

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

- noise_auc_mean: `0.5015`
- score_permutation_auc_mean: `0.4997`
- label_permutation_auc_mean: `0.5011`

## Sentinels

- `future_physiology` (future_physiology): column `future_physiology_sentinel_score`, AUC `0.6569`, expected `invalid post-anchor physiology comparator`
- `oracle_label` (oracle_label): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling label-adjacent leakage comparator`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0248`
- Matched rows: `4618`
- Matched strata: `233`

## Threshold sensitivity

- Fragile: `False`
- threshold `1.5000`: selected `0.3448`, enrichment `0.0230`
- threshold `2.5000`: selected `0.1043`, enrichment `0.0333`
- threshold `3.5000`: selected `0.0351`, enrichment `0.0306`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
