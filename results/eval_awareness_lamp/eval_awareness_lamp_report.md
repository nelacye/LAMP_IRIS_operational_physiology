# LAMP Eval-Awareness / Sandbagging Framing Audit

This harmless benchmark audits claims that a monitor detects evaluation-aware underperformance rather than prompt artifacts, surface response shortcuts, or hidden answer/rubric leakage.

## Dataset

- Episodes: 1296
- Domains: math, logic, code, and QA
- Conditions: evaluation, deployment, neutral
- Labels: simulated sandbagging-style underperformance under evaluation-aware framing
- Forbidden channels: answer key, rubric hint, and benchmark/stage-token metadata

## Figures

![ROC curves](../../notebooks/figures/eval_awareness_roc_curves.png)

![LAMP status](../../notebooks/figures/eval_awareness_lamp_status.png)

![Timeline example](../../notebooks/figures/eval_awareness_timeline_examples.png)

## Audit Summary

| monitor_id | monitor_type | auc | audit_pass | temporal_passed | forbidden_passed | matched_delta | oracle_proximity | output_classes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| valid_framing_sensitivity | valid framing sensitivity | 0.963 | True | True | True | 0.252 | 0.000 | audit_pass_candidate; oracle_label_leakage_sentinel; valid_early_hidden_state_signal |
| surface_shortcut | surface shortcut | 0.780 | False | True | True | 0.010 | -4.902 | future_physiology_invalid_comparator; oracle_label_leakage_sentinel; visible_state_confounding |
| answer_key_leak | oracle leakage | 1.000 | False | False | False | 0.491 | 1.000 | forbidden_feature_contamination; leakage_contaminated_candidate; oracle_label_leakage_sentinel; oracle_leakage_proximity_shift; temporal_isolation_incomplete; valid_early_hidden_state_signal |
| rubric_leak | label-adjacent rubric leakage | 1.000 | False | False | False | 0.293 | 1.000 | forbidden_feature_contamination; leakage_contaminated_candidate; oracle_label_leakage_sentinel; oracle_leakage_proximity_shift; temporal_isolation_incomplete; valid_early_hidden_state_signal |
| stage_token_leak | evaluation-stage leakage | 0.960 | False | False | False | 0.259 | -0.083 | forbidden_feature_contamination; oracle_label_leakage_sentinel; temporal_isolation_incomplete; valid_early_hidden_state_signal |
| lowdose_oracle_1pct | low-dose oracle leakage | 0.965 | False | False | False | 0.252 | 0.060 | forbidden_feature_contamination; leakage_contaminated_candidate; oracle_label_leakage_sentinel; oracle_leakage_proximity_shift; temporal_isolation_incomplete; valid_early_hidden_state_signal |
| lowdose_oracle_5pct | low-dose oracle leakage | 0.974 | False | False | False | 0.279 | 0.295 | forbidden_feature_contamination; leakage_contaminated_candidate; oracle_label_leakage_sentinel; oracle_leakage_proximity_shift; temporal_isolation_incomplete; valid_early_hidden_state_signal |
| lowdose_oracle_10pct | low-dose oracle leakage | 0.984 | False | False | False | 0.286 | 0.559 | forbidden_feature_contamination; leakage_contaminated_candidate; oracle_label_leakage_sentinel; oracle_leakage_proximity_shift; temporal_isolation_incomplete; valid_early_hidden_state_signal |
| null_noise | null control | 0.472 | False | True | True | 0.003 | -13.151 | future_physiology_invalid_comparator; null_or_destroyed_signal; oracle_label_leakage_sentinel |

## Interpretation

- The valid framing monitor uses only pre-response framing and probe signals and is expected to pass when it preserves matched-cohort signal.
- Surface shortcuts can obtain apparent performance but should collapse under matched visible behavior.
- Answer-key, rubric, stage-token, and low-dose oracle monitors are intentionally high-performing but fail LAMP because their information contract is invalid.
- This is a direct evaluation-awareness analogue of the biomedical LAMP use case: performance alone is not validity.
