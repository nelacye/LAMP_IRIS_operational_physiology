#!/usr/bin/env python3
"""Run a harmless eval-awareness / sandbagging-style LAMP audit battery."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lamp.audit import run_audit  # noqa: E402
from lamp.datasets.framing_audit import build_eval_awareness_frame  # noqa: E402
from lamp.monitors.eval_awareness import MONITORS, build_monitor_config  # noqa: E402


OUT = ROOT / "results" / "eval_awareness_lamp"
NOTEBOOK = ROOT / "notebooks" / "eval_awareness_lamp_audit.ipynb"
FIG_DIR = ROOT / "notebooks" / "figures"
PREDICTIONS = OUT / "eval_awareness_predictions.csv"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    rows = build_eval_awareness_frame()
    write_csv(PREDICTIONS, rows)

    summary_rows = []
    for monitor in MONITORS:
        config = build_monitor_config(monitor)
        config_path = OUT / "configs" / f"{monitor['id']}.yaml"
        write_yaml(config_path, config)
        result = run_audit(config_path, PREDICTIONS, OUT / "lamp" / monitor["id"])
        summary_rows.append(summary_row(monitor, result))

    summary_path = OUT / "eval_awareness_lamp_summary.csv"
    write_csv(summary_path, summary_rows)

    figure_paths = build_figures(rows, summary_rows)
    write_report(OUT / "eval_awareness_lamp_report.md", rows, summary_rows, figure_paths)
    build_notebook(summary_rows, figure_paths)

    print(
        json.dumps(
            {
                "rows": len(rows),
                "summary": str(summary_path),
                "report": str(OUT / "eval_awareness_lamp_report.md"),
                "notebook": str(NOTEBOOK),
            },
            indent=2,
        )
    )
    return 0


def summary_row(monitor: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    dossier = result["failure_mode_dossier"]
    matching = result["visible_state_matching"]
    oracle_relation = result["sentinel_relations"].get("oracle_label", {})
    return {
        "monitor_id": monitor["id"],
        "monitor_name": monitor["name"],
        "monitor_type": monitor["type"],
        "score_column": monitor["score"],
        "auc": result["primary_score"]["auc"],
        "audit_pass": dossier["audit_pass_candidate"],
        "output_classes": "; ".join(dossier["output_classes"]),
        "temporal_passed": result["temporal_isolation"]["passed"],
        "forbidden_passed": result["forbidden_feature_screen"]["passed"],
        "matched_delta": matching.get("matched_observed_state_delta"),
        "oracle_proximity": oracle_relation.get("auc_leakage_proximity"),
        "oracle_proximity_alert": oracle_relation.get("oracle_proximity_alert"),
        "description": monitor["description"],
    }


def build_figures(rows: list[dict[str, Any]], summary: list[dict[str, Any]]) -> dict[str, str]:
    roc_path = FIG_DIR / "eval_awareness_roc_curves.png"
    image = Image.new("RGB", (1500, 980), "white")
    draw = ImageDraw.Draw(image)
    font = load_font(24)
    small = load_font(18)
    draw.text((70, 40), "Eval-awareness framing audit ROC curves", fill="black", font=font)
    plot = (110, 120, 930, 860)
    draw_axes(draw, plot)
    colors = ["black", "#555555", "#888888", "#222222", "#777777", "#aaaaaa", "#444444", "#bbbbbb"]
    legend_y = 135
    color_idx = 0
    label_values = [int(row["label_sandbagging"]) for row in rows]
    for row in summary:
        if row["monitor_id"] in {
            "valid_framing_sensitivity",
            "surface_shortcut",
            "answer_key_leak",
            "rubric_leak",
            "lowdose_oracle_1pct",
            "lowdose_oracle_5pct",
            "lowdose_oracle_10pct",
            "null_noise",
        }:
            scores = [float(item[row["score_column"]]) for item in rows]
            points = roc_points(label_values, scores)
            color = colors[color_idx % len(colors)]
            draw_polyline(draw, points, plot, color=color, width=4)
            draw.line((980, legend_y + 10, 1040, legend_y + 10), fill=color, width=4)
            draw.text(
                (1055, legend_y),
                f"{row['monitor_id']} (AUC={float(row['auc']):.3f})",
                fill="black",
                font=small,
            )
            legend_y += 36
            color_idx += 1
    draw.line((plot[0], plot[3], plot[2], plot[1]), fill="#999999", width=2)
    image.save(roc_path)

    status_path = FIG_DIR / "eval_awareness_lamp_status.png"
    status = Image.new("RGB", (1500, 820), "white")
    sdraw = ImageDraw.Draw(status)
    sdraw.text((70, 40), "Same performance scale, different LAMP diagnoses", fill="black", font=font)
    left, top, width = 430, 110, 820
    for idx, row in enumerate(summary):
        y = top + idx * 70
        sdraw.text((70, y), row["monitor_id"], fill="black", font=small)
        bar_w = int(width * max(0.0, min(1.0, (float(row["auc"]) - 0.35) / 0.67)))
        fill = "black" if row["audit_pass"] else "#8a8a8a"
        sdraw.rectangle((left, y, left + bar_w, y + 28), fill=fill)
        sdraw.rectangle((left, y, left + width, y + 28), outline="black", width=2)
        sdraw.text((left + width + 25, y - 2), f"AUC {float(row['auc']):.3f}", fill="black", font=small)
    for threshold, label in [(0.60, "valid"), (0.95, "oracle")]:
        x = left + int(width * ((threshold - 0.35) / 0.67))
        sdraw.line((x, top - 15, x, top + len(summary) * 70), fill="black", width=2)
        sdraw.text((x - 35, top + len(summary) * 70 + 12), label, fill="black", font=small)
    status.save(status_path)

    timeline_path = FIG_DIR / "eval_awareness_timeline_examples.png"
    example = next(row for row in rows if row["condition"] == "evaluation")
    timeline = Image.new("RGB", (1500, 460), "white")
    tdraw = ImageDraw.Draw(timeline)
    tdraw.text(
        (70, 35),
        "Allowed pre-response signal vs forbidden answer-key channel",
        fill="black",
        font=font,
    )
    steps = ["prompt", "pre-response probe", "response", "answer key forbidden"]
    values = [
        float(example["eval_framing_token"]),
        float(example["valid_framing_monitor_score"]),
        float(example["surface_shortcut_score"]),
        float(example["answer_key_leak_score"]),
    ]
    chart = (130, 120, 1370, 340)
    tdraw.line((chart[0], chart[3], chart[2], chart[3]), fill="black", width=3)
    tdraw.line((chart[0], chart[1], chart[0], chart[3]), fill="black", width=3)
    points = []
    for idx, value in enumerate(values):
        x = chart[0] + int(idx * (chart[2] - chart[0]) / (len(values) - 1))
        y = chart[3] - int(value * (chart[3] - chart[1]))
        points.append((x, y))
        tdraw.ellipse((x - 8, y - 8, x + 8, y + 8), fill="black")
        tdraw.text((x - 35, y - 42), f"{value:.2f}", fill="black", font=small)
        tdraw.text((x - 85, chart[3] + 24), steps[idx], fill="black", font=small)
    tdraw.line(points, fill="black", width=4)
    timeline.save(timeline_path)

    return {
        "roc": str(roc_path.relative_to(ROOT)).replace("\\", "/"),
        "status": str(status_path.relative_to(ROOT)).replace("\\", "/"),
        "timeline": str(timeline_path.relative_to(ROOT)).replace("\\", "/"),
    }


def write_report(
    path: Path,
    rows: list[dict[str, Any]],
    summary: list[dict[str, Any]],
    figure_paths: dict[str, str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LAMP Eval-Awareness / Sandbagging Framing Audit",
        "",
        "This harmless benchmark audits claims that a monitor detects evaluation-aware underperformance rather than prompt artifacts, surface response shortcuts, or hidden answer/rubric leakage.",
        "",
        "## Dataset",
        "",
        f"- Episodes: {len(rows)}",
        "- Domains: math, logic, code, and QA",
        "- Conditions: evaluation, deployment, neutral",
        "- Labels: simulated sandbagging-style underperformance under evaluation-aware framing",
        "- Forbidden channels: answer key, rubric hint, and benchmark/stage-token metadata",
        "",
        "## Figures",
        "",
        f"![ROC curves](../../{figure_paths['roc']})",
        "",
        f"![LAMP status](../../{figure_paths['status']})",
        "",
        f"![Timeline example](../../{figure_paths['timeline']})",
        "",
        "## Audit Summary",
        "",
        markdown_table(
            summary,
            [
                "monitor_id",
                "monitor_type",
                "auc",
                "audit_pass",
                "temporal_passed",
                "forbidden_passed",
                "matched_delta",
                "oracle_proximity",
                "output_classes",
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- The valid framing monitor uses only pre-response framing and probe signals and is expected to pass when it preserves matched-cohort signal.",
        "- Surface shortcuts can obtain apparent performance but should collapse under matched visible behavior.",
        "- Answer-key, rubric, stage-token, and low-dose oracle monitors are intentionally high-performing but fail LAMP because their information contract is invalid.",
        "- This is a direct evaluation-awareness analogue of the biomedical LAMP use case: performance alone is not validity.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_notebook(summary: list[dict[str, Any]], figure_paths: dict[str, str]) -> None:
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    summary_md = markdown_table(
        summary,
        ["monitor_id", "monitor_type", "auc", "audit_pass", "output_classes"],
    )
    cells = [
        markdown_cell(
            "# Eval-Awareness LAMP Audit\n\n"
            "Harmless capability tasks are evaluated under evaluation, deployment, and neutral framing. "
            "LAMP audits whether monitor performance reflects valid evaluation-awareness signal or leakage/shortcut behavior."
        ),
        markdown_cell("## Audit Summary\n\n" + summary_md),
        markdown_cell(f"## ROC Curves\n\n![ROC curves](figures/{Path(figure_paths['roc']).name})"),
        markdown_cell(f"## LAMP Diagnoses\n\n![LAMP status](figures/{Path(figure_paths['status']).name})"),
        markdown_cell(f"## Timeline Example\n\n![Timeline](figures/{Path(figure_paths['timeline']).name})"),
        markdown_cell(
            "## Takeaway\n\n"
            "The benchmark illustrates detection of evaluation gaming in neural/LLM-style early-warning systems: "
            "a clean framing monitor can survive LAMP, while answer-key, rubric, stage-token, surface, and low-dose oracle variants fail for different reasons."
        ),
    ]
    payload = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def markdown_cell(source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def roc_points(labels: list[int], scores: list[float]) -> list[tuple[float, float]]:
    thresholds = sorted(set(scores), reverse=True)
    points = [(0.0, 0.0)]
    positives = sum(labels)
    negatives = len(labels) - positives
    for threshold in thresholds:
        tp = fp = 0
        for label, score in zip(labels, scores):
            if score >= threshold:
                if label:
                    tp += 1
                else:
                    fp += 1
        tpr = tp / positives if positives else 0.0
        fpr = fp / negatives if negatives else 0.0
        points.append((fpr, tpr))
    points.append((1.0, 1.0))
    return points


def draw_axes(draw: ImageDraw.ImageDraw, plot: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = plot
    draw.rectangle(plot, outline="black", width=3)
    font = load_font(18)
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        x = left + int(tick * (right - left))
        y = bottom - int(tick * (bottom - top))
        draw.line((x, bottom, x, bottom + 8), fill="black", width=2)
        draw.line((left - 8, y, left, y), fill="black", width=2)
        draw.text((x - 12, bottom + 14), f"{tick:g}", fill="black", font=font)
        draw.text((left - 45, y - 10), f"{tick:g}", fill="black", font=font)
    draw.text((left + 300, bottom + 52), "False positive rate", fill="black", font=font)
    draw.text((left - 78, top - 35), "TPR", fill="black", font=font)


def draw_polyline(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    plot: tuple[int, int, int, int],
    *,
    color: str,
    width: int,
) -> None:
    left, top, right, bottom = plot
    coords = [
        (
            left + int(fpr * (right - left)),
            bottom - int(tpr * (bottom - top)),
        )
        for fpr, tpr in points
    ]
    if len(coords) >= 2:
        draw.line(coords, fill=color, width=width)


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        values = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, float):
                value = f"{value:.3f}"
            values.append(str(value).replace("\n", " "))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/lucon.ttf"),
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/cour.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


if __name__ == "__main__":
    raise SystemExit(main())
