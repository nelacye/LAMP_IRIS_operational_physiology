# LAMP audit report: PhysioNet/CinC 2019 raw PSV sequence bench

## Executive summary

- Primary score: `mlp_probe_valid_score_oracle_mix_1pct`
- Primary AUC: `0.7802`
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
- `oracle_label_sentinel_score` latest_offset_h=1.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `oracle_label_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `oracle_label_sentinel_score`

## Negative controls

- noise_auc_mean: `0.4997`
- score_permutation_auc_mean: `0.5005`
- label_permutation_auc_mean: `0.4975`

## Sentinels

- `future_physiology` (future_window_invalid_comparator): column `future_physiology_sentinel_score`, AUC `0.5499`, expected `higher_auc_than_valid_if_future_physiology_is_informative`
- `oracle_label` (oracle_label_leakage): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling_auc_or_high_proximity`

## Sentinel relations

- `future_physiology`: gap `-0.2303`, proximity `-0.0042`, Pearson `-0.0121`, alert `False`
- `oracle_label`: gap `0.2198`, proximity `0.0044`, Pearson `0.2161`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0688`
- Matched rows: `6837`
- Matched strata: `81`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.5971`, enrichment `0.0266`
- threshold `0.4000`: selected `0.3206`, enrichment `0.0698`
- threshold `0.6000`: selected `0.1507`, enrichment `0.1348`
- threshold `0.8000`: selected `0.0443`, enrichment `0.2158`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
