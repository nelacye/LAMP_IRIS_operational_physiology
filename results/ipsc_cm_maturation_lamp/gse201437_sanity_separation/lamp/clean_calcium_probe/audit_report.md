# LAMP audit report: GSE201437 LAMP sanity separation: Clean calcium/electrophysiology probe

## Executive summary

- Primary score: `clean_calcium_probe_score`
- Primary AUC: `0.6939`
- Inverted AUC: `0.3061`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `True`
- Output classes: `audit_pass_candidate`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `valid_early_hidden_state_signal`

Primary AUC = 0.694; inverted AUC = 0.306. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time`
- Frozen before holdout: `GSE201437 accession`, `structural truth panel`, `disjoint calcium/electrophysiology probe panel`, `protocol shortcut definitions`, `oracle leakage definition`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `hcrp_protocol_shortcut_score`, `high_calcium_shortcut_score`, `oracle_structural_maturity_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.4702`
- score_permutation_auc_mean: `0.5239`
- label_permutation_auc_mean: `0.5067`

## Sentinels

- `high_calcium` (protocol_shortcut): column `high_calcium_shortcut_score`, AUC `0.8571`, expected `high-calcium metadata should fail as a monitor`
- `hcrp_protocol` (protocol_shortcut): column `hcrp_protocol_shortcut_score`, AUC `0.7857`, expected `exact HCRP condition should remain a protocol sentinel`
- `oracle_truth` (oracle_label): column `oracle_structural_maturity_score`, AUC `1.0000`, expected `direct label leakage ceiling`

## Sentinel relations

- `high_calcium`: gap `0.1633`, proximity `NA`, Pearson `0.2949`, alert `False`
- `hcrp_protocol`: gap `0.0918`, proximity `NA`, Pearson `0.6092`, alert `False`
- `oracle_truth`: gap `0.3061`, proximity `NA`, Pearson `0.4210`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.6071`
- Matched rows: `14`
- Matched strata: `4`

## Early-window sensitivity

- Evaluated: `False`

## Threshold sensitivity

- Fragile: `False`
- threshold `-0.5000`: selected `0.7143`, enrichment `0.1000`
- threshold `0.0000`: selected `0.4286`, enrichment `0.0000`
- threshold `0.5000`: selected `0.2143`, enrichment `0.1667`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
