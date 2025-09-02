########################
# generate_synthetic.py — create synthetic OCR-like bounding boxes
########################

import json
import math
import random
from typing import List, Tuple


# ────────────────────────────────
# Quadrant Builder
# ────────────────────────────────
HEADERS = ["Units", "Pieces", "Weight", "Description", "Total"]
ROWS = [
    ["2", "10", "2000", "Steel Rods", "1500"],
    ["1", "50", "25", "Nails", "100"],
    ["4", "20", "400", "Lumber", "2200"],
    ["1", "200", "20", "Glue", "50"],
    ["", "", "", "Total Charge", "3850"],
]


def make_quad(text: str, x: float, y: float, w: float = 0.08, h: float = 0.03) -> dict:
    ########################
    # Create an axis-aligned quadrilateral for text box
    ########################
    coords = [
        (x, y),          # top-left
        (x + w, y),      # top-right
        (x + w, y + h),  # bottom-right
        (x, y + h),      # bottom-left
    ]
    return {"text": text, "coords": coords}


def rotate_point(x: float, y: float, angle: float, cx: float = 0.5, cy: float = 0.5) -> Tuple[float, float]:
    x_shift, y_shift = x - cx, y - cy
    x_rot = x_shift * math.cos(angle) - y_shift * math.sin(angle)
    y_rot = x_shift * math.sin(angle) + y_shift * math.cos(angle)
    return x_rot + cx, y_rot + cy


def apply_skew(boxes: List[dict], max_angle: float = 4) -> List[dict]:
    skewed = []
    for b in boxes:
        coords = b["coords"]
        cx = sum(x for x, _ in coords) / 4
        cy = sum(y for _, y in coords) / 4

        if cx < 0.5 and cy < 0.5:
            angle = math.radians(random.uniform(-max_angle, 0))   # top-left
        elif cx >= 0.5 and cy < 0.5:
            angle = math.radians(random.uniform(0, max_angle))    # top-right
        elif cx < 0.5 and cy >= 0.5:
            angle = math.radians(random.uniform(0, max_angle))    # bottom-left
        else:
            angle = math.radians(random.uniform(-max_angle, 0))   # bottom-right

        new_coords = [rotate_point(x, y, angle) for x, y in coords]
        skewed.append({"text": b["text"], "coords": new_coords})

    return skewed


def generate_synthetic(rows=ROWS, headers=HEADERS, out_path="sample_data/ocr_output.json"):
    boxes = []
    for i, h in enumerate(headers):
        x = 0.1 + i * 0.15
        boxes.append(make_quad(h, x, 0.1))

    for r, row in enumerate(rows):
        y = 0.2 + r * 0.08
        for i, val in enumerate(row):
            if not val:
                continue
            x = 0.1 + i * 0.15
            boxes.append(make_quad(val, x, y))

    skewed = apply_skew(boxes)

    output = {"blocks": skewed}

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Synthetic OCR polygons saved to {out_path}")


# ────────────────────────────────
# Main
# ────────────────────────────────
if __name__ == "__main__":
    generate_synthetic()
