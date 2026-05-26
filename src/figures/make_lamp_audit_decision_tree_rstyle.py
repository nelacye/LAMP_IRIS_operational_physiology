#!/usr/bin/env python3
"""Render an old-school R/base-graphics style LAMP decision tree.

This mirrors `make_lamp_audit_decision_tree_rstyle.R` for environments without
R installed.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "figures" / "lamp_audit_decision_tree_rstyle.png"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 12,
            "axes.linewidth": 0.8,
        }
    )
    fig, ax = plt.subplots(figsize=(7.3, 9.3), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    x = 0.34
    ys = [0.88, 0.68, 0.48, 0.28, 0.10]
    labels = [
        "Latent-state claim",
        "Temporal isolation",
        "Matched cohorts",
        "Negative controls",
        "PASS",
    ]

    for label, y in zip(labels, ys):
        draw_rect(ax, x, y, label, bold=label in {"Latent-state claim", "PASS"})

    for upper, lower in zip(ys[:-1], ys[1:]):
        draw_arrow(ax, (x, upper - 0.062), (x, lower + 0.062))

    for y, outcome in zip(ys[1:4], ["FAIL -> Leakage", "FAIL -> Shortcut", "FAIL -> Contamination"]):
        draw_arrow(ax, (x + 0.205, y), (0.58, y))
        ax.text(0.62, y, outcome, ha="left", va="center", fontsize=12.3)

    ax.plot([0.26, 0.74], [0.037, 0.037], color="black", linewidth=0.9)
    ax.text(
        0.50,
        0.015,
        "LAMP Audit Protocol",
        ha="center",
        va="center",
        fontsize=14.0,
        fontweight="bold",
    )

    fig.savefig(OUT, bbox_inches="tight", facecolor="white", pad_inches=0.18)
    plt.close(fig)
    print(OUT)
    return 0


def draw_rect(ax: plt.Axes, x: float, y: float, label: str, bold: bool) -> None:
    width = 0.36
    height = 0.060
    ax.add_patch(
        Rectangle(
            (x - width / 2, y - height / 2),
            width,
            height,
            linewidth=1.05,
            edgecolor="black",
            facecolor="white",
        )
    )
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        fontsize=13.0 if bold else 12.4,
        fontweight="bold" if bold else "normal",
    )


def draw_arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.0,
            color="black",
            shrinkA=0,
            shrinkB=0,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
