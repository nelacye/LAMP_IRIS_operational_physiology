# LAMP-Bio Mechanistic Interpretation Layer

This layer moves beyond feature importance. It asks whether allowed
GSE175634 pseudo-bulk feature genes that help separate structural maturity
also have mechanistic support in independent or orthogonal evidence channels.

The current computed evidence channels are:

1. independent regulon/module expression in `GSE201437` RNA-seq;
2. motif/target-set enrichment proxy over top allowed feature genes;
3. virtual cistrome transfer support from public cardiac/iPSC-CM ChIP or footprint datasets.

Important caveat: TF activity here still does not mean direct TF binding,
nuclear localization, phosphorylation, or perturbation. The regulon channel
uses a curated module-expression proxy, and the tested feature gene is
removed from each module before correlation. Motif enrichment is a
lightweight target-set proxy, not a full promoter scan.

## Candidate Bridges

| Feature | Panel | TF | Feature AUC | Regulon r | Regulon p | Motif | Cistrome | Mechanistic evidence | Status |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| CACNA1C | calcium_electrophysiology | TBX5 | 0.827 | 0.785 | 0.00089 | yes | yes | 3/3 | three_channel_mechanistic_bridge |
| ATP2A2 | calcium_electrophysiology | TBX5 | 0.813 | 0.736 | 0.00268 | yes | yes | 3/3 | three_channel_mechanistic_bridge |
| RYR2 | calcium_electrophysiology | TBX5 | 0.877 | 0.653 | 0.0114 | yes | yes | 3/3 | three_channel_mechanistic_bridge |
| COX6A2 | metabolic | PPARGC1A/PGC-1A | 0.959 | 0.903 | 9.56e-06 | yes | no | 2/3 | two_channel_mechanistic_bridge |
| SLC25A4 | metabolic | PPARGC1A/PGC-1A | 0.708 | 0.741 | 0.00245 | yes | no | 2/3 | two_channel_mechanistic_bridge |
| ACADVL | metabolic | PPARGC1A/PGC-1A | 0.784 | 0.723 | 0.00348 | yes | no | 2/3 | two_channel_mechanistic_bridge |
| PLN | calcium_electrophysiology | PPARGC1A/PGC-1A | 0.918 | 0.719 | 0.00378 | yes | no | 2/3 | two_channel_mechanistic_bridge |
| PPARGC1A | metabolic | PPARGC1A/PGC-1A | 0.833 | 0.679 | 0.00756 | yes | no | 2/3 | two_channel_mechanistic_bridge |
| CACNA1C | calcium_electrophysiology | NKX2-5 | 0.827 | 0.626 | 0.0165 | no | yes | 2/3 | two_channel_mechanistic_bridge |
| ACADVL | metabolic | GATA4 | 0.784 | 0.609 | 0.0209 | no | yes | 2/3 | two_channel_mechanistic_bridge |
| CPT1B | metabolic | TBX5 | 0.661 | 0.569 | 0.0336 | yes | yes | 2/3 | two_channel_mechanistic_bridge |
| KCNQ1 | calcium_electrophysiology | TBX5 | 0.719 | 0.226 | 0.436 | yes | yes | 2/3 | two_channel_mechanistic_bridge |

## Direct Validation Inventory

| Accession | Organism | Cell type | Modalities | LAMP use | Access note |
| --- | --- | --- | --- | --- | --- |
| [GSE133833](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE133833) | Homo sapiens | iPSC-derived cardiomyocyte | RNA-seq; ATAC-seq; NKX2-5 ChIP-seq; H3K27ac ChIP-seq | validate whether RNA regulon/module proxy tracks direct NKX2-5 occupancy in matched iPSC-CM samples | GEO metadata/public series; raw controlled-access note must be handled before a full validation run |
| [GSE77548](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE77548) | Mus musculus | differentiating cardiac precursor/cardiomyocyte | GATA4; NKX2-5; TBX5 ChIP-exo density and footprint files | cross-species virtual cistrome support and footprint-method validation target | processed supplementary footprint/density files listed; large raw archive not needed for inventory |

These datasets are not used as final biological proof in this artifact.
`GSE133833` is the strongest next validation target because it contains
human iPSC-CM RNA-seq, ATAC-seq, and NKX2-5 ChIP-seq in one design.
`GSE77548` supplies cardiac GATA4/NKX2-5/TBX5 ChIP-exo footprints but
is mouse and therefore cross-species support.

## Reading

- Top allowed GSE175634 feature by pseudo-bulk AUC: `COX6A2` (0.959).
- Motif/target-set proxy supports 2 TF modules.
- Virtual cistrome inventory supports 4 TF modules.
- Mechanistic bridge candidates should be treated as hypotheses for
  follow-up perturbation or orthogonal TF-activity measurement.
- This layer does not rescue a failed LAMP audit by itself; it explains
  where a fragile rescued signal may be biologically anchored.
- Stronger next version: import GSE133833 peaks/counts and test whether
  the RNA regulon proxy tracks direct NKX2-5 ChIP/ATAC occupancy.

## Output Files

- Feature importance: `results/lamp_bio_mechanistic_interpretation/gse175634_feature_importance.csv`
- All feature/TF correlations: `results/lamp_bio_mechanistic_interpretation/gse201437_feature_tf_module_correlations.csv`
- Motif target enrichment proxy: `results/lamp_bio_mechanistic_interpretation/motif_target_enrichment_proxy.csv`
- Virtual cistrome evidence: `results/lamp_bio_mechanistic_interpretation/virtual_cistrome_evidence.csv`
- Direct validation inventory: `results/lamp_bio_mechanistic_interpretation/direct_validation_dataset_inventory.csv`
- Dossier: `results/lamp_bio_mechanistic_interpretation/mechanistic_interpretation_dossier.csv`
- Figure: `results/lamp_bio_mechanistic_interpretation/figures/feature_tf_mechanistic_bridges.png`
- Figure: `results/lamp_bio_mechanistic_interpretation/figures/gse175634_feature_importance.png`
