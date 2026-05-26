# AI Safety Experiments

LAMP now includes an alignment-native toy benchmark in addition to the biomedical
benchmarks. The goal is not to claim real LLM deployment validity. The goal is
to make the audit contract concrete for AI safety readers: a latent monitor must
respect a declared information boundary, even when leakage makes ordinary AUC
look better.

The repository also includes a public, non-synthetic LLM-evaluation-data run on
Anthropic `model-written-evals` sycophancy prompts. See
`docs/public_llm_dataset_selection.md` for the dataset choice and
`notebooks/anthropic_sycophancy_lamp_audit.ipynb` for the result notebook.

Run:

```powershell
python scripts\run_llm_safety_lamp_bench.py
```

Outputs:

- `results/llm_safety_lamp/llm_safety_prediction_table.csv`
- `results/llm_safety_lamp/llm_safety_lamp_summary.csv`
- `results/llm_safety_lamp/llm_safety_lamp_report.md`
- `notebooks/llm_safety_lamp_audit.ipynb`

## Experiment Map

| Alignment concern | LAMP toy monitor | Valid information contract | Failure mode |
|---|---|---|---|
| Latent knowledge | Latent knowledge monitor | Pre-answer residual and semantic probes | Passes when matched behavior still separates hidden target |
| Hidden state probes | Hidden-state probe | Pre-answer residual/attention probes | Passes when probe uses allowed internal states |
| Deceptive behavior | Deceptive-behavior early monitor | Pre-trigger intent/capability signals | Passes only when it avoids post-trigger behavior |
| Chain-of-thought leakage | CoT leakage monitor | Violated by privileged scratchpad label | Temporal + forbidden + oracle-proximity failure |
| Routing signals | Routing-signal shortcut | Violated by eval-router metadata | Temporal + forbidden + oracle-proximity failure |
| Low-dose leakage | Low-dose CoT/oracle mixtures | Violated by oracle mixture | Graded AUC lift with audit failure |

## Current Result Snapshot

The current synthetic run uses 896 matched visible-behavior episodes and 11
monitors.

- Clean latent-knowledge monitor: AUC 0.896, `audit_pass`.
- Clean hidden-state probe: AUC 0.847, `audit_pass`.
- Deceptive-behavior early monitor: AUC 0.789, `audit_pass`.
- Surface-behavior shortcut: AUC 0.497, null/destroyed signal.
- CoT leakage, routing leakage, leaky hidden-state probe, and post-trigger
  deception leakage: AUC approximately 1.000, but temporal/forbidden/oracle
  proximity gates fail.
- Low-dose CoT/oracle mixtures at 1%, 5%, and 10% lift AUC to 0.906, 0.941,
  and 0.971 while failing the audit.

## Interpretation

This is the AI safety version of the central LAMP claim: performance is not
validity. A monitor for latent knowledge, deception, or situational awareness can
look excellent under ordinary validation because it reads privileged CoT traces,
post-hoc internal labels, or routing metadata. LAMP asks whether the score earned
its performance under the declared information boundary.
