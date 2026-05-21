# LAMP audit report: Existing locked early score

## Executive summary

- Primary score: `existing_valid_early_warning_score`
- Primary AUC: `0.6145`
- Audit-pass candidate: `False`
- Output classes: `oracle_label_leakage_sentinel`

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
- score_permutation_auc_mean: `0.5007`
- label_permutation_auc_mean: `0.5000`

## Sentinels

- `future_physiology` (future_physiology): column `future_physiology_sentinel_score`, AUC `0.6846`, expected `post-anchor physiology comparator`
- `oracle_label` (oracle_label): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling label leakage comparator`

## Sentinel relations

- `future_physiology`: gap `0.0701`, proximity `NA`, Pearson `0.5303`, alert `False`
- `oracle_label`: gap `0.3855`, proximity `NA`, Pearson `0.0635`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0094`
- Matched rows: `4958`
- Matched strata: `234`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.9935`, enrichment `0.0003`
- threshold `0.4000`: selected `0.9285`, enrichment `0.0019`
- threshold `0.6000`: selected `0.8209`, enrichment `0.0052`
- threshold `0.8000`: selected `0.6900`, enrichment `0.0093`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
