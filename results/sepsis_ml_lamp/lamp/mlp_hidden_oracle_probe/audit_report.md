# LAMP audit report: Hidden-activation probe with oracle contamination

## Executive summary

- Primary score: `mlp_hidden_oracle_probe_score`
- Primary AUC: `0.9852`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `horizon_h`
- Frozen before holdout: `patient-level split`, `horizon list`, `model family`, `feature groups`, `contamination definitions`, `LAMP thresholds`, `random seed`

Temporal violations:
- `oracle_label_sentinel_score` latest_offset_h=1.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `future_physiology_sentinel_score`, `oracle_label_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `oracle_label_sentinel_score`

## Negative controls

- noise_auc_mean: `0.5000`
- score_permutation_auc_mean: `0.5010`
- label_permutation_auc_mean: `0.4999`

## Sentinels

- `future_physiology` (future_physiology): column `future_physiology_sentinel_score`, AUC `0.6846`, expected `post-anchor physiology comparator`
- `oracle_label` (oracle_label): column `oracle_label_sentinel_score`, AUC `1.0000`, expected `ceiling label leakage comparator`

## Sentinel relations

- `future_physiology`: gap `-0.3006`, proximity `-0.6835`, Pearson `0.1600`, alert `False`
- `oracle_label`: gap `0.0148`, proximity `0.8917`, Pearson `0.7472`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0959`
- Matched rows: `4958`
- Matched strata: `234`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2000`: selected `0.1667`, enrichment `0.2502`
- threshold `0.4000`: selected `0.1125`, enrichment `0.3948`
- threshold `0.6000`: selected `0.0753`, enrichment `0.4578`
- threshold `0.8000`: selected `0.0500`, enrichment `0.5956`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
