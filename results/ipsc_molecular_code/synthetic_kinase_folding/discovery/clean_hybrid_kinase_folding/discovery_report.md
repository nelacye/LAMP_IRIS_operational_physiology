# LAMP Discovery Dossier

This report turns a LAMP audit result into discovery-oriented hypotheses.
It does not convert an audit failure into validation; it converts the
failure into localized, testable next experiments.

## Monitor

- Score column: `clean_hybrid_kinase_folding_score`
- Primary AUC: 0.914
- Audit pass candidate: `True`

## Failure Localization

- Failure type: `audit_pass_discovery`
- Temporal passed: `True`
- Forbidden passed: `True`
- Valid score feature violations: `[]`

## Top Localized Features

| Feature | Source | Role/Axis | AUC | Inverted AUC | Corr(score) |
|---|---|---|---:|---:|---:|
| `early_mapk_phospho_slope` | declared_score_feature | MAPK/ERK axis | 0.856 | 0.144 | 0.860 |
| `early_chaperone_buffer` | declared_score_feature | chaperone buffering | 0.822 | 0.178 | 0.819 |
| `early_akt_mtor_pulse` | declared_score_feature | AKT/mTOR axis | 0.847 | 0.153 | 0.798 |
| `early_gsk3_cdk_balance` | declared_score_feature | GSK3/CDK balance | 0.810 | 0.190 | 0.770 |
| `early_upr_load` | declared_score_feature | unfolded-protein response | 0.234 | 0.766 | -0.708 |
| `early_autophagy_flux` | declared_score_feature | autophagy/proteasome axis | 0.739 | 0.261 | 0.656 |
| `early_stress_kinase_persistence` | declared_score_feature | stress-kinase persistence | 0.240 | 0.760 | -0.642 |
| `kinase_only_score` | molecular_axis_scan |  | 0.906 | 0.094 | 0.954 |
| `protocol_arm` | forbidden_feature | protocol/batch structure | 0.434 | 0.566 | -0.059 |
| `protocol_stressor_shortcut_score` | sentinel | protocol_shortcut | 0.663 | 0.337 | 0.009 |

## Mechanism Hypotheses

### H1. Candidate latent-state signal

- Confidence: `requires_prospective_test`
- Localized features: `[{'feature': 'early_mapk_phospho_slope', 'auc': 0.8559675071951858, 'axis_hint': 'MAPK/ERK axis', 'source': 'declared_score_feature'}, {'feature': 'early_chaperone_buffer', 'auc': 0.8218189920198848, 'axis_hint': 'chaperone buffering', 'source': 'declared_score_feature'}, {'feature': 'early_akt_mtor_pulse', 'auc': 0.8474416208791209, 'axis_hint': 'AKT/mTOR axis', 'source': 'declared_score_feature'}, {'feature': 'early_gsk3_cdk_balance', 'auc': 0.8102719453165882, 'axis_hint': 'GSK3/CDK balance', 'source': 'declared_score_feature'}, {'feature': 'early_upr_load', 'auc': 0.23367592229199372, 'axis_hint': 'unfolded-protein response', 'source': 'declared_score_feature'}, {'feature': 'early_autophagy_flux', 'auc': 0.739141810570382, 'axis_hint': 'autophagy/proteasome axis', 'source': 'declared_score_feature'}, {'feature': 'early_stress_kinase_persistence', 'auc': 0.23971824306645736, 'axis_hint': 'stress-kinase persistence', 'source': 'declared_score_feature'}, {'feature': 'kinase_only_score', 'auc': 0.9060803407901622, 'axis_hint': None, 'source': 'molecular_axis_scan'}]`
- Mechanism: The monitor survived the configured failure-mode tests. The top localized features are candidates for prospective perturbation.
- Testable prediction: Perturbing the localized kinase/proteostasis axis should shift the held-out folding endpoint without relying on protocol labels.

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

- Goal: Perturbing the localized kinase/proteostasis axis should shift the held-out folding endpoint without relying on protocol labels.
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
