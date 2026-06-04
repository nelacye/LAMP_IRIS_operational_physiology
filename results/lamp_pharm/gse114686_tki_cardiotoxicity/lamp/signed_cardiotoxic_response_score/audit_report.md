# LAMP audit report: GSE114686 LAMP-Pharm audit: Signed cardiotoxic-response expression score

## Executive summary

- Primary score: `signed_cardiotoxic_response_score`
- Primary AUC: `0.6099`
- Inverted AUC: `0.3901`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `threshold_fragile_claim`

Primary AUC = 0.610; inverted AUC = 0.390. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time`
- Frozen before holdout: `GSE114686 accession`, `processed RNA-seq table`, `sample ID parser`, `signed cardiotoxic-response panel`, `drug/dose/time sentinel definitions`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `combined_drug_dose_shortcut_score`, `endpoint_adjacent_marker_score`, `oracle_severe_highdose_tki_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.5005`
- score_permutation_auc_mean: `0.5007`
- label_permutation_auc_mean: `0.4999`

## Sentinels

- `severe_tki_identity` (protocol_drug_identity_shortcut): column `severe_tki_identity_shortcut_score`, AUC `0.9423`, expected `drug identity should not substitute for response biology`
- `dose` (protocol_dose_shortcut): column `dose_shortcut_score`, AUC `0.7133`, expected `administered dose is experimental structure`
- `exposure_time` (protocol_time_shortcut): column `exposure_time_shortcut_score`, AUC `0.5182`, expected `exposure duration is experimental structure`
- `combined_drug_dose` (protocol_shortcut): column `combined_drug_dose_shortcut_score`, AUC `1.0000`, expected `exact endpoint rule encoded as drug+dose structure`
- `oracle_endpoint` (oracle_label): column `oracle_severe_highdose_tki_score`, AUC `1.0000`, expected `ceiling endpoint comparator`
- `endpoint_adjacent_markers` (oracle_label): column `endpoint_adjacent_marker_score`, AUC `0.9973`, expected `genes selected against endpoint on same table`

## Sentinel relations

- `severe_tki_identity`: gap `0.3324`, proximity `NA`, Pearson `0.3042`, alert `False`
- `dose`: gap `0.1034`, proximity `NA`, Pearson `0.2948`, alert `False`
- `exposure_time`: gap `-0.0917`, proximity `NA`, Pearson `0.0273`, alert `False`
- `combined_drug_dose`: gap `0.3901`, proximity `NA`, Pearson `0.3500`, alert `False`
- `oracle_endpoint`: gap `0.3901`, proximity `NA`, Pearson `0.3500`, alert `False`
- `endpoint_adjacent_markers`: gap `0.3874`, proximity `NA`, Pearson `0.7066`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0169`
- Matched rows: `79`
- Matched strata: `13`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `True`
- threshold `-1.0000`: selected `0.9625`, enrichment `-0.0123`
- threshold `0.0000`: selected `0.3000`, enrichment `0.1500`
- threshold `1.0000`: selected `0.0875`, enrichment `0.6500`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
