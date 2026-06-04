#!/usr/bin/env python3
"""NASA C-MAPSS metric-blind leakage benchmark for LAMP.

This run treats near-failure prediction on FD001 as a hidden-degradation audit:
the valid monitor uses only current-cycle operational/sensor features, while
oracle mixtures inject true remaining-useful-life information at controlled
small doses.
"""

from __future__ import annotations

import csv
import io
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from lamp.audit import LAMP_Audit


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "cmapss"
OUT_DIR = ROOT / "results" / "cmapss_lamp"
SOURCE_URL = "https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
SEED = 20260531
HORIZON_CYCLES = 120
MAX_ROWS_PER_ENGINE = 80
LAMBDAS = [0.0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10]
AUC_DELTA_ALERT = 0.01
MI_BOOTSTRAPS = 300
MI_ALPHA = 0.05


COLUMNS = (
    ["unit", "cycle"]
    + [f"setting_{idx}" for idx in range(1, 4)]
    + [f"sensor_{idx}" for idx in range(1, 22)]
)
FEATURE_COLUMNS = [f"setting_{idx}" for idx in range(1, 4)] + [
    f"sensor_{idx}" for idx in range(1, 22)
]
MATCH_COLUMNS = ["cycle_frac", "setting_1", "setting_2", "sensor_2", "sensor_3", "sensor_4"]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset_dir = ensure_cmapss_data()
    train = load_fd001_train(dataset_dir)
    examples = build_examples(train)
    train_units, holdout_units = train_test_split(
        sorted(examples["unit"].unique()),
        test_size=0.30,
        random_state=SEED,
    )
    train_df = examples[examples["unit"].isin(train_units)].copy()
    holdout_df = examples[examples["unit"].isin(holdout_units)].copy()

    valid_model = make_pipeline(
        StandardScaler(),
        HistGradientBoostingClassifier(max_iter=180, learning_rate=0.045, random_state=SEED),
    )
    valid_model.fit(train_df[FEATURE_COLUMNS], train_df["label"])
    holdout_df["valid_score"] = valid_model.predict_proba(holdout_df[FEATURE_COLUMNS])[:, 1]

    rf_model = RandomForestClassifier(
        n_estimators=240,
        min_samples_leaf=8,
        n_jobs=-1,
        random_state=SEED,
    )
    rf_model.fit(train_df[FEATURE_COLUMNS], train_df["label"])
    holdout_df["rf_valid_score"] = rf_model.predict_proba(holdout_df[FEATURE_COLUMNS])[:, 1]

    leaky_cols = FEATURE_COLUMNS + ["future_sensor_mean", "future_sensor_slope", "oracle_rul_score"]
    leaky_model = make_pipeline(
        StandardScaler(),
        HistGradientBoostingClassifier(max_iter=180, learning_rate=0.045, random_state=SEED + 1),
    )
    leaky_model.fit(train_df[leaky_cols], train_df["label"])
    holdout_df["future_rul_leaky_score"] = leaky_model.predict_proba(holdout_df[leaky_cols])[:, 1]

    for lam in LAMBDAS:
        holdout_df[lambda_column(lam)] = (
            (1.0 - lam) * holdout_df["valid_score"] + lam * holdout_df["oracle_rul_score"]
        )

    rows = dataframe_to_lamp_rows(holdout_df)
    table_columns = list(rows[0])
    audit_rows = run_lamp_grid(rows, table_columns)
    write_summary_csv(audit_rows)
    write_report(audit_rows, train_df, holdout_df)
    write_figure(audit_rows)
    print(OUT_DIR / "cmapss_lamp_report.md")
    return 0


def ensure_cmapss_data() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    marker = DATA_DIR / "train_FD001.txt"
    if marker.exists():
        return DATA_DIR

    print(f"Downloading NASA C-MAPSS data from {SOURCE_URL}")
    with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        archive.extractall(DATA_DIR)

    for nested_zip in list(DATA_DIR.rglob("*.zip")):
        with zipfile.ZipFile(nested_zip) as archive:
            archive.extractall(nested_zip.parent)

    nested = next(DATA_DIR.rglob("train_FD001.txt"), None)
    if nested is None:
        raise FileNotFoundError("Could not find train_FD001.txt after extracting C-MAPSS ZIP")
    if nested.parent != DATA_DIR:
        for path in nested.parent.iterdir():
            if path.is_file():
                path.replace(DATA_DIR / path.name)
    return DATA_DIR


