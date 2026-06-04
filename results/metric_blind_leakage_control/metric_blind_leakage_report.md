# Metric-Blind Leakage Synthetic Control

This control keeps the data-generating process and valid score fixed, then
adds a known oracle-label score at dose lambda:

`mixed_score = (1 - lambda) * valid_score + lambda * oracle_score`

The purpose is to test whether metric-blind leakage is a structural failure
mode rather than an artifact of a particular clinical or LLM benchmark.

## Key Result

Baseline valid AUC is 0.8299. At lambda=0.001, AUC is 0.8305 (delta=0.0006), below the conventional 0.01 AUC-delta alert used here. LAMP still fails the monitor because the information contract is already broken.

In other words, performance can remain statistically boring while validity has already collapsed.

## Summary

| lambda | AUC | delta AUC | AUC-delta alert | LAMP pass | temporal | forbidden | oracle proximity | oracle alert |
|---:|---:|---:|:---:|:---:|:---:|:---:|---:|:---:|
| 0 | 0.8299 | 0.0000 | False | True | True | True | 0.0000 | False |
| 0.001 | 0.8305 | 0.0006 | False | False | False | False | 0.0038 | False |
| 0.002 | 0.8311 | 0.0013 | False | False | False | False | 0.0075 | False |
| 0.005 | 0.8331 | 0.0032 | False | False | False | False | 0.0188 | True |
| 0.01 | 0.8362 | 0.0064 | False | False | False | False | 0.0374 | True |
| 0.02 | 0.8425 | 0.0126 | True | False | False | False | 0.0741 | True |
| 0.05 | 0.8605 | 0.0306 | True | False | False | False | 0.1798 | True |
| 0.1 | 0.8882 | 0.0584 | True | False | False | False | 0.3431 | True |

## Interpretation

AUC answers whether rank discrimination changed. LAMP answers whether the
score was allowed to know what made it discriminate. The first nonzero
oracle dose already violates the declared temporal and forbidden-feature
contract, even when the AUC movement is smaller than a simple metric-delta
screen would treat as noteworthy.

This is the controlled synthetic version of the empirical observation from
the PhysioNet/CinC 2019 neural audit: RF valid AUC 0.8188 versus 1% oracle
mixture AUC 0.8231. Small metric movement does not imply preserved validity.

![AUC versus LAMP decision](metric_blind_leakage_curve.png)
