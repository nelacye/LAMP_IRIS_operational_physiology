# LAMP audit report: Synthetic deceptive-agent benchmark: post-trigger leaky monitor

## Executive summary

- Primary score: `deceptive_leakage_score`
- Primary AUC: `1.0000`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `anchor_step`
- Frozen before holdout: `agent strata`, `score formulas`, `sentinel definitions`, `visible matching variables`, `thresholds`, `random seed`

Temporal violations:
- `post_trigger_anomaly` latest_offset_h=4.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `future_behavior_sentinel_score`, `oracle_collapse_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `post_trigger_anomaly`

## Negative controls

- noise_auc_mean: `0.5005`
- score_permutation_auc_mean: `0.4987`
- label_permutation_auc_mean: `0.5003`

## Sentinels

- `future_behavior` (future_behavior): column `future_behavior_sentinel_score`, AUC `1.0000`, expected `invalid post-trigger behavior comparator`
- `oracle_collapse` (oracle_label): column `oracle_collapse_sentinel_score`, AUC `1.0000`, expected `ceiling collapse-label sentinel`

## Sentinel relations

- `future_behavior`: gap `0.0000`, proximity `1.0000`, Pearson `0.9942`, alert `False`
- `oracle_collapse`: gap `0.0000`, proximity `1.0000`, Pearson `0.9974`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `1.0000`
- Matched rows: `160`
- Matched strata: `8`

## Early-window sensitivity

- Evaluated: `True`
- `pretrigger_only_score`: evaluated `True`, AUC `0.7948`
- `valid_latent_score`: evaluated `True`, AUC `0.9236`
- `deceptive_leakage_score`: evaluated `True`, AUC `1.0000`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.3500`: selected `0.5000`, enrichment `0.5000`
- threshold `0.5000`: selected `0.5000`, enrichment `0.5000`
- threshold `0.6500`: selected `0.5000`, enrichment `0.5000`
- threshold `0.8000`: selected `0.5000`, enrichment `0.5000`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
