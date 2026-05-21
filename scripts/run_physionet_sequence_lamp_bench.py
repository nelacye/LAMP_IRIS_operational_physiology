#!/usr/bin/env python3
"""Run raw-PSV PhysioNet/CinC 2019 sequence monitors through LAMP.

This script builds early-window examples directly from `.psv` files, trains
valid and intentionally contaminated monitors, and audits the resulting
prediction table. PyTorch is required for the LSTM/GRU/Transformer branches;
the hand-crafted MLP probes run with the base LAMP dependencies.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from external_benchmarks.physionet2019_pipeline import (  # noqa: E402
    ExampleConfig,
    VISIBLE_MATCH_COLUMNS,
    build_examples_from_files,
    discover_psv_files,
    early_feature_columns,
    future_feature_columns,
)
from lamp.audit import run_audit  # noqa: E402


DEFAULT_DATA_ROOT = ROOT / "real_data/physionet/challenge-2019/training"
DEFAULT_OUT = ROOT / "results/physionet_sequence_lamp"
SEED = 2026
RAW_SEQUENCE_MATCH_COLUMNS = [
    "Age",
    "HR_early_last",
    "O2Sat_early_last",
    "early_missing_rate",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-patients", type=int, default=3000)
    parser.add_argument("--sets", default="A,B")
    parser.add_argument("--horizons", default="6,12,18")
    parser.add_argument("--early-window", type=int, default=12)
    parser.add_argument("--negative-gap", type=int, default=6)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--leakage-lambdas", default="0.01,0.05,0.10")
    parser.add_argument("--skip-neural", action="store_true")
    parser.add_argument("--skip-xgboost", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    horizons = tuple(int(x.strip()) for x in args.horizons.split(",") if x.strip())
    include_sets = tuple(x.strip().upper() for x in args.sets.split(",") if x.strip())
    config = ExampleConfig(
        horizons=horizons,
        early_window_h=args.early_window,
        negative_gap_h=args.negative_gap,
        max_patients=args.max_patients,
        include_sets=include_sets,
        seed=SEED,
    )

    cache_dir = args.out / "cache"
    table, valid_sequences, leaky_sequences = load_or_build_examples(
        data_root=args.data_root,
        cache_dir=cache_dir,
        config=config,
        force=args.force,
    )
    if table.empty:
        raise RuntimeError("No sequence examples were built from the raw PSV files.")

    early_cols = early_feature_columns(table)
    future_cols = future_feature_columns(table)
    match_cols = [col for col in RAW_SEQUENCE_MATCH_COLUMNS if col in table.columns]
    split_ids = patient_split(table, seed=SEED)

    all_prediction_frames = []
    metrics = []
    monitor_specs = []
    torch_status = torch_import_status()
    xgboost_status = xgboost_import_status(skip=args.skip_xgboost)
    leakage_lambdas = tuple(
        float(x.strip()) for x in args.leakage_lambdas.split(",") if x.strip()
    )

    for horizon in horizons:
        horizon_table = table[table["horizon_h"] == horizon].reset_index(drop=True)
        if horizon_table.empty:
            continue
        train_mask = horizon_table["patient_id"].isin(split_ids["train"]).to_numpy()
        test_mask = horizon_table["patient_id"].isin(split_ids["test"]).to_numpy()
        if not train_mask.any() or not test_mask.any():
            continue

        y_train = horizon_table.loc[train_mask, "label_future_sepsis"].astype(int).to_numpy()
        y_test = horizon_table.loc[test_mask, "label_future_sepsis"].astype(int).to_numpy()
        if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
            continue
        early_cols_h = usable_columns(horizon_table, early_cols, train_mask)
        future_cols_h = usable_columns(horizon_table, future_cols, train_mask)

        prediction_frame = base_prediction_frame(horizon_table.loc[test_mask].copy(), match_cols)
        weights = compute_sample_weight("balanced", y_train)

        mlp_valid = fit_sklearn_mlp(
            horizon_table.loc[train_mask, early_cols_h],
            y_train,
            sample_weight=weights,
            seed=SEED + horizon,
        )
        prediction_frame["mlp_probe_valid_score"] = predict_proba(
            mlp_valid,
            horizon_table.loc[test_mask, early_cols_h],
        )
        metrics.append(metric_row(horizon, "mlp_probe_valid_score", y_test, prediction_frame))
        monitor_specs.append(
            {
                "name": "MLP hand-crafted valid",
                "score": "mlp_probe_valid_score",
                "family": "MLP probe",
                "type": "valid",
                "leakage_level": "none",
                "feature_role": "early",
            }
        )

        leaky_cols = early_cols_h + future_cols_h + ["oracle_label_sentinel_score"]
        mlp_leaky = fit_sklearn_mlp(
            horizon_table.loc[train_mask, leaky_cols],
            y_train,
            sample_weight=weights,
            seed=SEED + horizon + 101,
        )
        prediction_frame["mlp_probe_leaky_score"] = predict_proba(
            mlp_leaky,
            horizon_table.loc[test_mask, leaky_cols],
        )
        prediction_frame["mlp_lowdose_oracle_score"] = mix_scores(
            prediction_frame["mlp_probe_valid_score"].to_numpy(),
            prediction_frame["oracle_label_sentinel_score"].to_numpy(),
            leakage_lambda=0.05,
        )
        metrics.append(metric_row(horizon, "mlp_probe_leaky_score", y_test, prediction_frame))
        add_oracle_mixtures(
            prediction_frame=prediction_frame,
            metrics=metrics,
            monitor_specs=monitor_specs,
            horizon=horizon,
            y_test=y_test,
            base_score="mlp_probe_valid_score",
            family="mlp_probe",
            leakage_lambdas=leakage_lambdas,
        )
        prediction_frame["oracle_leakage_ceiling_score"] = prediction_frame[
            "oracle_label_sentinel_score"
        ]
        metrics.append(
            metric_row(horizon, "oracle_leakage_ceiling_score", y_test, prediction_frame)
        )
        monitor_specs.extend(
            [
                {
                    "name": "MLP hand-crafted leaky",
                    "score": "mlp_probe_leaky_score",
                    "family": "MLP probe",
                    "type": "leaky",
                    "leakage_level": "future+oracle",
                    "feature_role": "future_oracle",
                    "baseline": "mlp_probe_valid_score",
                },
                {
                    "name": "Oracle label leakage ceiling",
                    "score": "oracle_leakage_ceiling_score",
                    "family": "oracle",
                    "type": "oracle",
                    "leakage_level": "oracle",
                    "feature_role": "oracle_mixture",
                },
            ]
        )

        classic_rows = run_classical_family(
            horizon=horizon,
            horizon_table=horizon_table,
            train_mask=train_mask,
            test_mask=test_mask,
            early_cols=early_cols_h,
            leaky_cols=leaky_cols,
            y_train=y_train,
            y_test=y_test,
            sample_weight=weights,
            prediction_frame=prediction_frame,
            leakage_lambdas=leakage_lambdas,
            xgboost_status=xgboost_status,
            seed=SEED + horizon,
        )
        metrics.extend(classic_rows["metrics"])
        monitor_specs.extend(classic_rows["monitor_specs"])

        if not args.skip_neural and torch_status["available"]:
            neural_rows = run_neural_family(
                horizon=horizon,
                valid_sequences=valid_sequences[horizon],
                leaky_sequences=leaky_sequences[horizon],
                train_mask=train_mask,
                test_mask=test_mask,
                y_train=y_train,
                y_test=y_test,
                prediction_frame=prediction_frame,
                epochs=args.epochs,
                batch_size=args.batch_size,
                hidden_dim=args.hidden_dim,
                leakage_lambdas=leakage_lambdas,
                seed=SEED + horizon,
            )
            metrics.extend(neural_rows["metrics"])
            monitor_specs.extend(neural_rows["monitor_specs"])

        all_prediction_frames.append(prediction_frame)

    predictions = pd.concat(all_prediction_frames, ignore_index=True)
    predictions_path = args.out / "physionet_sequence_predictions.csv"
    predictions.to_csv(predictions_path, index=False, lineterminator="\n")

    monitor_specs = unique_monitor_specs(monitor_specs)
    lamp_rows = run_lamp_audits(
        predictions=predictions,
        out_dir=args.out,
        monitor_specs=monitor_specs,
        match_cols=match_cols,
    )
    write_report(
        path=args.out / "physionet_sequence_lamp_report.md",
        args=args,
        table=table,
        predictions=predictions,
        metrics=metrics,
        lamp_rows=lamp_rows,
        torch_status=torch_status,
        xgboost_status=xgboost_status,
    )
    (args.out / "physionet_sequence_metrics.csv").write_text(
        pd.DataFrame(metrics).to_csv(index=False, lineterminator="\n"),
        encoding="utf-8",
    )
    (args.out / "physionet_sequence_lamp_summary.csv").write_text(
        pd.DataFrame(lamp_rows).to_csv(index=False, lineterminator="\n"),
        encoding="utf-8",
    )
    (args.out / "model_registry.csv").write_text(
        pd.DataFrame(monitor_specs).to_csv(index=False, lineterminator="\n"),
        encoding="utf-8",
    )
    print(json.dumps({"out": str(args.out), "n_predictions": len(predictions)}, indent=2))
    return 0


def load_or_build_examples(
    data_root: Path,
    cache_dir: Path,
    config: ExampleConfig,
    force: bool,
) -> tuple[pd.DataFrame, dict[int, np.ndarray], dict[int, np.ndarray]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    table_path = cache_dir / "examples.csv"
    arrays_path = cache_dir / "sequence_arrays.npz"
    manifest_path = cache_dir / "manifest.json"

    if not force and table_path.exists() and arrays_path.exists() and cache_matches(manifest_path, config):
        table = pd.read_csv(table_path)
        arrays = np.load(arrays_path)
        valid = {int(key.removeprefix("valid_h")): arrays[key] for key in arrays.files if key.startswith("valid_h")}
        leaky = {int(key.removeprefix("leaky_h")): arrays[key] for key in arrays.files if key.startswith("leaky_h")}
        return table, valid, leaky

    paths = discover_psv_files(
        data_root,
        include_sets=config.include_sets,
        max_patients=config.max_patients,
        seed=config.seed,
    )
    if not paths:
        raise FileNotFoundError(f"No .psv files found under {data_root}")

    table, valid, leaky = build_examples_from_files(paths, config)
    table.to_csv(table_path, index=False)
    np.savez_compressed(
        arrays_path,
        **{f"valid_h{h}": array for h, array in valid.items()},
        **{f"leaky_h{h}": array for h, array in leaky.items()},
    )
    manifest_path.write_text(
        json.dumps(
            {
                "n_source_files": len(paths),
                "n_examples": len(table),
                "horizons": list(config.horizons),
                "early_window_h": config.early_window_h,
                "max_patients": config.max_patients,
                "include_sets": list(config.include_sets),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return table, valid, leaky


def cache_matches(manifest_path: Path, config: ExampleConfig) -> bool:
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        tuple(manifest.get("horizons", [])) == tuple(config.horizons)
        and int(manifest.get("early_window_h", -1)) == config.early_window_h
        and int(manifest.get("max_patients", -1)) == config.max_patients
        and tuple(manifest.get("include_sets", [])) == tuple(config.include_sets)
    )


def patient_split(table: pd.DataFrame, seed: int) -> dict[str, set[str]]:
    patient_labels = (
        table.groupby("patient_id")["label_future_sepsis"].max().rename("label").reset_index()
    )
    stratify = patient_labels["label"] if patient_labels["label"].nunique() == 2 else None
    train, test = train_test_split(
        patient_labels["patient_id"],
        test_size=0.35,
        random_state=seed,
        stratify=stratify,
    )
    return {"train": set(train), "test": set(test)}


def usable_columns(frame: pd.DataFrame, columns: list[str], train_mask: np.ndarray) -> list[str]:
    return [column for column in columns if frame.loc[train_mask, column].notna().any()]


def base_prediction_frame(frame: pd.DataFrame, match_cols: list[str]) -> pd.DataFrame:
    keep = [
        "patient_id",
        "source_set",
        "horizon_h",
        "anchor_idx",
        "label_future_sepsis",
        "sepsis_onset_idx",
        "hours_to_onset",
        "future_physiology_sentinel_score",
        "oracle_label_sentinel_score",
    ]
    keep.extend(col for col in match_cols if col not in keep)
    return frame[keep].copy()


def fit_sklearn_mlp(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    sample_weight: np.ndarray,
    seed: int,
):
    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        MLPClassifier(
            hidden_layer_sizes=(48, 24),
            activation="relu",
            alpha=0.001,
            learning_rate_init=0.002,
            max_iter=350,
            early_stopping=True,
            random_state=seed,
        ),
    )
    try:
        model.fit(x_train, y_train, mlpclassifier__sample_weight=sample_weight)
    except TypeError:
        model.fit(x_train, y_train)
    return model


def predict_proba(model: Any, x: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(x)[:, 1]


def mix_scores(valid: np.ndarray, oracle: np.ndarray, leakage_lambda: float) -> np.ndarray:
    mixed = (1.0 - leakage_lambda) * valid + leakage_lambda * oracle
    return np.clip(mixed, 0.0, 1.0)


def add_oracle_mixtures(
    prediction_frame: pd.DataFrame,
    metrics: list[dict[str, Any]],
    monitor_specs: list[dict[str, Any]],
    horizon: int,
    y_test: np.ndarray,
    base_score: str,
    family: str,
    leakage_lambdas: tuple[float, ...],
) -> None:
    for leakage_lambda in leakage_lambdas:
        label = leakage_label(leakage_lambda)
        column = f"{base_score}_oracle_mix_{label}"
        prediction_frame[column] = mix_scores(
            prediction_frame[base_score].to_numpy(),
            prediction_frame["oracle_label_sentinel_score"].to_numpy(),
            leakage_lambda=leakage_lambda,
        )
        metrics.append(metric_row(horizon, column, y_test, prediction_frame))
        monitor_specs.append(
            {
                "name": f"{family} oracle mix {label}",
                "score": column,
                "family": family,
                "type": "low-dose leakage",
                "leakage_level": label,
                "leakage_lambda": leakage_lambda,
                "feature_role": "oracle_mixture",
                "baseline": base_score,
            }
        )


def leakage_label(value: float) -> str:
    pct = value * 100
    if pct < 1:
        return f"{pct:.1f}pct".replace(".", "p")
    return f"{pct:.0f}pct"


def run_classical_family(
    horizon: int,
    horizon_table: pd.DataFrame,
    train_mask: np.ndarray,
    test_mask: np.ndarray,
    early_cols: list[str],
    leaky_cols: list[str],
    y_train: np.ndarray,
    y_test: np.ndarray,
    sample_weight: np.ndarray,
    prediction_frame: pd.DataFrame,
    leakage_lambdas: tuple[float, ...],
    xgboost_status: dict[str, Any],
    seed: int,
) -> dict[str, list[dict[str, Any]]]:
    metrics: list[dict[str, Any]] = []
    monitor_specs: list[dict[str, Any]] = []

    families: list[tuple[str, Any, str]] = [
        (
            "rf",
            RandomForestClassifier(
                n_estimators=180,
                min_samples_leaf=8,
                max_features="sqrt",
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=seed,
            ),
            "Random Forest",
        ),
        (
            "histgb",
            HistGradientBoostingClassifier(
                max_iter=180,
                learning_rate=0.04,
                l2_regularization=0.01,
                max_leaf_nodes=24,
                random_state=seed,
            ),
            "HistGradientBoosting",
        ),
    ]
    if xgboost_status["available"]:
        families.append(("xgb", make_xgboost_classifier(y_train, seed), "XGBoost"))

    for prefix, estimator, display in families:
        valid_col = f"{prefix}_valid_score"
        leaky_col = f"{prefix}_future_leaky_score"

        valid_model = make_feature_pipeline(estimator)
        fit_feature_model(valid_model, horizon_table.loc[train_mask, early_cols], y_train, sample_weight)
        prediction_frame[valid_col] = predict_proba(valid_model, horizon_table.loc[test_mask, early_cols])
        metrics.append(metric_row(horizon, valid_col, y_test, prediction_frame))
        monitor_specs.append(
            {
                "name": f"{display} valid",
                "score": valid_col,
                "family": display,
                "type": "valid",
                "leakage_level": "none",
                "feature_role": "early",
            }
        )
        add_oracle_mixtures(
            prediction_frame=prediction_frame,
            metrics=metrics,
            monitor_specs=monitor_specs,
            horizon=horizon,
            y_test=y_test,
            base_score=valid_col,
            family=display,
            leakage_lambdas=leakage_lambdas,
        )

        leaky_model = make_feature_pipeline(clone_estimator(estimator, seed + 17))
        fit_feature_model(leaky_model, horizon_table.loc[train_mask, leaky_cols], y_train, sample_weight)
        prediction_frame[leaky_col] = predict_proba(leaky_model, horizon_table.loc[test_mask, leaky_cols])
        metrics.append(metric_row(horizon, leaky_col, y_test, prediction_frame))
        monitor_specs.append(
            {
                "name": f"{display} future/oracle leaky",
                "score": leaky_col,
                "family": display,
                "type": "leaky",
                "leakage_level": "future+oracle",
                "feature_role": "future_oracle",
                "baseline": valid_col,
            }
        )

    return {"metrics": metrics, "monitor_specs": monitor_specs}


def make_feature_pipeline(estimator: Any):
    return make_pipeline(SimpleImputer(strategy="median"), estimator)


def fit_feature_model(model: Any, x_train: pd.DataFrame, y_train: np.ndarray, sample_weight: np.ndarray) -> None:
    last_step = list(model.named_steps)[-1]
    try:
        model.fit(x_train, y_train, **{f"{last_step}__sample_weight": sample_weight})
    except TypeError:
        model.fit(x_train, y_train)


def clone_estimator(estimator: Any, seed: int) -> Any:
    from sklearn.base import clone

    cloned = clone(estimator)
    if hasattr(cloned, "random_state"):
        cloned.set_params(random_state=seed)
    return cloned


def make_xgboost_classifier(y_train: np.ndarray, seed: int) -> Any:
    from xgboost import XGBClassifier

    n_pos = max(float(y_train.sum()), 1.0)
    n_neg = max(float(len(y_train) - y_train.sum()), 1.0)
    return XGBClassifier(
        n_estimators=180,
        max_depth=3,
        learning_rate=0.04,
        subsample=0.9,
        colsample_bytree=0.85,
        min_child_weight=3,
        reg_lambda=2.0,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        scale_pos_weight=n_neg / n_pos,
        random_state=seed,
        n_jobs=2,
    )


def run_neural_family(
    horizon: int,
    valid_sequences: np.ndarray,
    leaky_sequences: np.ndarray,
    train_mask: np.ndarray,
    test_mask: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    prediction_frame: pd.DataFrame,
    epochs: int,
    batch_size: int,
    hidden_dim: int,
    leakage_lambdas: tuple[float, ...],
    seed: int,
) -> dict[str, list[dict[str, Any]]]:
    metrics: list[dict[str, Any]] = []
    monitor_specs: list[dict[str, Any]] = []
    for model_type in ["lstm", "gru", "transformer"]:
        valid_score = f"{model_type}_valid_score"
        leaky_score = f"{model_type}_future_leaky_score"

        valid_fit = fit_torch_sequence_model(
            model_type=model_type,
            x_train=valid_sequences[train_mask],
            y_train=y_train,
            x_test=valid_sequences[test_mask],
            epochs=epochs,
            batch_size=batch_size,
            hidden_dim=hidden_dim,
            seed=seed,
        )
        leaky_fit = fit_torch_sequence_model(
            model_type=model_type,
            x_train=leaky_sequences[train_mask],
            y_train=y_train,
            x_test=leaky_sequences[test_mask],
            epochs=epochs,
            batch_size=batch_size,
            hidden_dim=hidden_dim,
            seed=seed + 17,
        )
        prediction_frame[valid_score] = valid_fit["scores"]
        prediction_frame[leaky_score] = leaky_fit["scores"]
        metrics.append(metric_row(horizon, valid_score, y_test, prediction_frame))
        metrics.append(metric_row(horizon, leaky_score, y_test, prediction_frame))
        monitor_specs.extend(
            [
                {
                    "name": f"{model_type.upper()} valid sequence",
                    "score": valid_score,
                    "family": model_type.upper(),
                    "type": "valid",
                    "leakage_level": "none",
                    "feature_role": "early",
                },
                {
                    "name": f"{model_type.upper()} future-window leaky sequence",
                    "score": leaky_score,
                    "family": model_type.upper(),
                    "type": "leaky",
                    "leakage_level": "future",
                    "feature_role": "future_sequence",
                    "baseline": valid_score,
                },
            ]
        )
        add_oracle_mixtures(
            prediction_frame=prediction_frame,
            metrics=metrics,
            monitor_specs=monitor_specs,
            horizon=horizon,
            y_test=y_test,
            base_score=valid_score,
            family=model_type.upper(),
            leakage_lambdas=leakage_lambdas,
        )
        if model_type in {"lstm", "transformer"}:
            add_hidden_probe(
                prediction_frame=prediction_frame,
                metrics=metrics,
                monitor_specs=monitor_specs,
                horizon=horizon,
                y_train=y_train,
                y_test=y_test,
                train_repr=valid_fit["train_repr"],
                test_repr=valid_fit["test_repr"],
                family=model_type.upper(),
                prefix=f"{model_type}_hidden_probe_score",
                feature_role="early",
            )
            add_hidden_probe(
                prediction_frame=prediction_frame,
                metrics=metrics,
                monitor_specs=monitor_specs,
                horizon=horizon,
                y_train=y_train,
                y_test=y_test,
                train_repr=leaky_fit["train_repr"],
                test_repr=leaky_fit["test_repr"],
                family=model_type.upper(),
                prefix=f"{model_type}_future_hidden_probe_score",
                feature_role="future_sequence",
                baseline=valid_score,
            )
    return {"metrics": metrics, "monitor_specs": monitor_specs}


def torch_import_status() -> dict[str, Any]:
    try:
        import torch  # noqa: F401

        return {"available": True, "reason": None}
    except Exception as exc:  # pragma: no cover - depends on local environment
        return {"available": False, "reason": str(exc)}


def xgboost_import_status(skip: bool = False) -> dict[str, Any]:
    if skip:
        return {"available": False, "reason": "disabled by --skip-xgboost"}
    try:
        import xgboost  # noqa: F401

        return {"available": True, "reason": None}
    except Exception as exc:  # pragma: no cover - depends on local environment
        return {"available": False, "reason": str(exc)}


def add_hidden_probe(
    prediction_frame: pd.DataFrame,
    metrics: list[dict[str, Any]],
    monitor_specs: list[dict[str, Any]],
    horizon: int,
    y_train: np.ndarray,
    y_test: np.ndarray,
    train_repr: np.ndarray,
    test_repr: np.ndarray,
    family: str,
    prefix: str,
    feature_role: str,
    baseline: str | None = None,
) -> None:
    probe = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=500, class_weight="balanced", random_state=SEED + horizon),
    )
    probe.fit(train_repr, y_train)
    prediction_frame[prefix] = probe.predict_proba(test_repr)[:, 1]
    metrics.append(metric_row(horizon, prefix, y_test, prediction_frame))
    monitor_specs.append(
        {
            "name": f"{family} hidden-state probe"
            if feature_role == "early"
            else f"{family} future hidden-state probe",
            "score": prefix,
            "family": f"{family} hidden probe",
            "type": "hidden probe" if feature_role == "early" else "leaky hidden probe",
            "leakage_level": "none" if feature_role == "early" else "future",
            "feature_role": feature_role,
            "baseline": baseline,
        }
    )


def fit_torch_sequence_model(
    model_type: str,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    epochs: int,
    batch_size: int,
    hidden_dim: int,
    seed: int,
) -> dict[str, np.ndarray]:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    torch.manual_seed(seed)
    x_train, x_test = standardize_sequences(x_train, x_test)
    train_tensor = torch.tensor(x_train, dtype=torch.float32)
    y_tensor = torch.tensor(y_train.reshape(-1, 1), dtype=torch.float32)
    test_tensor = torch.tensor(x_test, dtype=torch.float32)

    model = SequenceClassifier(
        model_type=model_type,
        input_dim=x_train.shape[-1],
        hidden_dim=hidden_dim,
        max_len=x_train.shape[1],
    )
    n_pos = max(float(y_train.sum()), 1.0)
    n_neg = max(float(len(y_train) - y_train.sum()), 1.0)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([n_neg / n_pos]))
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.002, weight_decay=0.001)
    loader = DataLoader(
        TensorDataset(train_tensor, y_tensor),
        batch_size=batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )

    model.train()
    for _ in range(max(1, epochs)):
        for batch_x, batch_y in loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(batch_x)
            loss = loss_fn(logits, batch_y)
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        train_logits, train_repr = model(train_tensor, return_repr=True)
        test_logits, test_repr = model(test_tensor, return_repr=True)
        scores = torch.sigmoid(test_logits).squeeze(1).cpu().numpy()
    return {
        "scores": scores,
        "train_repr": train_repr.cpu().numpy(),
        "test_repr": test_repr.cpu().numpy(),
    }


class SequenceClassifier:  # constructed only when torch is available
    def __new__(cls, model_type: str, input_dim: int, hidden_dim: int, max_len: int):
        import torch
        from torch import nn

        class _Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.model_type = model_type
                self.input_proj = nn.Linear(input_dim, hidden_dim)
                if model_type == "lstm":
                    self.encoder = nn.LSTM(hidden_dim, hidden_dim, batch_first=True)
                elif model_type == "gru":
                    self.encoder = nn.GRU(hidden_dim, hidden_dim, batch_first=True)
                elif model_type == "transformer":
                    layer = nn.TransformerEncoderLayer(
                        d_model=hidden_dim,
                        nhead=4,
                        dim_feedforward=hidden_dim * 2,
                        dropout=0.05,
                        batch_first=True,
                    )
                    self.position = nn.Parameter(torch.zeros(1, max_len, hidden_dim))
                    self.encoder = nn.TransformerEncoder(layer, num_layers=1)
                else:
                    raise ValueError(f"Unknown sequence model type: {model_type}")
                self.head = nn.Sequential(
                    nn.LayerNorm(hidden_dim),
                    nn.Linear(hidden_dim, 1),
                )

            def encode(self, x):
                z = self.input_proj(x)
                if self.model_type in {"lstm", "gru"}:
                    out, _ = self.encoder(z)
                    pooled = out[:, -1, :]
                else:
                    z = z + self.position[:, : z.shape[1], :]
                    out = self.encoder(z)
                    pooled = out.mean(dim=1)
                return pooled

            def forward(self, x, return_repr: bool = False):
                pooled = self.encode(x)
                logits = self.head(pooled)
                if return_repr:
                    return logits, pooled
                return logits

        return _Model()


def standardize_sequences(x_train: np.ndarray, x_test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    train = x_train.copy()
    test = x_test.copy()
    med = np.nanmedian(train.reshape(-1, train.shape[-1]), axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    train = fill_nan(train, med)
    test = fill_nan(test, med)
    mean = train.reshape(-1, train.shape[-1]).mean(axis=0)
    std = train.reshape(-1, train.shape[-1]).std(axis=0)
    std = np.where(std < 1e-6, 1.0, std)
    return (train - mean) / std, (test - mean) / std


def fill_nan(values: np.ndarray, fill: np.ndarray) -> np.ndarray:
    out = values.copy()
    mask = ~np.isfinite(out)
    if mask.any():
        out[mask] = np.take(fill, np.where(mask)[-1])
    return out


def metric_row(
    horizon: int,
    score_col: str,
    y_test: np.ndarray,
    prediction_frame: pd.DataFrame,
) -> dict[str, Any]:
    scores = prediction_frame[score_col].to_numpy()
    auc = roc_auc_score(y_test, scores) if len(np.unique(y_test)) == 2 else math.nan
    return {
        "horizon_h": horizon,
        "score": score_col,
        "auc": float(auc),
        "n": int(len(y_test)),
        "n_positive": int(y_test.sum()),
    }


def run_lamp_audits(
    predictions: pd.DataFrame,
    out_dir: Path,
    monitor_specs: list[dict[str, Any]],
    match_cols: list[str],
) -> list[dict[str, Any]]:
    compact_cols = metadata_columns(predictions) + [spec["score"] for spec in monitor_specs]
    compact_cols = [col for col in dict.fromkeys(compact_cols) if col in predictions.columns]
    compact = predictions[compact_cols].copy()
    compact_path = out_dir / "lamp_prediction_table.csv"
    compact.to_csv(compact_path, index=False, lineterminator="\n")

    rows: list[dict[str, Any]] = []
    for spec in monitor_specs:
        cfg = lamp_config(spec, match_cols=match_cols)
        cfg_dir = out_dir / "configs"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = cfg_dir / f"{spec['score']}.yaml"
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        audit_dir = out_dir / "lamp" / spec["score"]
        result = run_audit(cfg_path, compact_path, audit_dir)
        classes = result["failure_mode_dossier"]["output_classes"]
        rows.append(
            {
                "monitor": spec["name"],
                "score": spec["score"],
                "auc": result["primary_score"]["auc"],
                "audit_pass": result["failure_mode_dossier"]["audit_pass_candidate"],
                "temporal_passed": result["temporal_isolation"]["passed"],
                "forbidden_passed": result["forbidden_feature_screen"]["passed"],
                "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
                "oracle_proximity_shift": "oracle_leakage_proximity_shift" in classes,
                "output_classes": ";".join(classes),
            }
        )
    return rows


def metadata_columns(predictions: pd.DataFrame) -> list[str]:
    preferred = [
        "patient_id",
        "source_set",
        "horizon_h",
        "anchor_idx",
        "label_future_sepsis",
        "sepsis_onset_idx",
        "hours_to_onset",
        "future_physiology_sentinel_score",
        "oracle_label_sentinel_score",
    ]
    return [col for col in preferred + VISIBLE_MATCH_COLUMNS if col in predictions.columns]


def lamp_config(spec: dict[str, Any], match_cols: list[str]) -> dict[str, Any]:
    role = spec.get("feature_role", "early")
    forbidden = ["future_sequence_window", "future_engineered_features", "oracle_label_sentinel_score"]
    valid_features = [{"name": "early_sequence_or_features", "latest_offset_h": 0}]
    valid_score_features = ["early_sequence_or_features"]
    if role in {"future_sequence", "future_oracle"}:
        valid_features.append({"name": "future_sequence_window", "latest_offset_h": 1})
        valid_score_features.append("future_sequence_window")
    if role in {"future_oracle", "oracle_mixture"}:
        valid_features.append({"name": "oracle_label_sentinel_score", "latest_offset_h": 1})
        valid_score_features.append("oracle_label_sentinel_score")

    cfg: dict[str, Any] = {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": "PhysioNet/CinC 2019 raw PSV sequence bench",
            "task": spec["name"],
            "role": "real_clinical_sequence_benchmark",
        },
        "columns": {
            "subject_id": "patient_id",
            "label": "label_future_sepsis",
            "positive_value": 1,
            "score": spec["score"],
            "anchor_time": "anchor_idx",
        },
        "temporal_isolation": {
            "anchor": "anchor_idx",
            "valid_features_must_be": "at_or_before_anchor",
            "frozen_before_holdout": ["patient split", "horizon definitions", "feature roles"],
            "valid_score_features": valid_features,
        },
        "forbidden_features": {
            "columns": forbidden,
            "allowed_metadata_columns": [],
            "valid_score_features": valid_score_features,
        },
        "sentinels": {
            "future_physiology": {
                "column": "future_physiology_sentinel_score",
                "role": "future_window_invalid_comparator",
                "expected_signature": "higher_auc_than_valid_if_future_physiology_is_informative",
            },
            "oracle_label": {
                "column": "oracle_label_sentinel_score",
                "role": "oracle_label_leakage",
                "expected_signature": "ceiling_auc_or_high_proximity",
            },
        },
        "negative_controls": {"n_permutations": 30, "seed": SEED},
        "visible_state_matching": {"columns": match_cols, "n_bins": 3, "min_bin_size": 4},
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.60,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.005,
            "matched_collapse_max": 0.002,
            "score_thresholds": [0.2, 0.4, 0.6, 0.8],
        },
    }
    if spec.get("baseline"):
        cfg["leakage_proximity"] = {
            "baseline_score": spec["baseline"],
            "oracle_proximity_alert_min": 0.01,
        }
    return cfg


def unique_monitor_specs(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for spec in specs:
        score = spec["score"]
        if score in seen:
            continue
        seen.add(score)
        unique.append(spec)
    return unique


def write_report(
    path: Path,
    args: argparse.Namespace,
    table: pd.DataFrame,
    predictions: pd.DataFrame,
    metrics: list[dict[str, Any]],
    lamp_rows: list[dict[str, Any]],
    torch_status: dict[str, Any],
    xgboost_status: dict[str, Any],
) -> None:
    lines = [
        "# PhysioNet/CinC 2019 Raw Sequence LAMP Benchmark",
        "",
        "This run builds examples directly from raw `.psv` files, creates early-window",
        "and future-window splits, trains valid and intentionally contaminated monitors,",
        "and applies LAMP to the resulting prediction table.",
        "",
        f"- Source examples: {len(table)}",
        f"- Held-out predictions: {len(predictions)}",
        f"- Max patients: {args.max_patients}",
        f"- Horizons: {args.horizons}",
        f"- Early window: {args.early_window} hours",
        f"- Leakage lambdas: {args.leakage_lambdas}",
        f"- PyTorch available: {torch_status['available']}",
        f"- XGBoost available: {xgboost_status['available']}",
    ]
    if not torch_status["available"]:
        lines.append(f"- Neural LSTM/GRU/Transformer skipped: `{torch_status['reason']}`")
    if not xgboost_status["available"]:
        lines.append(f"- XGBoost skipped: `{xgboost_status['reason']}`")
    lines.extend(["", "## LAMP Diagnoses", ""])
    lines.append("| monitor | score | auc | audit_pass | temporal | forbidden | oracle proximity | output_classes |")
    lines.append("|---|---|---:|:---:|:---:|:---:|:---:|---|")
    for row in lamp_rows:
        lines.append(
            f"| {row['monitor']} | `{row['score']}` | {fmt(row['auc'])} | "
            f"{row['audit_pass']} | {row['temporal_passed']} | {row['forbidden_passed']} | "
            f"{row['oracle_proximity_shift']} | `{row['output_classes']}` |"
        )
    lines.extend(["", "## Per-Horizon Metrics", ""])
    lines.append("| horizon_h | score | auc | n | n_positive |")
    lines.append("|---:|---|---:|---:|---:|")
    for row in metrics:
        lines.append(
            f"| {row['horizon_h']} | `{row['score']}` | {fmt(row['auc'])} | "
            f"{row['n']} | {row['n_positive']} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "Valid monitors only receive pre-anchor windows. Leaky monitors are trained",
            "with post-anchor physiology and/or oracle onset information so LAMP can",
            "separate performance from validity.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def fmt(value: Any) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
