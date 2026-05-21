# LAMP audit report: BIDSleep HR plus EEG-label wearable sleep benchmark

## Executive summary

- Primary score: `mixed_score`
- Primary AUC: `0.5720`
- Audit-pass candidate: `False`
- Output classes: `leakage_contaminated_candidate`, `null_or_destroyed_signal`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `early_minutes`
- Frozen before holdout: `early window`, `later-instability endpoint threshold`, `valid HR-only score`, `future HR sentinel`, `oracle EEG-label sentinel`, `visible-state matching variables`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `future_hr_sentinel_score`, `oracle_sleep_stage_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.5032`
- score_permutation_auc_mean: `0.4983`
- label_permutation_auc_mean: `0.5011`

## Sentinels

- `future_physiology` (future_physiology): column `future_hr_sentinel_score`, AUC `0.6112`, expected `invalid later-night wearable HR comparator`
- `oracle_label` (oracle_label): column `oracle_sleep_stage_sentinel_score`, AUC `1.0000`, expected `ceiling future EEG-label comparator`

## Sentinel relations

- `future_physiology`: gap `0.0392`, proximity `0.1111`, Pearson `0.6616`, alert `False`
- `oracle_label`: gap `0.4280`, proximity `0.0113`, Pearson `0.0936`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0500`
- Matched rows: `247`
- Matched strata: `25`

## Threshold sensitivity

- Fragile: `False`
- threshold `1.5000`: selected `1.0000`, enrichment `0.0000`
- threshold `2.0000`: selected `0.3690`, enrichment `0.0600`
- threshold `2.5000`: selected `0.0476`, enrichment `0.2778`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
