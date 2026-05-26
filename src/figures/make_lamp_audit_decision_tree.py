#!/usr/bin/env python3
"""Render a compact black-and-white LAMP audit decision tree."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "figures" / "lamp_audit_decision_tree.png"
OUT_SPACIOUS = ROOT / "paper" / "figures" / "lamp_audit_decision_tree_spacious.png"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9.5, 11.5), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    x = 0.31
    box_w = 0.34
    box_h = 0.050
    y_positions = {
        "Latent-state claim": 0.90,
        "Temporal isolation": 0.68,
        "Matched cohorts": 0.46,
        "Negative controls": 0.24,
        "PASS": 0.055,
    }

    for label, y in y_positions.items():
        draw_box(
            ax,
            x,
            y,
            box_w,
            box_h,
            label,
            fontsize=12.4 if label != "PASS" else 13.2,
            weight="bold" if label in {"Latent-state claim", "PASS"} else "normal",
        )

    labels = list(y_positions)
    for upper, lower in zip(labels[:-1], labels[1:]):
        draw_arrow(
            ax,
            (x, y_positions[upper] - box_h / 2 - 0.026),
            (x, y_positions[lower] + box_h / 2 + 0.026),
            linewidth=1.05,
            scale=10,
        )

    fail_branches = [
        ("Temporal isolation", "Leakage"),
        ("Matched cohorts", "Shortcut"),
        ("Negative controls", "Contamination"),
    ]
    for source, outcome in fail_branches:
        y = y_positions[source]
        start = (x + box_w / 2 + 0.026, y)
        end = (0.62, y)
        draw_arrow(ax, start, end, linewidth=1.0, scale=9.5)
        ax.text(
            0.66,
            y,
            f"FAIL \u2192 {outcome}",
            ha="left",
            va="center",
            fontsize=11.5,
            color="black",
        )

    ax.plot([0.22, 0.78], [0.015, 0.015], color="black", linewidth=0.75)
    ax.text(
        0.5,
        -0.012,
        "LAMP Audit Protocol",
        ha="center",
        va="center",
        fontsize=13.6,
        fontweight="bold",
        color="black",
    )

    fig.savefig(OUT, bbox_inches="tight", facecolor="white", pad_inches=0.12)
    fig.savefig(OUT_SPACIOUS, bbox_inches="tight", facecolor="white", pad_inches=0.12)
    plt.close(fig)
    print(OUT)
    print(OUT_SPACIOUS)
    return 0


def draw_box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    fontsize: float,
    weight: str,
) -> None:
    rect = Rectangle(
        (x - width / 2, y - height / 2),
        width,
        height,
        linewidth=1.1,
        edgecolor="black",
        facecolor="white",
    )
    ax.add_patch(rect)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color="black",
    )


def draw_arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    linewidth: float,
    scale: float,
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=scale,
            linewidth=linewidth,
            color="black",
            shrinkA=0,
            shrinkB=0,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
