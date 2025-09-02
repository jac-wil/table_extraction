########################
# - table_utilities.py — Core OCR utilities
# - Defines OCRBox and helpers for slope correction and table extraction
########################

import json
import math
import numpy as np
from typing import List, Dict, Any, Tuple


# ────────────────────────────────
# Data Structures
# ────────────────────────────────
class OCRBox:
    def __init__(self, text: str, coords: List[Tuple[float, float]]):
        ########################
        # coords = [(x0,y0), (x1,y1), (x2,y2), (x3,y3)]
        # Order: top-left, top-right, bottom-right, bottom-left
        ########################
        if len(coords) != 4:
            raise ValueError("OCRBox requires 4 corner coordinates")
        self.text = text
        self.coords = coords

    @property
    def center(self) -> Tuple[float, float]:
        xs, ys = zip(*self.coords)
        return (sum(xs) / 4, sum(ys) / 4)

    @property
    def width(self) -> float:
        (x0,y0), (x1,y1), *_ = self.coords
        return ((x1 - x0)**2 + (y1 - y0)**2) ** 0.5

    @property
    def height(self) -> float:
        (x0,y0), *_ , (x3,y3) = self.coords
        return ((x3 - x0)**2 + (y3 - y0)**2) ** 0.5

    @property
    def slope(self) -> float:
        (x0,y0), (x1,y1), *_ = self.coords
        dx = max(x1 - x0, 1e-6)
        dy = y1 - y0
        return dy / dx


# ────────────────────────────────
# Step 1: Load OCR Output
# ────────────────────────────────
def load_ocr_json(path: str) -> List[OCRBox]:
    ########################
    # Load OCR output JSON and return list of OCRBox objects
    # Supports:
    #   - Polygon format: {"text": "foo", "coords": [[x0,y0],[x1,y1],[x2,y2],[x3,y3]]}
    #   - Rect format:    {"text": "foo", "x0":..,"y0":..,"x1":..,"y1":..}
    ########################
    with open(path, "r") as f:
        raw = json.load(f)

    boxes = []
    for blk in raw["blocks"]:
        text = blk.get("text", "")

        if "coords" in blk and len(blk["coords"]) == 4:
            coords = [tuple(pt) for pt in blk["coords"]]

        elif all(k in blk for k in ["x0", "y0", "x1", "y1"]):
            x0, y0, x1, y1 = blk["x0"], blk["y0"], blk["x1"], blk["y1"]
            coords = [(x0,y0), (x1,y0), (x1,y1), (x0,y1)]

        else:
            raise ValueError(f"Unrecognized OCR block format: {blk}")

        boxes.append(OCRBox(text, coords))

    return boxes


# ────────────────────────────────
# Step 2: Quadrant-Based Slope Correction
# ────────────────────────────────
def correct_slope(boxes: List[OCRBox]) -> List[OCRBox]:
    ########################
    # Estimate slope per quadrant and correct coordinates
    # Uses box width as weight
    ########################
    def get_quadrant(cx: float, cy: float) -> int:
        if cx < 0.5 and cy < 0.5: return 0       # top-left
        if cx >= 0.5 and cy < 0.5: return 1      # top-right
        if cx < 0.5 and cy >= 0.5: return 2      # bottom-left
        return 3                                 # bottom-right

    slope_sums, weight_sums = {q:0 for q in range(4)}, {q:0 for q in range(4)}
    for b in boxes:
        q = get_quadrant(*b.center)
        slope_sums[q] += b.slope * b.width
        weight_sums[q] += b.width

    avg_slopes = {
        q: (slope_sums[q] / weight_sums[q] if weight_sums[q] > 0 else 0.0)
        for q in range(4)
    }

    corrected = []
    for b in boxes:
        cx, cy = b.center
        q = get_quadrant(cx, cy)
        angle = math.atan(avg_slopes[q])

        cos_a, sin_a = math.cos(-angle), math.sin(-angle)

        new_coords = []
        for (x,y) in b.coords:
            x_shift, y_shift = x - 0.5, y - 0.5
            x_rot = x_shift * cos_a - y_shift * sin_a
            y_rot = x_shift * sin_a + y_shift * cos_a
            new_coords.append((x_rot + 0.5, y_rot + 0.5))

        corrected.append(OCRBox(b.text, new_coords))

    return corrected
