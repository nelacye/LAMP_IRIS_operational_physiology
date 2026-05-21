from lamp.controls import auc_score, negative_controls


def test_auc_score_handles_ties_and_perfect_ordering():
    labels = [0, 0, 1, 1]
    scores = [0.1, 0.2, 0.8, 0.9]

    assert auc_score(labels, scores) == 1.0


def test_negative_controls_destroy_ordered_signal_on_average():
    labels = [0] * 20 + [1] * 20
    scores = [i / 100 for i in range(20)] + [0.8 + i / 100 for i in range(20)]

    controls = negative_controls(labels, scores, n_permutations=200, seed=5)

    assert controls["noise_auc_mean"] < 0.58
    assert controls["score_permutation_auc_mean"] < 0.58
    assert controls["label_permutation_auc_mean"] < 0.58
