# LAMP audit report: NASA C-MAPSS FD001: future_rul_leaky

## Executive summary

- Primary score: `future_rul_leaky_score`
- Primary AUC: `1.0000`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `temporal_isolation_incomplete`, `visible_state_confounding`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `cycle`
- Frozen before holdout: `FD001 engine-level split`, `near-failure horizon`, `valid current-cycle feature set`, `oracle mixture grid`, `LAMP thresholds`

Temporal violations:
- `future_sensor_mean` latest_offset_h=10.0
- `future_sensor_slope` latest_offset_h=10.0
- `oracle_rul_score` latest_offset_h=999.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `future_sensor_mean`, `future_sensor_slope`, `oracle_rul_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `future_sensor_mean`, `future_sensor_slope`, `oracle_rul_score`

## Negative controls

- noise_auc_mean: `0.4992`
- score_permutation_auc_mean: `0.4990`
- label_permutation_auc_mean: `0.4995`

## Sentinels

- `future_physiology` (future_physiology): column `future_sensor_mean`, AUC `0.8966`, expected `post-anchor sensor trajectory comparator`
- `future_physiology_slope` (future_physiology): column `future_sensor_slope`, AUC `0.6783`, expected `post-anchor sensor trajectory slope comparator`
- `oracle_label` (oracle_label): column `oracle_rul_score`, AUC `1.0000`, expected `true remaining-useful-life derived comparator`

## Sentinel relations

- `future_physiology`: gap `-0.1034`, proximity `-19.2221`, Pearson `0.6392`, alert `False`
- `future_physiology_slope`: gap `-0.3217`, proximity `-0.4398`, Pearson `0.3114`, alert `False`
- `oracle_label`: gap `0.0000`, proximity `1.0000`, Pearson `1.0000`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0000`
- Matched rows: `463`
- Matched strata: `12`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2500`: selected `0.6000`, enrichment `0.4000`
- threshold `0.5000`: selected `0.6000`, enrichment `0.4000`
- threshold `0.7500`: selected `0.6000`, enrichment `0.4000`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
