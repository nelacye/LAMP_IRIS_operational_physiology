# LAMP audit report: NASA C-MAPSS FD001: valid_hgb

## Executive summary

- Primary score: `valid_score`
- Primary AUC: `0.9017`
- Audit-pass candidate: `True`
- Output classes: `audit_pass_candidate`, `oracle_label_leakage_sentinel`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `cycle`
- Frozen before holdout: `FD001 engine-level split`, `near-failure horizon`, `valid current-cycle feature set`, `oracle mixture grid`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `future_sensor_mean`, `future_sensor_slope`, `oracle_rul_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.4992`
- score_permutation_auc_mean: `0.4989`
- label_permutation_auc_mean: `0.5004`

## Sentinels

- `future_physiology` (future_physiology): column `future_sensor_mean`, AUC `0.8966`, expected `post-anchor sensor trajectory comparator`
- `future_physiology_slope` (future_physiology): column `future_sensor_slope`, AUC `0.6783`, expected `post-anchor sensor trajectory slope comparator`
- `oracle_label` (oracle_label): column `oracle_rul_score`, AUC `1.0000`, expected `true remaining-useful-life derived comparator`

## Sentinel relations

- `future_physiology`: gap `-0.0051`, proximity `-0.0000`, Pearson `0.7891`, alert `False`
- `future_physiology_slope`: gap `-0.2235`, proximity `-0.0000`, Pearson `0.2559`, alert `False`
- `oracle_label`: gap `0.0983`, proximity `0.0000`, Pearson `0.6773`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0199`
- Matched rows: `596`
- Matched strata: `17`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2500`: selected `0.8617`, enrichment `0.0755`
- threshold `0.5000`: selected `0.6904`, enrichment `0.1821`
- threshold `0.7500`: selected `0.5171`, enrichment `0.3001`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
