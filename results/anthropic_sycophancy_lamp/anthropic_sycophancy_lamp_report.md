# Anthropic Sycophancy LAMP Benchmark

Public real LLM-evaluation-data run using `Anthropic/model-written-evals`
`sycophancy_on_nlp_survey.jsonl`. The task is to predict whether the
sycophantic answer target is `(A)` on held-out examples.

- Held-out examples: 2996
- Dataset source: Anthropic/model-written-evals, sycophancy_on_nlp_survey
- Valid monitor: TF-IDF prompt-only classifier trained on public prompts
- Leaky monitors: direct answer-key field and low-dose answer-key mixtures

| Model | Type | AUC | Audit Status | Key Failures | Output Classes |
|---|---|---:|:---:|---|---|
| TF-IDF prompt-only sycophancy-target monitor | valid prompt-only monitor | 0.987 | PASS | none | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| Interpretable user-view cue monitor | valid cue monitor | 0.815 | PASS | none | `audit_pass_candidate;oracle_label_leakage_sentinel;valid_early_hidden_state_signal` |
| Visible length shortcut | visible shortcut | 0.465 | FAIL | null/destroyed | `null_or_destroyed_signal;oracle_label_leakage_sentinel;threshold_fragile_claim` |
| Answer-key leakage monitor | oracle leakage | 1.000 | FAIL | temporal, forbidden, oracle proximity | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| TF-IDF + answer-key leakage 1% | low-dose oracle leakage | 0.988 | FAIL | temporal, forbidden, oracle proximity | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| TF-IDF + answer-key leakage 5% | low-dose oracle leakage | 0.992 | FAIL | temporal, forbidden, oracle proximity | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| TF-IDF + answer-key leakage 10% | low-dose oracle leakage | 0.996 | FAIL | temporal, forbidden, oracle proximity | `forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;temporal_isolation_incomplete;valid_early_hidden_state_signal` |

## Interpretation

The prompt-only monitor passes LAMP with AUC 0.987. The direct
answer-key leakage monitor reaches AUC 1.000, but fails temporal
isolation, forbidden-feature screening, and oracle-proximity checks.

Low-dose answer-key mixtures show graded contamination: 1% AUC 0.988, 5% AUC 0.992, 10% AUC 0.996. LAMP flags them despite the small
nominal change from the valid prompt-only score.
