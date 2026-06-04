# LAMP Discovery Dossier

This report turns a LAMP audit result into discovery-oriented hypotheses.
It does not convert an audit failure into validation; it converts the
failure into localized, testable next experiments.

## Monitor

- Score column: `protocol_stressor_shortcut_score`
- Primary AUC: 0.663
- Audit pass candidate: `False`

## Failure Localization

- Failure type: `protocol_shortcut`
- Temporal passed: `True`
- Forbidden passed: `False`
- Valid score feature violations: `['protocol_stressor_shortcut_score']`

## Top Localized Features

| Feature | Source | Role/Axis | AUC | Inverted AUC | Corr(score) |
|---|---|---|---:|---:|---:|
| `protocol_stressor_shortcut_score` | sentinel | protocol_shortcut | 0.663 | 0.337 | 1.000 |
| `differentiation_day` | forbidden_feature | protocol/batch structure | 0.536 | 0.464 | 0.333 |
| `protocol_arm` | forbidden_feature | protocol/batch structure | 0.434 | 0.566 | -0.201 |
| `stressor_dose` | forbidden_feature | stress-kinase persistence | 0.442 | 0.558 | -0.203 |
| `protocol_intensity_score` | forbidden_feature | protocol/batch structure | 0.441 | 0.559 | -0.098 |
| `mass_spec_run_score` | sentinel | donor_batch_shortcut | 0.505 | 0.495 | 0.045 |
| `donor_id` | forbidden_feature | protocol/batch structure | 0.483 | 0.517 | 0.024 |
| `batch_id` | forbidden_feature | protocol/batch structure | 0.505 | 0.495 | 0.008 |
| `future_folding_execution_score` | sentinel | future_folding_execution | 0.957 | 0.043 | 0.023 |
| `late_aggregate_burden_score` | sentinel | future_folding_execution | 0.073 | 0.927 | -0.037 |

## Mechanism Hypotheses

### H1. Protocol-conditioned biology rather than latent-state inference

- Confidence: `actionable_qc`
- Localized features: `[{'feature': 'protocol_stressor_shortcut_score', 'auc': 0.6632632620355835, 'axis_hint': 'stress-kinase persistence', 'source': 'sentinel'}, {'feature': 'differentiation_day', 'auc': 0.5364368704212454, 'axis_hint': 'protocol/batch structure', 'source': 'forbidden_feature'}, {'feature': 'protocol_arm', 'auc': 0.4339085393772894, 'axis_hint': 'protocol/batch structure', 'source': 'forbidden_feature'}, {'feature': 'stressor_dose', 'auc': 0.44206035779696495, 'axis_hint': 'stress-kinase persistence', 'source': 'forbidden_feature'}, {'feature': 'protocol_intensity_score', 'auc': 0.440676510989011, 'axis_hint': 'protocol/batch structure', 'source': 'forbidden_feature'}, {'feature': 'mass_spec_run_score', 'auc': 0.5051163494243851, 'axis_hint': 'protocol/batch structure', 'source': 'sentinel'}, {'feature': 'donor_id', 'auc': 0.4827468848116169, 'axis_hint': 'protocol/batch structure', 'source': 'forbidden_feature'}, {'feature': 'batch_id', 'auc': 0.5048087143511251, 'axis_hint': 'protocol/batch structure', 'source': 'forbidden_feature'}]`
- Mechanism: The monitor reads protocol or stressor assignment. The shortcut may still be biologically informative, but it cannot support the declared hidden-state claim without a balanced perturbation design.
- Testable prediction: After crossing protocol arms across donors and batches, the shortcut score should collapse while a genuine molecular-code signal remains.

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

- Goal: After crossing protocol arms across donors and batches, the shortcut score should collapse while a genuine molecular-code signal remains.
- Format: 96-well balanced time-course sketch
- Timepoints (min): `[0, 15, 30, 60, 120]`
- Perturbations: `['protocol arm A', 'protocol arm B', 'stressor low', 'stressor high']`
- Readouts: `['declared early kinase/proteostasis panel', 'held-out folding endpoint panel', 'batch/donor sentinel panel']`
- Controls: `['vehicle controls in every plate quadrant', 'donor-balanced wells', 'batch/run randomized acquisition order', 'endpoint markers hidden from monitor scoring']`

### Opentrons-Oriented Sketch

- Plate: 96-well flat-bottom plate
- Replicates per condition: 4
- Liquid classes: `['vehicle', 'kinase_modulator', 'stressor', 'lysis_or_fixation_buffer']`
- Note: This is a design sketch, not a wet-lab protocol. Volumes, cell density, compound identity, and biosafety constraints must be set by the experimental team.
