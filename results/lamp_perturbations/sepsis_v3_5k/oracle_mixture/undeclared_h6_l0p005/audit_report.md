# LAMP audit report: PhysioNet sepsis oracle mixture h6 lambda 0.005

## Executive summary

- Primary score: `mixed_score`
- Primary AUC: `0.6586`
- Audit-pass candidate: `False`
- Output classes: `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `valid_early_hidden_state_signal`

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

- noise_auc_mean: `0.4997`
- score_permutation_auc_mean: `0.4999`
- label_permutation_auc_mean: `0.5002`

## Sentinels

- `future_physiology` (future_physiology): column `future_physiology_sentinel_score`, AUC `0.6307`, expected `invalid post-anchor physiology comparator`
- `oracle_label` (oracle_label): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling label-adjacent leakage comparator`

## Sentinel relations

- `future_physiology`: gap `-0.0279`, proximity `-1.5538`, Pearson `0.5483`, alert `False`
- `oracle_label`: gap `0.3414`, proximity `0.0473`, Pearson `0.1044`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0351`
- Matched rows: `4681`
- Matched strata: `234`

## Threshold sensitivity

- Fragile: `False`
- threshold `1.5000`: selected `0.3487`, enrichment `0.0397`
- threshold `2.5000`: selected `0.1066`, enrichment `0.0620`
- threshold `3.5000`: selected `0.0355`, enrichment `0.0581`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
