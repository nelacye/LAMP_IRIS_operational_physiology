# LAMP audit report: GSE114686 LAMP-Pharm audit: Combined drug-dose shortcut score

## Executive summary

- Primary score: `combined_drug_dose_shortcut_score`
- Primary AUC: `1.0000`
- Inverted AUC: `0.0000`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `valid_early_hidden_state_signal`

Primary AUC = 1.000; inverted AUC = 0.000. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time`
- Frozen before holdout: `GSE114686 accession`, `processed RNA-seq table`, `sample ID parser`, `signed cardiotoxic-response panel`, `drug/dose/time sentinel definitions`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `combined_drug_dose_shortcut_score`, `endpoint_adjacent_marker_score`, `oracle_severe_highdose_tki_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `combined_drug_dose_shortcut_score`

## Negative controls

- noise_auc_mean: `0.5005`
- score_permutation_auc_mean: `0.5069`
- label_permutation_auc_mean: `0.4876`

## Sentinels

- `severe_tki_identity` (protocol_drug_identity_shortcut): column `severe_tki_identity_shortcut_score`, AUC `0.9423`, expected `drug identity should not substitute for response biology`
- `dose` (protocol_dose_shortcut): column `dose_shortcut_score`, AUC `0.7133`, expected `administered dose is experimental structure`
- `exposure_time` (protocol_time_shortcut): column `exposure_time_shortcut_score`, AUC `0.5182`, expected `exposure duration is experimental structure`
- `combined_drug_dose` (protocol_shortcut): column `combined_drug_dose_shortcut_score`, AUC `1.0000`, expected `exact endpoint rule encoded as drug+dose structure`
- `oracle_endpoint` (oracle_label): column `oracle_severe_highdose_tki_score`, AUC `1.0000`, expected `ceiling endpoint comparator`
- `endpoint_adjacent_markers` (oracle_label): column `endpoint_adjacent_marker_score`, AUC `0.9973`, expected `genes selected against endpoint on same table`

## Sentinel relations

- `severe_tki_identity`: gap `-0.0577`, proximity `NA`, Pearson `0.8535`, alert `False`
- `dose`: gap `-0.2867`, proximity `NA`, Pearson `0.3563`, alert `False`
- `exposure_time`: gap `-0.4818`, proximity `NA`, Pearson `0.0280`, alert `False`
- `combined_drug_dose`: gap `0.0000`, proximity `NA`, Pearson `1.0000`, alert `False`
- `oracle_endpoint`: gap `0.0000`, proximity `NA`, Pearson `1.0000`, alert `False`
- `endpoint_adjacent_markers`: gap `-0.0027`, proximity `NA`, Pearson `0.8154`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.4426`
- Matched rows: `61`
- Matched strata: `10`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-1.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `1.0000`: selected `0.3500`, enrichment `0.6500`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
