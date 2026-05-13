# PhysioNet component-layer grounding report

## Purpose

These datasets do not replace Antarctic human validation. They strengthen component-wise external grounding: workload/autonomic response, hypoxia/oxygenation observability, ECG/PCG signal quality, resting autonomic reference, and baseline RR distributions.

## Inventory by layer

| dataset_layer                        |   n_files |   total_mb |
|:-------------------------------------|----------:|-----------:|
| EPHNOGRAM electrophysiology/workload |        38 | 677.817    |
| ACTES graded workload/autonomic      |         5 |   1.72597  |
| unknown                              |         2 |   0.006781 |

## Numeric table summaries preview

| file                                                                                | dataset_layer                        | sep   |   rows_read |   n_columns |   n_numeric_columns | numeric_columns_preview                                                                                                                                                                                                                                    |   median_of_numeric_medians |   median_numeric_iqr |
|:------------------------------------------------------------------------------------|:-------------------------------------|:------|------------:|------------:|--------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------:|---------------------:|
| real_data\physionet_component_layers\actes-cycloergometer-exercise\test_measure.csv | ACTES graded workload/autonomic      | ,     |       20000 |           5 |                   5 | ID,time,RR,VO2,power                                                                                                                                                                                                                                       |                        95   |        132           |
| real_data\physionet_component_layers\actes-cycloergometer-exercise\subject-info.csv | ACTES graded workload/autonomic      | ,     |          18 |           7 |                   6 | ID,age,Weight,Height,P_vt1,P_vt2                                                                                                                                                                                                                           |                        84.2 |         19.575       |
| real_data\physionet_component_layers\ephnogram\ECGPCGSpreadsheet.csv                | EPHNOGRAM electrophysiology/workload | ,     |          70 |          45 |                  35 | Record Duration (min),Age (years),Num Channels,Unnamed: 13,Unnamed: 14,Unnamed: 15,Unnamed: 16,Unnamed: 17,Unnamed: 18,Unnamed: 19,Unnamed: 20,Unnamed: 21,Unnamed: 22,Unnamed: 23,Unnamed: 24,Unnamed: 25,Unnamed: 26,Unnamed: 27,Unnamed: 28,Unnamed: 29 |                        25   |          0           |
| real_data\physionet_component_layers\download_log.csv                               | unknown                              | ,     |          35 |           7 |                   2 | bytes,index                                                                                                                                                                                                                                                |                      8936.5 |          1.19981e+06 |
| real_data\physionet_component_layers\download_manifest.csv                          | unknown                              | ,     |           4 |           7 |                   1 | n_files_discovered                                                                                                                                                                                                                                         |                         2.5 |         56.75        |

## Manuscript wording

> Because no additional Antarctic HRV/autonomic cohort was identified on PhysioNet, Neumayer III was retained as the only Antarctic human boundary-condition layer. We therefore added non-Antarctic PhysioNet component layers with mechanistic relevance: ACTES for graded workload/RR-interval autonomic response, OpenOximetry for hypoxia and oxygenation observability, EPHNOGRAM for ECG/PCG workload and signal-quality priors, Autonomic Aging for large-scale resting ECG/BP autonomic reference, RR Healthy for baseline HRV distributions, and wearable exercise/frailty data for heart response to physical stressors.

## Limitation

> These datasets strengthen physiological grounding of IRIS components but do not constitute prospective Antarctic human validation.