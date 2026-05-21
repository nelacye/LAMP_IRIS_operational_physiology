# LAMP audit report: PhysioNet/CinC 2019 raw PSV sequence bench

## Executive summary

- Primary score: `transformer_future_leaky_score`
- Primary AUC: `0.6917`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

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

- noise_auc_mean: `0.4997`
- score_permutation_auc_mean: `0.4977`
- label_permutation_auc_mean: `0.4993`

## Sentinels

- `future_physiology` (future_window_invalid_comparator): column `future_physiology_sentinel_score`, AUC `0.5499`, expected `higher_auc_than_valid_if_future_physiology_is_informative`
- `oracle_label` (oracle_label_leakage): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling_auc_or_high_proximity`

## Sentinel relations

- `future_physiology`: gap `-0.1418`, proximity `-0.4307`, Pearson `0.1731`, alert `False`
- `oracle_label`: gap `0.3083`, proximity `0.1217`, Pearson `0.1439`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0506`
- Matched rows: `6837`
- Matched strata: `81`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.9942`, enrichment `0.0003`
- threshold `0.4000`: selected `0.6644`, enrichment `0.0187`
- threshold `0.6000`: selected `0.2322`, enrichment `0.0528`
- threshold `0.8000`: selected `0.0233`, enrichment `0.0648`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
