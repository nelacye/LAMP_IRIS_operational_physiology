# LAMP audit report: GSE175634 scRNA counts: Metabolic -> structural endpoint

## Executive summary

- Primary score: `metabolic_panel_score`
- Primary AUC: `0.4973`
- Inverted AUC: `0.5027`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `null_or_destroyed_signal`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `threshold_fragile_claim`

Primary AUC = 0.497; inverted AUC = 0.503. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `diffday_num`
- Frozen before holdout: `GSE175634 accession`, `structural endpoint marker panel`, `disjoint allowed calcium/electrophysiology and metabolic panels`, `forbidden day/pseudotime/annotation shortcuts`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `annotation_cm_score`, `diffday_numeric_score`, `dpt_pseudotime_score`, `structural_panel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.4999`
- score_permutation_auc_mean: `0.5003`
- label_permutation_auc_mean: `0.4998`

## Sentinels

- `structural_endpoint_oracle` (endpoint_adjacent_oracle): column `structural_panel_score`, AUC `1.0000`, expected `same marker axis that defines the endpoint`
- `day_protocol` (timepoint_protocol_shortcut): column `diffday_numeric_score`, AUC `0.7712`, expected `differentiation day should not be used as molecular evidence`
- `published_pseudotime` (endpoint_adjacent_oracle): column `dpt_pseudotime_score`, AUC `0.7807`, expected `published pseudotime is inferred from full expression trajectory`
- `published_annotation` (annotation_shortcut): column `annotation_cm_score`, AUC `0.6536`, expected `published cell-type annotation is a label-adjacent channel`

## Sentinel relations

- `structural_endpoint_oracle`: gap `0.5027`, proximity `NA`, Pearson `0.2203`, alert `False`
- `day_protocol`: gap `0.2738`, proximity `NA`, Pearson `-0.0751`, alert `False`
- `published_pseudotime`: gap `0.2836`, proximity `NA`, Pearson `0.0532`, alert `False`
- `published_annotation`: gap `0.1563`, proximity `NA`, Pearson `0.2042`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0198`
- Matched rows: `60000`
- Matched strata: `27`

## Early-window sensitivity

- Evaluated: `True`
- `calcium_ephys_panel_score`: evaluated `True`, AUC `0.5705`
- `metabolic_panel_score`: evaluated `True`, AUC `0.4973`
- `combined_disjoint_biology_score`: evaluated `True`, AUC `0.5479`
- `diffday_numeric_score`: evaluated `True`, AUC `0.7712`
- `dpt_pseudotime_score`: evaluated `True`, AUC `0.7807`

## Threshold sensitivity

- Fragile: `True`
- threshold `-0.7500`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0000`: selected `0.4535`, enrichment `-0.0065`
- threshold `0.7500`: selected `0.0263`, enrichment `0.2697`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
