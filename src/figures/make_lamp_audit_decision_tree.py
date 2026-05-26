#!/usr/bin/env python3
"""Render a horizontal pixel-style LAMP audit decision tree."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "figures" / "lamp_audit_decision_tree.png"
OUT_SPACIOUS = ROOT / "paper" / "figures" / "lamp_audit_decision_tree_spacious.png"
OUT_HORIZONTAL = ROOT / "paper" / "figures" / "lamp_audit_decision_tree_horizontal.png"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    base = Image.new("RGB", (740, 198), "white")
    draw = ImageDraw.Draw(base)
    font = ImageFont.load_default_imagefont()

    main_y = 52
    box_h = 26
    boxes = [
        ("Latent-state claim", 78, 138, True),
        ("Temporal isolation", 230, 132, False),
        ("Matched cohorts", 374, 124, False),
        ("Negative controls", 520, 138, False),
        ("PASS", 666, 64, True),
    ]

    for label, x, width, bold in boxes:
        draw_box(draw, x, main_y, width, box_h, label, font, bold=bold)

    for (_, x0, w0, _), (_, x1, w1, _) in zip(boxes[:-1], boxes[1:]):
        draw_arrow(draw, (x0 + w0 // 2 + 6, main_y), (x1 - w1 // 2 - 6, main_y))

    fail_y = 118
    for label, x in [
        ("FAIL -> Leakage", boxes[1][1]),
        ("FAIL -> Shortcut", boxes[2][1]),
        ("FAIL -> Contamination", boxes[3][1]),
    ]:
        draw_arrow(draw, (x, main_y + box_h // 2 + 7), (x, fail_y - 13))
        draw_centered_text(draw, (x, fail_y), label, font)

    draw.line((252, 164, 488, 164), fill="black", width=1)
    draw_centered_text(draw, (370, 183), "LAMP Audit Protocol", font, bold=True)

    final = base.resize((base.width * 5, base.height * 5), Image.Resampling.NEAREST)
    for out in (OUT, OUT_SPACIOUS, OUT_HORIZONTAL):
        final.save(out)
        print(out)
    return 0


def draw_box(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    label: str,
    font: ImageFont.ImageFont,
    *,
    bold: bool,
) -> None:
    draw.rectangle(
        (x - width // 2, y - height // 2, x + width // 2, y + height // 2),
        outline="black",
        width=1,
    )
    draw_centered_text(draw, (x, y), label, font, bold=bold)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    *,
    bold: bool = False,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = center[0] - width // 2
    y = center[1] - height // 2 - 1
    draw.text((x, y), text, fill="black", font=font)
    if bold:
        draw.text((x + 1, y), text, fill="black", font=font)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
) -> None:
    draw.line((start[0], start[1], end[0], end[1]), fill="black", width=1)
    if start[1] == end[1]:
        direction = 1 if end[0] > start[0] else -1
        tip = end
        draw.polygon(
            [
                tip,
                (tip[0] - 7 * direction, tip[1] - 4),
                (tip[0] - 7 * direction, tip[1] + 4),
            ],
            fill="black",
        )
    else:
        direction = 1 if end[1] > start[1] else -1
        tip = end
        draw.polygon(
            [
                tip,
                (tip[0] - 4, tip[1] - 7 * direction),
                (tip[0] + 4, tip[1] - 7 * direction),
            ],
            fill="black",
        )


if __name__ == "__main__":
    raise SystemExit(main())
