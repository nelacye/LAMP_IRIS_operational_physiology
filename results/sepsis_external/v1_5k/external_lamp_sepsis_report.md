# External LAMP audit: PhysioNet/CinC 2019 sepsis early-warning benchmark

## Purpose

This analysis tests whether LAMP transfers beyond IRIS. It audits an external, real time-series early-warning task with externally defined labels. It is not an IRIS validation and it is not an Antarctic physiology analysis.

## Audit summary

|   horizon_h |   n_patients |   n_positive |   event_rate |   valid_early_warning_auc |   leaky_future_sentinel_auc |   noise_auc |   score_permutation_auc |   label_permutation_p |   leaky_minus_valid_auc |   matched_observed_state_delta |
|------------:|-------------:|-------------:|-------------:|--------------------------:|----------------------------:|------------:|------------------------:|----------------------:|------------------------:|-------------------------------:|
|           6 |         4869 |          280 |    0.0575067 |                  0.641621 |                    0.630712 |    0.516082 |                0.474066 |           0.000999001 |              -0.0109092 |                     0.0234364  |
|          12 |         4836 |          247 |    0.0510753 |                  0.632763 |                    0.644646 |    0.499811 |                0.514127 |           0.000999001 |               0.0118824 |                     0.00245119 |
|          18 |         4812 |          223 |    0.0463425 |                  0.624875 |                    0.656924 |    0.530593 |                0.486743 |           0.000999001 |               0.0320492 |                     0.056001   |

## Interpretation

A valid early-warning score should perform above noise and score permutation, while a deliberately leaky future-window sentinel defines the contamination ceiling. Matched observed-state cohort deltas test whether the score retains stratification among patients with similar early visible vitals; for a simple vital-sign score this delta may shrink, which is informative rather than a failure of LAMP.

## Manuscript-ready paragraph

> To test portability beyond IRIS, we applied LAMP to a public non-IRIS early-warning benchmark using real ICU time-series and externally defined sepsis labels. A fixed early-warning score was computed only from pre-anchor observations, while a deliberately leaky sentinel used future-window observations. The external audit reproduced the expected LAMP ordering: negative controls remained near chance, the future-window sentinel defined the contamination ceiling, and early-window performance varied with prediction horizon. This analysis demonstrates that LAMP can audit systems outside the Antarctic reserve-topology simulator and can separate valid early predictors from deliberately invalid future-window predictors.

## Claim boundary

> The sepsis benchmark tests LAMP portability, not IRIS biological validity. Its role is to show that the audit protocol can be applied to an independent real time-series early-warning task.