def load_fd001_train(dataset_dir: Path) -> pd.DataFrame:
    path = dataset_dir / "train_FD001.txt"
    frame = pd.read_csv(path, sep=r"\s+", header=None, names=COLUMNS)
    max_cycle = frame.groupby("unit")["cycle"].transform("max")
    frame["rul"] = max_cycle - frame["cycle"]
    frame["cycle_frac"] = frame["cycle"] / max_cycle
    frame["label"] = (frame["rul"] <= HORIZON_CYCLES).astype(int)
    frame["oracle_rul_score"] = frame["label"].astype(float)
    return frame


def build_examples(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, engine in frame.groupby("unit", sort=True):
        engine = engine.sort_values("cycle").copy()
        if len(engine) > MAX_ROWS_PER_ENGINE:
            keep_idx = np.linspace(0, len(engine) - 1, MAX_ROWS_PER_ENGINE).round().astype(int)
            engine = engine.iloc[sorted(set(keep_idx))].copy()

        future_mean = []
        future_slope = []
        sensor_mean = engine[["sensor_2", "sensor_3", "sensor_4", "sensor_11", "sensor_15"]].mean(axis=1)
        values = sensor_mean.to_numpy()
        for idx in range(len(engine)):
            lo = min(idx + 1, len(engine) - 1)
            hi = min(idx + 11, len(engine))
            future = values[lo:hi]
            if len(future) == 0:
                future = values[idx : idx + 1]
            future_mean.append(float(np.mean(future)))
            future_slope.append(float(future[-1] - values[idx]))
        engine["future_sensor_mean"] = future_mean
        engine["future_sensor_slope"] = future_slope
        rows.append(engine)
    return pd.concat(rows, ignore_index=True)


def run_lamp_grid(rows: list[dict[str, Any]], table_columns: list[str]) -> list[dict[str, Any]]:
    audit_rows = []
    baseline_auc = None
    labels = np.array([int(row["label"]) for row in rows], dtype=int)
    valid_scores = np.array([float(row["valid_score"]) for row in rows], dtype=float)

    monitor_specs = [
        ("valid_hgb", "valid_score", 0.0, "valid current-cycle degradation monitor"),
        ("rf_valid", "rf_valid_score", 0.0, "random forest current-cycle monitor"),
        ("future_rul_leaky", "future_rul_leaky_score", None, "future/RUL contaminated comparator"),
    ]
    monitor_specs += [
        (f"oracle_mix_{lambda_slug(lam)}", lambda_column(lam), lam, "low-dose oracle RUL mixture")
        for lam in LAMBDAS
    ]

    for monitor_id, score_col, lam, monitor_type in monitor_specs:
        result = LAMP_Audit(
            config=build_config(score_col, monitor_id, monitor_type, lam),
            rows=rows,
            table_columns=table_columns,
        ).run(OUT_DIR / "lamp" / monitor_id)

        auc = result["primary_score"]["auc"]
        if score_col == "valid_score":
            baseline_auc = auc
        if baseline_auc is None:
            baseline_auc = roc_auc_from_rows(rows, "label", "valid_score")

        mi = None
        if monitor_id == "valid_hgb" or monitor_id.startswith("oracle_mix_"):
            scores = np.array([float(row[score_col]) for row in rows], dtype=float)
            mi = incremental_mi_bootstrap(
                valid_scores=valid_scores,
                candidate_scores=scores,
                labels=labels,
                seed=SEED + len(audit_rows),
            )
        dossier = result["failure_mode_dossier"]
        relations = result["sentinel_relations"].get("oracle_label", {})
        temporal = result["temporal_isolation"]
        forbidden = result["forbidden_feature_screen"]
        auc_delta = auc - baseline_auc
        audit_rows.append(
            {
                "monitor_id": monitor_id,
                "monitor_type": monitor_type,
                "lambda": "" if lam is None else lam,
                "score_column": score_col,
                "auc": auc,
                "delta_auc_vs_valid": auc_delta,
                "auc_delta_alert_0p01": abs(auc_delta) >= AUC_DELTA_ALERT,
                "audit_pass": dossier["audit_pass_candidate"],
                "temporal_passed": temporal["passed"],
                "forbidden_passed": forbidden["passed"],
                "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
                "oracle_proximity": relations.get("auc_leakage_proximity"),
                "oracle_proximity_alert": relations.get("oracle_proximity_alert"),
                "valid_score_mi_nats": None if mi is None else mi["valid_mi"],
                "candidate_score_mi_nats": None if mi is None else mi["candidate_mi"],
                "incremental_mi_nats": None if mi is None else mi["delta_mi"],
                "incremental_mi_ci_low": None if mi is None else mi["ci_low"],
                "incremental_mi_ci_high": None if mi is None else mi["ci_high"],
                "incremental_mi_p_value": None if mi is None else mi["p_value"],
                "incremental_mi_significant": None if mi is None else mi["significant"],
                "output_classes": ";".join(dossier["output_classes"]),
            }
        )
    return audit_rows


def build_config(score_col: str, monitor_id: str, monitor_type: str, lam: float | None) -> dict[str, Any]:
    valid_features = FEATURE_COLUMNS.copy()
    temporal_features = [{"name": col, "latest_offset_h": 0} for col in FEATURE_COLUMNS]

    if lam is not None and lam > 0:
        valid_features.append("oracle_rul_score")
        temporal_features.append({"name": "oracle_rul_score", "latest_offset_h": 999})
    if score_col == "future_rul_leaky_score":
        valid_features.extend(["future_sensor_mean", "future_sensor_slope", "oracle_rul_score"])
        temporal_features.extend(
            [
                {"name": "future_sensor_mean", "latest_offset_h": 10},
                {"name": "future_sensor_slope", "latest_offset_h": 10},
                {"name": "oracle_rul_score", "latest_offset_h": 999},
            ]
        )

    return {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"NASA C-MAPSS FD001: {monitor_id}",
            "task": f"near-failure within {HORIZON_CYCLES} cycles",
            "role": "physical degradation benchmark",
            "monitor_type": monitor_type,
        },
        "columns": {
            "subject_id": "row_id",
            "label": "label",
            "positive_value": 1,
            "score": score_col,
            "anchor_time": "cycle",
        },
        "temporal_isolation": {
            "anchor": "cycle",
            "valid_features_must_be": "at_or_before_anchor",
            "frozen_before_holdout": [
                "FD001 engine-level split",
                "near-failure horizon",
                "valid current-cycle feature set",
                "oracle mixture grid",
                "LAMP thresholds",
            ],
            "valid_score_features": temporal_features,
        },
        "forbidden_features": {
            "columns": ["oracle_rul_score", "future_sensor_mean", "future_sensor_slope"],
            "valid_score_features": valid_features,
        },
        "sentinels": {
            "future_physiology": {
                "column": "future_sensor_mean",
                "role": "future_physiology",
                "expected_signature": "post-anchor sensor trajectory comparator",
            },
            "future_physiology_slope": {
                "column": "future_sensor_slope",
                "role": "future_physiology",
                "expected_signature": "post-anchor sensor trajectory slope comparator",
            },
            "oracle_label": {
                "column": "oracle_rul_score",
                "role": "oracle_label",
                "expected_signature": "true remaining-useful-life derived comparator",
            },
        },
        "leakage_proximity": {
            "baseline_score": score_col if monitor_id in {"valid_hgb", "rf_valid"} else "valid_score",
            "oracle_proximity_alert_min": 0.01,
        },
        "negative_controls": {
            "n_permutations": 100,
            "seed": 43,
        },
        "visible_state_matching": {
            "columns": MATCH_COLUMNS,
            "n_bins": 3,
            "min_bin_size": 20,
        },
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.015,
            "matched_collapse_max": 0.005,
            "score_thresholds": [0.25, 0.50, 0.75],
        },
    }


