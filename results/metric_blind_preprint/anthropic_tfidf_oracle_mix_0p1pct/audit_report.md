# LAMP audit report: Anthropic model-written-evals sycophancy: TF-IDF + 0.1% oracle mixture

## Executive summary

- Primary score: `tfidf_prompt_valid_score_oracle_mix_0p1pct`
- Primary AUC: `0.9874`
- Audit-pass candidate: `False`
- Output classes: `forbidden_feature_contamination`, `oracle_label_leakage_sentinel`, `temporal_isolation_incomplete`, `valid_early_hidden_state_signal`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `False`
- Anchor: `anchor_step`
- Frozen before holdout: `source file`, `train/holdout split seed`, `TF-IDF model specification`, `sentinel columns`, `visible matching variables`, `thresholds`

Temporal violations:
- `oracle_answer_key_score` latest_offset_h=999.0

## Forbidden-feature screen

- Passed: `False`
- Declared sentinels present: `oracle_answer_key_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `oracle_answer_key_score`

## Negative controls

- noise_auc_mean: `0.4997`
- score_permutation_auc_mean: `0.4991`
- label_permutation_auc_mean: `0.5002`

## Sentinels

- `oracle_answer_key` (oracle_label): column `oracle_answer_key_score`, AUC `1.0000`, expected `dataset answer_matching_behavior field`

## Sentinel relations

- `oracle_answer_key`: gap `0.0126`, proximity `0.0095`, Pearson `0.8822`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.8669`
- Matched rows: `2992`
- Matched strata: `8`

## Early-window sensitivity

- Evaluated: `True`
- `tfidf_prompt_valid_score`: evaluated `True`, AUC `0.9873`
- `cue_prompt_valid_score`: evaluated `True`, AUC `0.8153`
- `visible_length_shortcut_score`: evaluated `True`, AUC `0.4654`
- `answer_key_leakage_score`: evaluated `True`, AUC `1.0000`
- `tfidf_prompt_valid_score_oracle_mix_0p1pct`: evaluated `True`, AUC `0.9874`

## Threshold sensitivity

- Fragile: `False`
- threshold `0.2500`: selected `0.7286`, enrichment `0.1844`
- threshold `0.5000`: selected `0.5093`, enrichment `0.4384`
- threshold `0.7500`: selected `0.2870`, enrichment `0.4965`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
