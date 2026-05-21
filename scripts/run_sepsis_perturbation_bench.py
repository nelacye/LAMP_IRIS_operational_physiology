#!/usr/bin/env python3
"""Run LAMP perturbation benchmarks on the existing sepsis v3 5k score table."""

from __future__ import annotations

import copy
import csv
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402
from lamp.controls import as_float  # noqa: E402


BASE_TABLE = ROOT / "results/sepsis_external/v3_5k/tables/sepsis_patient_scores.csv"
BASE_CONFIG = ROOT / "examples/sepsis/physionet_v3_5k_existing_results_config.yaml"
OUT_DIR = ROOT / "results/lamp_perturbations/sepsis_v3_5k"
LAMBDAS = [0.0, 0.005, 0.01, 0.02, 0.05, 0.10]
HORIZONS = [6, 12, 18]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = read_csv(BASE_TABLE)
    config = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))

    oracle_rows = run_oracle_mixture(rows, config)
    visible_rows = run_visible_confounding(rows, config)

    write_csv(OUT_DIR / "oracle_mixture_summary.csv", oracle_rows)
    write_csv(OUT_DIR / "visible_confounding_summary.csv", visible_rows)
    write_report(OUT_DIR / "perturbation_report.md", oracle_rows, visible_rows)

    print(OUT_DIR / "oracle_mixture_summary.csv")
    print(OUT_DIR / "visible_confounding_summary.csv")
    print(OUT_DIR / "perturbation_report.md")
    return 0


def run_oracle_mixture(
    rows: list[dict[str, str]],
    base_config: dict[str, Any],
) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for horizon in HORIZONS:
        horizon_rows = [row for row in rows if int(float(row["horizon_h"])) == horizon]
        for lam in LAMBDAS:
            mixed_rows = with_mixed_score(horizon_rows, lam)
            table_path = OUT_DIR / "tables" / f"oracle_h{horizon}_l{lambda_tag(lam)}.csv"
            write_csv(table_path, mixed_rows)
            for provenance in ["undeclared", "declared"]:
                run_dir = (
                    OUT_DIR
                    / "oracle_mixture"
                    / f"{provenance}_h{horizon}_l{lambda_tag(lam)}"
                )
                run_dir.mkdir(parents=True, exist_ok=True)
                config_path = run_dir / "config.yaml"

                config = mixture_config(base_config, lam, provenance)
                config["dataset"] = {
                    "name": f"PhysioNet sepsis oracle mixture h{horizon} lambda {lam:g}",
                    "task": "low-dose oracle leakage sensitivity",
                    "role": f"perturbation benchmark: {provenance} oracle provenance",
                    "lambda": lam,
                    "horizon_h": horizon,
                }
                config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

                result = run_audit(config_path, table_path, run_dir)
                summary.append(flatten_oracle_result(horizon, lam, provenance, result))
                print(f"oracle mixture h={horizon} lambda={lam:g} {provenance}")
    return summary


def run_visible_confounding(
    rows: list[dict[str, str]],
    base_config: dict[str, Any],
) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for horizon in HORIZONS:
        horizon_rows = [row for row in rows if int(float(row["horizon_h"])) == horizon]
        visible_rows = with_visible_only_score(horizon_rows)
        run_dir = OUT_DIR / "visible_confounding" / f"horizon_{horizon}"
        run_dir.mkdir(parents=True, exist_ok=True)
        table_path = OUT_DIR / "tables" / f"visible_h{horizon}.csv"
        config_path = run_dir / "config.yaml"
        write_csv(table_path, visible_rows)

        config = visible_config(base_config)
        config["dataset"] = {
            "name": f"PhysioNet sepsis visible-only score h{horizon}",
            "task": "visible-confounding collapse test",
            "role": "perturbation benchmark",
            "horizon_h": horizon,
        }
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

        result = run_audit(config_path, table_path, run_dir)
        summary.append(flatten_visible_result(horizon, result))
        print(f"visible confounding h={horizon}")
    return summary


