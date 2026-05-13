# Neumayer modern comparator audit

## Purpose

This audit addresses the critique that HR-only is a weak conventional comparator. It compares IRIS-style scores against best single markers and regularized LOOCV models using early HRV features.

## Results

| model                                         | endpoint                   | early_window   | late_window   |   n_subjects |   n_high_endpoint |      auc |   label_permutation_p |
|:----------------------------------------------|:---------------------------|:---------------|:--------------|-------------:|------------------:|---------:|----------------------:|
| IRIS_balanced                                 | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.923611 |            0.00039992 |
| IRIS_hybrid                                   | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.923611 |            0.00019996 |
| IRIS_vagal_sympathetic                        | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.902778 |            0.00019996 |
| best_single_marker_in_sample__mean_hfnu_early | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.868056 |            0.00039992 |
| LOOCV_logistic_ridge_lam_0.1                  | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.847222 |            0.00219956 |
| LOOCV_logistic_ridge_lam_10.0                 | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.847222 |            0.00279944 |
| LOOCV_logistic_ridge_lam_1.0                  | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.840278 |            0.00259948 |
| LOOCV_linear_ridge_lam_10.0                   | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.826389 |            0.00339932 |
| LOOCV_linear_ridge_lam_1.0                    | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.791667 |            0.00839832 |
| LOOCV_linear_ridge_lam_0.1                    | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.784722 |            0.0103979  |
| HR_only                                       | end_late_sympathetic_state | E0             | L6_9          |           25 |                 9 | 0.638889 |            0.142971   |

## Interpretation guardrail

If LOOCV ridge/logistic models match or outperform IRIS composites, the claim should be reframed from 'IRIS beats conventional monitoring' to 'IRIS captures an interpretable autonomic geometry comparable to small-n multivariable HRV models.'

The best single-marker screen is optimistic and should not be treated as a validated comparator unless cross-validated or replicated.
