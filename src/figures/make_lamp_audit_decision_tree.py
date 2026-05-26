#!/usr/bin/env python3
"""Render a horizontal black-and-white LAMP audit decision tree."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "figures" / "lamp_audit_decision_tree.png"
OUT_SPACIOUS = ROOT / "paper" / "figures" / "lamp_audit_decision_tree_spacious.png"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update(
        {
            "font.family": "serif",
            "axes.linewidth": 0.8,
        }
    )
    fig, ax = plt.subplots(figsize=(13.5, 4.8), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    main_y = 0.68
    box_h = 0.115
    labels = [
        "Latent-state claim",
        "Temporal isolation",
        "Matched cohorts",
        "Negative controls",
        "PASS",
    ]
    xs = [0.115, 0.33, 0.535, 0.74, 0.915]
    widths = [0.185, 0.175, 0.170, 0.175, 0.095]

    for label, x, width in zip(labels, xs, widths):
        draw_box(
            ax,
            x,
            main_y,
            width,
            box_h,
            label,
            fontsize=10.7 if label != "PASS" else 11.3,
            weight="bold" if label in {"Latent-state claim", "PASS"} else "normal",
        )

    for i in range(len(xs) - 1):
        draw_arrow(
            ax,
            (xs[i] + widths[i] / 2 + 0.006, main_y),
            (xs[i + 1] - widths[i + 1] / 2 - 0.006, main_y),
            linewidth=1.05,
            scale=10,
        )

    fail_branches = [
        (xs[1], "Leakage"),
        (xs[2], "Shortcut"),
        (xs[3], "Contamination"),
    ]
    fail_y = 0.34
    for x, outcome in fail_branches:
        draw_arrow(
            ax,
            (x, main_y - box_h / 2 - 0.025),
            (x, fail_y + 0.050),
            linewidth=1.0,
            scale=9.5,
        )
        ax.text(
            x,
            fail_y,
            f"FAIL -> {outcome}",
            ha="center",
            va="center",
            fontsize=10.6,
            color="black",
        )

    ax.plot([0.31, 0.69], [0.130, 0.130], color="black", linewidth=0.75)
    ax.text(
        0.5,
        0.065,
        "LAMP Audit Protocol",
        ha="center",
        va="center",
        fontsize=13.2,
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
