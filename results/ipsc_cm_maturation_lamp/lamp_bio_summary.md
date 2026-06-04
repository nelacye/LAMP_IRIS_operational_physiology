# LAMP-Bio iPSC-CM Maturation Audit Summary

LAMP-Bio extends LAMP to AI-in-biomedicine claims where a model is said to
detect an early latent biological state. The current public-data artifacts use
iPSC-derived cardiomyocyte maturation as a testbed for protocol, timepoint,
endpoint-adjacent, and intervention shortcuts.

## Public Artifacts

| Artifact | Dataset | Claim Type | Valid/Candidate Score | Shortcut Sentinels | Main Result |
|---|---|---|---|---|---|
| GSE209997 maturation micro-audit | GEO `GSE209997` | D50 3D organotypic cardiac microtissue state | Curated cardiomyocyte maturation marker panel, AUC 1.000 | Day/timepoint AUC 0.833, 3D protocol AUC 0.833, endpoint-adjacent markers AUC 1.000 | Converts a maturation claim into a LAMP object and shows that protocol/timepoint sentinels are also predictive. |
| GSE201437 protocol-shortcut audit | GEO `GSE201437` | HCRP high-calcium plus ramp-pacing maturation condition | Curated cardiomyocyte maturation marker panel, AUC 1.000 | High calcium AUC 0.850, ramp pacing AUC 0.850, exact HCRP intervention code AUC 1.000 | Demonstrates the core LAMP-Bio failure mode: a maturation monitor can appear strong while intervention-condition shortcuts carry substantial signal. |
| GSE201437 controlled separation sanity check | GEO `GSE201437` | Known clean/protocol/leakage information contracts on the same expression rows | Clean disjoint calcium/electrophysiology probe, AUC 0.694, PASS | High-calcium shortcut AUC 0.857, FAIL; oracle leakage AUC 1.000, FAIL | Shows LAMP can emit PASS on biological data when the declared information contract is clean, rather than mechanically failing every messy dataset. |

## Robustness Check

The GSE201437 controlled separation was stress-tested with stratified bootstrap
resampling, alternative disjoint probe panels, leave-one-protocol-group-out
sensitivity, and audit-threshold grids.

| Check | Result | Interpretation |
|---|---|---|
| Stratified bootstrap | Clean probe PASS rate 0.503 over 300 resamples; shortcut/leakage expected-decision rate 1.000 | The clean PASS is reachable but small-n fragile; shortcut/leakage rejection is stable. |
| Alternative clean panels | 4/5 disjoint probe panels PASS | The result is not tied to exactly one marker list, but calcium-handling-only fails. |
| Leave-one-protocol-group-out | Clean probe PASS after leaving out HCNP, LCNP, or LCRP; FAIL after leaving out HCRP | The clean signal depends partly on HCRP coverage, which is expected in this tiny protocol-coupled table. |
| Threshold grid | Clean PASS rate 0.667 across tested audit cutoffs | The decision is sensitive to raising `valid_auc_min` to 0.70. |

Donor-held-out stability is not evaluable because the processed GEO table does
not expose donor IDs.

## Biological Contract Diagnosis

The iPSC-CM biological contract is defined in
`configs/ipsc_cm_maturation_contract.yaml` and documented in
`docs/ipsc_cm_maturation_contract.md`. Applying it to the controlled GSE201437
outputs gives:

| Model | Biological Diagnosis | Interpretation |
|---|---|---|
| Clean calcium/electrophysiology probe | `valid_biological_signal_fragile` | Plausible disjoint biological evidence, but bootstrap, leave-group-out, protocol-sentinel dominance, and donor-heldout warnings limit interpretation. |
| High-calcium protocol shortcut | `protocol_confounded_signal` | The monitor uses intervention metadata rather than an allowed biological probe axis. |
| Explicit oracle leakage | `endpoint_adjacent_contamination` | The monitor reuses the endpoint/label channel and fails temporal/forbidden isolation. |

## Interpretation Boundary

These are small public-data audit artifacts, not prospective biological
validation. Their purpose is to make the information contract explicit: a model
claiming early biological maturation inference must survive checks against
timepoint, batch, donor, protocol, intervention, and endpoint-adjacent channels.

The serious next benchmark should use high-replicate scRNA-seq or multimodal
iPSC-CM/organoid data with donor-held-out, protocol-held-out, and
stage-held-out splits, ideally with electrophysiology or calcium-imaging
endpoints.