def dataframe_to_lamp_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    keep = [
        "unit",
        "cycle",
        "cycle_frac",
        "label",
        "valid_score",
        "rf_valid_score",
        "future_rul_leaky_score",
        "oracle_rul_score",
        "future_sensor_mean",
        "future_sensor_slope",
    ] + FEATURE_COLUMNS + [lambda_column(lam) for lam in LAMBDAS]
    rows = []
    for idx, row in frame[keep].reset_index(drop=True).iterrows():
        out = {"row_id": f"FD001_{int(row['unit']):03d}_{int(row['cycle']):04d}"}
        for col in keep:
            value = row[col]
            if col in {"unit", "cycle", "label"}:
                out[col] = int(value)
            elif isinstance(value, (np.integer, int)):
                out[col] = int(value)
            else:
                out[col] = float(value)
        rows.append(out)
    return rows


def write_summary_csv(rows: list[dict[str, Any]]) -> None:
    with (OUT_DIR / "cmapss_lamp_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(audit_rows: list[dict[str, Any]], train_df: pd.DataFrame, holdout_df: pd.DataFrame) -> None:
    valid = next(row for row in audit_rows if row["score_column"] == "valid_score")
    first_blind = next(
        row
        for row in audit_rows
        if isinstance(row["lambda"], float) and row["lambda"] > 0 and not row["auc_delta_alert_0p01"]
    )
    lines = [
        "# NASA C-MAPSS LAMP Benchmark",
        "",
        "This benchmark applies LAMP to NASA C-MAPSS FD001 as a physical",
        "hidden-degradation task. The valid monitor predicts whether an engine is",
        f"within {HORIZON_CYCLES} cycles of failure using only current-cycle",
        "operational and sensor channels. Oracle mixtures inject true RUL-derived",
        "information at controlled low doses.",
        "",
        "## Dataset",
        "",
        f"- Source: NASA Prognostics Center of Excellence C-MAPSS turbofan simulation",
        f"- Train examples: {len(train_df)} rows across {train_df['unit'].nunique()} engines",
        f"- Held-out examples: {len(holdout_df)} rows across {holdout_df['unit'].nunique()} engines",
        f"- Positive label: RUL <= {HORIZON_CYCLES} cycles",
        "",
        "## Key Result",
        "",
        (
            f"Valid current-cycle AUC is {valid['auc']:.4f}. At lambda={first_blind['lambda']:.3g}, "
            f"AUC is {first_blind['auc']:.4f} (delta={first_blind['delta_auc_vs_valid']:.4f}), "
            f"below the {AUC_DELTA_ALERT:.2f} AUC-delta alert. The incremental MI test is also "
            f"not significant at alpha={MI_ALPHA:.2f} (delta MI={first_blind['incremental_mi_nats']:.4f} "
            f"nats, 95% CI {first_blind['incremental_mi_ci_low']:.4f} to "
            f"{first_blind['incremental_mi_ci_high']:.4f}, p={first_blind['incremental_mi_p_value']:.3f}). "
            "LAMP still rejects the monitor because the score now violates the declared RUL information boundary."
        ),
        "",
        "This is metric-blind leakage in a physically interpretable degradation system:",
        "standard discrimination barely moves, but the validity claim has already changed.",
        "",
        "## Audit Summary",
        "",
        "| monitor | lambda | AUC | delta AUC | AUC alert | delta MI | MI p | MI sig | LAMP pass | temporal | forbidden | oracle proximity | oracle alert |",
        "|---|---:|---:|---:|:---:|---:|---:|:---:|:---:|:---:|:---:|---:|:---:|",
    ]
    for row in audit_rows:
        lam = row["lambda"] if row["lambda"] != "" else "NA"
        lines.append(
            "| "
            f"{row['monitor_id']} | {lam} | {row['auc']:.4f} | "
            f"{row['delta_auc_vs_valid']:.4f} | {bool(row['auc_delta_alert_0p01'])} | "
            f"{format_optional(row['incremental_mi_nats'])} | {format_optional(row['incremental_mi_p_value'])} | "
            f"{format_bool_optional(row['incremental_mi_significant'])} | "
            f"{bool(row['audit_pass'])} | {bool(row['temporal_passed'])} | "
            f"{bool(row['forbidden_passed'])} | {format_optional(row['oracle_proximity'])} | "
            f"{bool(row['oracle_proximity_alert'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "C-MAPSS makes the information contract physically legible: RUL is a verified",
            "run-to-failure quantity, while current-cycle sensors are the allowed monitor",
            "view. A low-dose RUL oracle can leave AUC and incremental-MI screens below",
            "conventional significance while still invalidating the hidden-degradation claim.",
            "",
            "![C-MAPSS metric-blind leakage curve](cmapss_metric_blind_leakage_curve.png)",
            "",
        ]
    )
    (OUT_DIR / "cmapss_lamp_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_figure(rows: list[dict[str, Any]]) -> None:
    mixes = [row for row in rows if isinstance(row["lambda"], float)]
    lambdas = [row["lambda"] for row in mixes]
    aucs = [row["auc"] for row in mixes]
    flags = [row["auc_delta_alert_0p01"] for row in mixes]
    passes = [row["audit_pass"] for row in mixes]

    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=180)
    ax.plot(lambdas, aucs, color="black", linewidth=1.8, marker="o")
    for lam, auc, metric_flag, passed in zip(lambdas, aucs, flags, passes):
        if passed:
            ax.scatter([lam], [auc], marker="s", s=70, edgecolor="black", facecolor="white", zorder=3)
        elif metric_flag:
            ax.scatter([lam], [auc], marker="o", s=70, edgecolor="black", facecolor="black", zorder=3)
        else:
            ax.scatter([lam], [auc], marker="x", s=70, color="black", zorder=3)
    ax.axhline(aucs[0] + AUC_DELTA_ALERT, color="black", linestyle=":", linewidth=1.0)
    ax.text(max(lambdas), aucs[0] + AUC_DELTA_ALERT + 0.001, "AUC + 0.01", ha="right", va="bottom", fontsize=9)
    ax.set_xlabel("Oracle RUL leakage dose (lambda)")
    ax.set_ylabel("ROC AUC")
    ax.set_title("C-MAPSS: metric-blind RUL leakage")
    ax.grid(axis="y", color="0.85", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "cmapss_metric_blind_leakage_curve.png")
    plt.close(fig)


