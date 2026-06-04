# LAMP audit report: Synthetic iPSC molecular-code audit: strict_declared oracle mixture lambda=0.001

## Executive summary

- Primary score: `oracle_mix_lambda_0p00100_score`
- Primary AUC: `0.9145`
- Inverted AUC: `0.0855`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `protocol_batch_or_donor_shortcut_sentinel`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Primary AUC = 0.915; inverted AUC = 0.085. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `anchor_time`
- Frozen before holdout: `synthetic generator seed`, `molecular-code biological contract`, `monitor score family definitions`, `LAMP thresholds`

Temporal violations:
- `oracle_folding_label_score` latest_offset_h=24.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `future_folding_execution_score`, `late_aggregate_burden_score`, `mass_spec_run_score`, `oracle_folding_label_score`, `protocol_stressor_shortcut_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `oracle_folding_label_score`

## Negative controls

- noise_auc_mean: `0.5005`
- score_permutation_auc_mean: `0.4985`
- label_permutation_auc_mean: `0.5008`

## Sentinels

- `protocol_stressor` (protocol_shortcut): column `protocol_stressor_shortcut_score`, AUC `0.6633`, expected `protocol/stressor metadata should not be sufficient evidence`
- `donor_batch` (donor_batch_shortcut): column `mass_spec_run_score`, AUC `0.5051`, expected `run or donor/batch structure should remain a sentinel`
- `future_folding` (future_folding_execution): column `future_folding_execution_score`, AUC `0.9567`, expected `post-anchor folding state should be a future invalid comparator`
- `late_aggregate_burden` (future_folding_execution): column `late_aggregate_burden_score`, AUC `0.0732`, expected `late aggregate burden is endpoint-adjacent future state`
- `oracle_endpoint` (oracle_label): column `oracle_folding_label_score`, AUC `1.0000`, expected `endpoint label leakage ceiling`

## Sentinel relations

- `protocol_stressor`: gap `-0.2512`, proximity `-0.0015`, Pearson `0.0093`, alert `False`
- `donor_batch`: gap `-0.4094`, proximity `-0.0009`, Pearson `0.0012`, alert `False`
- `future_folding`: gap `0.0422`, proximity `0.0089`, Pearson `0.9233`, alert `False`
- `late_aggregate_burden`: gap `-0.8413`, proximity `-0.0005`, Pearson `-0.8578`, alert `False`
- `oracle_endpoint`: gap `0.0855`, proximity `0.0044`, Pearson `0.6854`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.6107`
- Matched rows: `1400`
- Matched strata: `27`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-1.0000`: selected `0.8436`, enrichment `0.0882`
- threshold `0.0000`: selected `0.4921`, enrichment `0.3255`
- threshold `1.0000`: selected `0.1629`, enrichment `0.5025`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
