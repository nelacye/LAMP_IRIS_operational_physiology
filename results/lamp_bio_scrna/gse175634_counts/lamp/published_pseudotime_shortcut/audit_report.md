# LAMP audit report: GSE175634 scRNA counts: Published pseudotime shortcut

## Executive summary

- Primary score: `dpt_pseudotime_score`
- Primary AUC: `0.7807`
- Inverted AUC: `0.2193`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Primary AUC = 0.781; inverted AUC = 0.219. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `diffday_num`
- Frozen before holdout: `GSE175634 accession`, `structural endpoint marker panel`, `disjoint allowed calcium/electrophysiology and metabolic panels`, `forbidden day/pseudotime/annotation shortcuts`, `LAMP thresholds`

Temporal violations:
- `dpt_pseudotime_score` latest_offset_h=999.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `annotation_cm_score`, `diffday_numeric_score`, `dpt_pseudotime_score`, `structural_panel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `dpt_pseudotime_score`

## Negative controls

- noise_auc_mean: `0.4997`
- score_permutation_auc_mean: `0.5002`
- label_permutation_auc_mean: `0.5004`

## Sentinels

- `structural_endpoint_oracle` (endpoint_adjacent_oracle): column `structural_panel_score`, AUC `1.0000`, expected `same marker axis that defines the endpoint`
- `day_protocol` (timepoint_protocol_shortcut): column `diffday_numeric_score`, AUC `0.7712`, expected `differentiation day should not be used as molecular evidence`
- `published_pseudotime` (endpoint_adjacent_oracle): column `dpt_pseudotime_score`, AUC `0.7807`, expected `published pseudotime is inferred from full expression trajectory`
- `published_annotation` (annotation_shortcut): column `annotation_cm_score`, AUC `0.6536`, expected `published cell-type annotation is a label-adjacent channel`

## Sentinel relations

- `structural_endpoint_oracle`: gap `0.2193`, proximity `NA`, Pearson `0.6698`, alert `False`
- `day_protocol`: gap `0.0035`, proximity `NA`, Pearson `0.7828`, alert `False`
- `published_pseudotime`: gap `0.0000`, proximity `NA`, Pearson `1.0000`, alert `False`
- `published_annotation`: gap `-0.1141`, proximity `NA`, Pearson `0.5961`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0990`
- Matched rows: `55886`
- Matched strata: `27`

## Early-window sensitivity

- Evaluated: `True`
- `calcium_ephys_panel_score`: evaluated `True`, AUC `0.5705`
- `metabolic_panel_score`: evaluated `True`, AUC `0.4973`
- `combined_disjoint_biology_score`: evaluated `True`, AUC `0.5479`
- `diffday_numeric_score`: evaluated `True`, AUC `0.7712`
- `dpt_pseudotime_score`: evaluated `True`, AUC `0.7807`

## Threshold sensitivity

- Fragile: `False`
- threshold `-0.7500`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.7500`: selected `0.0218`, enrichment `0.7029`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
