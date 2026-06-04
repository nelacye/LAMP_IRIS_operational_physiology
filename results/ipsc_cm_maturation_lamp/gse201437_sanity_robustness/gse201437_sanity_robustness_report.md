# GSE201437 LAMP Sanity Robustness

Reviewer-facing robustness checks for the controlled GSE201437 separation
experiment. The goal is to answer whether the clean PASS is stable, not
whether this 14-sample dataset is a final biological benchmark.

## Summary

- Base expected-vs-observed separation passed: `True`.
- Clean bootstrap PASS rate: `0.503` over 300 stratified resamples.
- Shortcut/leakage bootstrap expected-decision stability >=90%: `True`.
- Alternative clean probe panels passing: `4/5`.
- Clean threshold-grid PASS rate: `0.667`.
- Donor-held-out stability: `not evaluable` because this processed GEO table does not expose donor IDs.
- True protocol-held-out training/evaluation: `not evaluable` here because the experiment has 14 samples and the label itself is coupled to protocol structure.

## Base Separation

| Model | Expected | Observed | AUC | Matched Delta | Threshold Fragile | Key Reasons |
|---|:---:|:---:|---:|---:|:---:|---|
| Clean calcium/electrophysiology probe | PASS | PASS | 0.694 | 0.607 | False | protocol sentinel present, oracle sentinel present |
| High-calcium protocol shortcut | FAIL | FAIL | 0.857 | 0.286 | False | forbidden, protocol sentinel present, oracle sentinel present |
| Explicit oracle leakage | FAIL | FAIL | 1.000 | 1.000 | False | temporal, forbidden, protocol sentinel present, oracle sentinel present |

## Stratified Bootstrap

| Model | Expected | PASS Rate | Expected Decision Rate | AUC Mean | AUC 95% Interval | Matched Delta Mean | Matched Delta 95% Interval |
|---|:---:|---:|---:|---:|---|---:|---|
| Clean calcium/electrophysiology probe | PASS | 0.503 | 0.503 | 0.706 | 0.408-0.949 | 0.334 | -0.180-0.877 |
| High-calcium protocol shortcut | FAIL | 0.000 | 1.000 | 0.860 | 0.714-1.000 | 0.243 | -0.139-1.000 |
| Explicit oracle leakage | FAIL | 0.000 | 1.000 | 1.000 | 1.000-1.000 | 0.552 | 0.000-1.000 |

## Alternative Clean Probe Panels

| Panel | AUC | Observed | Matched Delta | Threshold Fragile | Genes Present |
|---|---:|:---:|---:|:---:|---|
| full calcium electrophysiology | 0.694 | PASS | 0.607 | False | `ATP2A2;PLN;RYR2;CACNA1C;SCN5A;KCNH2` |
| calcium handling | 0.551 | FAIL | 0.000 | True | `ATP2A2;PLN;RYR2;CACNA1C` |
| ion channel core | 0.673 | PASS | 0.607 | False | `RYR2;CACNA1C;SCN5A;KCNH2` |
| depolarization repolarization | 0.714 | PASS | 0.607 | False | `CACNA1C;SCN5A;KCNH2` |
| minimal calcium pair | 0.694 | PASS | 0.321 | False | `ATP2A2;PLN` |

## Leave-One-Protocol-Group-Out

| Left-Out Group | Model | Observed | AUC | Matched Delta | Rows | Pos/Neg | Key Reasons |
|---|---|:---:|---:|---:|---:|---:|---|
| HCNP | Clean calcium/electrophysiology probe | PASS | 0.733 | 0.182 | 11 | 5/6 | protocol sentinel present, oracle sentinel present |
| HCNP | High-calcium protocol shortcut | FAIL | 0.900 | 0.182 | 11 | 5/6 | forbidden, protocol sentinel present, oracle sentinel present |
| HCNP | Explicit oracle leakage | FAIL | 1.000 | 0.364 | 11 | 5/6 | temporal, forbidden, protocol sentinel present, oracle sentinel present |
| HCRP | Clean calcium/electrophysiology probe | FAIL | 0.524 | 0.500 | 10 | 3/7 | threshold fragile, protocol sentinel present, oracle sentinel present |
| HCRP | High-calcium protocol shortcut | FAIL | 0.762 | 0.000 | 10 | 3/7 | forbidden, protocol sentinel present, oracle sentinel present |
| HCRP | Explicit oracle leakage | FAIL | 1.000 | 0.500 | 10 | 3/7 | temporal, forbidden, protocol sentinel present, oracle sentinel present |
| LCNP | Clean calcium/electrophysiology probe | PASS | 0.762 | 0.300 | 10 | 7/3 | protocol sentinel present, oracle sentinel present |
| LCNP | High-calcium protocol shortcut | FAIL | 0.762 | 0.400 | 10 | 7/3 | forbidden, protocol sentinel present, oracle sentinel present |
| LCNP | Explicit oracle leakage | FAIL | 1.000 | 0.700 | 10 | 7/3 | temporal, forbidden, protocol sentinel present, oracle sentinel present |
| LCRP | Clean calcium/electrophysiology probe | PASS | 0.733 | 0.318 | 11 | 6/5 | protocol sentinel present, oracle sentinel present |
| LCRP | High-calcium protocol shortcut | FAIL | 0.900 | 0.000 | 11 | 6/5 | forbidden, protocol sentinel present, oracle sentinel present |
| LCRP | Explicit oracle leakage | FAIL | 1.000 | 0.250 | 11 | 6/5 | temporal, forbidden, protocol sentinel present, oracle sentinel present |

## Threshold Grid

| Model | valid_auc_min | matched_delta_min | Observed | AUC | Matched Delta |
|---|---:|---:|:---:|---:|---:|
| Clean calcium/electrophysiology probe | 0.600 | 0.020 | PASS | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.600 | 0.020 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.600 | 0.020 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.600 | 0.100 | PASS | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.600 | 0.100 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.600 | 0.100 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.600 | 0.200 | PASS | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.600 | 0.200 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.600 | 0.200 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.600 | 0.500 | PASS | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.600 | 0.500 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.600 | 0.500 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.650 | 0.020 | PASS | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.650 | 0.020 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.650 | 0.020 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.650 | 0.100 | PASS | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.650 | 0.100 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.650 | 0.100 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.650 | 0.200 | PASS | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.650 | 0.200 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.650 | 0.200 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.650 | 0.500 | PASS | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.650 | 0.500 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.650 | 0.500 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.700 | 0.020 | FAIL | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.700 | 0.020 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.700 | 0.020 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.700 | 0.100 | FAIL | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.700 | 0.100 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.700 | 0.100 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.700 | 0.200 | FAIL | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.700 | 0.200 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.700 | 0.200 | FAIL | 1.000 | 1.000 |
| Clean calcium/electrophysiology probe | 0.700 | 0.500 | FAIL | 0.694 | 0.607 |
| High-calcium protocol shortcut | 0.700 | 0.500 | FAIL | 0.857 | 0.286 |
| Explicit oracle leakage | 0.700 | 0.500 | FAIL | 1.000 | 1.000 |

## Interpretation

The clean PASS is reachable and survives the base contract, but it is not a
strong biological validation claim. The bootstrap and panel-variant tables
should be read as small-n stability diagnostics. A reviewer should still ask
for donor-held-out, protocol-held-out, and independent-dataset replication.

The important negative control is that shortcut and oracle monitors continue
to fail even when their AUC is higher than the clean probe.
