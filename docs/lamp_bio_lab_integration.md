# LAMP-Bio Lab Integration

LAMP-Bio extends the audit from "does this score pass?" to "what laboratory
decision produced the evidence, and could that decision be the shortcut?"

The executable contract is:

`configs/lamp_bio_lab_integration_contract.yaml`

The synthetic demo is:

```bash
python scripts/run_lamp_bio_lab_integration_demo.py
```

It writes:

- `results/lamp_bio_lab_integration/lamp_bio_lab_integration_report.md`
- `results/lamp_bio_lab_integration/qc_decisions.csv`
- `results/lamp_bio_lab_integration/cluster_annotation.csv`
- `results/lamp_bio_lab_integration/context_manifest_audit.csv`
- `results/lamp_bio_lab_integration/cross_modal_sample_table.csv`
- `results/lamp_bio_lab_integration/hypothesis_dossier.csv`

## 1. QC Decisions

Single-cell QC is not just preprocessing. It is a provenance layer that can
become a hidden shortcut.

LAMP-Bio records:

- mitochondrial burden
- gene/count depth
- doublet score
- ambient RNA score
- stress-signature score
- keep/review/drop decision
- near-threshold rate
- per-sample QC burden

The audit question is:

> Is the model detecting biology, or is it detecting the way cells were filtered?

Important failure modes:

- `qc_artifact_shortcut`: score tracks mitochondrial burden, ambient RNA,
  doublets, low-count cells, or retained-cell fraction.
- `qc_threshold_fragility`: biological conclusion changes when reasonable QC
  thresholds move.

## 2. Biological Annotation

Cluster annotation is an interpretation layer, not ground truth. LAMP-Bio keeps
annotation probabilistic:

- top label
- confidence
- second-best label
- top-minus-second margin
- ambiguity flag
- contamination flag

Example ambiguity:

```text
cluster_7 -> ventricular_cm, confidence 0.51
second_best -> stressed_cm, confidence 0.43
diagnosis -> unknown_or_mixed
```

The audit question is:

> Is the monitor using a biological state, or a manual/atlas/cluster-label artifact?

Important failure modes:

- `annotation_shortcut`: score learns cluster ID or manual annotation.
- `contamination_as_signal`: fibroblast, endothelial, stressed-cell, or
  low-quality-cell composition explains the claim.

## 3. Experimental Context Integration

Most biological shortcuts live outside the expression matrix.

Required context fields:

- donor
- batch
- protocol
- plate
- passage
- medium
- stimulation
- timepoint
- replicate

LAMP-Bio treats these as metadata and sentinel sources, not as biological
evidence. They may be present in the table, but they must not enter the valid
score unless the claim explicitly targets that intervention.

The audit question is:

> Could this score be reconstructed from donor, protocol, batch, plate, passage,
> medium, or stimulation?

Important failure modes:

- `protocol_shortcut`
- `donor_batch_plate_shortcut`
- `context_missingness_risk`
- `protocol_not_balanced_across_donor_or_batch`

## 4. Cross-Modal Integration

LAMP-Bio supports multimodal evidence but requires axis disjointness.

Example modalities:

- RNA: structural, calcium-handling, metabolic, stress, cell-cycle axes
- phosphoproteomics: kinase, stress-kinase, proteostasis axes
- morphology: sarcomere alignment, cell area, shape regularity
- calcium traces: transient amplitude, decay, beat regularity, arrhythmia burden

The audit question is:

> Do independent modalities point to the same hidden biological transition, or
> is one modality acting as a future/endpoint/protocol sentinel?

Important rules:

- Endpoint axis and score axis must be disjoint.
- Future calcium traces are sentinels unless available at the anchor.
- Context fields are sentinels, not biological evidence.
- QC burden is a sentinel or covariate, not primary biological evidence.

## 5. Hypothesis Generation

LAMP-Bio hypothesis generation is post-audit. It does not turn a failed score
into validation.

Allowed hypothesis outputs:

- hidden-state transition hypothesis
- localized modality or biological axis
- alternative shortcut explanation
- prospective perturbation or holdout test

Example:

```text
Likely hidden-state transition:
  calcium-handling maturation

Localized evidence:
  RNA calcium-handling axis + phospho-kinase axis + early morphology

Alternative explanation:
  protocol/high-calcium condition or QC/stress burden

Prospective test:
  hide future calcium traces, balance donor/batch/protocol, perturb early kinase
  signaling, and retest a disjoint structural/electrophysiology endpoint.
```

## Practical Interpretation

LAMP-Bio should report results in this form:

```text
The monitor supports a calcium-handling maturation hypothesis under the declared
contract, but the claim remains fragile because protocol/context and QC sentinels
are not fully dominated by the biological score.
```

That is a laboratory-facing answer. It is more useful than "AUC good" and more
honest than "model discovered maturation."
