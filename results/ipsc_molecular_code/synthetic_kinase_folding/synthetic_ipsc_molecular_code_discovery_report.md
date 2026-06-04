# iPSC Molecular-Code Discovery Summary

This report is the first LAMP-Discovery emulator artifact. It treats audit
outcomes as entry points for localized hypotheses and prospective experiment
design, not only PASS/FAIL labels.

| Monitor | AUC | Audit Pass | Discovery Class | Top Localized Feature | Hypothesis |
|---|---:|:---:|---|---|---|
| `clean_hybrid_kinase_folding` | 0.914 | True | `audit_pass_discovery` | `early_mapk_phospho_slope` (0.856) | Candidate latent-state signal |
| `protocol_stressor_shortcut` | 0.663 | False | `protocol_shortcut` | `protocol_stressor_shortcut_score` (0.663) | Protocol-conditioned biology rather than latent-state inference |
| `future_folding_leakage` | 0.957 | False | `future_folding` | `future_folding_execution_score` (0.957) | Time-lagged kinase-to-folding coupling |
| `lowdose_oracle_mix_005` | 0.916 | False | `future_folding` | `oracle_folding_label_score` (1.000) | Time-lagged kinase-to-folding coupling |

## What Changed

The audit layer says whether the declared information contract survived.
The discovery layer asks what the failure is made of: the suspected
feature/channel, the biological mechanism hypothesis, and a concrete
time-course plate sketch for the next experiment.

The important design constraint remains intact: a leakage channel does not
become validation. It becomes a hypothesis only after being moved out of
the monitor and into a prospective perturbation/readout design.
