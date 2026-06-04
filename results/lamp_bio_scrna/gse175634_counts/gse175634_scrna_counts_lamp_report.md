# GSE175634 scRNA Count-Matrix LAMP-Bio Audit

This count-level pilot asks whether disjoint biological marker axes survive
after day, published pseudotime, published annotation, and endpoint-axis
reuse are treated as forbidden/sentinel channels.

## Contract

- Source: `GSE175634` (https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE175634)
- Rows: 60,000 first matrix-order cells (max_cells=60000).
- Individuals: 6; collections: 11.
- Endpoint axis: high structural maturation marker-panel score.
- Allowed disjoint axes: calcium/electrophysiology and metabolic marker panels.
- Forbidden/sentinel axes: day, pseudotime, published annotation, and structural endpoint score as monitor.
- Structural endpoint positives: 18,000 / 60,000.

## LAMP Results

| Monitor | AUC | Diagnosis | LAMP | Key reasons | Bootstrap pass | Leave-individual min AUC |
| --- | ---: | --- | --- | --- | ---: | ---: |
| Calcium/electrophysiology -> structural endpoint | 0.571 | not_biologically_interpretable_under_contract | FAIL | null/destroyed | 0.00 | 0.552 |
| Metabolic -> structural endpoint | 0.497 | not_biologically_interpretable_under_contract | FAIL | threshold fragile, null/destroyed | 0.00 | 0.481 |
| Combined disjoint biology -> structural endpoint | 0.548 | not_biologically_interpretable_under_contract | FAIL | null/destroyed | 0.00 | 0.530 |
| Structural endpoint-adjacent oracle | 1.000 | not_biologically_interpretable_under_contract | FAIL | temporal isolation, forbidden feature | 1.00 | 1.000 |
| Differentiation-day protocol shortcut | 0.771 | not_biologically_interpretable_under_contract | FAIL | forbidden feature | 1.00 | 0.752 |
| Published annotation shortcut | 0.654 | not_biologically_interpretable_under_contract | FAIL | temporal isolation, forbidden feature, matched collapse | 1.00 | 0.628 |
| Published pseudotime shortcut | 0.781 | not_biologically_interpretable_under_contract | FAIL | temporal isolation, forbidden feature | 1.00 | 0.718 |

## Sentinel AUCs

| Sentinel | AUC vs structural endpoint |
| --- | ---: |
| Structural endpoint oracle | 1.000 |
| Differentiation day | 0.771 |
| Published pseudotime | 0.781 |
| Published CM annotation | 0.654 |

## Interpretation

A PASS here would mean a disjoint marker axis still separates structural
maturation after matching on day and QC-like visible state. A fragile PASS
would be interesting but not enough for a strong maturation claim. A FAIL
means the apparent biological signal is null, shortcut-like, threshold
fragile, or violates the declared information contract.

This is not yet a true early-to-late longitudinal prediction. It is a
same-cell disjoint-axis contract test. The next stronger design is an
individual/collection-level early-day panel predicting late-day endpoint
held out by individual or collection.

## Files

- Prediction table: `results/lamp_bio_scrna/gse175634_counts/gse175634_scrna_counts_prediction_table.csv`
- Summary: `results/lamp_bio_scrna/gse175634_counts/gse175634_scrna_counts_lamp_summary.csv`
- Inventory: `results/lamp_bio_scrna/gse175634_counts/gse175634_scrna_counts_inventory.json`
- Figure: `results/lamp_bio_scrna/gse175634_counts/figures/panel_scores_by_structural_endpoint.png`
- Figure: `results/lamp_bio_scrna/gse175634_counts/figures/counts_monitor_auc_summary.png`
