# LAMP audit report: GSE114686 LAMP-Pharm audit: Endpoint-adjacent marker-selection score

## Executive summary

- Primary score: `endpoint_adjacent_marker_score`
- Primary AUC: `0.9973`
- Inverted AUC: `0.0027`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Primary AUC = 0.997; inverted AUC = 0.003. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `anchor_time`
- Frozen before holdout: `GSE114686 accession`, `processed RNA-seq table`, `sample ID parser`, `signed cardiotoxic-response panel`, `drug/dose/time sentinel definitions`, `LAMP thresholds`

Temporal violations:
- `endpoint_adjacent_marker_score` latest_offset_h=999.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `combined_drug_dose_shortcut_score`, `endpoint_adjacent_marker_score`, `oracle_severe_highdose_tki_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `endpoint_adjacent_marker_score`

## Negative controls

- noise_auc_mean: `0.5005`
- score_permutation_auc_mean: `0.5091`
- label_permutation_auc_mean: `0.4905`

## Sentinels

- `severe_tki_identity` (protocol_drug_identity_shortcut): column `severe_tki_identity_shortcut_score`, AUC `0.9423`, expected `drug identity should not substitute for response biology`
- `dose` (protocol_dose_shortcut): column `dose_shortcut_score`, AUC `0.7133`, expected `administered dose is experimental structure`
- `exposure_time` (protocol_time_shortcut): column `exposure_time_shortcut_score`, AUC `0.5182`, expected `exposure duration is experimental structure`
- `combined_drug_dose` (protocol_shortcut): column `combined_drug_dose_shortcut_score`, AUC `1.0000`, expected `exact endpoint rule encoded as drug+dose structure`
- `oracle_endpoint` (oracle_label): column `oracle_severe_highdose_tki_score`, AUC `1.0000`, expected `ceiling endpoint comparator`
- `endpoint_adjacent_markers` (oracle_label): column `endpoint_adjacent_marker_score`, AUC `0.9973`, expected `genes selected against endpoint on same table`

## Sentinel relations

- `severe_tki_identity`: gap `-0.0549`, proximity `NA`, Pearson `0.7615`, alert `False`
- `dose`: gap `-0.2840`, proximity `NA`, Pearson `0.3390`, alert `False`
- `exposure_time`: gap `-0.4791`, proximity `NA`, Pearson `0.0540`, alert `False`
- `combined_drug_dose`: gap `0.0027`, proximity `NA`, Pearson `0.8154`, alert `False`
- `oracle_endpoint`: gap `0.0027`, proximity `NA`, Pearson `0.8154`, alert `False`
- `endpoint_adjacent_markers`: gap `0.0000`, proximity `NA`, Pearson `1.0000`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.3228`
- Matched rows: `79`
- Matched strata: `13`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-1.0000`: selected `0.9625`, enrichment `0.0136`
- threshold `0.0000`: selected `0.3875`, enrichment `0.5532`
- threshold `1.0000`: selected `0.1000`, enrichment `0.6500`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
