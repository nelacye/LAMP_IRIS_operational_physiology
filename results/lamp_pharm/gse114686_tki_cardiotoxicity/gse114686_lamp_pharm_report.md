# GSE114686 LAMP-Pharm Cardiotoxicity Shortcut Audit

Public-data LAMP-Pharm artifact asking whether a monitor detects
pharmacological cardiotoxic response biology or experimental structure.

## Source

- GEO accession: `GSE114686`
- GEO record: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE114686
- Study: hiPSC-derived cardiomyocytes treated with four tyrosine kinase inhibitors and DMSO controls.
- Design used here: 80 processed RNA-seq samples across drug, dose, exposure time, and biological replicate/experiment codes.
- Endpoint: Sorafenib or Sunitinib at dose >= 3 uM (28 positives, 52 controls).
- Drug counts: DMSO=11, Erlotinib=18, Lapatinib=17, Sorafenib=17, Sunitinib=17.

## LAMP Setup

- Candidate biology score: stress/apoptosis activation minus cardiac-program expression.
- Drug/dose/time sentinels: severe-TKI identity, administered dose, exposure time, and exact drug-dose endpoint code.
- Oracle sentinels: endpoint label and endpoint-adjacent genes selected on this table.
- Matching variables: sample mean expression and detected gene count.

## Audit Summary

| Monitor | AUC | Inverted AUC | Direction? | Audit Pass | Temporal | Forbidden | Matched Delta | Key Warnings | Output Classes |
|---|---:|---:|:---:|:---:|:---:|:---:|---:|---|---|
| Signed cardiotoxic-response expression score | 0.610 | 0.390 | False | False | True | True | 0.017 | drug/dose/time sentinel, oracle sentinel | `oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;threshold_fragile_claim` |
| Severe-TKI drug-identity shortcut score | 0.942 | 0.058 | False | False | True | False | 0.402 | forbidden, drug/dose/time sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;valid_early_hidden_state_signal` |
| Dose shortcut score | 0.713 | 0.287 | False | False | True | False | 0.262 | forbidden, drug/dose/time sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;valid_early_hidden_state_signal` |
| Exposure-time shortcut score | 0.518 | 0.482 | False | False | True | False | -0.042 | forbidden, drug/dose/time sentinel, oracle sentinel | `forbidden_feature_contamination;null_or_destroyed_signal;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel` |
| Combined drug-dose shortcut score | 1.000 | 0.000 | False | False | True | False | 0.443 | forbidden, drug/dose/time sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;valid_early_hidden_state_signal` |
| Endpoint-adjacent marker-selection score | 0.997 | 0.003 | False | False | False | False | 0.323 | temporal, forbidden, drug/dose/time sentinel, oracle sentinel | `forbidden_feature_contamination;oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal` |

## Interpretation

This artifact should not be read as a high-performance cardiotoxicity model.
The signed biology panel is intentionally transparent and modest. The point is
that drug identity and dose structure are stronger than the candidate biology
score, while the exact drug-dose rule and endpoint-selected genes reach oracle
performance. LAMP-Pharm therefore turns a pharmacology claim into the explicit
question: response biology, or experimental structure?

A serious follow-up should use held-out drugs, held-out doses, held-out batches,
and perturbation-matched controls, ideally in iPSC-CM cardiotoxicity, CiPA/MEA,
LINCS/L1000, or organoid drug-response datasets.

## Signed Biology Panel

- Stress/apoptosis genes present: NPPB, NPPA, ATF3, DDIT3, JUN, FOS, EGR1, HMOX1, BAX, CDKN1A, GADD45A, BBC3, PMAIP1, CASP3, CASP7, MDM2.
- Cardiac-program genes present: TNNT2, TNNI3, MYH6, MYH7, MYL2, MYL7, ACTN2, TTN, ATP2A2, PLN, RYR2, CACNA1C, SCN5A, KCNH2.

## Endpoint-Adjacent Genes

These genes were selected against the severe/high-dose TKI endpoint on the same
table and are treated only as oracle/leaky sentinels:

- `FILIP1L/ENSG00000168386:-1.506`
- `SNORD3B-2/ENSG00000262074:-1.478`
- `PIK3CD/ENSG00000171608:1.463`
- `SERPIND1/ENSG00000099937:-1.452`
- `DKC1/ENSG00000130826:1.449`
- `PIK3R3/ENSG00000117461:-1.416`
- `MURC/ENSG00000170681:-1.414`
- `MFHAS1/ENSG00000147324:1.414`
- `GDF11/ENSG00000135414:-1.413`
- `CSRP3/ENSG00000129170:-1.398`
- `DENND5A/ENSG00000184014:-1.380`
- `ANKRD34C/ENSG00000235711:-1.379`
- `PDE4DIP/ENSG00000178104:-1.378`
- `HECW2/ENSG00000138411:-1.372`
- `LOXL4/ENSG00000138131:-1.371`
- `SCD/ENSG00000099194:1.371`
- `LRRC1/ENSG00000137269:1.369`
- `ZNF275/ENSG00000063587:1.365`
- `STX7/ENSG00000079950:1.364`
- `WEE1/ENSG00000166483:-1.357`
