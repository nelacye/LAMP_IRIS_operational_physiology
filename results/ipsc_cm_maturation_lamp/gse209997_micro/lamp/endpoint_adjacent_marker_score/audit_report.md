# LAMP audit report: GSE209997 iPSC-CM maturation micro-audit: Endpoint-adjacent marker-selection score

## Executive summary

- Primary score: `endpoint_adjacent_marker_score`
- Primary AUC: `1.0000`
- Inverted AUC: `0.0000`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Primary AUC = 1.000; inverted AUC = 0.000. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `anchor_time`
- Frozen before holdout: `GSE209997 accession`, `sample metadata parser`, `curated marker list`, `shortcut/sentinel definitions`, `LAMP thresholds`

Temporal violations:
- `endpoint_adjacent_marker_score` latest_offset_h=999.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `culture_3d`, `day_numeric`, `endpoint_adjacent_marker_score`, `oracle_mature_state_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `endpoint_adjacent_marker_score`

## Negative controls

- noise_auc_mean: `0.4922`
- score_permutation_auc_mean: `0.5148`
- label_permutation_auc_mean: `0.4874`

## Sentinels

- `timepoint` (future_timepoint): column `day_numeric`, AUC `0.8333`, expected `invalid shortcut for early maturation prediction`
- `protocol` (protocol_shortcut): column `culture_3d`, AUC `0.8333`, expected `3D-vs-2D culture shortcut, not hidden maturation state`
- `oracle_endpoint` (oracle_label): column `oracle_mature_state_score`, AUC `1.0000`, expected `ceiling endpoint comparator`
- `endpoint_adjacent_markers` (oracle_label): column `endpoint_adjacent_marker_score`, AUC `1.0000`, expected `genes selected against endpoint on same tiny table`

## Sentinel relations

- `timepoint`: gap `-0.1667`, proximity `NA`, Pearson `0.5730`, alert `False`
- `protocol`: gap `-0.1667`, proximity `NA`, Pearson `0.5941`, alert `False`
- `oracle_endpoint`: gap `0.0000`, proximity `NA`, Pearson `0.9988`, alert `False`
- `endpoint_adjacent_markers`: gap `0.0000`, proximity `NA`, Pearson `1.0000`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.5000`
- Matched rows: `10`
- Matched strata: `2`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-1.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0000`: selected `0.2500`, enrichment `0.7500`
- threshold `1.0000`: selected `0.2500`, enrichment `0.7500`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
