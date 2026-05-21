# LAMP-CriticalCare Battery

## Purpose

The LAMP-CriticalCare Battery tests whether the same executable audit separates
failure modes across multiple real critical-care time-series endpoints.

Main narrative:

- Benchmark A: PhysioNet/CinC 2019 sepsis v3_5k.
- Benchmark B: Clinical Trajectory Flow ICU cardiac-arrest-risk cohort.
- Benchmark C: Clinical Trajectory Flow ICU gastrointestinal bleeding cohort.

BIDSleep is treated as a supplemental wearable negative benchmark, not part of
the main critical-care story.

## Access

Clinical Trajectory Flow ICU is PhysioNet credentialed access. It requires a
credentialed PhysioNet account, CITI Data or Specimens Only Research training,
and signing the resource DUA.

After access is approved, configure `~/.netrc` or `$HOME\.netrc` locally:

```text
machine physionet.org login YOUR_USERNAME password YOUR_PASSWORD
```

Then download:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\download_clinical_trajectory_flow_icu.ps1
```

The expected local files are:

- `real_data/clinical-trajectory-flow-icu-1.0.0/eICU_cardiacArrest_physionet.csv`
- `real_data/clinical-trajectory-flow-icu-1.0.0/MIMIC_gib_physionet.csv`

## Audit Design

The Clinical Trajectory Flow ICU files provide first-24h trajectories and
outcome labels rather than explicit onset timestamps. In this battery, the
reported windows are early-window lengths, and future sentinels use the later
part of the first 24h.

Cardiac-arrest-risk windows:

- 1h
- 2h
- 4h
- 6h

GIB windows:

- 6h
- 12h
- 24h

For each cohort/window, the runner builds:

- valid early score
- future-physiology sentinel
- oracle outcome sentinel
- negative controls
- visible/workflow shortcut score
- low-dose oracle mixture, with lambda values 0, 0.005, 0.01, 0.05, and 0.10

## Run

```powershell
python scripts\run_lamp_criticalcare_battery.py
```

Outputs:

- `results/lamp_criticalcare_battery/criticalcare_battery_summary.csv`
- `results/lamp_criticalcare_battery/criticalcare_battery_report.md`
- per-cohort score tables, configs, LAMP JSON reports, and perturbation summaries
  when credentialed CSV files are present

## Interpretation

The target result is not maximum AUC. The target result is qualitative
replication of LAMP failure-mode diagnoses across independent critical-care
endpoints:

- valid early score earns `audit_pass_candidate`
- future physiology produces an invalid comparator signature
- oracle label score behaves as a ceiling sentinel
- low-dose oracle mixtures shift toward oracle leakage before AUC alone becomes
  obviously suspicious
- visible shortcuts lose signal under matched visible-state analysis

Survives LAMP does not mean clinically valid. It means the score survived the
configured failure-mode audit and earned prospective testing.
