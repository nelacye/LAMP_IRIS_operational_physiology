# GSE175634 Real scRNA Metadata LAMP-Bio Audit

This is the first real hiPSC/hiPSC-CM single-cell RNA-seq artifact for LAMP-Bio.
It is intentionally metadata-first: it tests provenance, annotation, QC/context
and endpoint-adjacent sentinels before making marker-panel maturation claims.

## Dataset Found

- Source: `GSE175634` (https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE175634)
- GEO summary: differentiating human iPSC-derived cardiac cells across multiple
  timepoints, collections, and cell lines.
- Full cell metadata rows loaded: 230,786.
- Audit rows used: 60,000 (max-cells=60000; use `--max-cells 0` for all rows).
- Individuals: 19; collections: 57; samples: 131.
- Collection-context join rate: 0.609.
- CM endpoint positives in audit table: 5,651 / 60,000.

## Cell-State Inventory

| Field | Values |
| --- | --- |
| diffday | day0: 10,702, day1: 10,747, day11: 10,172, day15: 4,758, day3: 7,776, day5: 5,020, day7: 10,825 |
| type | MES: 14,486, CF: 11,969, IPSC: 10,300, PROG: 9,198, CM: 5,651, CMES: 4,975, UNK: 3,421 |

## LAMP Monitors

| Monitor | AUC | LAMP | Key reasons | Output classes |
| --- | ---: | --- | --- | --- |
| Cell-cycle exit metadata probe | 0.582 | FAIL | oracle sentinel, protocol/donor sentinel | oracle_label_leakage_sentinel;protocol_batch_or_donor_shortcut_sentinel |
| DPT pseudotime endpoint-adjacent probe | 0.899 | FAIL | temporal isolation, forbidden feature, oracle sentinel, protocol/donor sentinel, oracle proximity | forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;protocol_batch_or_donor_shortcut_sentinel;temporal_isolation_incomplete;valid_early_hidden_state_signal |
| Differentiation-day protocol shortcut | 0.827 | FAIL | forbidden feature, oracle sentinel, protocol/donor sentinel, oracle proximity | forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;protocol_batch_or_donor_shortcut_sentinel;valid_early_hidden_state_signal |
| Published annotation oracle | 1.000 | FAIL | temporal isolation, forbidden feature, oracle sentinel, protocol/donor sentinel, oracle proximity | forbidden_feature_contamination;leakage_contaminated_candidate;oracle_label_leakage_sentinel;oracle_leakage_proximity_shift;protocol_batch_or_donor_shortcut_sentinel;temporal_isolation_incomplete;visible_state_confounding |

## Interpretation

- `cell_cycle_exit_metadata_probe` is an intentionally weak allowed metadata
  probe. It is a QC/annotation sanity check, not a maturation marker panel.
- `dpt_pseudotime_score` is biologically meaningful but endpoint-adjacent for
  this contract because pseudotime is inferred from the full expression
  trajectory rather than available as a clean early measurement.
- `diffday_numeric_score` tests the obvious protocol/timepoint shortcut.
- `annotation_oracle_score` tests direct published-label leakage.

## Why This Dataset Is Useful

GSE175634 has exactly the metadata structure LAMP-Bio needs for a serious
single-cell contract: cell-level labels, pseudotime, donor/line IDs,
differentiation days, pooled collections, and collection-level experimental
context. The next step is to download the sparse count matrix and define a
disjoint marker-panel contract: endpoint axis versus allowed evidence axis.

## Files

- Prediction table: `results/lamp_bio_scrna/gse175634_metadata/gse175634_scrna_metadata_prediction_table.csv`
- Summary: `results/lamp_bio_scrna/gse175634_metadata/gse175634_scrna_metadata_lamp_summary.csv`
- Inventory: `results/lamp_bio_scrna/gse175634_metadata/gse175634_scrna_metadata_inventory.json`
- Figure: `results/lamp_bio_scrna/gse175634_metadata/figures/cell_type_by_day.png`
- Figure: `results/lamp_bio_scrna/gse175634_metadata/figures/monitor_auc_summary.png`

## Limitations

- This first pass does not use raw gene expression counts.
- It should not be cited as evidence that an early transcriptomic maturation
  monitor passes LAMP.
- The useful result here is dataset suitability plus explicit detection of
  endpoint-adjacent and protocol shortcut channels.
