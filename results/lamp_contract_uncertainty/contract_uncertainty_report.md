# LAMP Contract-Uncertainty Analysis

This stress analysis asks what happens when the audit contract is not ideal: provenance is incompletely specified, biological contracts are noisy, or confounding is only partially observed.

## 1. Incomplete Provenance Specification

Known oracle contamination was injected into an otherwise valid score. Three audit modes were compared: complete declared provenance, sentinel-only provenance, and score-only provenance with no oracle sentinel.

| Mode | First detected nonzero dose | Pass at 0.5%? | Main interpretation |
| --- | ---: | :---: | --- |
| complete_declared | 0.01% | no | contract violation is directly auditable from declared provenance |
| sentinel_only | 0.05% | no | detectable only after score geometry moves toward oracle sentinel |
| score_only | not detected | yes | false-pass risk: score provenance and oracle sentinel are both missing |

**Conclusion:** LAMP is strongest when provenance is declared. With an oracle sentinel but no declared score feature, geometry can still detect movement toward the sentinel. With neither declared provenance nor a sentinel, the same contaminated score can pass. That is not a bug; it is the limit of auditing an unspecified information boundary.

## 2. Noisy Biological Contracts

The biological stress test flips a fraction of endpoint-axis labels while keeping the allowed disjoint calcium/electrophysiology-style probe fixed.

| Endpoint noise | AUC | Matched delta | Bootstrap stability | LAMP |
| ---: | ---: | ---: | ---: | --- |
| 0% | 0.775 | 0.383 | 1.000 | PASS |
| 5% | 0.736 | 0.298 | 1.000 | PASS |
| 10% | 0.678 | 0.205 | 1.000 | PASS |
| 20% | 0.648 | 0.207 | 1.000 | PASS |
| 30% | 0.585 | 0.114 | 0.188 | FAIL |
| 40% | 0.534 | 0.038 | 0.000 | FAIL |

**Conclusion:** noisy biological contracts do not behave like leakage. They mostly erode AUC, matched-cohort signal, and bootstrap stability. The right diagnosis is usually fragile or not biologically interpretable, not contamination, unless endpoint-adjacent features are explicitly used.

## 3. Partially Observed Confounding

The confounding stress test creates a score that is only a shortcut through a true confounder. Matching sees only a noisy proxy for that confounder.

| Confounder observed | Shortcut AUC | Matched delta | Audit pass? | Interpretation |
| ---: | ---: | ---: | :---: | --- |
| 0% | 0.789 | 0.433 | yes | false-pass risk if unobserved confounder is not represented in matching |
| 25% | 0.784 | 0.412 | yes | false-pass risk if unobserved confounder is not represented in matching |
| 50% | 0.787 | 0.283 | yes | false-pass risk if unobserved confounder is not represented in matching |
| 75% | 0.788 | 0.188 | yes | false-pass risk if unobserved confounder is not represented in matching |
| 100% | 0.760 | -0.020 | no | shortcut collapses once matching observes the confounder |

**Conclusion:** partially observed confounding is the most dangerous case. If the matching variables do not capture the true shortcut structure, the matched delta can remain positive and LAMP may pass a shortcut. The audit should therefore report observed-confounder coverage and run additional donor/protocol/batch sentinels whenever possible.

## Practical Rule

LAMP should not be read as `PASS means true`. It should be read as: `PASS under this declared contract and this observed confounder set`. Incomplete provenance creates false-pass risk; noisy biological contracts create fragility/interpretability risk; partially observed confounding creates the strongest shortcut risk.

## Figures

- `figures/provenance_uncertainty.png`
- `figures/biological_contract_noise.png`
- `figures/partial_confounding.png`