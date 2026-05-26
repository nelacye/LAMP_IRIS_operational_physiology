# Reproducibility

## Minimal Executable Audit

Install the package:

```powershell
python -m pip install -e .
```

Run the synthetic example:

```powershell
lamp audit --config examples/synthetic/config.yaml --input examples/synthetic/input.csv --out examples/synthetic --print-json
```

Run tests:

```powershell
python -m pytest
```

## Locked Benchmark Discipline

For external benchmarks, the following must be frozen before holdout evaluation:

- cohort split
- prediction horizons
- feature list
- score construction
- sentinel definitions
- visible-state matching variables
- forbidden-feature rules
- thresholds
- null-control seed and permutation count

The holdout run should reuse the same YAML schema. If a benchmark requires
dataset-specific preprocessing, export a locked score table first and run LAMP on
that table.

## PhysioNet/CinC 2019 Sepsis

The sepsis benchmark should explicitly report:

- which partition is training/design set A
- which partition is training/locked set B
- which features were used by the valid score
- how the anchor hour and prediction horizon were defined
- which sentinel columns are declared
- why the oracle sentinel is an audit comparator rather than leakage in the valid model
- evidence that the valid score does not use post-anchor physiology

## LAMP-CriticalCare Battery

Run the battery wrapper after the sepsis v3_5k outputs exist:

```powershell
python scripts\run_lamp_criticalcare_battery.py
```

If Clinical Trajectory Flow ICU files are not present, the wrapper keeps sepsis
as Benchmark A and writes missing-file notes for the credentialed cardiac-arrest
and GIB cohorts.

After PhysioNet credentialed access is approved and `$HOME\.netrc` is configured,
download the Clinical Trajectory Flow ICU CSV files:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\download_clinical_trajectory_flow_icu.ps1
```

Then rerun the battery wrapper. The cardiac-arrest-risk cohort uses 1h, 2h, 4h,
and 6h early windows. The GIB cohort uses 6h, 12h, and 24h early windows.

## Sepsis ML Prediction Audit

Run the ML audit over the exported PhysioNet/CinC 2019 sepsis v3_5k feature
table:

```powershell
python scripts\run_sepsis_ml_lamp_bench.py
```

This trains early-window MLP, gradient-boosted, and linear sequential-feature
models on a patient-level split, then audits their held-out predictions with
LAMP. It also builds deliberate contaminated variants:

- future-window feature leakage
- low-dose oracle mixtures
- oracle-contaminated hidden-activation probes

Outputs are written to:

- `results/sepsis_ml_lamp/sepsis_ml_predictions.csv`
- `results/sepsis_ml_lamp/sepsis_ml_lamp_summary.csv`
- `results/sepsis_ml_lamp/sepsis_ml_lamp_report.md`

This exported-table run is separate from the raw sequence benchmark below.

## LLM-Safety Toy Audit Battery

Run the alignment-native toy battery:

```powershell
python scripts\run_llm_safety_lamp_bench.py
```

This creates matched visible-behavior LLM-like episodes and audits monitors for:

- latent knowledge
- hidden-state probes
- deceptive behavior toy tasks
- chain-of-thought leakage
- evaluation routing signals
- low-dose oracle contamination

Outputs are written to:

- `results/llm_safety_lamp/llm_safety_prediction_table.csv`
- `results/llm_safety_lamp/llm_safety_lamp_summary.csv`
- `results/llm_safety_lamp/llm_safety_lamp_report.md`
- `notebooks/llm_safety_lamp_audit.ipynb`

## Public Anthropic Sycophancy Benchmark

Run the first public non-synthetic LLM-evaluation-data benchmark:

```powershell
python scripts\run_anthropic_sycophancy_lamp_bench.py
```

This downloads the open `Anthropic/model-written-evals`
`sycophancy_on_nlp_survey.jsonl` file into an ignored cache, trains a
prompt-only TF-IDF monitor on the public prompts, evaluates held-out examples,
and audits deliberate answer-key leakage variants.

Outputs are written to:

- `results/anthropic_sycophancy_lamp/anthropic_sycophancy_predictions.csv`
- `results/anthropic_sycophancy_lamp/anthropic_sycophancy_lamp_summary.csv`
- `results/anthropic_sycophancy_lamp/anthropic_sycophancy_lamp_report.md`
- `notebooks/anthropic_sycophancy_lamp_audit.ipynb`

## Raw PSV Sequence Audit

Download the open PhysioNet benchmarks:

```powershell
.\scripts\download_open_physionet_benchmarks.ps1
```

Build early-window examples directly from raw `.psv` files and run the LAMP
sequence audit:

```powershell
python scripts\run_physionet_sequence_lamp_bench.py --max-patients 3000
```

The raw pipeline performs:

- patient-level `.psv` parsing
- native hourly resampling, with support for alternate aggregate frequencies
- early-window and post-anchor future-window extraction
- trend, variability, slope, and missingness feature engineering
- visible-state matching feature export
- valid and leaky prediction-table generation for LAMP

The hand-crafted MLP probe runs with the base dependencies. For LSTM, GRU,
Transformer, and XGBoost sequence/classical monitors, install the optional
benchmark dependencies:

```powershell
python -m pip install -e ".[benchmarks]"
python scripts\run_physionet_sequence_lamp_bench.py --max-patients 8000 --horizons 6,12,18 --early-window 12 --epochs 4
python scripts\build_cinc2019_lamp_neural_notebook.py
```

Outputs are written to:

- `results/physionet_sequence_lamp/physionet_sequence_predictions.csv`
- `results/physionet_sequence_lamp/lamp_prediction_table.csv`
- `results/physionet_sequence_lamp/physionet_sequence_lamp_summary.csv`
- `results/physionet_sequence_lamp/physionet_sequence_lamp_report.md`
- `notebooks/cinc2019_lamp_neural_audit.ipynb`
