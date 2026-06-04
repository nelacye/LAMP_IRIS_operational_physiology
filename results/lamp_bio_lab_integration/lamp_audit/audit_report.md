# LAMP audit report: Synthetic LAMP-Bio lab integration demo

## Executive summary

- Primary score: `cross_modal_maturation_score`
- Primary AUC: `0.9506`
- Inverted AUC: `0.0494`
- Score-direction ambiguous: `False`
- Audit-pass candidate: `True`
- Output classes: `audit_pass_candidate`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `valid_early_hidden_state_signal`

Primary AUC = 0.951; inverted AUC = 0.049. No strong score-direction ambiguity was detected under the default higher-score-means-positive convention.

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_time_h`
- Frozen before holdout: `QC policy`, `annotation policy`, `context manifest fields`, `cross-modal score formula`, `sentinel definitions`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `annotation_contamination_sentinel_score`, `endpoint_oracle_score`, `future_calcium_trace_score`, `protocol_context_sentinel_score`, `qc_burden_sentinel_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.4934`
- score_permutation_auc_mean: `0.5069`
- label_permutation_auc_mean: `0.5034`

## Sentinels

- `future_calcium_trace` (future_physiology): column `future_calcium_trace_score`, AUC `0.9979`, expected `future functional calcium comparator`
- `endpoint_oracle` (oracle_label): column `endpoint_oracle_score`, AUC `1.0000`, expected `endpoint-adjacent readiness comparator`
- `protocol_context` (protocol_shortcut): column `protocol_context_sentinel_score`, AUC `0.6204`, expected `protocol, medium, stimulation context comparator`
- `qc_burden` (qc_artifact_shortcut): column `qc_burden_sentinel_score`, AUC `0.2021`, expected `QC filtering and low-quality-cell comparator`
- `annotation_contamination` (annotation_contamination_shortcut): column `annotation_contamination_sentinel_score`, AUC `0.1705`, expected `fibroblast/stressed-cell composition comparator`

## Sentinel relations

- `future_calcium_trace`: gap `0.0473`, proximity `NA`, Pearson `0.8244`, alert `False`
- `endpoint_oracle`: gap `0.0494`, proximity `NA`, Pearson `0.7198`, alert `False`
- `protocol_context`: gap `-0.3303`, proximity `NA`, Pearson `0.2932`, alert `False`
- `qc_burden`: gap `-0.7486`, proximity `NA`, Pearson `-0.7332`, alert `False`
- `annotation_contamination`: gap `-0.7801`, proximity `NA`, Pearson `-0.7396`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.1003`
- Matched rows: `115`
- Matched strata: `6`

## Early-window sensitivity

- Evaluated: `True`
- `early_rna_calcium_axis`: evaluated `True`, AUC `0.9292`
- `early_phospho_kinase_axis`: evaluated `True`, AUC `0.8738`
- `early_morphology_sarcomere_axis`: evaluated `True`, AUC `0.8602`

## Threshold sensitivity

- Fragile: `False`
- threshold `-1.0000`: selected `0.8500`, enrichment `0.0922`
- threshold `0.0000`: selected `0.5444`, enrichment `0.3349`
- threshold `1.0000`: selected `0.1333`, enrichment `0.4778`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
