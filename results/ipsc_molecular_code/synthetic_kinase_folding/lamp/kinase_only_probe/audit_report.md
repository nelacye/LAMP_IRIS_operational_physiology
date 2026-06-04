# LAMP audit report: Synthetic iPSC molecular-code audit: Kinase-only early monitor

## Executive summary

- Primary score: `kinase_only_score`
- Primary AUC: `0.9061`
- Inverted AUC: `0.0939`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `True`
- Output classes: `audit_pass_candidate`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `valid_early_hidden_state_signal`

Primary AUC = 0.906; inverted AUC = 0.094. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time`
- Frozen before holdout: `synthetic generator seed`, `molecular-code biological contract`, `monitor score family definitions`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `future_folding_execution_score`, `late_aggregate_burden_score`, `mass_spec_run_score`, `oracle_folding_label_score`, `protocol_stressor_shortcut_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.5005`
- score_permutation_auc_mean: `0.4989`
- label_permutation_auc_mean: `0.5009`

## Sentinels

- `protocol_stressor` (protocol_shortcut): column `protocol_stressor_shortcut_score`, AUC `0.6633`, expected `protocol/stressor metadata should not be sufficient evidence`
- `donor_batch` (donor_batch_shortcut): column `mass_spec_run_score`, AUC `0.5051`, expected `run or donor/batch structure should remain a sentinel`
- `future_folding` (future_folding_execution): column `future_folding_execution_score`, AUC `0.9567`, expected `post-anchor folding state should be a future invalid comparator`
- `late_aggregate_burden` (future_folding_execution): column `late_aggregate_burden_score`, AUC `0.0732`, expected `late aggregate burden is endpoint-adjacent future state`
- `oracle_endpoint` (oracle_label): column `oracle_folding_label_score`, AUC `1.0000`, expected `endpoint label leakage ceiling`

## Sentinel relations

- `protocol_stressor`: gap `-0.2428`, proximity `0.0321`, Pearson `0.0113`, alert `False`
- `donor_batch`: gap `-0.4010`, proximity `0.0197`, Pearson `0.0036`, alert `False`
- `future_folding`: gap `0.0506`, proximity `-0.1889`, Pearson `0.8925`, alert `False`
- `late_aggregate_burden`: gap `-0.8329`, proximity `0.0096`, Pearson `-0.8234`, alert `False`
- `oracle_endpoint`: gap `0.0939`, proximity `-0.0937`, Pearson `0.6738`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.6050`
- Matched rows: `1400`
- Matched strata: `27`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-1.0000`: selected `0.8429`, enrichment `0.0869`
- threshold `0.0000`: selected `0.4950`, enrichment `0.3194`
- threshold `1.0000`: selected `0.1700`, enrichment `0.4990`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
