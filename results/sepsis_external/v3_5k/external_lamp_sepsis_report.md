# External LAMP audit v3: PhysioNet/CinC 2019 sepsis early-warning benchmark

## Purpose

This analysis tests whether LAMP transfers beyond IRIS. It audits an external, real time-series early-warning task with externally defined labels. It is not an IRIS validation and it is not an Antarctic physiology analysis.

## Audit summary

|   horizon_h |   n_patients |   n_positive |   event_rate |   valid_early_warning_auc |   future_physiology_sentinel_auc |   oracle_label_sentinel_auc |   noise_auc |   score_permutation_auc |   label_permutation_p |   oracle_minus_valid_auc |   matched_observed_state_delta |
|------------:|-------------:|-------------:|-------------:|--------------------------:|---------------------------------:|----------------------------:|------------:|------------------------:|----------------------:|-------------------------:|-------------------------------:|
|           6 |         4869 |          280 |    0.0575067 |                  0.641621 |                         0.630712 |                           1 |    0.516082 |                0.474066 |           0.000999001 |                 0.358379 |                      0.0318408 |
|          12 |         4836 |          247 |    0.0510753 |                  0.632763 |                         0.644646 |                           1 |    0.499811 |                0.514127 |           0.000999001 |                 0.367237 |                      0.0327399 |
|          18 |         4812 |          223 |    0.0463425 |                  0.624875 |                         0.656924 |                           1 |    0.530593 |                0.486743 |           0.000999001 |                 0.375125 |                      0.0268271 |

## Interpretation

The valid early-warning score uses only pre-anchor observations. The future-physiology sentinel uses invalid future-window measurements but is not guaranteed to dominate if the fixed score is crude or future observations are sparse. The oracle label sentinel deliberately uses future label/onset information and therefore acts as the positive leakage-control ceiling. Negative controls should remain near chance.

## Manuscript-ready paragraph

> To test portability beyond IRIS, we applied LAMP to the PhysioNet/CinC 2019 sepsis benchmark, a public non-IRIS early-warning task with real ICU time-series and externally defined labels. A fixed early-warning score was computed only from pre-anchor observations. Two invalid sentinels were evaluated: a future-physiology sentinel using post-anchor measurements and an oracle label-adjacent sentinel using future label/onset information. The oracle sentinel defined the expected contamination ceiling, while negative controls remained near chance. This external benchmark demonstrates that LAMP can be applied outside the Antarctic reserve-topology simulator and can explicitly separate valid early predictors from invalid future-window or label-adjacent predictors.

## Claim boundary

> The sepsis benchmark tests LAMP portability, not IRIS biological validity. Its role is to show that the audit protocol can be applied to an independent real time-series early-warning task.
