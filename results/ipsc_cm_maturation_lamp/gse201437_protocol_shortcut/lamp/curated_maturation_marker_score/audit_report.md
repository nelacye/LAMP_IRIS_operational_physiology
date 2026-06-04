# LAMP audit report: GSE201437 protocol-shortcut audit: Curated maturation-marker expression score

## Executive summary

- Primary score: `curated_maturation_marker_score`
- Primary AUC: `1.0000`
- Inverted AUC: `0.0000`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `True`
- Output classes: `audit_pass_candidate`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `valid_early_hidden_state_signal`

Primary AUC = 1.000; inverted AUC = 0.000. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time`
- Frozen before holdout: `GSE201437 accession`, `GEO processed counts`, `sample group parser`, `curated marker list`, `protocol sentinel definitions`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `combined_intervention_shortcut_score`, `endpoint_adjacent_marker_score`, `high_calcium`, `oracle_hcrp_label_score`, `ramp_pacing`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.4790`
- score_permutation_auc_mean: `0.5117`
- label_permutation_auc_mean: `0.4940`

## Sentinels

- `high_calcium` (protocol_shortcut): column `high_calcium`, AUC `0.8500`, expected `high-calcium intervention should not count as hidden maturation inference`
- `ramp_pacing` (protocol_shortcut): column `ramp_pacing`, AUC `0.8500`, expected `ramp-pacing intervention should not count as hidden maturation inference`
- `combined_intervention` (protocol_shortcut): column `combined_intervention_shortcut_score`, AUC `1.0000`, expected `exact HCRP intervention code is a protocol shortcut`
- `oracle_endpoint` (oracle_label): column `oracle_hcrp_label_score`, AUC `1.0000`, expected `ceiling endpoint comparator`
- `endpoint_adjacent_markers` (oracle_label): column `endpoint_adjacent_marker_score`, AUC `1.0000`, expected `genes selected against endpoint on same tiny table`

## Sentinel relations

- `high_calcium`: gap `-0.1500`, proximity `NA`, Pearson `0.5984`, alert `False`
- `ramp_pacing`: gap `-0.1500`, proximity `NA`, Pearson `0.5355`, alert `False`
- `combined_intervention`: gap `0.0000`, proximity `NA`, Pearson `0.7004`, alert `False`
- `oracle_endpoint`: gap `0.0000`, proximity `NA`, Pearson `0.7004`, alert `False`
- `endpoint_adjacent_markers`: gap `0.0000`, proximity `NA`, Pearson `0.7491`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.4643`
- Matched rows: `14`
- Matched strata: `4`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-1.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0000`: selected `0.6429`, enrichment `0.1587`
- threshold `1.0000`: selected `0.0000`, enrichment `NA`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
