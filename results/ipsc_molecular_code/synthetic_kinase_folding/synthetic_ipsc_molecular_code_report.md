# Synthetic iPSC Molecular-Code LAMP Audit

This is a controlled LAMP-Bio experiment, not a biological validation claim.
It asks whether a monitor is detecting an early molecular-code signal or
reading protocol structure / future folding state / endpoint labels.

## Biological Contract

- Signalling protocol: early kinase/phosphosignaling dynamics.
- Execution correctness: later protein folding, proteostasis, and aggregate burden.
- Clean evidence: disjoint early kinase plus early chaperone/UPR/autophagy features.
- Forbidden evidence: protocol, stressor, batch/donor/run metadata, future folding state, or endpoint labels.

## Synthetic Setup

- Rows: 1400 synthetic cells.
- Positive later folding-execution labels: 672; negatives: 728.
- Matched visible state: early morphology, density, and viability proxies.
- Endpoint is generated from latent proteostasis capacity plus later folding and aggregate burden.

## Monitor Comparison

| Monitor | Expected | Observed | AUC | Matched Delta | Bio Diagnosis | Temporal | Forbidden | Key Reasons |
|---|:---:|:---:|---:|---:|---|:---:|:---:|---|
| Clean hybrid kinase/proteostasis monitor | PASS | PASS | 0.914 | 0.611 | `valid_biological_signal_stable` | True | True | none |
| Kinase-only early monitor | FRAGILE_PASS_OR_FAIL | PASS | 0.906 | 0.605 | `valid_biological_signal_fragile` | True | True | none |
| Protocol/stressor shortcut | FAIL | FAIL | 0.663 | 0.211 | `protocol_confounded_signal` | True | False | forbidden, forbidden_protocol_feature_used_by_score, score_axis_not_declared_as_allowed_probe, protocol/batch sentinel |
| Future folding-state leakage | FAIL | FAIL | 0.957 | 0.699 | `endpoint_adjacent_contamination` | False | False | temporal, forbidden, endpoint_axis_reused_as_score_axis, temporal_isolation_failed, oracle proximity, protocol/batch sentinel |
| Oracle endpoint leakage | FAIL | FAIL | 1.000 | 1.000 | `endpoint_adjacent_contamination` | False | False | temporal, forbidden, endpoint_axis_reused_as_score_axis, temporal_isolation_failed, oracle proximity, protocol/batch sentinel |
| 0.5% oracle-contaminated hybrid monitor | FAIL | FAIL | 0.916 | 0.611 | `endpoint_adjacent_contamination` | False | False | temporal, forbidden, temporal_isolation_failed, oracle proximity, protocol/batch sentinel |

## Interpretation

The clean hybrid monitor is allowed to pass because it uses early, disjoint
kinase/proteostasis signals and retains a matched visible-state delta. The
kinase-only probe is informative but intentionally less stable: it captures
the signalling protocol without enough execution-buffer evidence. Protocol,
future-state, oracle, and low-dose oracle monitors fail for different reasons,
which is the useful property: LAMP is not just saying that biology is messy;
it is separating information-contract violations.
