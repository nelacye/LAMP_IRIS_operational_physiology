# LAMP audit report: GSE175634 pseudo-bulk rescue: Pseudo-bulk annotation shortcut

## Executive summary

- Primary score: `annotation_cm_score`
- Primary AUC: `0.9474`
- Inverted AUC: `0.0526`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Primary AUC = 0.947; inverted AUC = 0.053. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `diffday_num`
- Frozen before holdout: `GSE175634 count-level pilot`, `pseudo-bulk grouping columns`, `structural endpoint definition`, `forbidden day/pseudotime/annotation channels`, `LAMP thresholds`

Temporal violations:
- `annotation_cm_score` latest_offset_h=999.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `annotation_cm_score`, `diffday_numeric_score`, `dpt_pseudotime_score`, `structural_panel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `annotation_cm_score`

## Negative controls

- noise_auc_mean: `0.4816`
- score_permutation_auc_mean: `0.5029`
- label_permutation_auc_mean: `0.5005`

## Sentinels

- `structural_endpoint_oracle` (endpoint_adjacent_oracle): column `structural_panel_score`, AUC `1.0000`, expected `same marker axis that defines the endpoint`
- `day_protocol` (timepoint_protocol_shortcut): column `diffday_numeric_score`, AUC `0.8801`, expected `differentiation day / protocol timing`
- `published_pseudotime` (endpoint_adjacent_oracle): column `dpt_pseudotime_score`, AUC `0.9415`, expected `full-trajectory pseudotime`
- `published_annotation` (annotation_shortcut): column `annotation_cm_score`, AUC `0.9474`, expected `published CM annotation fraction`

## Sentinel relations

- `structural_endpoint_oracle`: gap `0.0526`, proximity `NA`, Pearson `0.9569`, alert `False`
- `day_protocol`: gap `-0.0673`, proximity `NA`, Pearson `0.6526`, alert `False`
- `published_pseudotime`: gap `-0.0058`, proximity `NA`, Pearson `0.7034`, alert `False`
- `published_annotation`: gap `0.0000`, proximity `NA`, Pearson `1.0000`, alert `False`

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

- Fragile: `False`
- threshold `-0.0500`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0500`: selected `0.3929`, enrichment `0.4058`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
