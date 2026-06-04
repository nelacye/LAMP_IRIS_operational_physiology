# LAMP-Bio Lab Integration Demo

This synthetic artifact integrates five lab-facing decision layers into a LAMP-Bio audit: single-cell QC, biological annotation, experimental context, cross-modal evidence, and hypothesis generation.

## 1. QC Decisions

- Cells audited: `11101`
- Decisions: `drop`=7006, `keep`=2703, `review`=1392
- Top QC reasons: `ambient_rna`=6199, `pass`=2703, `high_mito`=1103, `near_ambient`=1018, `doublet`=1005, `near_high_mito`=372
- Mean review/drop burden by well is encoded as `qc_burden_sentinel_score`.

## 2. Biological Annotation

- Clusters annotated: `6`
- Ambiguous clusters: `5`
- Contamination-flagged clusters: `1`

| Cluster | Label | Confidence | Second Best | Ambiguous | Contamination |
| ---: | --- | ---: | --- | --- | --- |
| 0 | unknown_or_mixed | 0.547 | fibroblast_contamination | True | False |
| 1 | unknown_or_mixed | 0.467 | fibroblast_contamination | True | False |
| 2 | unknown_or_mixed | 0.501 | immature_cm | True | False |
| 3 | ventricular_cm | 0.618 | immature_cm | False | False |
| 4 | unknown_or_mixed | 0.336 | ventricular_cm | True | False |
| 5 | unknown_or_mixed | 0.413 | stressed_cm | True | True |

## 3. Experimental Context

- Wells/samples: `180`
- Mean context completeness: `1.000`
- Context fields are retained as metadata/sentinels, not valid biological score evidence.

## 4. Cross-Modal LAMP Audit

- Cross-modal score AUC: `0.951`
- Matched observed-state delta: `0.100`
- Audit pass candidate: `True`
- Output classes: `audit_pass_candidate`, `oracle_label_leakage_sentinel`, `protocol_batch_or_donor_shortcut_sentinel`, `valid_early_hidden_state_signal`

| Sentinel | Role | AUC |
| --- | --- | ---: |
| future_calcium_trace | future_physiology | 0.998 |
| endpoint_oracle | oracle_label | 1.000 |
| protocol_context | protocol_shortcut | 0.620 |
| qc_burden | qc_artifact_shortcut | 0.202 |
| annotation_contamination | annotation_contamination_shortcut | 0.171 |

## 5. Hypothesis Generation

Top biological hypothesis: `calcium_handling_maturation` with support `0.776`.
Strongest sentinel/control channel: `future_endpoint_leakage` with support `0.998`. This is not a valid biological hypothesis; it is the channel to remove, hide, or hold out before validation.

| Rank | Category | Hypothesis | Support | Top Feature / Axis | Prospective Test |
| ---: | --- | --- | ---: | --- | --- |
| 1 | biological_hypothesis | calcium_handling_maturation | 0.776 | early_rna_calcium_axis | Hold out future calcium traces, perturb early kinase/calcium axes, and retest a disjoint structural or electrophysiology endpoint. |
| 2 | alternative_shortcut | contamination_composition_shift | 0.706 | stressed_cm_fraction | Match or purify cell-type composition and retest after removing fibroblast/stressed-cell composition from the score. |
| 3 | alternative_shortcut | stress_or_qc_artifact | 0.373 | qc_burden_sentinel_score | Match QC burden, perturb QC thresholds, run ambient-RNA correction, and check whether the signal survives. |
| 4 | alternative_shortcut | protocol_or_batch_shortcut | 0.241 | protocol_context_sentinel_score | Cross donor, batch, protocol, plate, medium, and stimulation in a balanced design; require protocol-heldout performance. |
| 5 | sentinel_control | future_endpoint_leakage | 0.998 | endpoint_oracle_score | Remove endpoint-adjacent and future trace channels from the monitor and repeat with a frozen pre-anchor feature set. |

## Interpretation

The demo does not claim biological discovery. It shows the intended LAMP-Bio behavior: QC decisions, annotation ambiguity, and context fields are first-class audit objects; cross-modal evidence is interpreted only after sentinels and matched cohorts are checked; hypotheses are emitted as prospective tests, not validation.

## Files

- `qc_decisions.csv`
- `cluster_annotation.csv`
- `context_manifest_audit.csv`
- `cross_modal_sample_table.csv`
- `hypothesis_dossier.csv`
- `lamp_audit/audit_summary.json`
- `figures/qc_decision_summary.png`
- `figures/hypothesis_support.png`