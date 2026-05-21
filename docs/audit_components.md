# LAMP Audit Components

LAMP is meant to be run, not only cited as a checklist. A LAMP audit consumes a
CSV prediction table and a YAML configuration, then writes a JSON summary and a
Markdown report.

## Temporal Isolation

The config must declare the prediction anchor and the feature timing used by the
valid score. Valid-score features should be at or before the anchor. Post-anchor
features belong only in declared sentinel comparators or in forbidden-feature
tests.

## Forbidden-Feature Screening

The config declares columns and feature names that are invalid for the valid
model. Declared sentinels are allowed to appear in the audit table because they
are comparators. They become leakage only if the valid score uses them or uses an
equivalent forbidden feature.

## Negative Controls

LAMP recomputes null behavior with noise scores, score permutations, and label
permutations. A credible audit-pass candidate should not depend on null controls
that also look predictive.

## Visible-State Matching

LAMP bins declared visible-state variables, compares high-score and low-score
rows within matched strata, and reports a matched observed-state delta. If an
apparently predictive score collapses after matching, the result is more
consistent with visible-state confounding than hidden-state signal.

## Sentinels

Sentinels are deliberately invalid comparators. Typical sentinels include a
future-physiology score and an oracle-label score. They define recognizable audit
geometry: future physiology should behave differently from direct label leakage,
and neither should be silently mixed into the valid score.

## Threshold Sensitivity

LAMP evaluates configured score thresholds and flags claims whose apparent risk
enrichment changes direction across thresholds.

## Reports

The JSON report is the machine-readable dossier. The Markdown report is the
reviewer-facing interpretation layer. Both should preserve the same central
boundary: survives LAMP does not mean clinically valid; it earns prospective
testing.
