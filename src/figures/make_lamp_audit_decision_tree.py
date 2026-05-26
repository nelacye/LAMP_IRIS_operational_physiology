#!/usr/bin/env python3
"""Render a horizontal terminal-style LAMP audit decision tree."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "figures" / "lamp_audit_decision_tree.png"
OUT_SPACIOUS = ROOT / "paper" / "figures" / "lamp_audit_decision_tree_spacious.png"
OUT_HORIZONTAL = ROOT / "paper" / "figures" / "lamp_audit_decision_tree_horizontal.png"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    base = Image.new("RGB", (4200, 1180), "white")
    draw = ImageDraw.Draw(base)
    font = load_font(54)
    bold_font = load_font(60)
    small_font = load_font(46)

    main_y = 315
    box_h = 170
    boxes = [
        ("Latent-state claim", 450, 730, True),
        ("Temporal isolation", 1270, 700, False),
        ("Matched cohorts", 2050, 650, False),
        ("Negative controls", 2830, 710, False),
        ("PASS", 3740, 340, True),
    ]

    for label, x, width, bold in boxes:
        draw_box(
            draw,
            x,
            main_y,
            width,
            box_h,
            label,
            bold_font if bold else font,
        )

    for (_, x0, w0, _), (_, x1, w1, _) in zip(boxes[:-1], boxes[1:]):
        draw_arrow(draw, (x0 + w0 // 2 + 36, main_y), (x1 - w1 // 2 - 36, main_y))

    fail_y = 700
    for label, x in [
        ("FAIL -> Leakage", boxes[1][1]),
        ("FAIL -> Shortcut", boxes[2][1]),
        ("FAIL -> Contamination", boxes[3][1]),
    ]:
        draw_arrow(draw, (x, main_y + box_h // 2 + 48), (x, fail_y - 58))
        draw_centered_text(draw, (x, fail_y), label, small_font)

    draw.line((1390, 945, 2810, 945), fill="black", width=7)
    draw_centered_text(draw, (2100, 1040), "LAMP Audit Protocol", bold_font)

    for out in (OUT, OUT_SPACIOUS, OUT_HORIZONTAL):
        base.save(out)
        print(out)
    return 0


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


def draw_box(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    label: str,
    font: ImageFont.ImageFont,
) -> None:
    draw.rectangle(
        (x - width // 2, y - height // 2, x + width // 2, y + height // 2),
        outline="black",
        width=8,
    )
    draw_centered_text(draw, (x, y), label, font)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = center[0] - width // 2
    y = center[1] - height // 2 - 1
    draw.text((x, y), text, fill="black", font=font)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
) -> None:
    draw.line((start[0], start[1], end[0], end[1]), fill="black", width=8)
    if start[1] == end[1]:
        direction = 1 if end[0] > start[0] else -1
        tip = end
        draw.polygon(
            [
                tip,
                (tip[0] - 42 * direction, tip[1] - 24),
                (tip[0] - 42 * direction, tip[1] + 24),
            ],
            fill="black",
        )
    else:
        direction = 1 if end[1] > start[1] else -1
        tip = end
        draw.polygon(
            [
                tip,
                (tip[0] - 24, tip[1] - 42 * direction),
                (tip[0] + 24, tip[1] - 42 * direction),
            ],
            fill="black",
        )


if __name__ == "__main__":
    raise SystemExit(main())
