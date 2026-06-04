# LAMP audit report: Metric-blind leakage synthetic control lambda=0

## Executive summary

- Primary score: `mixed_score_l0p0`
- Primary AUC: `0.8299`
- Audit-pass candidate: `True`
- Output classes: `audit_pass_candidate`, `oracle_label_leakage_sentinel`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time_h`
- Frozen before holdout: `synthetic data-generating process`, `valid score`, `oracle mixture grid`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `future_score`, `oracle_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.5000`
- score_permutation_auc_mean: `0.4994`
- label_permutation_auc_mean: `0.5001`

## Sentinels

- `future_physiology` (future_physiology): column `future_score`, AUC `0.8731`, expected `invalid post-anchor comparator`
- `oracle_label` (oracle_label): column `oracle_score`, AUC `1.0000`, expected `known ceiling label-adjacent leakage`

## Sentinel relations

- `future_physiology`: gap `0.0432`, proximity `0.0000`, Pearson `0.7145`, alert `False`
- `oracle_label`: gap `0.1701`, proximity `0.0000`, Pearson `0.5707`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.3066`
- Matched rows: `20000`
- Matched strata: `16`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2500`: selected `0.7027`, enrichment `0.1464`
- threshold `0.5000`: selected `0.4987`, enrichment `0.2495`
- threshold `0.7500`: selected `0.2947`, enrichment `0.3540`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
