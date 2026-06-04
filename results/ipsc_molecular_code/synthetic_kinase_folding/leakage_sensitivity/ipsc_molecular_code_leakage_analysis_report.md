# iPSC Molecular-Code Leakage Analysis

This analysis adds ROC overlays, a known-truth confusion matrix, and
oracle-leakage sensitivity curves to the synthetic molecular-code audit.

## ROC Overlay

- Clean hybrid AUC: `0.9141`.
- 0.5% oracle mix AUC: `0.9159`.
- Delta AUC: `0.0018`.
- Figure: `figures/roc_clean_vs_oracle_005.png`.

## LAMP vs Known Synthetic Contract

- True positives (invalid detected): `4`.
- True negatives (valid accepted): `2`.
- False positives: `0`.
- False negatives: `0`.
- Sensitivity: `1.000`.
- Specificity: `1.000`.
- Figure: `figures/lamp_confusion_matrix.png`.

## Leakage Sensitivity

- Strict declared provenance first detects leakage at `0.001%`.
- Geometry-only first detects leakage at `0.05%`.
- Figure: `figures/oracle_leakage_sensitivity.png`.

| Lambda | Leakage % | Strict AUC | Strict Decision | Geometry AUC | Geometry Decision | Geometry Proximity |
|---:|---:|---:|---|---:|---|---:|
| 0 | 0 | 0.9141 | valid | 0.9141 | valid | 0.0000 |
| 1e-05 | 0.001 | 0.9141 | invalid | 0.9141 | valid | 0.0000 |
| 5e-05 | 0.005 | 0.9142 | invalid | 0.9142 | valid | 0.0003 |
| 0.0001 | 0.01 | 0.9142 | invalid | 0.9142 | valid | 0.0006 |
| 0.0005 | 0.05 | 0.9143 | invalid | 0.9143 | invalid | 0.0024 |
| 0.001 | 0.1 | 0.9145 | invalid | 0.9145 | invalid | 0.0044 |
| 0.002 | 0.2 | 0.9148 | invalid | 0.9148 | invalid | 0.0082 |
| 0.005 | 0.5 | 0.9159 | invalid | 0.9159 | invalid | 0.0208 |
| 0.01 | 1 | 0.9177 | invalid | 0.9177 | invalid | 0.0414 |
| 0.02 | 2 | 0.9210 | invalid | 0.9210 | invalid | 0.0805 |
| 0.05 | 5 | 0.9311 | invalid | 0.9311 | invalid | 0.1975 |
| 0.1 | 10 | 0.9469 | invalid | 0.9469 | invalid | 0.3820 |

Interpretation: strict provenance mode is a hard information-contract test.
If the score is known to include any endpoint/oracle channel, any nonzero
lambda is invalid. Geometry-only mode is weaker but still detects tiny
rank-geometry shifts once the oracle proximity exceeds the configured
threshold.
