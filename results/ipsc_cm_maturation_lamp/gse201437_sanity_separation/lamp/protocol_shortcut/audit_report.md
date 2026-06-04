# LAMP audit report: GSE201437 LAMP sanity separation: High-calcium protocol shortcut

## Executive summary

- Primary score: `high_calcium_shortcut_score`
- Primary AUC: `0.8571`
- Inverted AUC: `0.1429`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `valid_early_hidden_state_signal`

Primary AUC = 0.857; inverted AUC = 0.143. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time`
- Frozen before holdout: `GSE201437 accession`, `structural truth panel`, `disjoint calcium/electrophysiology probe panel`, `protocol shortcut definitions`, `oracle leakage definition`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `hcrp_protocol_shortcut_score`, `high_calcium_shortcut_score`, `oracle_structural_maturity_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `high_calcium_shortcut_score`

## Negative controls

- noise_auc_mean: `0.4702`
- score_permutation_auc_mean: `0.4971`
- label_permutation_auc_mean: `0.5000`

## Sentinels

- `high_calcium` (protocol_shortcut): column `high_calcium_shortcut_score`, AUC `0.8571`, expected `high-calcium metadata should fail as a monitor`
- `hcrp_protocol` (protocol_shortcut): column `hcrp_protocol_shortcut_score`, AUC `0.7857`, expected `exact HCRP condition should remain a protocol sentinel`
- `oracle_truth` (oracle_label): column `oracle_structural_maturity_score`, AUC `1.0000`, expected `direct label leakage ceiling`

## Sentinel relations

- `high_calcium`: gap `0.0000`, proximity `NA`, Pearson `1.0000`, alert `False`
- `hcrp_protocol`: gap `-0.0714`, proximity `NA`, Pearson `0.6325`, alert `False`
- `oracle_truth`: gap `0.1429`, proximity `NA`, Pearson `0.7143`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.2857`
- Matched rows: `7`
- Matched strata: `2`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-0.5000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.5000`: selected `0.5000`, enrichment `0.3571`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
