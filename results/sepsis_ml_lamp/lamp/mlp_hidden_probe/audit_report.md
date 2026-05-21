# LAMP audit report: Linear probe on MLP hidden activation

## Executive summary

- Primary score: `mlp_hidden_probe_score`
- Primary AUC: `0.8632`
- Audit-pass candidate: `True`
- Output classes: `audit_pass_candidate`, `oracle_label_leakage_sentinel`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `horizon_h`
- Frozen before holdout: `patient-level split`, `horizon list`, `model family`, `feature groups`, `contamination definitions`, `LAMP thresholds`, `random seed`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `future_physiology_sentinel_score`, `oracle_label_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.5000`
- score_permutation_auc_mean: `0.5011`
- label_permutation_auc_mean: `0.5001`

## Sentinels

- `future_physiology` (future_physiology): column `future_physiology_sentinel_score`, AUC `0.6846`, expected `post-anchor physiology comparator`
- `oracle_label` (oracle_label): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling label leakage comparator`

## Sentinel relations

- `future_physiology`: gap `-0.1785`, proximity `NA`, Pearson `0.1533`, alert `False`
- `oracle_label`: gap `0.1368`, proximity `NA`, Pearson `0.4872`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0773`
- Matched rows: `4958`
- Matched strata: `234`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.1568`, enrichment `0.1736`
- threshold `0.4000`: selected `0.0983`, enrichment `0.2666`
- threshold `0.6000`: selected `0.0680`, enrichment `0.3760`
- threshold `0.8000`: selected `0.0471`, enrichment `0.5023`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
