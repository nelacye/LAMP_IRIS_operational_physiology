# GSE209997 iPSC-CM Maturation LAMP Micro Audit

Public-data smoke test for applying LAMP to AI claims about early latent-state
detection in iPSC-derived cardiac maturation systems.

## Source

- GEO accession: `GSE209997`
- GEO record: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE209997
- Design: D30/D50 iPSC-derived 3D organotypic cardiac microtissues vs 2D monolayer controls.
- Samples used: 12 (3 D50-3D endpoint positives, 9 controls).

## LAMP Setup

- Label: D50 3D mature organotypic state.
- Candidate valid score: fixed curated cardiomyocyte maturation/electrophysiology marker panel.
- Shortcut sentinels: sample day and 3D-vs-2D protocol.
- Oracle sentinels: endpoint label and endpoint-adjacent genes selected on this tiny table.
- Matching variables: library total counts and detected gene count.

## Audit Summary

| Monitor | AUC | Inverted AUC | Direction? | Audit Pass | Temporal | Forbidden | Matched Delta | Key Warnings | Output Classes |
|---|---:|---:|:---:|:---:|:---:|:---:|---:|---|---|
| Curated maturation-marker expression score | 1.000 | 0.000 | False | True | True | True | 0.500 | protocol/batch/donor sentinel, oracle sentinel | `audit_pass_candidate;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;valid_early_hidden_state_signal` |
| Timepoint shortcut score | 0.833 | 0.167 | False | False | False | False | 0.333 | temporal, forbidden, protocol/batch/donor sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |
| Protocol shortcut score | 0.833 | 0.167 | False | False | True | False | 0.500 | forbidden, protocol/batch/donor sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;valid_early_hidden_state_signal` |
| Endpoint-adjacent marker-selection score | 1.000 | 0.000 | False | False | False | False | 0.500 | temporal, forbidden, protocol/batch/donor sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |

## Interpretation

This is not a benchmark-level claim: the table has only 12 RNA-seq samples.
Its purpose is to show how an iPSC maturation claim can be converted into a
LAMP audit object. The important result is the separation of a declared
maturation-marker score from explicit timepoint, protocol, and endpoint-adjacent
sentinels.

A high AUC here should not be read as prospective validity. The 3D protocol
sentinel is also predictive, so the serious version must use donor-held-out,
protocol-held-out, and
timepoint-held-out splits on larger iPSC-CM or organoid datasets, preferably
with electrophysiology or calcium-imaging endpoints.

## Endpoint-Adjacent Genes

These genes were selected against the endpoint on the same tiny table and are
therefore treated only as an oracle/leaky sentinel, not as a valid model:

- `ENSG00000244260:2.205`
- `ENSG00000227719:2.205`
- `ENSG00000224670:2.205`
- `ENSG00000234043:2.205`
- `ENSG00000254245:2.205`
- `ENSG00000267646:2.205`
- `ENSG00000246022:2.205`
- `ENSG00000088756:-2.198`
- `ENSG00000148204:-2.190`
- `ENSG00000137872:-2.186`
- `ENSG00000152578:-2.176`
- `ENSG00000284612:2.172`
- `ENSG00000171243:-2.169`
- `ENSG00000035664:2.166`
- `ENSG00000129103:-2.165`
- `ENSG00000160191:-2.164`
- `ENSG00000232002:2.164`
- `ENSG00000077264:-2.161`
- `ENSG00000234456:-2.159`
- `ENSG00000145703:-2.159`
