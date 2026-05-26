# LAMP audit report: Anthropic model-written-evals sycophancy: Visible length shortcut

## Executive summary

- Primary score: `visible_length_shortcut_score`
- Primary AUC: `0.4654`
- Audit-pass candidate: `False`
- Output classes: `null_or_destroyed_signal`, `oracle_label_leakage_sentinel`, `threshold_fragile_claim`

Passing LAMP does not establish clinical validity. It means the score survived
the configured failure-mode audit and earned prospective testing.

## Temporal isolation

- Declared: `True`
- Passed: `True`
- Anchor: `anchor_step`
- Frozen before holdout: `source file`, `train/holdout split seed`, `TF-IDF model specification`, `sentinel columns`, `visible matching variables`, `thresholds`

## Forbidden-feature screen

- Passed: `True`
- Declared sentinels present: `oracle_answer_key_score`
- Unexpected forbidden columns: `none`
- Valid-score feature violations: `none`

## Negative controls

- noise_auc_mean: `0.4997`
- score_permutation_auc_mean: `0.5005`
- label_permutation_auc_mean: `0.4998`

## Sentinels

- `oracle_answer_key` (oracle_label): column `oracle_answer_key_score`, AUC `1.0000`, expected `dataset answer_matching_behavior field`

## Sentinel relations

- `oracle_answer_key`: gap `0.5346`, proximity `-40.9640`, Pearson `-0.0622`, alert `False`

## Visible-state matching

- Evaluated: `True`
- Matched observed-state delta: `0.0369`
- Matched rows: `2992`
- Matched strata: `8`

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

- Fragile: `True`
- threshold `0.2500`: selected `0.8949`, enrichment `0.0028`
- threshold `0.5000`: selected `0.2827`, enrichment `-0.0643`
- threshold `0.7500`: selected `0.0137`, enrichment `-0.1585`

## Interpretation boundary

LAMP is a failure-mode audit, not a substitute for prospective clinical
validation, deployment monitoring, safety review, or causal proof. A surviving
score should be described as an audit-pass candidate for prospective testing.
