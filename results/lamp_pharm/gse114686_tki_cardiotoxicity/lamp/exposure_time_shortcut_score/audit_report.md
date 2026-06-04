# LAMP audit report: GSE114686 LAMP-Pharm audit: Exposure-time shortcut score

## Executive summary

- Primary score: `exposure_time_shortcut_score`
- Primary AUC: `0.5182`
- Inverted AUC: `0.4818`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `null_or_destroyed_signal`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`

Primary AUC = 0.518; inverted AUC = 0.482. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

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
- Valid-score feature violations: `exposure_time_h`

## Negative controls

- noise_auc_mean: `0.5005`
- score_permutation_auc_mean: `0.4984`
- label_permutation_auc_mean: `0.5088`

## Sentinels

- `severe_tki_identity` (protocol_drug_identity_shortcut): column `severe_tki_identity_shortcut_score`, AUC `0.9423`, expected `drug identity should not substitute for response biology`
- `dose` (protocol_dose_shortcut): column `dose_shortcut_score`, AUC `0.7133`, expected `administered dose is experimental structure`
- `exposure_time` (protocol_time_shortcut): column `exposure_time_shortcut_score`, AUC `0.5182`, expected `exposure duration is experimental structure`
- `combined_drug_dose` (protocol_shortcut): column `combined_drug_dose_shortcut_score`, AUC `1.0000`, expected `exact endpoint rule encoded as drug+dose structure`
- `oracle_endpoint` (oracle_label): column `oracle_severe_highdose_tki_score`, AUC `1.0000`, expected `ceiling endpoint comparator`
- `endpoint_adjacent_markers` (oracle_label): column `endpoint_adjacent_marker_score`, AUC `0.9973`, expected `genes selected against endpoint on same table`

## Sentinel relations

- `severe_tki_identity`: gap `0.4241`, proximity `NA`, Pearson `-0.0118`, alert `False`
- `dose`: gap `0.1951`, proximity `NA`, Pearson `-0.0126`, alert `False`
- `exposure_time`: gap `0.0000`, proximity `NA`, Pearson `1.0000`, alert `False`
- `combined_drug_dose`: gap `0.4818`, proximity `NA`, Pearson `0.0280`, alert `False`
- `oracle_endpoint`: gap `0.4818`, proximity `NA`, Pearson `0.0280`, alert `False`
- `endpoint_adjacent_markers`: gap `0.4791`, proximity `NA`, Pearson `0.0540`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `-0.0425`
- Matched rows: `65`
- Matched strata: `10`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-1.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `1.0000`: selected `1.0000`, enrichment `0.0000`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
