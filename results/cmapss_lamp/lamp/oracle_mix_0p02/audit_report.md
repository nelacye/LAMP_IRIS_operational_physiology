# LAMP audit report: NASA C-MAPSS FD001: oracle_mix_0p02

## Executive summary

- Primary score: `oracle_mix_l0p02`
- Primary AUC: `0.9091`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `cycle`
- Frozen before holdout: `FD001 engine-level split`, `near-failure horizon`, `valid current-cycle feature set`, `oracle mixture grid`, `LAMP thresholds`

Temporal violations:
- `oracle_rul_score` latest_offset_h=999.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `future_sensor_mean`, `future_sensor_slope`, `oracle_rul_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `oracle_rul_score`

## Negative controls

- noise_auc_mean: `0.4992`
- score_permutation_auc_mean: `0.4989`
- label_permutation_auc_mean: `0.5004`

## Sentinels

- `future_physiology` (future_physiology): column `future_sensor_mean`, AUC `0.8966`, expected `post-anchor sensor trajectory comparator`
- `future_physiology_slope` (future_physiology): column `future_sensor_slope`, AUC `0.6783`, expected `post-anchor sensor trajectory slope comparator`
- `oracle_label` (oracle_label): column `oracle_rul_score`, AUC `1.0000`, expected `true remaining-useful-life derived comparator`

## Sentinel relations

- `future_physiology`: gap `-0.0125`, proximity `-1.4458`, Pearson `0.7921`, alert `False`
- `future_physiology_slope`: gap `-0.2309`, proximity `-0.0331`, Pearson `0.2601`, alert `False`
- `oracle_label`: gap `0.0909`, proximity `0.0752`, Pearson `0.6938`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0266`
- Matched rows: `596`
- Matched strata: `17`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2500`: selected `0.8621`, enrichment `0.0781`
- threshold `0.5000`: selected `0.6879`, enrichment `0.1898`
- threshold `0.7500`: selected `0.5158`, enrichment `0.3055`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
