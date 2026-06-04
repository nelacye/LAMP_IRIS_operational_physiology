# LAMP audit report: GSE201437 protocol-shortcut audit: Ramp-pacing protocol shortcut score

## Executive summary

- Primary score: `ramp_pacing_shortcut_score`
- Primary AUC: `0.8500`
- Inverted AUC: `0.1500`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `valid_early_hidden_state_signal`

Primary AUC = 0.850; inverted AUC = 0.150. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time`
- Frozen before holdout: `GSE201437 accession`, `GEO processed counts`, `sample group parser`, `curated marker list`, `protocol sentinel definitions`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `combined_intervention_shortcut_score`, `endpoint_adjacent_marker_score`, `high_calcium`, `oracle_hcrp_label_score`, `ramp_pacing`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `ramp_pacing`

## Negative controls

- noise_auc_mean: `0.4790`
- score_permutation_auc_mean: `0.5245`
- label_permutation_auc_mean: `0.5035`

## Sentinels

- `high_calcium` (protocol_shortcut): column `high_calcium`, AUC `0.8500`, expected `high-calcium intervention should not count as hidden maturation inference`
- `ramp_pacing` (protocol_shortcut): column `ramp_pacing`, AUC `0.8500`, expected `ramp-pacing intervention should not count as hidden maturation inference`
- `combined_intervention` (protocol_shortcut): column `combined_intervention_shortcut_score`, AUC `1.0000`, expected `exact HCRP intervention code is a protocol shortcut`
- `oracle_endpoint` (oracle_label): column `oracle_hcrp_label_score`, AUC `1.0000`, expected `ceiling endpoint comparator`
- `endpoint_adjacent_markers` (oracle_label): column `endpoint_adjacent_marker_score`, AUC `1.0000`, expected `genes selected against endpoint on same tiny table`

## Sentinel relations

- `high_calcium`: gap `0.0000`, proximity `NA`, Pearson `0.1429`, alert `False`
- `ramp_pacing`: gap `0.0000`, proximity `NA`, Pearson `1.0000`, alert `False`
- `combined_intervention`: gap `0.1500`, proximity `NA`, Pearson `0.6325`, alert `False`
- `oracle_endpoint`: gap `0.1500`, proximity `NA`, Pearson `0.6325`, alert `False`
- `endpoint_adjacent_markers`: gap `0.1500`, proximity `NA`, Pearson `0.6728`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.6190`
- Matched rows: `7`
- Matched strata: `2`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-1.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `1.0000`: selected `0.5000`, enrichment `0.2857`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
