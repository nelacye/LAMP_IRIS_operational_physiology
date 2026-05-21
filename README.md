# LAMP: Latent-state Audit with Matched-cohort Protocol

**A general, executable framework for auditing claims of hidden/latent state
inference in complex systems, with direct applications to AI alignment and
scalable oversight.**

Many AI safety proposals depend on early-warning or latent monitoring systems
that claim to detect deception, situational awareness, capability gain, or
alignment drift *before* these phenomena become visible in behavior. Such claims
are notoriously difficult to validate and are vulnerable to evaluation leakage,
proxy gaming, temporal confounding, and hidden shortcuts.

LAMP provides a structured failure-mode audit protocol to rigorously stress-test
these claims.

## Core Contribution

LAMP takes a time-series prediction table plus a YAML audit configuration and
outputs a standardized machine-readable dossier that distinguishes:

- Null / destroyed signal
- Valid early latent signal
- Future-window leakage
- Label-adjacent contamination

It implements eight audit components, including temporal isolation, forbidden
feature screening, negative controls, matched observed-state cohorts, leaky
sentinels, early-window sensitivity, and threshold robustness.

## Evidence

- **IRIS**: mechanistic toy model of multi-axis reserve topology, analogous to
  toy models in mechanistic interpretability.
- Large-scale sweeps across 10,000+ systems under realistic Antarctic forcing
  profiles.
- Successful transfer to real clinical data: PhysioNet/CinC 2019 sepsis
  early-warning benchmark (`audit_pass` with clear signal-leakage separation).
- Synthetic deception experiments demonstrating detection of evaluation gaming.

## Alignment Relevance

LAMP is directly transferable to auditing:

- Latent knowledge and situational awareness in LLMs
- Deceptive alignment
- Agent trajectories and hidden goals
- Sudden capability jumps or safety property erosion ("reserve collapse")

## Alignment Angles

- Matched-behavior latent knowledge audits: same visible output, different
  internals
- Deceptive alignment early-warning benchmarks
- Scalable oversight leakage atlas: controlled contamination experiments
- Capability reserve-collapse monitoring in agent runs

## Quick Start

```bash
pip install -e .

# Synthetic deception demo (recommended)
python scripts/run_synthetic_deception_experiment.py

# Run a custom audit
lamp audit --config configs/iris_antarctic.yaml --data results/predictions.csv --output audit_results/
```

See `notebooks/synthetic_deception_demo.ipynb` for a full walkthrough.

If the `lamp` entry point is not on `PATH`, use:

```bash
python -m lamp.cli audit --config configs/iris_antarctic.yaml --data results/predictions.csv --output audit_results/
```

## Important Caveat

Passing LAMP does not prove real-world validity or alignment safety. It means
the system survived a configured set of failure-mode tests and earned the right
to further, more expensive evaluation.

## Status

Active pre-submission research. Open to collaboration and extensions.
