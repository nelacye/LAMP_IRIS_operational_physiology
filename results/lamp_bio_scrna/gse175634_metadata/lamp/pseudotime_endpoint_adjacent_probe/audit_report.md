# LAMP audit report: GSE175634 scRNA metadata: DPT pseudotime endpoint-adjacent probe

## Executive summary

- Primary score: `dpt_pseudotime_score`
- Primary AUC: `0.8986`
- Inverted AUC: `0.1014`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `protocol_batch_or_donor_shortcut_sentinel`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Primary AUC = 0.899; inverted AUC = 0.101. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `diffday_num`
- Frozen before holdout: `GSE175634 accession`, `metadata-only first-pass contract`, `cardiomyocyte-state endpoint label`, `forbidden endpoint-adjacent sentinels`, `LAMP thresholds`

Temporal violations:
- `dpt_pseudotime_score` latest_offset_h=999.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `annotation_oracle_score`, `collection_beating_score`, `collection_cm_rate_score`, `diffday_numeric_score`, `dpt_pseudotime_score`, `experiment_batch_score`, `individual_cm_rate_score`, `leiden_label_rate_score`, `terminal_state_oracle_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `dpt_pseudotime_score`

## Negative controls

- noise_auc_mean: `0.4999`
- score_permutation_auc_mean: `0.5001`
- label_permutation_auc_mean: `0.5007`

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

- `timepoint_protocol`: gap `-0.0639`, proximity `1.2523`, Pearson `0.7724`, alert `False`
- `published_pseudotime`: gap `0.0000`, proximity `1.0000`, Pearson `1.0000`, alert `True`
- `annotation_oracle`: gap `0.1014`, proximity `0.7579`, Pearson `0.5109`, alert `True`
- `terminal_state_oracle`: gap `-0.0162`, proximity `1.0536`, Pearson `0.7312`, alert `True`
- `collection_beating`: gap `-0.2945`, proximity `13.8745`, Pearson `0.3460`, alert `False`
- `experiment_batch`: gap `-0.5014`, proximity `-1.7244`, Pearson `-0.0753`, alert `False`
- `leiden_cluster_label_rate`: gap `0.1014`, proximity `0.7579`, Pearson `0.5109`, alert `True`
- `individual_cm_rate`: gap `-0.1788`, proximity `2.2910`, Pearson `-0.0198`, alert `False`
- `collection_cm_rate`: gap `-0.0979`, proximity `1.4458`, Pearson `0.3018`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0953`
- Matched rows: `56347`
- Matched strata: `73`

## Early-window sensitivity

- Evaluated: `True`
- `cell_cycle_exit_score`: evaluated `True`, AUC `0.5819`
- `dpt_pseudotime_score`: evaluated `True`, AUC `0.8986`
- `diffday_numeric_score`: evaluated `True`, AUC `0.8270`

## Threshold sensitivity

- Fragile: `False`
- threshold `-0.5000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.0000`: selected `1.0000`, enrichment `0.0000`
- threshold `0.5000`: selected `0.0455`, enrichment `0.8993`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
