# LAMP / IRIS operational physiology audit framework

This repository contains code and manuscript assets for LAMP, a leakage-audited framework for evaluating latent-state inference systems in operational physiology.

## Repository structure

- src/lamp/ — shared LAMP audit logic
- src/iris/ — IRIS Antarctic reserve-topology simulation and robustness scripts
- src/external_benchmarks/ — external LAMP benchmark audits, including PhysioNet/CinC 2019 sepsis and WESAD
- src/human_grounding/ — retrospective human-signal grounding scripts
- src/figures/ — manuscript figure-generation scripts
- esults/ — selected processed outputs and audit summaries
- manuscript/ — manuscript-ready tables, figure exports and text scaffolds
- data_manifest/ — dataset provenance and download notes

## Evidence layers

1. IRIS Antarctic simulation and LAMP audit
2. 10,000-system station sweep
3. Threshold sensitivity and radiation-channel ablation
4. External benchmark LAMP portability audit
5. Human physiological component-grounding layer

## Data note

Raw datasets are not stored in this repository. They should be downloaded from their original sources and placed under eal_data/, which is excluded from version control.

## Current status

Pre-submission research repository. Not intended for clinical or operational deployment.
