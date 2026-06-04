# GSE201437 LAMP Controlled Separation Sanity Check

This is an implementation and criterion sanity check, not a biological
benchmark claim. It asks whether LAMP can return PASS and FAIL on the same
real expression rows when the information contracts are intentionally known.

## Setup

- Source: `GSE201437` (https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE201437)
- Rows: 14 samples (7 positive structural-maturation labels, 7 controls).
- Truth label: median split of a structural maturation panel: TNNT2, TNNI3, MYH6, MYH7, MYL2, MYL7, ACTN2, TTN.
- Clean probe: disjoint calcium/electrophysiology panel: ATP2A2, PLN, RYR2, CACNA1C, SCN5A, KCNH2.
- Shortcut model: high-calcium intervention metadata.
- Leakage model: direct structural maturation label.

## Expected vs Observed

| Model | Expected | Observed | AUC | Temporal | Forbidden | Matched Delta | Threshold Fragile | Key Reasons |
|---|:---:|:---:|---:|:---:|:---:|---:|:---:|---|
| Clean calcium/electrophysiology probe | PASS | PASS | 0.694 | True | True | 0.607 | False | protocol sentinel present, oracle sentinel present |
| High-calcium protocol shortcut | FAIL | FAIL | 0.857 | True | False | 0.286 | False | forbidden, protocol sentinel present, oracle sentinel present |
| Explicit oracle leakage | FAIL | FAIL | 1.000 | False | False | 1.000 | False | temporal, forbidden, protocol sentinel present, oracle sentinel present |

## Result

- Separation sanity check passed: `True`.
- The clean disjoint expression probe can pass LAMP.
- The protocol shortcut fails because it uses a forbidden intervention channel.
- The explicit leakage model fails temporal isolation and forbidden-feature screening.

This does not prove that every real biological claim should pass. It shows that
the current LAMP criteria are not mechanically rejecting every biological
dataset: PASS is reachable when the declared information contract is clean.
