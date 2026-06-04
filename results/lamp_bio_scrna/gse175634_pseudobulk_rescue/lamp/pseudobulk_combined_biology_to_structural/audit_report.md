# LAMP audit report: GSE175634 pseudo-bulk rescue: Pseudo-bulk combined biology -> structural endpoint

## Executive summary

- Primary score: `combined_disjoint_biology_score`
- Primary AUC: `0.5263`
- Inverted AUC: `0.4737`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `null_or_destroyed_signal`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `threshold_fragile_claim`

Primary AUC = 0.526; inverted AUC = 0.474. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `diffday_num`
- Frozen before holdout: `GSE175634 count-level pilot`, `pseudo-bulk grouping columns`, `structural endpoint definition`, `forbidden day/pseudotime/annotation channels`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `annotation_cm_score`, `diffday_numeric_score`, `dpt_pseudotime_score`, `structural_panel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.4816`
- score_permutation_auc_mean: `0.5093`
- label_permutation_auc_mean: `0.5001`

## Sentinels

- `structural_endpoint_oracle` (endpoint_adjacent_oracle): column `structural_panel_score`, AUC `1.0000`, expected `same marker axis that defines the endpoint`
- `day_protocol` (timepoint_protocol_shortcut): column `diffday_numeric_score`, AUC `0.8801`, expected `differentiation day / protocol timing`
- `published_pseudotime` (endpoint_adjacent_oracle): column `dpt_pseudotime_score`, AUC `0.9415`, expected `full-trajectory pseudotime`
- `published_annotation` (annotation_shortcut): column `annotation_cm_score`, AUC `0.9474`, expected `published CM annotation fraction`

## Sentinel relations

- `structural_endpoint_oracle`: gap `0.4737`, proximity `NA`, Pearson `0.5240`, alert `False`
- `day_protocol`: gap `0.3538`, proximity `NA`, Pearson `0.0410`, alert `False`
- `published_pseudotime`: gap `0.4152`, proximity `NA`, Pearson `0.1315`, alert `False`
- `published_annotation`: gap `0.4211`, proximity `NA`, Pearson `0.6662`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.1607`
- Matched rows: `28`
- Matched strata: `5`

## Early-window sensitivity

- Evaluated: `True`
- `calcium_ephys_panel_score`: evaluated `True`, AUC `0.6257`
- `metabolic_panel_score`: evaluated `True`, AUC `0.5380`
- `combined_disjoint_biology_score`: evaluated `True`, AUC `0.5263`
- `diffday_numeric_score`: evaluated `True`, AUC `0.8801`
- `dpt_pseudotime_score`: evaluated `True`, AUC `0.9415`
- `annotation_cm_score`: evaluated `True`, AUC `0.9474`

## Threshold sensitivity

- Fragile: `True`
- threshold `-0.0500`: selected `0.5714`, enrichment `-0.0089`
- threshold `0.0000`: selected `0.3571`, enrichment `0.0786`
- threshold `0.0500`: selected `0.1071`, enrichment `0.6786`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
