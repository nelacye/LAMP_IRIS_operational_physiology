# LAMP Discovery Dossier

This report turns a LAMP audit result into discovery-oriented hypotheses.
It does not convert an audit failure into validation; it converts the
failure into localized, testable next experiments.

## Monitor

- Score column: `future_folding_execution_score`
- Primary AUC: 0.957
- Audit pass candidate: `False`

## Failure Localization

- Failure type: `future_folding`
- Temporal passed: `False`
- Forbidden passed: `False`
- Valid score feature violations: `['future_folding_execution_score']`

## Top Localized Features

| Feature | Source | Role/Axis | AUC | Inverted AUC | Corr(score) |
|---|---|---|---:|---:|---:|
| `future_folding_execution_score` | sentinel | future_folding_execution | 0.957 | 0.043 | 1.000 |
| `late_aggregate_burden_score` | sentinel | future_folding_execution | 0.073 | 0.927 | -0.946 |
| `clean_hybrid_kinase_folding_score` | molecular_axis_scan | folding execution | 0.914 | 0.086 | 0.923 |
| `oracle_folding_label_score` | sentinel | oracle_label | 1.000 | 0.000 | 0.741 |
| `label_later_folding_execution_stable` | molecular_axis_scan | folding execution | 1.000 | 0.000 | 0.741 |
| `early_mapk_phospho_slope` | molecular_axis_scan | MAPK/ERK axis | 0.856 | 0.144 | 0.815 |
| `early_stress_kinase_persistence` | molecular_axis_scan | stress-kinase persistence | 0.240 | 0.760 | -0.583 |
| `early_autophagy_flux` | molecular_axis_scan | autophagy/proteasome axis | 0.739 | 0.261 | 0.567 |
| `protocol_stressor_shortcut_score` | sentinel | protocol_shortcut | 0.663 | 0.337 | 0.023 |
| `stressor_dose` | forbidden_feature | stress-kinase persistence | 0.442 | 0.558 | -0.058 |

## Mechanism Hypotheses

### H1. Time-lagged kinase-to-folding coupling

- Confidence: `hypothesis_generating`
- Localized features: `[{'feature': 'early_mapk_phospho_slope', 'auc': 0.8559675071951858, 'axis_hint': 'MAPK/ERK axis', 'source': 'molecular_axis_scan'}, {'feature': 'future_folding_execution_score', 'auc': 0.9567246369701727, 'axis_hint': 'folding execution', 'source': 'sentinel'}]`
- Mechanism: The monitor is invalid as an early predictor because it uses post-anchor folding state, but the same localized channel can suggest a causal time-lag: early kinase dynamics may precede later proteostasis/folding execution.
- Testable prediction: Modulating the localized kinase axis should alter the localized folding/proteostasis readout at later 15/30/60/120 minute windows.

### H2. Sentinel-driven hypothesis: protocol_stressor

- Confidence: `sentinel_supported`
- Localized features: `[{'feature': 'protocol_stressor_shortcut_score', 'auc': 0.6632632620355835, 'role': 'protocol_shortcut'}]`
- Mechanism: The monitor is reading intervention, timing, donor, batch, or run structure rather than the declared latent biology.
- Testable prediction: Use a balanced factorial plate with protocol, donor, and batch crossed against the perturbation of interest.

### H3. Sentinel-driven hypothesis: future_folding

- Confidence: `sentinel_supported`
- Localized features: `[{'feature': 'future_folding_execution_score', 'auc': 0.9567246369701727, 'role': 'future_folding_execution'}]`
- Mechanism: The score is close to post-anchor folding/proteostasis state. This can be an invalid future channel, but the localized feature can also define a time-lagged biological hypothesis.
- Testable prediction: Run a time-course perturbation with early kinase modulation and measure folding/proteostasis markers at 15, 30, 60, and 120 minutes.

### H4. Sentinel-driven hypothesis: late_aggregate_burden

- Confidence: `sentinel_supported`
- Localized features: `[{'feature': 'late_aggregate_burden_score', 'auc': 0.07317626569858712, 'role': 'future_folding_execution'}]`
- Mechanism: The score is close to post-anchor folding/proteostasis state. This can be an invalid future channel, but the localized feature can also define a time-lagged biological hypothesis.
- Testable prediction: Run a time-course perturbation with early kinase modulation and measure folding/proteostasis markers at 15, 30, 60, and 120 minutes.

## Follow-Up Experiment Sketch

- Goal: Modulating the localized kinase axis should alter the localized folding/proteostasis readout at later 15/30/60/120 minute windows.
- Format: 96-well balanced time-course sketch
- Timepoints (min): `[0, 15, 30, 60, 120]`
- Perturbations: `['AKT/mTOR inhibitor', 'GSK3/CDK modulation', 'HSP90 chaperone modulation', 'vehicle control']`
- Readouts: `['phospho-kinase panel', 'HSP90/HSPA5 chaperone panel', 'UPR/autophagy panel', 'aggregate/folding endpoint panel']`
- Controls: `['vehicle controls in every plate quadrant', 'donor-balanced wells', 'batch/run randomized acquisition order', 'endpoint markers hidden from monitor scoring']`

### Opentrons-Oriented Sketch

- Plate: 96-well flat-bottom plate
- Replicates per condition: 4
- Liquid classes: `['vehicle', 'kinase_modulator', 'stressor', 'lysis_or_fixation_buffer']`
- Note: This is a design sketch, not a wet-lab protocol. Volumes, cell density, compound identity, and biosafety constraints must be set by the experimental team.
