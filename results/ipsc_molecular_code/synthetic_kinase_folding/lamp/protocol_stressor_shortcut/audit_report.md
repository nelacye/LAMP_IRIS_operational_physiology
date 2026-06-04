# LAMP audit report: Synthetic iPSC molecular-code audit: Protocol/stressor shortcut

## Executive summary

- Primary score: `protocol_stressor_shortcut_score`
- Primary AUC: `0.6633`
- Inverted AUC: `0.3367`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `future_physiology_invalid_comparator`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `valid_early_hidden_state_signal`

Primary AUC = 0.663; inverted AUC = 0.337. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time`
- Frozen before holdout: `synthetic generator seed`, `molecular-code biological contract`, `monitor score family definitions`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `future_folding_execution_score`, `late_aggregate_burden_score`, `mass_spec_run_score`, `oracle_folding_label_score`, `protocol_stressor_shortcut_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `protocol_stressor_shortcut_score`

## Negative controls

- noise_auc_mean: `0.5005`
- score_permutation_auc_mean: `0.5020`
- label_permutation_auc_mean: `0.4998`

## Sentinels

- `protocol_stressor` (protocol_shortcut): column `protocol_stressor_shortcut_score`, AUC `0.6633`, expected `protocol/stressor metadata should not be sufficient evidence`
- `donor_batch` (donor_batch_shortcut): column `mass_spec_run_score`, AUC `0.5051`, expected `run or donor/batch structure should remain a sentinel`
- `future_folding` (future_folding_execution): column `future_folding_execution_score`, AUC `0.9567`, expected `post-anchor folding state should be a future invalid comparator`
- `late_aggregate_burden` (future_folding_execution): column `late_aggregate_burden_score`, AUC `0.0732`, expected `late aggregate burden is endpoint-adjacent future state`
- `oracle_endpoint` (oracle_label): column `oracle_folding_label_score`, AUC `1.0000`, expected `endpoint label leakage ceiling`

## Sentinel relations

- `protocol_stressor`: gap `0.0000`, proximity `1.0000`, Pearson `1.0000`, alert `False`
- `donor_batch`: gap `-0.1581`, proximity `0.6133`, Pearson `0.0452`, alert `False`
- `future_folding`: gap `0.2935`, proximity `-5.8893`, Pearson `0.0235`, alert `False`
- `late_aggregate_burden`: gap `-0.5901`, proximity `0.2983`, Pearson `-0.0366`, alert `False`
- `oracle_endpoint`: gap `0.3367`, proximity `-2.9214`, Pearson `0.3024`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.2107`
- Matched rows: `1400`
- Matched strata: `27`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-1.0000`: selected `0.8586`, enrichment `0.0350`
- threshold `0.0000`: selected `0.4007`, enrichment `0.1546`
- threshold `1.0000`: selected `0.2086`, enrichment `0.2529`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
