import numpy as np
import pandas as pd

from external_benchmarks.physionet2019_pipeline import (
    choose_anchors,
    early_feature_columns,
    oracle_sentinel,
    sequence_matrix,
)


def test_choose_anchors_positive_and_negative():
    anchors = choose_anchors(
        n_rows=40,
        onset_idx=24,
        horizon_h=6,
        early_window_h=8,
        negative_gap_h=6,
    )

    assert (18, "event_horizon_positive") in anchors
    assert (12, "pre_event_negative") in anchors


def test_oracle_sentinel_only_inside_horizon():
    assert oracle_sentinel(onset_idx=12, anchor_idx=8, horizon_h=6) > 0
    assert oracle_sentinel(onset_idx=20, anchor_idx=8, horizon_h=6) == 0
    assert oracle_sentinel(onset_idx=None, anchor_idx=8, horizon_h=6) == 0


def test_feature_columns_drop_future_and_all_missing():
    frame = pd.DataFrame(
        {
            "HR_early_mean": [80.0, 90.0],
            "future_HR_mean": [100.0, 110.0],
            "all_missing_early_slope": [np.nan, np.nan],
            "label_future_sepsis": [0, 1],
        }
    )

    assert early_feature_columns(frame) == ["HR_early_mean"]


def test_sequence_matrix_keeps_requested_shape():
    frame = pd.DataFrame({"HR": [80, 81], "O2Sat": [98, 97]})
    matrix = sequence_matrix(frame, ["HR", "O2Sat", "Resp"])

    assert matrix.shape == (2, 3)
    assert np.isnan(matrix[:, 2]).all()
