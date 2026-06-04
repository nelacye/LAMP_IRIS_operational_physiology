# LAMP-Pharm Summary

LAMP-Pharm applies the LAMP audit protocol to pharmacology and perturbation
claims where a model is said to detect biological drug response rather than
experimental structure.

## Public Artifact

| Artifact | Dataset | Claim Type | Candidate Biology Score | Shortcut Sentinels | Main Result |
|---|---|---|---|---|---|
| GSE114686 TKI cardiotoxicity shortcut audit | GEO `GSE114686` | Severe/high-dose cardiotoxic TKI exposure in hiPSC-derived cardiomyocytes | Signed stress/apoptosis minus cardiac-program expression, AUC 0.610 | Severe-TKI identity AUC 0.942, dose AUC 0.713, exact drug-dose rule AUC 1.000, endpoint-adjacent genes AUC 0.997 | Candidate biology is modest and fragile, while drug identity/dose structure is much stronger. LAMP-Pharm frames the core question: pharmacological biology or experimental structure? |

## Interpretation Boundary

This is a public-data audit artifact, not a deployed cardiotoxicity predictor.
The purpose is to make shortcut channels explicit: drug identity, administered
dose, exposure time, batch/replicate structure, and endpoint-adjacent genes.

The next stronger benchmark should use held-out drugs, held-out doses,
batch-held-out splits, and perturbation-matched controls in iPSC-CM
cardiotoxicity, CiPA/MEA, LINCS/L1000, CRISPR perturbation, or organoid
drug-response data.