def mixture_config(
    base_config: dict[str, Any],
    lam: float,
    provenance: str,
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    config["columns"]["score"] = "mixed_score"
    config["negative_controls"]["n_permutations"] = 200
    config["leakage_proximity"] = {
        "baseline_score": "valid_early_warning_score",
        "oracle_proximity_alert_min": 0.01,
    }

    if provenance == "declared" and lam > 0:
        config["forbidden_features"]["valid_score_features"] = list(
            config["forbidden_features"].get("valid_score_features", [])
        ) + ["oracle_label_sentinel_score"]
        config["temporal_isolation"]["valid_score_features"] = list(
            config["temporal_isolation"].get("valid_score_features", [])
        ) + [{"name": "oracle_label_sentinel_score", "latest_offset_h": 1}]
    return config


def visible_config(base_config: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    config["columns"]["score"] = "visible_only_score"
    config["negative_controls"]["n_permutations"] = 200
    config["leakage_proximity"] = {
        "baseline_score": "valid_early_warning_score",
        "oracle_proximity_alert_min": 1.1,
    }
    config["temporal_isolation"]["valid_score_features"] = [
        {"name": "ICULOS", "latest_offset_h": 0},
    ]
    config["forbidden_features"]["valid_score_features"] = [
        "ICULOS",
    ]
    config["visible_state_matching"]["columns"] = ["ICULOS"]
    config["visible_state_matching"]["n_bins"] = 3
    config["visible_state_matching"]["min_bin_size"] = 8
    return config


def with_mixed_score(rows: list[dict[str, str]], lam: float) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        new = dict(row)
        valid = as_float(row.get("valid_early_warning_score")) or 0.0
        oracle = as_float(row.get("oracle_label_sentinel_score")) or 0.0
        new["mixed_score"] = f"{((1.0 - lam) * valid + lam * oracle):.12g}"
        out.append(new)
    return out


def with_visible_only_score(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = [dict(row) for row in rows]
    workflow_bins = lamp_style_bins(out, "ICULOS", n_bins=3)
    for idx, new in enumerate(out):
        # This score is intentionally built only from a coarse visible workflow
        # stratum. It is predictive because event cases have different observed
        # ICU history, but inside the same matched workflow stratum it has no
        # hidden-state information left.
        new["visible_only_score"] = f"{workflow_bins.get(idx, 1):.12g}"
    return out


def lamp_style_bins(
    rows: list[dict[str, str]],
    column: str,
    n_bins: int,
) -> dict[int, int]:
    values = [
        (as_float(row.get(column)), idx)
        for idx, row in enumerate(rows)
        if as_float(row.get(column)) is not None
    ]
    ordered = sorted(values, key=lambda item: item[0])
    total = len(ordered)
    result: dict[int, int] = {}
    for position, (_, idx) in enumerate(ordered):
        result[idx] = min(int(position * n_bins / total), n_bins - 1)
    return result


def flatten_oracle_result(
    horizon: int,
    lam: float,
    provenance: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    primary = result["primary_score"]
    oracle_rel = result["sentinel_relations"].get("oracle_label", {})
    future_rel = result["sentinel_relations"].get("future_physiology", {})
    dossier = result["failure_mode_dossier"]
    return {
        "horizon_h": horizon,
        "lambda": lam,
        "provenance": provenance,
        "n": primary["n"],
        "n_positive": primary["n_positive"],
        "auc": primary["auc"],
        "baseline_valid_auc": oracle_rel.get("baseline_auc"),
        "oracle_auc": oracle_rel.get("sentinel_auc"),
        "distance_to_oracle_auc": oracle_rel.get("sentinel_minus_primary_auc"),
        "oracle_auc_leakage_proximity": oracle_rel.get("auc_leakage_proximity"),
        "oracle_score_pearson": oracle_rel.get("primary_sentinel_pearson"),
        "future_auc": future_rel.get("sentinel_auc"),
        "future_auc_gap": future_rel.get("sentinel_minus_primary_auc"),
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "forbidden_valid_feature_violations": ";".join(
            result["forbidden_feature_screen"]["valid_score_feature_violations"]
        ),
        "early_window_plausible": result["temporal_isolation"]["passed"]
        and result["forbidden_feature_screen"]["passed"],
        "matched_delta": result["visible_state_matching"].get(
            "matched_observed_state_delta"
        ),
        "audit_pass_candidate": dossier["audit_pass_candidate"],
        "output_classes": ";".join(dossier["output_classes"]),
    }


def flatten_visible_result(horizon: int, result: dict[str, Any]) -> dict[str, Any]:
    primary = result["primary_score"]
    oracle_rel = result["sentinel_relations"].get("oracle_label", {})
    dossier = result["failure_mode_dossier"]
    return {
        "horizon_h": horizon,
        "n": primary["n"],
        "n_positive": primary["n_positive"],
        "visible_only_auc": primary["auc"],
        "baseline_valid_auc": oracle_rel.get("baseline_auc"),
        "auc_vs_valid_delta": (
            primary["auc"] - oracle_rel["baseline_auc"]
            if primary["auc"] is not None and oracle_rel.get("baseline_auc") is not None
            else None
        ),
        "matched_delta": result["visible_state_matching"].get(
            "matched_observed_state_delta"
        ),
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "audit_pass_candidate": dossier["audit_pass_candidate"],
        "output_classes": ";".join(dossier["output_classes"]),
    }


def write_report(
    path: Path,
    oracle_rows: list[dict[str, Any]],
    visible_rows: list[dict[str, Any]],
) -> None:
    lines = [
        "# LAMP perturbation benchmark: PhysioNet/CinC 2019 sepsis v3 5k",
        "",
        "## Oracle low-dose mixture",
        "",
        "Score definition: `mixed_score = (1 - lambda) * valid_score + lambda * oracle_score`.",
        "",
        "| horizon | lambda | provenance | AUC | distance_to_oracle | oracle_proximity | temporal | forbidden | audit_pass | output_classes |",
        "|---:|---:|---|---:|---:|---:|:---:|:---:|:---:|---|",
    ]
    for row in oracle_rows:
        lines.append(
            f"| {row['horizon_h']} | {row['lambda']:.3g} | {row['provenance']} | "
            f"{fmt(row['auc'])} | {fmt(row['distance_to_oracle_auc'])} | "
            f"{fmt(row['oracle_auc_leakage_proximity'])} | {row['temporal_passed']} | "
            f"{row['forbidden_passed']} | {row['audit_pass_candidate']} | `{row['output_classes']}` |"
        )

    lines.extend(
        [
            "",
            "## Visible-confounding collapse",
            "",
            "| horizon | visible_only_auc | baseline_valid_auc | auc_delta | matched_delta | audit_pass | output_classes |",
            "|---:|---:|---:|---:|---:|:---:|---|",
        ]
    )
    for row in visible_rows:
        lines.append(
            f"| {row['horizon_h']} | {fmt(row['visible_only_auc'])} | "
            f"{fmt(row['baseline_valid_auc'])} | {fmt(row['auc_vs_valid_delta'])} | "
            f"{fmt(row['matched_delta'])} | {row['audit_pass_candidate']} | `{row['output_classes']}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "This perturbation benchmark tests audit behavior under controlled score contamination.",
            "It does not establish clinical validity. Surviving LAMP earns prospective testing.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clipped(value: float, low: float = 0.0, high: float = 5.0) -> float:
    return min(max(value, low), high)


def lambda_tag(lam: float) -> str:
    return str(lam).replace(".", "p")


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    return f"{float(value):.6f}"


if __name__ == "__main__":
    raise SystemExit(main())
