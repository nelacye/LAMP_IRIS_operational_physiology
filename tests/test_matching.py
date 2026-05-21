from lamp.matching import matched_cohort_delta


def test_visible_state_matching_collapses_visible_only_score():
    rows = []
    for age, score, label in [
        (40, 0.2, 0),
        (40, 0.2, 0),
        (40, 0.2, 1),
        (40, 0.2, 1),
        (70, 0.8, 0),
        (70, 0.8, 0),
        (70, 0.8, 1),
        (70, 0.8, 1),
    ]:
        rows.append({"label": str(label), "score": str(score), "age": str(age)})

    match = matched_cohort_delta(
        rows,
        label_col="label",
        score_col="score",
        match_columns=["age"],
        n_bins=2,
        min_bin_size=4,
    )

    assert match["evaluated"]
    assert match["matched_observed_state_delta"] == 0.0


def test_visible_state_matching_preserves_hidden_state_ranking():
    rows = []
    for age in [40, 70]:
        for _ in range(4):
            rows.append({"label": "0", "score": "0.2", "age": str(age)})
        for _ in range(4):
            rows.append({"label": "1", "score": "0.8", "age": str(age)})

    match = matched_cohort_delta(
        rows,
        label_col="label",
        score_col="score",
        match_columns=["age"],
        n_bins=2,
        min_bin_size=4,
    )

    assert match["evaluated"]
    assert match["matched_observed_state_delta"] > 0.9
