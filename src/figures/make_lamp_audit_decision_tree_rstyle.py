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
    fig, ax = plt.subplots(figsize=(12.8, 5.2), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    main_y = 0.68
    xs = [0.115, 0.33, 0.535, 0.74, 0.915]
    widths = [0.185, 0.175, 0.170, 0.175, 0.095]
    labels = [
        "Latent-state claim",
        "Temporal isolation",
        "Matched cohorts",
        "Negative controls",
        "PASS",
    ]

    for label, x, width in zip(labels, xs, widths):
        draw_rect(
            ax,
            x,
            main_y,
            label,
            width=width,
            bold=label in {"Latent-state claim", "PASS"},
        )

    for i in range(len(xs) - 1):
        start_x = xs[i] + widths[i] / 2 + 0.006
        end_x = xs[i + 1] - widths[i + 1] / 2 - 0.006
        draw_arrow(ax, (start_x, main_y), (end_x, main_y))

    fail_y = 0.34
    for x, outcome in zip(
        xs[1:4],
        ["FAIL -> Leakage", "FAIL -> Shortcut", "FAIL -> Contamination"],
    ):
        draw_arrow(ax, (x, main_y - 0.083), (x, fail_y + 0.050))
        ax.text(x, fail_y, outcome, ha="center", va="center", fontsize=10.6)

    ax.plot([0.31, 0.69], [0.130, 0.130], color="black", linewidth=0.9)
    ax.text(
        0.50,
        0.065,
        "LAMP Audit Protocol",
        ha="center",
        va="center",
        fontsize=13.2,
        fontweight="bold",
    )

    fig.savefig(OUT, bbox_inches="tight", facecolor="white", pad_inches=0.18)
    plt.close(fig)
    print(OUT)
    return 0


def draw_rect(ax: plt.Axes, x: float, y: float, label: str, width: float, bold: bool) -> None:
    height = 0.110
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
        fontsize=10.7 if bold else 10.4,
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
