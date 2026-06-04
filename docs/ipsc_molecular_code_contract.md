# iPSC Molecular-Code Contract

This LAMP-Bio contract audits a hybrid claim:

> Early kinase/phosphosignaling dynamics plus early proteostasis state predict
> later protein-folding execution quality.

The core distinction is not "kinases versus folding." The claim is that kinase
phosphorylation trajectories are the signalling protocol, while folding,
chaperone buffering, proteostasis, and aggregation are execution correctness.
LAMP asks whether a monitor is reading this molecular-code trajectory or
exploiting protocol structure, future endpoint state, or label-adjacent
features.

## Biological Axes

`kinase_phosphosignaling_dynamics`

Early phosphorylation dynamics in MAPK/ERK, PI3K/AKT/mTOR, JAK/STAT,
stress-energy kinases, and neurodegeneration-linked kinases such as GSK3B,
CDK5, LRRK2, and PRKACA.

`protein_folding_execution_proteostasis`

Chaperone buffering, unfolded-protein response, proteasome/autophagy balance,
and neurodegenerative effector proteins such as SNCA, MAPT, APP, TARDBP, FUS,
SOD1, and HTT.

`kinase_folding_coupled_signal`

A declared composite axis for early signals that combine phosphorylation
dynamics with early proteostasis buffering. This is the intended clean monitor
axis for the synthetic control.

`intervention_protocol_structure`

Forbidden evidence: differentiation day, protocol, induction method, kinase
inhibitor, stressor, treatment, dose, donor/line/clone ID, plate, batch,
phospho-enrichment batch, mass-spec run, or sequencing lane.

## Claim Contract

For the default claim, the endpoint axis is later
`protein_folding_execution_proteostasis`. A clean monitor may use
`kinase_phosphosignaling_dynamics`, early proteostasis-buffering features, or the
declared coupled axis, but not future folding state, endpoint labels, exact
endpoint markers, or protocol metadata.

Required sentinels:

- protocol/timepoint sentinel
- donor/batch/run sentinel
- endpoint-effector oracle
- future-folding sentinel
- score-direction sanity check

## Synthetic Control

Run:

```bash
python scripts/run_synthetic_ipsc_molecular_code_audit.py
```

The script writes a synthetic prediction table, per-monitor LAMP configs, JSON
audit summaries, bio-contract diagnoses, and a Markdown report under:

```text
results/ipsc_molecular_code/synthetic_kinase_folding/
```

Expected separation:

| Monitor | Intended Role | Expected Diagnosis |
|---|---|---|
| Clean hybrid kinase/proteostasis monitor | early disjoint molecular-code signal | `valid_biological_signal_stable` |
| Kinase-only early monitor | useful but incomplete signalling probe | `valid_biological_signal_fragile` |
| Protocol/stressor shortcut | forbidden protocol structure | `protocol_confounded_signal` |
| Future folding-state leakage | post-anchor endpoint-adjacent state | `endpoint_adjacent_contamination` |
| Oracle endpoint leakage | direct label leakage | `endpoint_adjacent_contamination` |
| 0.5% oracle-contaminated hybrid monitor | metric-blind low-dose leakage | `endpoint_adjacent_contamination` |

This is a positive-control experiment, not a biological validation claim. It
checks that LAMP can say PASS for a clean known-generative signal and FAIL for
shortcut/leakage monitors on the same rows.

## Real-Data Direction

The most natural public-data progression is:

1. Longitudinal iPSC-derived neuron proteome/phosphoproteome data with matched
   time points, using early phosphosite/kinase dynamics to predict later
   proteostasis or maturation axes.
2. iPSC-derived dopaminergic neuron protein-turnover data for Parkinson's-like
   proteostasis and mitochondrial turnover claims.
3. iPSC-derived neuron tau/SNCA proteostasis or aggregation screens where
   endpoint-adjacent aggregate markers must be sentinels rather than score
   evidence.

The biological claim should be written before training:

```yaml
claim: Early kinase/phosphosignaling dynamics predicts later protein-folding execution
endpoint_axis: protein_folding_execution_proteostasis
allowed_probe_axes:
  - kinase_phosphosignaling_dynamics
  - kinase_folding_coupled_signal
forbidden_axes:
  - intervention_protocol_structure
required_sentinels:
  - protocol_sentinel
  - timepoint_sentinel
  - donor_batch_sentinel
  - future_folding_sentinel
  - endpoint_effector_oracle
```

That order matters. Otherwise LAMP becomes a suspiciousness calculator rather
than an interpreter of a declared biological latent-state claim.
