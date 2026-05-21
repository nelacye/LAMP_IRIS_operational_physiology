# LAMP audit report: Linear sequential-feature model

## Executive summary

- Primary score: `linear_sequence_score`
- Primary AUC: `0.9669`
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
- score_permutation_auc_mean: `0.5000`
- label_permutation_auc_mean: `0.5011`

## Sentinels

- `future_physiology` (future_physiology): column `future_physiology_sentinel_score`, AUC `0.6846`, expected `post-anchor physiology comparator`
- `oracle_label` (oracle_label): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling label leakage comparator`

## Sentinel relations

- `future_physiology`: gap `-0.2823`, proximity `NA`, Pearson `0.1590`, alert `False`
- `oracle_label`: gap `0.0331`, proximity `NA`, Pearson `0.5950`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0943`
- Matched rows: `4958`
- Matched strata: `234`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.2390`, enrichment `0.1511`
- threshold `0.4000`: selected `0.1482`, enrichment `0.2478`
- threshold `0.6000`: selected `0.0879`, enrichment `0.4118`
- threshold `0.8000`: selected `0.0491`, enrichment `0.6407`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
