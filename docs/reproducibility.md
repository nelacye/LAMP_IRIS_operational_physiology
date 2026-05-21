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
