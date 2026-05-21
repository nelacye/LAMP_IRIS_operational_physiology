# LAMP audit report: PhysioNet/CinC 2019 raw PSV sequence bench

## Executive summary

- Primary score: `transformer_valid_score`
- Primary AUC: `0.5827`
- Audit-pass candidate: `False`
- Output classes: `oracle_label_leakage_sentinel`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_idx`
- Frozen before holdout: `patient split`, `horizon definitions`, `feature roles`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `oracle_label_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.4982`
- score_permutation_auc_mean: `0.4932`
- label_permutation_auc_mean: `0.5024`

## Sentinels

- `future_physiology` (future_window_invalid_comparator): column `future_physiology_sentinel_score`, AUC `0.5450`, expected `higher_auc_than_valid_if_future_physiology_is_informative`
- `oracle_label` (oracle_label_leakage): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling_auc_or_high_proximity`

## Sentinel relations

- `future_physiology`: gap `-0.0377`, proximity `NA`, Pearson `0.2089`, alert `False`
- `oracle_label`: gap `0.4173`, proximity `NA`, Pearson `0.0852`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0023`
- Matched rows: `2518`
- Matched strata: `81`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.9775`, enrichment `0.0008`
- threshold `0.4000`: selected `0.5085`, enrichment `0.0089`
- threshold `0.6000`: selected `0.1546`, enrichment `0.0411`
- threshold `0.8000`: selected `0.0047`, enrichment `0.1157`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
