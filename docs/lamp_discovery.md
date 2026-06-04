# LAMP-Discovery

LAMP-Discovery is the first step from audit-only LAMP toward a discovery engine.
It does not soften audit failures. Instead, it converts them into localized,
testable hypotheses.

## Contract

Audit mode asks:

> Did this monitor respect the declared information contract?

Discovery mode asks:

> If the contract failed, where did the information come from, what mechanism
> might explain that channel, and what experiment should test it prospectively?

## Inputs

`lamp discover` needs the same artifacts produced by an audit:

- `audit_summary.json`
- LAMP audit config YAML
- prediction table CSV
- optional LAMP-Bio contract YAML

Example:

```bash
lamp discover \
  --audit-summary results/ipsc_molecular_code/synthetic_kinase_folding/lamp/future_folding_leakage/audit_summary.json \
  --config results/ipsc_molecular_code/synthetic_kinase_folding/configs/future_folding_leakage.yaml \
  --data results/ipsc_molecular_code/synthetic_kinase_folding/synthetic_ipsc_molecular_code_predictions.csv \
  --contract configs/ipsc_molecular_code_contract.yaml \
  --output results/ipsc_molecular_code/synthetic_kinase_folding/discovery/future_folding_leakage
```

## Outputs

`discovery_dossier.json`

Machine-readable localization:

- failure type
- localized features/channels
- sentinel evidence
- mechanism hypotheses
- follow-up experiment sketch

`discovery_report.md`

Human-readable report for a scientist:

- why the monitor failed or passed
- which features/channels were localized
- what biological mechanism is plausible
- what next perturbation/readout design would separate shortcut from biology

## iPSC Molecular-Code Emulator

Run:

```bash
python scripts/run_ipsc_molecular_code_discovery.py
```

Current synthetic results:

| Monitor | Discovery Class | Top Localized Feature | Follow-Up Logic |
|---|---|---|---|
| clean hybrid kinase/proteostasis | `audit_pass_discovery` | `early_mapk_phospho_slope` | perturb early kinase/proteostasis axes and test held-out folding endpoint |
| protocol/stressor shortcut | `protocol_shortcut` | `protocol_stressor_shortcut_score` | cross protocol arms across donor/batch and verify shortcut collapse |
| future folding leakage | `future_folding` | `future_folding_execution_score` | treat leakage as a time-lagged kinase-to-folding hypothesis |
| low-dose oracle mix | `future_folding` | `oracle_folding_label_score` | remove endpoint channel, then prospectively retest disjoint early panel |

## Leakage Sensitivity Add-On

Run:

```bash
python scripts/run_ipsc_molecular_code_leakage_analysis.py
```

This writes:

- ROC overlay for clean hybrid vs 0.5% oracle contamination
- known-truth LAMP confusion matrix
- lambda sweep for strict declared-provenance and geometry-only detection

Current result:

- Clean AUC: `0.9141`
- 0.5% oracle AUC: `0.9159`
- Delta AUC: `0.0018`
- Canonical synthetic sensitivity/specificity: `1.000` / `1.000`
- Strict declared-provenance detection floor: `0.001%` oracle leakage
- Geometry-only detection floor: `0.05%` oracle leakage

## Design Principle

A leakage channel does not become validation. It becomes a discovery hypothesis
only after it is moved out of the monitor and into a prospective experiment
where it can be perturbed, hidden, balanced, or held out.
