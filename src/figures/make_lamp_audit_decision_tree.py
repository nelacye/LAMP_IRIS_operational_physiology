#!/usr/bin/env python3
"""Render the LAMP audit decision tree figure."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "figures" / "lamp_audit_decision_tree.png"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.4, 8.9), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    center_x = 0.35
    node_w = 0.38
    node_h = 0.074
    fail_x = 0.78
    fail_w = 0.24
    fail_h = 0.062

    nodes = [
        ("Latent-state claim", 0.86),
        ("Temporal isolation", 0.70),
        ("Matched cohorts", 0.53),
        ("Negative controls", 0.36),
        ("PASS", 0.19),
    ]

    for text, y in nodes:
        draw_box(
            ax,
            center_x,
            y,
            node_w,
            node_h,
            text,
            fontsize=12.2 if text != "PASS" else 14.5,
            weight="bold" if text in {"Latent-state claim", "PASS"} else "normal",
        )

    for (_, y0), (_, y1) in zip(nodes[:-1], nodes[1:]):
        draw_arrow(
            ax,
            (center_x, y0 - node_h / 2 - 0.008),
            (center_x, y1 + node_h / 2 + 0.008),
        )

    fail_branches = [
        (0.70, "Leakage"),
        (0.53, "Shortcut"),
        (0.36, "Contamination"),
    ]
    for y, outcome in fail_branches:
        start = (center_x + node_w / 2 + 0.012, y)
        end = (fail_x - fail_w / 2 - 0.018, y)
        draw_arrow(ax, start, end)
        ax.text(
            (start[0] + end[0]) / 2,
            y + 0.020,
            "FAIL",
            ha="center",
            va="bottom",
            fontsize=9.6,
            fontweight="bold",
            color="black",
        )
        draw_box(ax, fail_x, y, fail_w, fail_h, outcome, fontsize=11.8)

    ax.text(
        0.5,
        0.065,
        "LAMP Audit Protocol",
        ha="center",
        va="center",
        fontsize=14.2,
        fontweight="bold",
        color="black",
    )

    ax.plot([0.28, 0.72], [0.105, 0.105], color="black", linewidth=1.2)

    fig.savefig(OUT, bbox_inches="tight", facecolor="white", pad_inches=0.18)
    plt.close(fig)
    print(OUT)
    return 0


def draw_box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    fontsize: float,
    weight: str = "normal",
) -> None:
    box = FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.012",
        linewidth=1.6,
        edgecolor="black",
        facecolor="white",
    )
    ax.add_patch(box)
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


def draw_arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=1.55,
        color="black",
        shrinkA=0,
        shrinkB=0,
    )
    ax.add_patch(arrow)


if __name__ == "__main__":
    raise SystemExit(main())
