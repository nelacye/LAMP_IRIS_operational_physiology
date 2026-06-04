# Real PhysioNet Oracle-Injection Control

This artifact uses the real PhysioNet/CinC 2019 sepsis v3_5k score table already integrated in LAMP, then injects a known oracle-label component into the monitor score by construction.

```text
mixed_score = z((1 - lambda) * z(valid_score) + lambda * z(oracle_score))
primary test lambda = 0.005 (0.5% oracle injection)
```

Ground truth is therefore known: lambda = 0 is clean; every nonzero lambda contains oracle leakage. The strict-declared mode checks the stated information contract. The geometry-only mode does not declare the oracle as a score feature and instead uses LAMP's sentinel proximity relation.

## 0.5% Oracle Injection Rows

| Horizon | Mode | Clean AUC | 0.5% AUC | Delta | AUC delta >= 0.01 | LAMP decision | Key classes |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| 6h | geometry_only | 0.6416 | 0.6494 | 0.0078 | False | FAIL | leakage_contaminated_candidate, oracle_label_leakage_sentinel, oracle_leakage_proximity_shift, valid_early_hidden_state_signal |
| 6h | strict_declared | 0.6416 | 0.6494 | 0.0078 | False | FAIL | forbidden_feature_contamination, leakage_contaminated_candidate, oracle_label_leakage_sentinel, oracle_leakage_proximity_shift, temporal_isolation_incomplete, valid_early_hidden_state_signal |
| 12h | geometry_only | 0.6328 | 0.6411 | 0.0083 | False | FAIL | leakage_contaminated_candidate, oracle_label_leakage_sentinel, oracle_leakage_proximity_shift, valid_early_hidden_state_signal |
| 12h | strict_declared | 0.6328 | 0.6411 | 0.0083 | False | FAIL | forbidden_feature_contamination, leakage_contaminated_candidate, oracle_label_leakage_sentinel, oracle_leakage_proximity_shift, temporal_isolation_incomplete, valid_early_hidden_state_signal |
| 18h | geometry_only | 0.6249 | 0.6336 | 0.0087 | False | FAIL | leakage_contaminated_candidate, oracle_label_leakage_sentinel, oracle_leakage_proximity_shift, valid_early_hidden_state_signal |
| 18h | strict_declared | 0.6249 | 0.6336 | 0.0087 | False | FAIL | forbidden_feature_contamination, leakage_contaminated_candidate, oracle_label_leakage_sentinel, oracle_leakage_proximity_shift, temporal_isolation_incomplete, valid_early_hidden_state_signal |

## LAMP vs Known Ground Truth

| Mode | Scope | TN | FP | FN | TP | Sensitivity | Specificity |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| geometry_only | full_lambda_sweep | 3 | 0 | 9 | 24 | 0.727 | 1.000 |
| geometry_only | clean_vs_0p5pct | 3 | 0 | 0 | 3 | 1.000 | 1.000 |
| strict_declared | full_lambda_sweep | 3 | 0 | 0 | 33 | 1.000 | 1.000 |
| strict_declared | clean_vs_0p5pct | 3 | 0 | 0 | 3 | 1.000 | 1.000 |

## Sensitivity Floor

### strict_declared
- 6h: first detected dose = 0.001% (lambda=1e-05, AUC delta=0.00002).
- 12h: first detected dose = 0.001% (lambda=1e-05, AUC delta=0.00002).
- 18h: first detected dose = 0.001% (lambda=1e-05, AUC delta=0.00001).

### geometry_only
- 6h: first detected dose = 0.05% (lambda=0.0005, AUC delta=0.00075).
- 12h: first detected dose = 0.05% (lambda=0.0005, AUC delta=0.00087).
- 18h: first detected dose = 0.05% (lambda=0.0005, AUC delta=0.00086).

## Interpretation

The 0.5% oracle-injected ROC curves are visually close to the clean curves, and the AUC deltas remain below a simple 0.01 metric-change alert across all horizons. LAMP still fails the contaminated scores because the information contract is broken by construction; in geometry-only mode it also detects the score's movement toward the oracle sentinel.

## Figures

- `figures/physionet_roc_clean_vs_0p5pct_oracle.png`
- `figures/physionet_oracle_leakage_sensitivity.png`
- `figures/physionet_lamp_vs_known_leakage_confusion.png`
