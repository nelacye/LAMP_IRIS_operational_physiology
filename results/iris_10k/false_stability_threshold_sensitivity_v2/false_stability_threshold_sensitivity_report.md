# False-stability threshold sensitivity audit v2

## Purpose

This audit tests whether false-stability station rankings depend on a single arbitrary cutoff.

## Detected columns

- latent drop: `true_drop_from_early_to_late`
- observed slope: `observed_slope_final_6h`
- primary flag: `false_stability_flag`

## Primary false-stability rates

| station      |   primary_false_stability_cases |   n_systems |   primary_false_stability_rate |
|:-------------|--------------------------------:|------------:|-------------------------------:|
| Byrd         |                               0 |       10000 |                         0      |
| Cape Denison |                               0 |       10000 |                         0      |
| Clean Air    |                             166 |       10000 |                         0.0166 |
| Concordia    |                             990 |       10000 |                         0.099  |
| Dome A       |                            2260 |       10000 |                         0.226  |
| Dome C       |                             427 |       10000 |                         0.0427 |
| Dome Fuji    |                            1536 |       10000 |                         0.1536 |

## Threshold-ranking summary

| station      |   median_rank |   best_rank |   worst_rank |   median_rate |   min_rate |   max_rate |
|:-------------|--------------:|------------:|-------------:|--------------:|-----------:|-----------:|
| Dome A       |             1 |           1 |            1 |       0.665   |     0.2013 |     0.8312 |
| Dome Fuji    |             2 |           2 |            2 |       0.5971  |     0.1363 |     0.8238 |
| Concordia    |             3 |           3 |            3 |       0.5312  |     0.0863 |     0.817  |
| Dome C       |             4 |           4 |            4 |       0.39225 |     0.0376 |     0.7865 |
| Clean Air    |             5 |           5 |            5 |       0.3011  |     0.0153 |     0.7537 |
| Byrd         |             6 |           6 |            7 |       0.01515 |     0      |     0.3109 |
| Cape Denison |             7 |           6 |            7 |       0.00135 |     0      |     0.1233 |

## Sensitivity grid preview