def roc_auc_from_rows(rows: list[dict[str, Any]], label_col: str, score_col: str) -> float:
    labels = [int(row[label_col]) for row in rows]
    scores = [float(row[score_col]) for row in rows]
    return float(roc_auc_score(labels, scores))


def incremental_mi_bootstrap(
    valid_scores: np.ndarray,
    candidate_scores: np.ndarray,
    labels: np.ndarray,
    seed: int,
) -> dict[str, Any]:
    valid_mi = binned_mutual_information(valid_scores, labels)
    candidate_mi = binned_mutual_information(candidate_scores, labels)
    delta = candidate_mi - valid_mi
    if np.allclose(candidate_scores, valid_scores):
        return {
            "valid_mi": valid_mi,
            "candidate_mi": candidate_mi,
            "delta_mi": 0.0,
            "ci_low": 0.0,
            "ci_high": 0.0,
            "p_value": 1.0,
            "significant": False,
        }

    rng = np.random.default_rng(seed)
    boot = []
    n = len(labels)
    for _ in range(MI_BOOTSTRAPS):
        idx = rng.integers(0, n, n)
        boot.append(
            binned_mutual_information(candidate_scores[idx], labels[idx])
            - binned_mutual_information(valid_scores[idx], labels[idx])
        )
    boot_arr = np.array(boot)
    p_value = float((np.sum(boot_arr <= 0.0) + 1) / (len(boot_arr) + 1))
    return {
        "valid_mi": valid_mi,
        "candidate_mi": candidate_mi,
        "delta_mi": float(delta),
        "ci_low": float(np.quantile(boot_arr, 0.025)),
        "ci_high": float(np.quantile(boot_arr, 0.975)),
        "p_value": p_value,
        "significant": bool(p_value < MI_ALPHA),
    }


def binned_mutual_information(scores: np.ndarray, labels: np.ndarray, bins: int = 20) -> float:
    edges = np.unique(np.quantile(scores, np.linspace(0.0, 1.0, bins + 1)))
    if len(edges) <= 2:
        return 0.0
    score_bins = np.digitize(scores, edges[1:-1], right=True)
    mi = 0.0
    for score_bin in np.unique(score_bins):
        p_x = float(np.mean(score_bins == score_bin))
        for label in (0, 1):
            p_y = float(np.mean(labels == label))
            p_xy = float(np.mean((score_bins == score_bin) & (labels == label)))
            if p_x > 0.0 and p_y > 0.0 and p_xy > 0.0:
                mi += p_xy * np.log(p_xy / (p_x * p_y))
    return float(mi)


def lambda_column(lam: float) -> str:
    return f"oracle_mix_l{lambda_slug(lam)}"


def lambda_slug(lam: float) -> str:
    return str(lam).replace(".", "p")


def format_optional(value: Any) -> str:
    if value is None or value == "":
        return "NA"
    return f"{float(value):.4f}"


def format_bool_optional(value: Any) -> str:
    if value is None or value == "":
        return "NA"
    return str(bool(value))


if __name__ == "__main__":
    raise SystemExit(main())
