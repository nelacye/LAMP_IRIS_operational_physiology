# GSE201437 iPSC-CM Protocol-Shortcut LAMP Audit

Public-data LAMP-Bio artifact for auditing whether an iPSC-CM maturation
monitor distinguishes biological expression evidence from intervention
structure: high calcium, ramp pacing, or the exact combined HCRP condition.

## Source

- GEO accession: `GSE201437`
- GEO record: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE201437
- GEO title: Physiological Calcium Combined with Electrical Pacing accelerates Maturation of Human Engineered Heart Tissue.
- Design: four engineered-heart-tissue RNA-seq groups: HCNP, HCRP, LCNP, and LCRP.
- Samples used: 14 (4 HCRP endpoint positives, 10 controls).
- Group counts: HCNP=3, HCRP=4, LCNP=4, LCRP=3.

## LAMP Setup

- Label: HCRP combined high-calcium plus ramp-pacing condition.
- Candidate biological score: fixed curated cardiomyocyte maturation/electrophysiology marker panel.
- Protocol sentinels: high calcium, ramp pacing, and exact HCRP intervention code.
- Oracle sentinels: endpoint label and endpoint-adjacent genes selected on this table.
- Matching variables: library total counts and detected gene count.

## Audit Summary

| Monitor | AUC | Inverted AUC | Direction? | Audit Pass | Temporal | Forbidden | Matched Delta | Key Warnings | Output Classes |
|---|---:|---:|:---:|:---:|:---:|:---:|---:|---|---|
| Curated maturation-marker expression score | 1.000 | 0.000 | False | True | True | True | 0.464 | protocol/intervention sentinel, oracle sentinel | `audit_pass_candidate;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;valid_early_hidden_state_signal` |
| High-calcium protocol shortcut score | 0.850 | 0.150 | False | False | True | False | 0.286 | forbidden, protocol/intervention sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;valid_early_hidden_state_signal` |
| Ramp-pacing protocol shortcut score | 0.850 | 0.150 | False | False | True | False | 0.619 | forbidden, protocol/intervention sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;valid_early_hidden_state_signal` |
| Combined HCRP intervention shortcut score | 1.000 | 0.000 | False | False | True | False | 0.429 | forbidden, protocol/intervention sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;valid_early_hidden_state_signal` |
| Endpoint-adjacent marker-selection score | 1.000 | 0.000 | False | False | False | False | 0.464 | temporal, forbidden, protocol/intervention sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |

## Interpretation

This is a deliberately small protocol-shortcut audit, not a prospective
biological validation. The key signal is not that a marker panel separates
HCRP samples on 14 RNA-seq profiles; it is that intervention sentinels also
carry strong predictive information. That is exactly the failure mode LAMP-Bio
is meant to expose: an AI maturation monitor may be reading the experimental
condition rather than a latent biological readiness state.

A serious follow-up should use donor-held-out, protocol-held-out, and
stage-held-out splits, preferably on high-replicate scRNA-seq or multimodal
iPSC-CM datasets with electrophysiology or calcium-imaging endpoints.

## Endpoint-Adjacent Genes

These genes were selected against the HCRP endpoint on the same tiny table and
are treated only as an oracle/leaky sentinel, not as a valid model:

- `ENSG00000258708/SLC25A21-AS1:-2.079`
- `ENSG00000019549/SNAI2:-2.045`
- `ENSG00000164106/SCRG1:-2.011`
- `ENSG00000118004/COLEC11:-1.994`
- `ENSG00000287047/---:1.993`
- `ENSG00000110675/ELMOD1:1.984`
- `ENSG00000110492/MDK:-1.972`
- `ENSG00000137154/RPS6:-1.969`
- `ENSG00000075945/KIFAP3:1.967`
- `ENSG00000159200/RCAN1:1.966`
- `ENSG00000224578/HNRNPA1P48:-1.963`
- `ENSG00000145425/RPS3A:-1.951`
- `ENSG00000223722/IFITM3P2:-1.946`
- `ENSG00000149273/RPS3:-1.946`
- `ENSG00000170290/SLN:1.942`
- `ENSG00000137970/RPL7P9:-1.938`
- `ENSG00000273156/---:-1.937`
- `ENSG00000174748/RPL15:-1.935`
- `ENSG00000182534/MXRA7:1.935`
- `ENSG00000140092/FBLN5:-1.933`
