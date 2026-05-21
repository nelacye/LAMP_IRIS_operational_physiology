# LAMP audit report: Synthetic hidden-state demo

## Executive summary

- Primary score: `valid_score`
- Primary AUC: `1.0000`
- Audit-pass candidate: `True`
- Output classes: `audit_pass_candidate`, `oracle_label_leakage_sentinel`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time_h`
- Frozen before holdout: `score definition`, `visible-state matching columns`, `sentinel columns`, `null-control seed`, `audit thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `future_score`, `oracle_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.4974`
- score_permutation_auc_mean: `0.5093`
- label_permutation_auc_mean: `0.4834`

## Sentinels

- `future_physiology` (future_physiology): column `future_score`, AUC `1.0000`, expected `invalid post-anchor comparator`
- `oracle_label` (oracle_label): column `oracle_score`, AUC `1.0000`, expected `ceiling label-adjacent leakage`

## Sentinel relations

- `future_physiology`: gap `0.0000`, proximity `NA`, Pearson `0.9688`, alert `False`
- `oracle_label`: gap `0.0000`, proximity `NA`, Pearson `0.9543`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `1.0000`
- Matched rows: `40`
- Matched strata: `4`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.4000`: selected `0.5500`, enrichment `0.4091`
- threshold `0.5000`: selected `0.5000`, enrichment `0.5000`
- threshold `0.6000`: selected `0.5000`, enrichment `0.5000`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
