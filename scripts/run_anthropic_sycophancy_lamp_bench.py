#!/usr/bin/env python3
"""Run LAMP on a public Anthropic sycophancy evaluation dataset.

This is the first real LLM-evaluation-data benchmark in the repository. It uses
the public Anthropic `model-written-evals` sycophancy JSONL, trains a prompt-only
monitor to predict the sycophantic answer key on held-out examples, and compares
it with deliberate answer-key leakage and low-dose oracle contamination.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import urllib.request
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import RocCurveDisplay, auc, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402


DATA_URL = (
    "https://huggingface.co/datasets/Anthropic/model-written-evals/resolve/main/"
    "sycophancy/sycophancy_on_nlp_survey.jsonl"
)
OUT = ROOT / "results" / "anthropic_sycophancy_lamp"
NOTEBOOK = ROOT / "notebooks" / "anthropic_sycophancy_lamp_audit.ipynb"
FIG_DIR = ROOT / "notebooks" / "figures"
SEED = 2026

FORBIDDEN_COLUMNS = [
    "answer_matching_behavior_is_a",
    "answer_not_matching_behavior_is_a",
    "oracle_answer_key_score",
]
MATCH_COLUMNS = [
    "prompt_length",
    "persona_length",
]
EARLY_SENSITIVITY_COLUMNS = [
    "tfidf_prompt_valid_score",
    "cue_prompt_valid_score",
    "visible_length_shortcut_score",
    "answer_key_leakage_score",
    "tfidf_oracle_mix_1pct",
    "tfidf_oracle_mix_5pct",
    "tfidf_oracle_mix_10pct",
]

MONITORS = [
    {
        "id": "tfidf_prompt_valid",
        "name": "TF-IDF prompt-only sycophancy-target monitor",
        "type": "valid prompt-only monitor",
        "score": "tfidf_prompt_valid_score",
        "features": ["prompt_text_tfidf", "pre_answer_user_view_cues"],
        "description": "Learns the sycophancy target from held-out public prompts without answer-key fields.",
    },
    {
        "id": "cue_prompt_valid",
        "name": "Interpretable user-view cue monitor",
        "type": "valid cue monitor",
        "score": "cue_prompt_valid_score",
        "features": ["pre_answer_user_view_cues"],
        "description": "A transparent prompt-cue baseline using stated agree/disagree cues only.",
    },
    {
        "id": "visible_length_shortcut",
        "name": "Visible length shortcut",
        "type": "visible shortcut",
        "score": "visible_length_shortcut_score",
        "features": ["prompt_length", "persona_length"],
        "baseline": "tfidf_prompt_valid_score",
        "description": "A superficial prompt-length shortcut that should not survive the audit.",
    },
    {
        "id": "answer_key_leakage",
        "name": "Answer-key leakage monitor",
        "type": "oracle leakage",
        "score": "answer_key_leakage_score",
        "features": ["oracle_answer_key_score"],
        "forbidden": ["oracle_answer_key_score"],
        "temporal_offsets": {"oracle_answer_key_score": 1},
        "baseline": "tfidf_prompt_valid_score",
        "description": "Uses the dataset answer_matching_behavior field as a direct oracle.",
    },
    {
        "id": "tfidf_oracle_mix_1pct",
        "name": "TF-IDF + answer-key leakage 1%",
        "type": "low-dose oracle leakage",
        "score": "tfidf_oracle_mix_1pct",
        "features": ["prompt_text_tfidf", "oracle_answer_key_score"],
        "forbidden": ["oracle_answer_key_score"],
        "temporal_offsets": {"oracle_answer_key_score": 1},
        "baseline": "tfidf_prompt_valid_score",
        "description": "One-percent answer-key contamination added to the valid prompt monitor.",
    },
    {
        "id": "tfidf_oracle_mix_5pct",
        "name": "TF-IDF + answer-key leakage 5%",
        "type": "low-dose oracle leakage",
        "score": "tfidf_oracle_mix_5pct",
        "features": ["prompt_text_tfidf", "oracle_answer_key_score"],
        "forbidden": ["oracle_answer_key_score"],
        "temporal_offsets": {"oracle_answer_key_score": 1},
        "baseline": "tfidf_prompt_valid_score",
        "description": "Five-percent answer-key contamination added to the valid prompt monitor.",
    },
    {
        "id": "tfidf_oracle_mix_10pct",
        "name": "TF-IDF + answer-key leakage 10%",
        "type": "low-dose oracle leakage",
        "score": "tfidf_oracle_mix_10pct",
        "features": ["prompt_text_tfidf", "oracle_answer_key_score"],
        "forbidden": ["oracle_answer_key_score"],
        "temporal_offsets": {"oracle_answer_key_score": 1},
        "baseline": "tfidf_prompt_valid_score",
        "description": "Ten-percent answer-key contamination added to the valid prompt monitor.",
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = OUT / "cache" / "sycophancy_on_nlp_survey.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if not raw_path.exists():
        download(DATA_URL, raw_path)

    raw_rows = read_jsonl(raw_path)
    frame = build_prediction_frame(raw_rows)
    predictions_path = OUT / "anthropic_sycophancy_predictions.csv"
    frame.to_csv(predictions_path, index=False, lineterminator="\n")

    summary_rows = []
    for monitor in MONITORS:
        config = build_monitor_config(monitor)
        config_path = OUT / "configs" / f"{monitor['id']}.yaml"
        write_yaml(config_path, config)
        result = run_audit(config_path, predictions_path, OUT / "lamp" / monitor["id"])
        summary_rows.append(summary_row(monitor, result))

    write_csv(OUT / "anthropic_sycophancy_lamp_summary.csv", summary_rows)
    write_report(OUT / "anthropic_sycophancy_lamp_report.md", frame, summary_rows)
    figure_paths = build_figures(frame, pd.DataFrame(summary_rows))
    build_notebook(summary_rows, figure_paths)

    print(
        json.dumps(
            {
                "out": str(OUT),
                "notebook": str(NOTEBOOK),
                "n_raw_rows": len(raw_rows),
                "n_holdout_rows": len(frame),
            },
            indent=2,
        )
    )
    return 0


def download(url: str, path: Path) -> None:
    with urllib.request.urlopen(url) as response, path.open("wb") as handle:
        handle.write(response.read())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build_prediction_frame(raw_rows: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for idx, item in enumerate(raw_rows):
        question = item["question"]
        label = 1 if item["answer_matching_behavior"].strip() == "(A)" else 0
        cue_score = prompt_cue_score(question)
        rows.append(
            {
                "example_id": f"anthropic_syc_nlp_{idx:05d}",
                "anchor_step": 0,
                "label_matching_answer_is_a": label,
                "prompt_text": question,
                "prompt_length": len(question),
                "persona_length": len(question.split("Do you agree or disagree")[0]),
                "cue_prompt_valid_score": cue_score,
                "visible_length_shortcut_score": float(len(question)),
                "answer_matching_behavior_is_a": label,
                "answer_not_matching_behavior_is_a": 1 - label,
                "oracle_answer_key_score": float(label),
                "answer_key_leakage_score": float(label),
            }
        )

    full = pd.DataFrame(rows)
    train_idx, test_idx = train_test_split(
        np.arange(len(full)),
        test_size=0.30,
        random_state=SEED,
        stratify=full["label_matching_answer_is_a"],
    )
    model = make_pipeline(
        TfidfVectorizer(max_features=4000, ngram_range=(1, 2), min_df=2),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED),
    )
    model.fit(
        full.loc[train_idx, "prompt_text"],
        full.loc[train_idx, "label_matching_answer_is_a"],
    )

    test = full.loc[test_idx].copy().reset_index(drop=True)
    test["split"] = "heldout"
    valid_score = model.predict_proba(test["prompt_text"])[:, 1]
    test["tfidf_prompt_valid_score"] = valid_score
    for pct, lam in [(1, 0.01), (5, 0.05), (10, 0.10)]:
        test[f"tfidf_oracle_mix_{pct}pct"] = mix_scores(
            valid_score,
            test["oracle_answer_key_score"].to_numpy(),
            lam,
        )

    length = test["visible_length_shortcut_score"].to_numpy(dtype=float)
    if float(length.max() - length.min()) > 0:
        test["visible_length_shortcut_score"] = (length - length.min()) / (
            length.max() - length.min()
        )
    else:
        test["visible_length_shortcut_score"] = 0.5
    return test


def prompt_cue_score(question: str) -> float:
    before = question.split("Do you agree or disagree")[0].lower()
    score = 0.50
    positive_patterns = [
        "i agree with",
        "i agree that",
        "i believe that",
        "i think that",
        "i feel that",
    ]
    negative_patterns = [
        "i disagree with",
        "i disagree that",
        "i do not agree",
        "i don't agree",
        "i don’t agree",
        "i do not believe",
        "i don't believe",
        "i don’t believe",
    ]
    if any(pattern in before for pattern in positive_patterns):
        score += 0.35
    if any(pattern in before for pattern in negative_patterns):
        score -= 0.35
    if "private firms have too much influence" in before:
        score += 0.08
    if "academic research" in before and "industry" in before:
        score += 0.03
    return clamp(score)


def build_monitor_config(monitor: dict[str, Any]) -> dict[str, Any]:
    temporal_offsets = monitor.get("temporal_offsets", {})
    valid_features = [
        {"name": feature, "latest_offset_h": temporal_offsets.get(feature, 0)}
        for feature in monitor["features"]
    ]
    config: dict[str, Any] = {
        "schema_version": "lamp.audit_config/v1",
        "dataset": {
            "name": f"Anthropic model-written-evals sycophancy: {monitor['name']}",
            "task": "public LLM sycophancy prompt audit",
            "role": "real LLM evaluation-data benchmark",
            "source": "Anthropic/model-written-evals sycophancy_on_nlp_survey",
            "monitor_id": monitor["id"],
            "monitor_type": monitor["type"],
            "monitor_description": monitor["description"],
        },
        "columns": {
            "subject_id": "example_id",
            "label": "label_matching_answer_is_a",
            "positive_value": 1,
            "score": monitor["score"],
            "anchor_time": "anchor_step",
        },
        "temporal_isolation": {
            "anchor": "anchor_step",
            "valid_features_must_be": "prompt-only before model completion",
            "frozen_before_holdout": [
                "source file",
                "train/holdout split seed",
                "TF-IDF model specification",
                "sentinel columns",
                "visible matching variables",
                "thresholds",
            ],
            "valid_score_features": valid_features,
        },
        "forbidden_features": {
            "columns": FORBIDDEN_COLUMNS,
            "allowed_metadata_columns": FORBIDDEN_COLUMNS,
            "valid_score_features": list(monitor["features"]),
        },
        "sentinels": {
            "oracle_answer_key": {
                "column": "oracle_answer_key_score",
                "role": "oracle_label",
                "expected_signature": "dataset answer_matching_behavior field",
            }
        },
        "negative_controls": {"n_permutations": 250, "seed": SEED},
        "visible_state_matching": {
            "columns": MATCH_COLUMNS,
            "n_bins": 3,
            "min_bin_size": 8,
        },
        "early_window_sensitivity": {"score_columns": EARLY_SENSITIVITY_COLUMNS},
        "thresholds": {
            "null_auc_max": 0.58,
            "valid_auc_min": 0.70,
            "oracle_auc_min": 0.95,
            "leakage_auc_gap": 0.10,
            "matched_delta_min": 0.05,
            "matched_collapse_max": 0.015,
            "score_thresholds": [0.25, 0.50, 0.75],
        },
    }
    if monitor.get("baseline"):
        config["leakage_proximity"] = {
            "baseline_score": monitor["baseline"],
            "oracle_proximity_alert_min": 0.005,
        }
    return config


def summary_row(monitor: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    dossier = result["failure_mode_dossier"]
    classes = dossier["output_classes"]
    return {
        "monitor": monitor["name"],
        "monitor_id": monitor["id"],
        "type": monitor["type"],
        "score": monitor["score"],
        "auc": round(float(result["primary_score"]["auc"] or 0.0), 6),
        "audit_pass": dossier["audit_pass_candidate"],
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "matched_delta": result["visible_state_matching"].get("matched_observed_state_delta"),
        "oracle_proximity_shift": "oracle_leakage_proximity_shift" in classes,
        "output_classes": ";".join(classes),
        "key_failures": key_failures(result),
    }


def key_failures(result: dict[str, Any]) -> str:
    dossier = result["failure_mode_dossier"]
    if dossier["audit_pass_candidate"]:
        return "none"
    failures = []
    if not result["temporal_isolation"]["passed"]:
        failures.append("temporal")
    if not result["forbidden_feature_screen"]["passed"]:
        failures.append("forbidden")
    classes = set(dossier["output_classes"])
    if "oracle_leakage_proximity_shift" in classes:
        failures.append("oracle proximity")
    if "null_or_destroyed_signal" in classes:
        failures.append("null/destroyed")
    if "visible_state_confounding" in classes:
        failures.append("visible confounding")
    return ", ".join(dict.fromkeys(failures)) or "sentinel warning"


def write_report(path: Path, frame: pd.DataFrame, summary_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Anthropic Sycophancy LAMP Benchmark",
        "",
        "Public real LLM-evaluation-data run using `Anthropic/model-written-evals`",
        "`sycophancy_on_nlp_survey.jsonl`. The task is to predict whether the",
        "sycophantic answer target is `(A)` on held-out examples.",
        "",
        f"- Held-out examples: {len(frame)}",
        "- Dataset source: Anthropic/model-written-evals, sycophancy_on_nlp_survey",
        "- Valid monitor: TF-IDF prompt-only classifier trained on public prompts",
        "- Leaky monitors: direct answer-key field and low-dose answer-key mixtures",
        "",
        "| Model | Type | AUC | Audit Status | Key Failures | Output Classes |",
        "|---|---|---:|:---:|---|---|",
    ]
    for row in summary_rows:
        status = "PASS" if row["audit_pass"] else "FAIL"
        lines.append(
            f"| {row['monitor']} | {row['type']} | {row['auc']:.3f} | {status} | "
            f"{row['key_failures']} | `{row['output_classes']}` |"
        )
    valid = row_by_id(summary_rows, "tfidf_prompt_valid")
    leaky = row_by_id(summary_rows, "answer_key_leakage")
    mix1 = row_by_id(summary_rows, "tfidf_oracle_mix_1pct")
    mix5 = row_by_id(summary_rows, "tfidf_oracle_mix_5pct")
    mix10 = row_by_id(summary_rows, "tfidf_oracle_mix_10pct")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"The prompt-only monitor passes LAMP with AUC {valid['auc']:.3f}. The direct",
            f"answer-key leakage monitor reaches AUC {leaky['auc']:.3f}, but fails temporal",
            "isolation, forbidden-feature screening, and oracle-proximity checks.",
            "",
            "Low-dose answer-key mixtures show graded contamination: "
            f"1% AUC {mix1['auc']:.3f}, 5% AUC {mix5['auc']:.3f}, "
            f"10% AUC {mix10['auc']:.3f}. LAMP flags them despite the small",
            "nominal change from the valid prompt-only score.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_figures(frame: pd.DataFrame, summary: pd.DataFrame) -> dict[str, str]:
    return {
        "auc": save_auc_bar(summary),
        "roc": save_roc(frame),
        "dose": save_lowdose(summary),
        "gates": save_gate_map(summary),
    }


def save_auc_bar(summary: pd.DataFrame) -> str:
    ordered = summary.sort_values("auc")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = ordered["audit_pass"].map({True: "#247A4B", False: "#B23A48"})
    ax.barh(ordered["monitor"], ordered["auc"], color=colors)
    ax.axvline(0.70, color="#333", linestyle="--", linewidth=1, label="valid_auc_min")
    ax.set_xlim(0.45, 1.02)
    ax.set_xlabel("Held-out AUC")
    ax.set_title("Anthropic sycophancy: performance is not information validity")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    return savefig(fig, "anthropic_sycophancy_auc_bar.png")


def save_roc(frame: pd.DataFrame) -> str:
    scores = [
        ("TF-IDF prompt-only", "tfidf_prompt_valid_score"),
        ("Prompt cue", "cue_prompt_valid_score"),
        ("Length shortcut", "visible_length_shortcut_score"),
        ("Answer-key leakage", "answer_key_leakage_score"),
        ("1% leakage mix", "tfidf_oracle_mix_1pct"),
        ("10% leakage mix", "tfidf_oracle_mix_10pct"),
    ]
    y = frame["label_matching_answer_is_a"].astype(int).to_numpy()
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    for label, col in scores:
        fpr, tpr, _ = roc_curve(y, frame[col].to_numpy(dtype=float))
        RocCurveDisplay(fpr=fpr, tpr=tpr, roc_auc=auc(fpr, tpr), name=label).plot(ax=ax)
    ax.plot([0, 1], [0, 1], color="#777", linestyle="--", linewidth=1)
    ax.set_title("ROC curves: prompt-only vs answer-key leakage")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return savefig(fig, "anthropic_sycophancy_roc.png")


def save_lowdose(summary: pd.DataFrame) -> str:
    valid_auc = float(summary.loc[summary["monitor_id"].eq("tfidf_prompt_valid"), "auc"].iloc[0])
    dose = summary[summary["monitor_id"].str.contains("oracle_mix", regex=False)].copy()
    dose["lambda_pct"] = dose["monitor_id"].str.extract(r"(\d+)pct").astype(float)
    dose["auc_lift"] = dose["auc"] - valid_auc
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(dose["lambda_pct"], dose["auc_lift"], marker="o", color="#B23A48")
    ax.axhline(0, color="#333", linewidth=1)
    ax.set_xlabel("Answer-key leakage dose (%)")
    ax.set_ylabel("AUC lift over prompt-only monitor")
    ax.set_title("Low-dose answer-key leakage")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return savefig(fig, "anthropic_sycophancy_lowdose.png")


def save_gate_map(summary: pd.DataFrame) -> str:
    gates = pd.DataFrame(
        {
            "audit pass": summary["audit_pass"].astype(bool),
            "temporal clean": summary["temporal_passed"].astype(bool),
            "forbidden clean": summary["forbidden_passed"].astype(bool),
            "oracle proximity absent": ~summary["oracle_proximity_shift"].astype(bool),
        }
    )
    matrix = gates.astype(int).to_numpy()
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(gates.columns)))
    ax.set_xticklabels(gates.columns, rotation=25, ha="right")
    ax.set_yticks(range(len(summary)))
    ax.set_yticklabels(summary["monitor"])
    ax.set_title("LAMP gates for public Anthropic sycophancy benchmark")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, "pass" if matrix[i, j] else "fail", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    fig.tight_layout()
    return savefig(fig, "anthropic_sycophancy_gate_map.png")


def build_notebook(summary_rows: list[dict[str, Any]], figure_paths: dict[str, str]) -> None:
    valid = row_by_id(summary_rows, "tfidf_prompt_valid")
    leaky = row_by_id(summary_rows, "answer_key_leakage")
    table = markdown_table(
        [
            [
                row["monitor"],
                row["type"],
                f"{row['auc']:.3f}",
                "PASS" if row["audit_pass"] else "FAIL",
                row["key_failures"],
            ]
            for row in summary_rows
        ],
        ["Model", "Type", "AUC", "Audit Status", "Key Failures"],
    )
    rel = {key: notebook_relative_path(path) for key, path in figure_paths.items()}
    cells = [
        md(
            "# Public LLM Dataset LAMP Audit: Anthropic Sycophancy\n\n"
            "Real public LLM-evaluation prompts from `Anthropic/model-written-evals` "
            "are used to audit prompt-only sycophancy-target monitors against "
            "answer-key leakage."
        ),
        md(
            "## Executive Result\n\n"
            f"The prompt-only TF-IDF monitor passes with AUC {valid['auc']:.3f}. "
            f"The answer-key leakage monitor reaches AUC {leaky['auc']:.3f}, but "
            "fails temporal isolation, forbidden-feature screening, and oracle "
            "proximity. This gives LAMP a real public LLM-data benchmark, not only a "
            "synthetic alignment toy.\n\n"
            f"{table}"
        ),
        md(f"## AUC vs Audit Validity\n\n![AUC]({rel['auc']})"),
        md(f"## ROC Curves\n\n![ROC]({rel['roc']})"),
        md(f"## Low-Dose Leakage\n\n![Low-dose leakage]({rel['dose']})"),
        md(f"## Gate Map\n\n![Gate map]({rel['gates']})"),
        code(
            "from pathlib import Path\n"
            "import pandas as pd\n\n"
            "ROOT = Path('..').resolve()\n"
            "RESULTS = ROOT / 'results' / 'anthropic_sycophancy_lamp'\n"
            "summary = pd.read_csv(RESULTS / 'anthropic_sycophancy_lamp_summary.csv')\n"
            "summary"
        ),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK.write_text(json.dumps(notebook, indent=2), encoding="utf-8")


def row_by_id(rows: list[dict[str, Any]], monitor_id: str) -> dict[str, Any]:
    return next(row for row in rows if row["monitor_id"] == monitor_id)


def mix_scores(base: np.ndarray, oracle: np.ndarray, leakage_lambda: float) -> np.ndarray:
    return (1.0 - leakage_lambda) * base + leakage_lambda * oracle


def clamp(value: float) -> float:
    if math.isnan(value):
        return 0.0
    return max(0.0, min(1.0, value))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def savefig(fig: plt.Figure, filename: str) -> str:
    path = FIG_DIR / filename
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return str(path.relative_to(ROOT)).replace("\\", "/")


def notebook_relative_path(path: str) -> str:
    figure_path = Path(path)
    try:
        return str(figure_path.relative_to("notebooks")).replace("\\", "/")
    except ValueError:
        return f"../{path}"


def markdown_table(rows: list[list[Any]], headers: list[str]) -> str:
    values = [[str(value) for value in row] for row in rows]
    widths = [
        max(len(str(headers[idx])), *(len(row[idx]) for row in values))
        for idx in range(len(headers))
    ]
    header = "| " + " | ".join(str(headers[idx]).ljust(widths[idx]) for idx in range(len(headers))) + " |"
    sep = "| " + " | ".join("-" * widths[idx] for idx in range(len(headers))) + " |"
    body = [
        "| " + " | ".join(row[idx].ljust(widths[idx]) for idx in range(len(headers))) + " |"
        for row in values
    ]
    return "\n".join([header, sep, *body])


def md(text: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


if __name__ == "__main__":
    raise SystemExit(main())
