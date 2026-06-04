# LAMP audit report: GSE175634 scRNA metadata: Cell-cycle exit metadata probe

## Executive summary

- Primary score: `cell_cycle_exit_score`
- Primary AUC: `0.5819`
- Inverted AUC: `0.4181`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`

Primary AUC = 0.582; inverted AUC = 0.418. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `diffday_num`
- Frozen before holdout: `GSE175634 accession`, `metadata-only first-pass contract`, `cardiomyocyte-state endpoint label`, `forbidden endpoint-adjacent sentinels`, `LAMP thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `annotation_oracle_score`, `collection_beating_score`, `collection_cm_rate_score`, `diffday_numeric_score`, `dpt_pseudotime_score`, `experiment_batch_score`, `individual_cm_rate_score`, `leiden_label_rate_score`, `terminal_state_oracle_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.5000`
- score_permutation_auc_mean: `0.5006`
- label_permutation_auc_mean: `0.4997`

## Sentinels

- `timepoint_protocol` (timepoint_protocol_shortcut): column `diffday_numeric_score`, AUC `0.8270`, expected `differentiation day is a protocol shortcut for endpoint state`
- `published_pseudotime` (endpoint_adjacent_oracle): column `dpt_pseudotime_score`, AUC `0.8986`, expected `trajectory pseudotime is not clean early evidence here`
- `annotation_oracle` (oracle_label): column `annotation_oracle_score`, AUC `1.0000`, expected `direct published cell-type label leakage`
- `terminal_state_oracle` (oracle_label): column `terminal_state_oracle_score`, AUC `0.8899`, expected `broader terminal cardiac-state label leakage`
- `collection_beating` (protocol_context_shortcut): column `collection_beating_score`, AUC `0.6036`, expected `collection-level beating notes are context, not cell-intrinsic evidence`
- `experiment_batch` (batch_shortcut): column `experiment_batch_score`, AUC `0.4037`, expected `experiment batch checks provenance shortcut risk`
- `leiden_cluster_label_rate` (endpoint_adjacent_cluster_oracle): column `leiden_label_rate_score`, AUC `1.0000`, expected `cluster label-rate score is endpoint-adjacent`
- `individual_cm_rate` (donor_batch_shortcut): column `individual_cm_rate_score`, AUC `0.7164`, expected `line-level CM prevalence checks donor/protocol confounding`
- `collection_cm_rate` (collection_target_rate_shortcut): column `collection_cm_rate_score`, AUC `0.7900`, expected `collection-level CM prevalence checks pooled-collection shortcut risk`

## Sentinel relations

- `timepoint_protocol`: gap `0.2451`, proximity `0.0000`, Pearson `-0.0017`, alert `False`
- `published_pseudotime`: gap `0.3174`, proximity `0.0000`, Pearson `0.0824`, alert `False`
- `annotation_oracle`: gap `0.4181`, proximity `0.0000`, Pearson `0.0690`, alert `False`
- `terminal_state_oracle`: gap `0.3080`, proximity `0.0000`, Pearson `0.0548`, alert `False`
- `collection_beating`: gap `0.0217`, proximity `0.0000`, Pearson `0.0315`, alert `False`
- `experiment_batch`: gap `-0.1782`, proximity `-0.0000`, Pearson `0.0372`, alert `False`
- `leiden_cluster_label_rate`: gap `0.4181`, proximity `0.0000`, Pearson `0.0690`, alert `False`
- `individual_cm_rate`: gap `0.1345`, proximity `0.0000`, Pearson `0.0183`, alert `False`
- `collection_cm_rate`: gap `0.2080`, proximity `0.0000`, Pearson `-0.0013`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0187`
- Matched rows: `59740`
- Matched strata: `73`

## Early-window sensitivity

- Evaluated: `True`
- `cell_cycle_exit_score`: evaluated `True`, AUC `0.5819`
- `dpt_pseudotime_score`: evaluated `True`, AUC `0.8986`
- `diffday_numeric_score`: evaluated `True`, AUC `0.8270`

## Threshold sensitivity

- Fragile: `False`
- threshold `-0.5000`: selected `0.7220`, enrichment `0.0152`
- threshold `0.0000`: selected `0.3895`, enrichment `0.0188`
- threshold `0.5000`: selected `0.2045`, enrichment `0.0242`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
