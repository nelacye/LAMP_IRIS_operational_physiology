# Data manifest

Raw datasets are not included in the repository.

## Antarctic forcing
- AntAWS station meteorology
- NMDB South Pole neutron monitor proxy

## External LAMP benchmark
- PhysioNet/CinC 2019 Challenge sepsis time-series
- Source: https://physionet.org/content/challenge-2019/1.0.0/
- Local path: `real_data/physionet/challenge-2019/training/`
- Current local status: full training set downloaded from the public PhysioNet S3 mirror
  - `training_setA`: 20,336 `.psv` files
  - `training_setB`: 20,000 `.psv` files
  - Combined raw `.psv` size: about 255 MB

## Cardiac collapse / arrhythmia benchmark
- VitalDB Arrhythmia Database
- Source: https://physionet.org/content/vitaldb-arrhythmia/1.0.0/
- Local path: `real_data/vitaldb-arrhythmia-1.0.0/`
- Current local status: metadata, license, checksums, README, and 482 annotation CSV files downloaded from the public PhysioNet S3 mirror.

## Wearable / continuous monitoring benchmark
- BIG IDEAs Lab Glycemic Variability and Wearable Device Data
- Source: https://physionet.org/content/big-ideas-glycemic-wearable/1.1.3/
- Local path: `real_data/big-ideas-glycemic-wearable-1.1.3.zip`
- Current local status: large ZIP download started but incomplete/resumable; `.aria2` control file is present. The full ZIP is about 4.7 GB and extraction is about 34 GB.
- Resume command:

```powershell
.\scripts\download_open_physionet_benchmarks.ps1 -SkipCinC -SkipVitalDB -IncludeBigIdeas
```

## Human grounding layer
- ACTES cycloergometer exercise
- EPHNOGRAM ECG/PCG
- BIDMC oxygenation-related time-series
- Harespod hypoxia/altitude physiology
- Neumayer III HRV

## Wearable benchmark extension
- WESAD wearable stress and affect dataset
- Expected local files: S2.pkl, S3.pkl, ..., S17.pkl

