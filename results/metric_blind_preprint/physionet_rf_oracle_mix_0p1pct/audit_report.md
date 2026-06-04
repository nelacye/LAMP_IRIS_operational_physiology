# LAMP audit report: PhysioNet/CinC 2019 raw PSV sequence bench

## Executive summary

- Primary score: `rf_valid_score_oracle_mix_0p1pct`
- Primary AUC: `0.8198`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `oracle_label_leakage_sentinel`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `anchor_idx`
- Frozen before holdout: `patient split`, `horizon definitions`, `feature roles`

Temporal violations:
- `oracle_label_sentinel_score` latest_offset_h=999.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `oracle_label_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `oracle_label_sentinel_score`

## Negative controls

- noise_auc_mean: `0.4997`
- score_permutation_auc_mean: `0.5017`
- label_permutation_auc_mean: `0.5001`

## Sentinels

- `future_physiology` (future_window_invalid_comparator): column `future_physiology_sentinel_score`, AUC `0.5499`, expected `higher_auc_than_valid_if_future_physiology_is_informative`
- `oracle_label` (oracle_label_leakage): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling_auc_or_high_proximity`

## Sentinel relations

- `future_physiology`: gap `-0.2699`, proximity `-0.0035`, Pearson `0.0836`, alert `False`
- `oracle_label`: gap `0.1802`, proximity `0.0052`, Pearson `0.3911`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0682`
- Matched rows: `6837`
- Matched strata: `81`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.1613`, enrichment `0.1694`
- threshold `0.4000`: selected `0.0688`, enrichment `0.4015`
- threshold `0.6000`: selected `0.0458`, enrichment `0.4269`
- threshold `0.8000`: selected `0.0098`, enrichment `0.3789`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
