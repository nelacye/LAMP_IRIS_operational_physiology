# LAMP audit report: Anthropic model-written-evals sycophancy: Answer-key leakage monitor

## Executive summary

- Primary score: `answer_key_leakage_score`
- Primary AUC: `1.0000`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `leakage_contaminated_candidate`, `oracle_label_leakage_sentinel`, `oracle_leakage_proximity_shift`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `anchor_step`
- Frozen before holdout: `source file`, `train/holdout split seed`, `TF-IDF model specification`, `sentinel columns`, `visible matching variables`, `thresholds`

Temporal violations:
- `oracle_answer_key_score` latest_offset_h=1.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `oracle_answer_key_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `oracle_answer_key_score`

## Negative controls

- noise_auc_mean: `0.4997`
- score_permutation_auc_mean: `0.4994`
- label_permutation_auc_mean: `0.5000`

## Sentinels

- `oracle_answer_key` (oracle_label): column `oracle_answer_key_score`, AUC `1.0000`, expected `dataset answer_matching_behavior field`

## Sentinel relations

- `oracle_answer_key`: gap `0.0000`, proximity `1.0000`, Pearson `1.0000`, alert `True`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `1.0000`
- Matched rows: `2035`
- Matched strata: `6`

## Early-window sensitivity

- Evaluated: `True`
- `tfidf_prompt_valid_score`: evaluated `True`, AUC `0.9873`
- `cue_prompt_valid_score`: evaluated `True`, AUC `0.8153`
- `visible_length_shortcut_score`: evaluated `True`, AUC `0.4654`
- `answer_key_leakage_score`: evaluated `True`, AUC `1.0000`
- `tfidf_oracle_mix_1pct`: evaluated `True`, AUC `0.9885`
- `tfidf_oracle_mix_5pct`: evaluated `True`, AUC `0.9925`
- `tfidf_oracle_mix_10pct`: evaluated `True`, AUC `0.9959`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2500`: selected `0.5000`, enrichment `0.5000`
- threshold `0.5000`: selected `0.5000`, enrichment `0.5000`
- threshold `0.7500`: selected `0.5000`, enrichment `0.5000`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
