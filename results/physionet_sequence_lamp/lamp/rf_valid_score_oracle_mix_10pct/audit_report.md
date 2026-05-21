# LAMP audit report: PhysioNet/CinC 2019 raw PSV sequence bench

## Executive summary

- Primary score: `rf_valid_score_oracle_mix_10pct`
- Primary AUC: `0.8408`
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
- `oracle_label_sentinel_score` latest_offset_h=1.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `oracle_label_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `oracle_label_sentinel_score`

## Negative controls

- noise_auc_mean: `0.4997`
- score_permutation_auc_mean: `0.5019`
- label_permutation_auc_mean: `0.4999`

## Sentinels

- `future_physiology` (future_window_invalid_comparator): column `future_physiology_sentinel_score`, AUC `0.5499`, expected `higher_auc_than_valid_if_future_physiology_is_informative`
- `oracle_label` (oracle_label_leakage): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling_auc_or_high_proximity`

## Sentinel relations

- `future_physiology`: gap `-0.2909`, proximity `-0.0816`, Pearson `0.0840`, alert `False`
- `oracle_label`: gap `0.1592`, proximity `0.1212`, Pearson `0.4057`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0787`
- Matched rows: `6837`
- Matched strata: `81`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.1373`, enrichment `0.2064`
- threshold `0.4000`: selected `0.0642`, enrichment `0.4210`
- threshold `0.6000`: selected `0.0362`, enrichment `0.4380`
- threshold `0.8000`: selected `0.0016`, enrichment `0.4915`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
