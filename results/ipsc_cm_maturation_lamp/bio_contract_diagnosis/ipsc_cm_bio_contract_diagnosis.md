# iPSC-CM Biological Contract Diagnosis

This report applies `configs/ipsc_cm_maturation_contract.yaml` to the
controlled GSE201437 LAMP sanity outputs. It translates raw audit classes
into biological maturation interpretation levels.

## Claim Contract

- Claim: disjoint calcium/electrophysiology evidence predicts structural maturation state.
- Endpoint axis: structural maturation.
- Allowed evidence axis: calcium-handling / electrophysiology maturation.
- Forbidden axis: day/protocol/intervention/batch/donor/drug/dose/replicate structure.
- Required sentinels: protocol, timepoint, endpoint-marker/oracle, donor/batch, score-direction sanity.

## Diagnosis Table

| Model | AUC | Audit Pass | Biological Diagnosis | Flags | Warnings |
|---|---:|:---:|---|---|---|
| Clean calcium/electrophysiology probe | 0.694 | True | `valid_biological_signal_fragile` | `none` | `bootstrap_pass_rate_below_stable_threshold`, `donor_heldout_not_evaluable`, `leave_group_out_pass_rate_below_stable_threshold`, `oracle_sentinel_present`, `protocol_heldout_not_evaluable`, `protocol_sentinel_dominance_present`, `threshold_grid_not_fully_stable` |
| High-calcium protocol shortcut | 0.857 | False | `protocol_confounded_signal` | `forbidden_protocol_feature_used_by_score`, `score_axis_not_declared_as_allowed_probe` | `oracle_sentinel_present`, `protocol_sentinel_dominance_present` |
| Explicit oracle leakage | 1.000 | False | `endpoint_adjacent_contamination` | `endpoint_axis_reused_as_score_axis`, `score_axis_not_declared_as_allowed_probe`, `temporal_isolation_failed` | `oracle_sentinel_present` |

## Interpretation

The claim has a plausible disjoint biological signal, but robustness or sentinel-dominance warnings limit interpretation.

For the current GSE201437 clean probe, the correct biological reading is:

> A disjoint calcium/electrophysiology probe supports a biologically plausible
> structural maturation signal, but the interpretation is fragile. Bootstrap
> PASS rate is approximately 0.503, leave-one-HCRP-out fails, and donor-held-out
> stability is not evaluable from the processed GEO table.

Protocol and oracle monitors are still rejected, so this is not evidence that
LAMP mechanically fails every biological dataset. It is evidence that the
current tiny biological PASS should be treated as a fragile sanity check, not
as a mature iPSC-CM validation claim.

## Stability Inputs

- Bootstrap PASS rate: 0.503.
- Bootstrap AUC mean: 0.706 (0.408-0.949).
- Alternative panel PASS rate: 0.800.
- Leave-group-out PASS rate: 0.750.
- Threshold-grid PASS rate: 0.667.
- Donor-held-out: not evaluable.
- Protocol-held-out: not evaluable for this tiny protocol-coupled sanity table.
