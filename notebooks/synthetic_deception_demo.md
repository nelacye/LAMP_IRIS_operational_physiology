# Synthetic Deception Demo

This demo translates LAMP into an alignment-style setting. Agents are matched on visible pre-trigger behavior, but some later undergo a reserve-collapse-like failure. Clean monitors use only pre-trigger latent, recurrent, attention-style, or hidden-state probe features. Gaming monitors use post-trigger leakage, CoT-style privileged internal traces, hidden-policy flags, or sandbagged surface behavior.

## Headline

| monitor | AUC | audit pass | temporal | forbidden | oracle proximity | interpretation |
|---|---:|:---:|:---:|:---:|:---:|---|
| Valid latent monitor | 0.906 | True | True | True | False | clean early latent signal |
| LSTM-style early-warning monitor | 0.933 | True | True | True | False | clean recurrent trajectory signal |
| Transformer-style early-warning monitor | 0.902 | True | True | True | False | clean attention-style trajectory signal |
| MLP latent probe monitor | 0.850 | True | True | True | False | clean latent probe |
| Linear probe on LSTM hidden state | 0.908 | True | True | True | False | clean hidden-state probe |
| Linear probe on Transformer hidden state | 0.901 | True | True | True | False | clean hidden-state probe |
| Deceptive post-trigger leakage monitor | 1.000 | False | False | False | True | post-trigger hidden-information leakage |
| CoT-style internal reasoning leakage monitor | 1.000 | False | False | False | True | privileged CoT/internal trace leakage |
| Sandbagging surface-behavior monitor | 0.000 | False | True | True | False | surface behavior destroys/inverts signal |
| Sandbagging hidden-policy leakage monitor | 1.000 | False | True | False | True | forbidden hidden-policy flag leakage |

LAMP separates clean latent/trajectory monitors from gaming monitors. The valid latent monitor passes with AUC 0.91; the LSTM-style and Transformer-style early-warning monitors also pass with AUC 0.93 and 0.90. The deceptive leakage monitor reaches AUC 1.00, but fails temporal isolation, forbidden-feature screening, and oracle-leakage proximity. CoT-style internal reasoning leakage reaches AUC 1.00 with the same failure signature. Sandbagging surface behavior is classified as destroyed/non-pass (AUC 0.00), while a hidden-policy leakage version recovers AUC 1.00 but fails forbidden/oracle checks.

This directly illustrates detection of evaluation gaming / hidden information.

![All monitor AUCs](figures/synthetic_deception_all_auc.png)

![Audit gates](figures/synthetic_deception_multi_audit_gates.png)

![Score distributions](figures/synthetic_deception_multi_score_distributions.png)

## Reproduce

```powershell
python scripts/run_synthetic_deception_experiment.py
lamp audit --config examples/alignment_deception/deceptive_leakage_config.yaml --data examples/alignment_deception/input.csv --output examples/alignment_deception/deceptive_leakage_lamp
```