| station      |   latent_drop_threshold |   observed_slope_abs_threshold |   n_systems |   false_stability_cases |   false_stability_rate |
|:-------------|------------------------:|-------------------------------:|------------:|------------------------:|-----------------------:|
| Byrd         |                    0.12 |                          0.005 |       10000 |                    2506 |                 0.2506 |
| Cape Denison |                    0.12 |                          0.005 |       10000 |                    1073 |                 0.1073 |
| Clean Air    |                    0.12 |                          0.005 |       10000 |                    6035 |                 0.6035 |
| Concordia    |                    0.12 |                          0.005 |       10000 |                    6247 |                 0.6247 |
| Dome A       |                    0.12 |                          0.005 |       10000 |                    6311 |                 0.6311 |
| Dome C       |                    0.12 |                          0.005 |       10000 |                    6130 |                 0.613  |
| Dome Fuji    |                    0.12 |                          0.005 |       10000 |                    6295 |                 0.6295 |
| Byrd         |                    0.12 |                          0.01  |       10000 |                    3067 |                 0.3067 |
| Cape Denison |                    0.12 |                          0.01  |       10000 |                    1227 |                 0.1227 |
| Clean Air    |                    0.12 |                          0.01  |       10000 |                    7433 |                 0.7433 |
| Concordia    |                    0.12 |                          0.01  |       10000 |                    7993 |                 0.7993 |
| Dome A       |                    0.12 |                          0.01  |       10000 |                    8124 |                 0.8124 |
| Dome C       |                    0.12 |                          0.01  |       10000 |                    7736 |                 0.7736 |
| Dome Fuji    |                    0.12 |                          0.01  |       10000 |                    8056 |                 0.8056 |
| Byrd         |                    0.12 |                          0.015 |       10000 |                    3107 |                 0.3107 |
| Cape Denison |                    0.12 |                          0.015 |       10000 |                    1233 |                 0.1233 |
| Clean Air    |                    0.12 |                          0.015 |       10000 |                    7536 |                 0.7536 |
| Concordia    |                    0.12 |                          0.015 |       10000 |                    8162 |                 0.8162 |
| Dome A       |                    0.12 |                          0.015 |       10000 |                    8303 |                 0.8303 |
| Dome C       |                    0.12 |                          0.015 |       10000 |                    7863 |                 0.7863 |
| Dome Fuji    |                    0.12 |                          0.015 |       10000 |                    8229 |                 0.8229 |
| Byrd         |                    0.12 |                          0.02  |       10000 |                    3109 |                 0.3109 |
| Cape Denison |                    0.12 |                          0.02  |       10000 |                    1233 |                 0.1233 |
| Clean Air    |                    0.12 |                          0.02  |       10000 |                    7537 |                 0.7537 |
| Concordia    |                    0.12 |                          0.02  |       10000 |                    8170 |                 0.817  |
| Dome A       |                    0.12 |                          0.02  |       10000 |                    8312 |                 0.8312 |
| Dome C       |                    0.12 |                          0.02  |       10000 |                    7865 |                 0.7865 |
| Dome Fuji    |                    0.12 |                          0.02  |       10000 |                    8238 |                 0.8238 |
| Byrd         |                    0.12 |                          0.03  |       10000 |                    3109 |                 0.3109 |
| Cape Denison |                    0.12 |                          0.03  |       10000 |                    1233 |                 0.1233 |
| Clean Air    |                    0.12 |                          0.03  |       10000 |                    7537 |                 0.7537 |
| Concordia    |                    0.12 |                          0.03  |       10000 |                    8170 |                 0.817  |
| Dome A       |                    0.12 |                          0.03  |       10000 |                    8312 |                 0.8312 |
| Dome C       |                    0.12 |                          0.03  |       10000 |                    7865 |                 0.7865 |
| Dome Fuji    |                    0.12 |                          0.03  |       10000 |                    8238 |                 0.8238 |
| Byrd         |                    0.15 |                          0.005 |       10000 |                     921 |                 0.0921 |
| Cape Denison |                    0.15 |                          0.005 |       10000 |                     191 |                 0.0191 |
| Clean Air    |                    0.15 |                          0.005 |       10000 |                    4962 |                 0.4962 |
| Concordia    |                    0.15 |                          0.005 |       10000 |                    5880 |                 0.588  |
| Dome A       |                    0.15 |                          0.005 |       10000 |                    6154 |                 0.6154 |
| Dome C       |                    0.15 |                          0.005 |       10000 |                    5394 |                 0.5394 |
| Dome Fuji    |                    0.15 |                          0.005 |       10000 |                    6044 |                 0.6044 |
| Byrd         |                    0.15 |                          0.01  |       10000 |                    1145 |                 0.1145 |
| Cape Denison |                    0.15 |                          0.01  |       10000 |                     212 |                 0.0212 |
| Clean Air    |                    0.15 |                          0.01  |       10000 |                    6157 |                 0.6157 |
| Concordia    |                    0.15 |                          0.01  |       10000 |                    7525 |                 0.7525 |
| Dome A       |                    0.15 |                          0.01  |       10000 |                    7923 |                 0.7923 |
| Dome C       |                    0.15 |                          0.01  |       10000 |                    6823 |                 0.6823 |
| Dome Fuji    |                    0.15 |                          0.01  |       10000 |                    7741 |                 0.7741 |
| Byrd         |                    0.15 |                          0.015 |       10000 |                    1163 |                 0.1163 |
| Cape Denison |                    0.15 |                          0.015 |       10000 |                     216 |                 0.0216 |
| Clean Air    |                    0.15 |                          0.015 |       10000 |                    6248 |                 0.6248 |
| Concordia    |                    0.15 |                          0.015 |       10000 |                    7686 |                 0.7686 |
| Dome A       |                    0.15 |                          0.015 |       10000 |                    8097 |                 0.8097 |
| Dome C       |                    0.15 |                          0.015 |       10000 |                    6946 |                 0.6946 |
| Dome Fuji    |                    0.15 |                          0.015 |       10000 |                    7905 |                 0.7905 |
| Byrd         |                    0.15 |                          0.02  |       10000 |                    1164 |                 0.1164 |
| Cape Denison |                    0.15 |                          0.02  |       10000 |                     216 |                 0.0216 |
| Clean Air    |                    0.15 |                          0.02  |       10000 |                    6249 |                 0.6249 |
| Concordia    |                    0.15 |                          0.02  |       10000 |                    7694 |                 0.7694 |

## Interpretation rule

If Dome A / Dome Fuji / Concordia remain high across adjacent thresholds, report that absolute rates are threshold-sensitive but station ordering is robust. If rankings flip substantially, demote station false-stability comparisons to calibration-dependent screening outputs.

## Manuscript-ready wording

> False stability was defined using paper-mode thresholds fixed before the 10,000-system station sweep. To assess threshold dependence, we recomputed false-stability rates across adjacent latent-drop and observed-slope cutoffs using the saved per-system `true_drop_from_early_to_late` and `observed_slope_final_6h` quantities. The headline threshold was not selected to maximize Dome A or any other station result.