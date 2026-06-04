# LAMP-Bio Cross-Dataset Contrast: GSE201437 vs GSE175634

The interesting question is no longer `where does LAMP find PASS?`.
The stronger question is why one iPSC-CM dataset admits a fragile
disjoint biological signal while another collapses under a stricter
single-cell count-matrix contract.

## Main Contrast

| Dataset | Resolution | Allowed biology AUC | Best shortcut AUC | Oracle AUC | Diagnosis |
| --- | --- | ---: | ---: | ---: | --- |
| GSE201437 | sample-level processed expression | 0.694 | 0.857 | 1.000 | valid_biological_signal_fragile |
| GSE175634 | cell-level scRNA counts | 0.571 | 0.781 | 1.000 | not_biologically_interpretable_under_contract |

## Dataset-Level Reading

- **GSE201437**: A clean disjoint calcium/electrophysiology probe can pass, but stability is weak and HCRP leave-out collapses. bootstrap PASS rate 0.503; leave-group min AUC 0.524.
- **GSE175634**: Disjoint calcium/metabolic axes collapse under the strict single-cell contract, while day and pseudotime remain predictive. allowed bootstrap PASS rate 0.000; leave-individual min AUC 0.552.

The contrast is the result. LAMP is not mechanically saying all biology
fails, and it is not rewarding every high-AUC biological score. It separates
a small fragile sample-level signal from a large single-cell setting where
timepoint and trajectory-derived channels dominate the declared contract.

## Why Published Annotation AUC 0.654 Matters

The published CM annotation in GSE175634 is predictive but far from an oracle
for the strict structural endpoint. That means at least one of three things
is true: the annotation is not identical to structural maturation, the
structural endpoint is narrower than the cell-type label, or the dataset
contains many transitional cells. All three interpretations are biologically
interesting and argue against treating annotation, pseudotime, or day as
clean latent-state evidence.

## Working Formulation

> In a large real-world hiPSC differentiation dataset, independent biological
> axes failed to reproduce structural maturation labels under a strict
> disjoint-axis contract. Temporal and trajectory-derived channels remained
> highly predictive. This suggests that apparent maturation performance may
> be dominated by timepoint and reconstruction structure rather than
> transferable biological state information.

## Hypotheses

| Hypothesis | Evidence now | Next test | Status |
| --- | --- | --- | --- |
| A_marker_panels_are_bad | Possible, but not sufficient: the calcium/electrophysiology panel supports a fragile signal in GSE201437 and all selected marker genes are present in GSE175634. | Repeat with alternative curated panels and data-driven disjoint gene modules learned without endpoint genes. | open_but_not_primary |
| B_stage_specific_axis_decoupling | Plausible: GSE175634 pilot covers early/intermediate single-cell states where structural markers may rise before calcium/metabolic maturation becomes coordinated. | Run day-stratified and late-day-only audits; test structural->calcium and metabolic endpoint reversals. | strong_candidate |
| C_single_cell_noise_collapses_cross_axis_signal | Plausible: cell-level calcium/metabolic AUCs are near null, while published annotation only reaches AUC 0.654 against the strict structural endpoint, consistent with transitional/noisy cells. | Aggregate pseudo-bulk by individual x collection x day x cell type; compare cell-level, pseudo-bulk, and sample-level contracts. | strong_candidate |
| D_time_and_trajectory_channels_dominate | Strong: in GSE175634, day AUC 0.771 and pseudotime AUC 0.781 beat all allowed disjoint biology panels (best AUC 0.571). | Evaluate day-held-out, pseudotime-withheld, and reconstruction-free contracts across additional scRNA maturation datasets. | strong_candidate |

## Figure

![Allowed biology vs shortcut AUC](figures/allowed_biology_vs_shortcut_auc.png)

## Files

- Summary CSV: `results/lamp_bio_cross_dataset_contrast/gse201437_vs_gse175634_contrast_summary.csv`
- Hypotheses CSV: `results/lamp_bio_cross_dataset_contrast/gse201437_vs_gse175634_hypotheses.csv`
- Figure: `results/lamp_bio_cross_dataset_contrast/figures/allowed_biology_vs_shortcut_auc.png`
