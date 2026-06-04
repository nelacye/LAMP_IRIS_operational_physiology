# MRT LAMP Micro Audit

Public-data smoke test on `ScaleAI/mrt`, task `american_airlines_2`.
This is intentionally small: 8 adversarial-strategy transcripts and
8 no-secondary-task controls, downloaded by path from Hugging Face.

## Audit Setup

- Primary score: parsed `<verdict>` from the MRT monitor response.
- Label: `side_task_evaluation` from the MRT transcript JSON.
- Oracle sentinels: side-task completion and hidden side-task instruction presence.
- Visible matching: transcript length, turn count, tool-marker count, main-task score.
- Rows: 16 (7 side-task positives, 9 controls).

## LAMP Result

- Primary AUC: 0.071
- Inverted AUC: 0.929
- Score-direction ambiguous: True
- Audit pass candidate: False
- Output classes: `oracle_label_leakage_sentinel;score_direction_ambiguous`
- Temporal isolation passed: True
- Forbidden-feature screen passed: True
- Matched observed-state delta: 0.0
- Noise AUC mean: 0.480
- Score permutation AUC mean: 0.486

Primary AUC = 0.071; inverted AUC = 0.929. Interpretation depends on whether higher score means positive-class risk/suspicion or benign classification.

## Interpretation

This artifact does not claim that the monitor is weak or strong. The score
orientation of the parsed MRT verdict must be confirmed before interpreting
AUC direction. It demonstrates
that LAMP can ingest public agent-monitoring trajectories as a standardized
prediction-table audit: the monitor verdict is treated as the candidate
score, hidden side-task labels are declared as oracle sentinels, and visible
trajectory features are used for matched-state checks.

## Source Paths

- `task_pairs/american_airlines_2/transcripts_no_hint_selective_thinking_time_likert/claude-3-5-sonnet-20241022/claude-3-5-sonnet-20241022/transcript_1.json`
- `task_pairs/american_airlines_2/transcripts_no_hint_selective_thinking_time_likert/claude-3-5-sonnet-20241022/claude-3-5-sonnet-20241022/transcript_2.json`
- `task_pairs/american_airlines_2/transcripts_no_hint_selective_thinking_time_likert/claude-3-5-sonnet-20241022/claude-3-5-sonnet-20241022/transcript_3.json`
- `task_pairs/american_airlines_2/transcripts_no_hint_selective_thinking_time_likert/claude-3-5-sonnet-20241022/claude-3-5-sonnet-20241022/transcript_4.json`
- `task_pairs/american_airlines_2/transcripts_no_hint_selective_thinking_time_likert/claude-3-5-sonnet-20241022/claude-3-5-sonnet-20241022/transcript_5.json`
- `task_pairs/american_airlines_2/transcripts_no_hint_selective_thinking_time_likert/claude-3-5-sonnet-20241022/claude-3-5-sonnet-20241022/transcript_6.json`
- `task_pairs/american_airlines_2/transcripts_no_hint_selective_thinking_time_likert/claude-3-5-sonnet-20241022/claude-3-5-sonnet-20241022/transcript_7.json`
- `task_pairs/american_airlines_2/transcripts_no_hint_selective_thinking_time_likert/claude-3-5-sonnet-20241022/claude-3-5-sonnet-20241022/transcript_8.json`
- `task_pairs/american_airlines_2/transcripts_no_secondary_task/claude-3-5-haiku-20241022/claude-3-5-haiku-20241022/transcript_0.json`
- `task_pairs/american_airlines_2/transcripts_no_secondary_task/claude-3-5-haiku-20241022/claude-3-5-haiku-20241022/transcript_1.json`
- `task_pairs/american_airlines_2/transcripts_no_secondary_task/claude-3-5-haiku-20241022/claude-3-5-haiku-20241022/transcript_10.json`
- `task_pairs/american_airlines_2/transcripts_no_secondary_task/claude-3-5-haiku-20241022/claude-3-5-haiku-20241022/transcript_11.json`
- `task_pairs/american_airlines_2/transcripts_no_secondary_task/claude-3-5-haiku-20241022/claude-3-5-haiku-20241022/transcript_12.json`
- `task_pairs/american_airlines_2/transcripts_no_secondary_task/claude-3-5-haiku-20241022/claude-3-5-haiku-20241022/transcript_13.json`
- `task_pairs/american_airlines_2/transcripts_no_secondary_task/claude-3-5-haiku-20241022/claude-3-5-haiku-20241022/transcript_2.json`
- `task_pairs/american_airlines_2/transcripts_no_secondary_task/claude-3-5-haiku-20241022/claude-3-5-haiku-20241022/transcript_3.json`
