# LAMP audit report: PhysioNet/CinC 2019 raw PSV sequence bench

## Executive summary

- Primary score: `transformer_future_leaky_score`
- Primary AUC: `0.5916`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `temporal_isolation_incomplete`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `anchor_idx`
- Frozen before holdout: `patient split`, `horizon definitions`, `feature roles`

Temporal violations:
- `future_sequence_window` latest_offset_h=1.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `oracle_label_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `future_sequence_window`

## Negative controls

- noise_auc_mean: `0.4982`
- score_permutation_auc_mean: `0.4942`
- label_permutation_auc_mean: `0.5056`

## Sentinels

- `future_physiology` (future_window_invalid_comparator): column `future_physiology_sentinel_score`, AUC `0.5450`, expected `higher_auc_than_valid_if_future_physiology_is_informative`
- `oracle_label` (oracle_label_leakage): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling_auc_or_high_proximity`

## Sentinel relations

- `future_physiology`: gap `-0.0466`, proximity `-0.2352`, Pearson `0.1312`, alert `False`
- `oracle_label`: gap `0.4084`, proximity `0.0212`, Pearson `0.0721`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0119`
- Matched rows: `2518`
- Matched strata: `81`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.7552`, enrichment `0.0040`
- threshold `0.4000`: selected `0.3926`, enrichment `0.0144`
- threshold `0.6000`: selected `0.1609`, enrichment `0.0448`
- threshold `0.8000`: selected `0.0225`, enrichment `0.0718`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
