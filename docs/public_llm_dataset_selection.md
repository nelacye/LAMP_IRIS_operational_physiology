# Public LLM Dataset Selection

Goal: add one real, public LLM-data benchmark where LAMP can produce
`audit_pass` and `audit_fail` diagnoses on alignment-relevant failure modes.

## Candidates Considered

| Dataset | Fit for LAMP | Pros | Limitation |
|---|---|---|---|
| Anthropic `model-written-evals` sycophancy | Chosen first benchmark | Public JSONL, around 10k examples per sycophancy topic, explicit matching/non-matching answer keys, direct alignment relevance | Prompt/eval data rather than model hidden-state activations |
| `meg-tong/sycophancy-eval` | Strong next behavioral benchmark | Public sycophancy prompts from "Towards Understanding Sycophancy in Language Models" | Requires running model inference or extra scoring to obtain response-level monitor outputs |
| TruthfulQA | Good truthfulness benchmark | Public, stable, compact, common in LLM evaluation | Better for truthfulness/hallucination than latent-monitor leakage unless paired with model outputs |
| Representation Engineering datasets | Strong for hidden-state/probe story | Directly aligned with representation/activation monitoring | Public prompts are easier to use than precomputed hidden states; full run requires model activations |
| Apollo/ARC deception datasets | High alignment salience | Closest conceptually to deception probes/scheming | Public availability and schema vary by project; likely needs extra data/code integration |

## Chosen Benchmark

The first real LLM-data run uses Anthropic's `model-written-evals`
`sycophancy/sycophancy_on_nlp_survey.jsonl`.

Why:

- It is public and directly downloadable.
- The dataset card documents that the sycophancy files test whether models
  repeat back user views.
- Rows include a prompt plus `answer_matching_behavior` and
  `answer_not_matching_behavior`, so LAMP can cleanly separate prompt-only
  monitors from answer-key leakage.
- It supports low-dose leakage experiments without needing closed model APIs.

Run:

```powershell
python scripts\run_anthropic_sycophancy_lamp_bench.py
```

Current result:

- Raw examples: 9,984.
- Held-out audit rows: 2,996.
- Prompt-only TF-IDF monitor: AUC 0.987, `audit_pass`.
- Interpretable user-view cue monitor: AUC 0.815, `audit_pass`.
- Visible length shortcut: AUC 0.465, null/destroyed.
- Direct answer-key leakage: AUC 1.000, audit fail.
- Low-dose answer-key leakage at 1%, 5%, and 10%: AUC 0.988, 0.992, 0.996;
  all fail temporal/forbidden/oracle-proximity gates.

Outputs:

- `results/anthropic_sycophancy_lamp/anthropic_sycophancy_lamp_report.md`
- `results/anthropic_sycophancy_lamp/anthropic_sycophancy_lamp_summary.csv`
- `notebooks/anthropic_sycophancy_lamp_audit.ipynb`

## Next Best Extensions

1. Run the same LAMP pattern on `meg-tong/sycophancy-eval` after adding either
   open-model inference or a response-scoring layer.
2. Add TruthfulQA with model-generated answers and score truthfulness vs.
   answer-key leakage.
3. Add a Representation Engineering hidden-state/probe run using a small open
   model and cached activations.
