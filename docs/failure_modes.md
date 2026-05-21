# Failure Modes

LAMP separates audit signatures rather than producing a single pass/fail metric.

## `null_or_destroyed_signal`

The primary score is near null, or the label/score structure is too weak to
support a hidden-state claim.

## `visible_state_confounding`

The primary score has apparent discrimination, but the matched observed-state
delta collapses after balancing declared visible physiology.

## `valid_early_hidden_state_signal`

The primary score remains predictive after temporal isolation, null controls, and
visible-state matching. This is an audit signal, not clinical validation.

## `future_physiology_invalid_comparator`

A post-anchor physiology comparator behaves like a strong predictor. This is
useful because it shows what invalid future information looks like under the same
audit geometry.

## `oracle_label_leakage_sentinel`

An oracle or label-adjacent comparator reaches ceiling-like performance. This is
expected for the sentinel and is a violation only if the valid score uses the same
information.

## `threshold_fragile_claim`

The direction or enrichment of the thresholded claim changes across configured
thresholds.

## `audit_pass_candidate`

The score survived the configured LAMP audit. The correct claim is narrow:
survives LAMP does not mean clinically valid; it earns prospective testing.
