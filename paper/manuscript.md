# LAMP: an executable failure-mode audit framework for hidden-state biomedical AI

## Working abstract

Biomedical monitoring models can appear predictive when they exploit visible-state
confounding, post-anchor physiology, label-adjacent leakage, threshold choices, or
workflow shortcuts rather than early hidden-state signal. We introduce LAMP, an
executable audit framework that accepts a time-series prediction table and a YAML
audit specification, then returns a standardized failure-mode dossier. LAMP
combines temporal isolation, recomputation metadata, forbidden-feature screening,
negative controls, visible-state matched cohorts, sentinel comparators, early-window
sensitivity, and threshold diagnostics. Synthetic IRIS experiments provide a
controlled mechanistic demonstration; PhysioNet/CinC 2019 sepsis provides an
external locked benchmark; Antarctic forcing geometry is used as a stress-test
setting rather than the central claim. Passing LAMP does not establish clinical
validity. It identifies an audit-pass candidate that has earned prospective
testing.

## Central positioning

The primary object of the paper is LAMP. IRIS is a controlled mechanistic
demonstration. PhysioNet sepsis is an external locked benchmark. Antarctica is a
stress-test geometry. Human grounding datasets are a support layer.

## Figure 1

Figure 1 should be the LAMP failure-mode separation map:

Input time-series table plus YAML audit specification to LAMP components to output
classes:

- `null_or_destroyed_signal`
- `visible_state_confounding`
- `valid_early_hidden_state_signal`
- `future_physiology_invalid_comparator`
- `oracle_label_leakage_sentinel`
- `threshold_fragile_claim`
- `audit_pass_candidate`

## Benchmark direction

The strongest next benchmark is LAMP-Bench: a controlled failure-mode benchmark for
hidden-state biomedical inference. The most valuable first experiment is low-dose
leakage sensitivity, mixing valid early scores with oracle and future-physiology
sentinels at fixed contamination doses.
