########################
# - table_reconstruction.py — Debug and visualize tabular data
########################

import json
import math
import numpy as np
from typing import List
import matplotlib.pyplot as plt
from shapely.affinity import rotate
from shapely.geometry import Polygon
from table_utilities import OCRBox, load_ocr_json, correct_slope


# ────────────────────────────────
# Quadrant Helper
# ────────────────────────────────
def get_quadrant(cx: float, cy: float) -> int:
    if cx < 0.5 and cy < 0.5: return 0
    if cx >= 0.5 and cy < 0.5: return 1
    if cx < 0.5 and cy >= 0.5: return 2
    return 3

QUAD_COLORS = {0:"red", 1:"blue", 2:"purple", 3:"green"}


# ────────────────────────────────
# Visualization
# ────────────────────────────────
def box_angle(b: OCRBox) -> float:
    ########################
    # - Return angle (degrees) of top edge
    ########################
    (x0,y0), (x1,y1), *_ = b.coords
    angle_rad = math.atan2(y1 - y0, x1 - x0)
    return math.degrees(angle_rad)


def cluster_rows(y_values, tol=0.02):
    ########################
    # - Collapse nearby y-values into a single representative (mean)
    # - Example: [0.11,0.12,0.13,0.21,0.22] → [0.12, 0.215]
    ########################
    if not y_values:
        return []
    clustered = []
    current_group = [y_values[0]]

    for y in y_values[1:]:
        if abs(y - np.mean(current_group)) <= tol:
            current_group.append(y)
        else:
            clustered.append(np.mean(current_group))
            current_group = [y]
    clustered.append(np.mean(current_group))
    return clustered


def plot_table_grid(ax, boxes: List[OCRBox], headers: List[str], footers: List[str], title: str):
    ########################
    # - Draw table before corrections
    ########################
    all_x = [x for b in boxes for (x, _) in b.coords]
    all_y = [y for b in boxes for (_, y) in b.coords]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)

    header_boxes = [b for b in boxes if b.text.lower() and any(b.text.lower() in h.lower() for h in headers)]

    lefts = [min(x for x, _ in b.coords) for b in header_boxes]
    right = max(max(x for x, _ in b.coords) for b in header_boxes)
    col_edges = sorted(lefts + [right])

    header_top = min(y for b in boxes if any(h.lower() in b.text.lower() for h in headers) for (_, y) in b.coords)
    footer_bottom = max(y for b in boxes if any(f.lower() in b.text.lower() for f in footers) for (_, y) in b.coords)

    raw_item_rows = sorted({round(b.center[1], 3) for b in boxes if (header_top*1.15) < b.center[1] < (footer_bottom*.85)})
    item_rows = cluster_rows(raw_item_rows, tol=0.02)

    n_items = len(item_rows)
    n_rows = 1 + n_items + 1

    row_edges = np.linspace(header_top, footer_bottom, n_rows + 1)

    row_edges = [r for r in row_edges if r <= footer_bottom]

    row_height = 0.01
    padding = row_height * 0.02

    ax.plot([x_min, x_max], [y_min - padding, y_min - padding], color="black", linewidth=1.5)
    ax.plot([x_min, x_max], [y_max + padding, y_max + padding], color="black", linewidth=1.5)
    ax.plot([x_min, x_min], [y_min - padding, y_max + padding], color="black", linewidth=1.5)
    ax.plot([x_max, x_max], [y_min - padding, y_max + padding], color="black", linewidth=1.5)

    for x in col_edges[1:-1]:
        ax.plot([x, x], [y_min - padding, y_max + padding], color="lightgray", linewidth=0.8)

    for i, y in enumerate(row_edges):
        y_top = y - padding / 2
        y_bottom = y + padding / 2

        is_header = (i == 0)
        is_total = (abs(y - footer_bottom) < 1e-3) if footer_bottom else False
        lw = 1.5 if (is_header or is_total) else 0.8

        ax.plot([x_min, x_max], [y_top, y_top], color="black" if (is_header or is_total) else "gray", linewidth=lw)

    for b in boxes:
        cx, cy = b.center
        angle = box_angle(b)

        is_header = any(h.lower() in b.text.lower() for h in headers) and b.text.lower() not in footers
        is_total  = any(f.lower() in b.text.lower() for f in footers) and b.text.lower() not in headers

        fontweight = "bold" if (is_header or is_total) else "normal"
        fontsize = 8 if (is_header or is_total) else 7

        color = QUAD_COLORS[get_quadrant(cx, cy)]
        poly = plt.Polygon(b.coords, fill=False, edgecolor=color, linewidth=0.8)
        ax.add_patch(poly)

        ax.text(
            cx, cy, b.text,
            fontsize=fontsize, weight=fontweight,
            color=color,
            ha="center", va="center",
            rotation=-angle, rotation_mode="anchor"
        )

    ax.set_title(title)
    ax.set_xlim(x_min - 0.02, x_max + 0.02)
    ax.set_ylim(y_min - 0.02, y_max + 0.02)
    ax.invert_yaxis()
    ax.axis("off")


def plot_table_grid_auto(ax, boxes: List[OCRBox], headers: List[str], footers: List[str], title: str):
    ########################
    # - Draw reconstructed table
    ########################
    all_x = [x for b in boxes for (x, _) in b.coords]
    all_y = [y for b in boxes for (_, y) in b.coords]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)

    header_boxes = [b for b in boxes if b.text.lower() and any(b.text.lower() in h.lower() for h in headers)]

    if header_boxes:
        lefts = [min(x for x, _ in b.coords) for b in header_boxes]
        right = max(max(x for x, _ in b.coords) for b in header_boxes)
        col_edges = sorted(lefts + [right])
    else:
        col_edges = np.linspace(x_min, x_max, len(headers)+1)

    n_cols = len(col_edges) - 1

    header_top = min(y for b in boxes if any(h.lower() in b.text.lower() for h in headers) for (_, y) in b.coords)
    footer_bottom = max(y for b in boxes if any(f.lower() in b.text.lower() for f in footers) for (_, y) in b.coords)

    raw_item_rows = sorted({round(b.center[1], 3) for b in boxes if (header_top*1.2) < b.center[1] < (footer_bottom*.8)})
    item_rows = cluster_rows(raw_item_rows, tol=0.02)

    n_items = len(item_rows)
    n_rows = 1 + n_items + 1

    row_edges = np.linspace(header_top, footer_bottom, n_rows + 1)

    ax.plot([x_min, x_max], [y_min, y_min], color="black", linewidth=1.5)
    ax.plot([x_min, x_max], [footer_bottom, footer_bottom], color="black", linewidth=1.5)
    ax.plot([x_min, x_min], [y_min, footer_bottom], color="black", linewidth=1.5)
    ax.plot([x_max, x_max], [y_min, footer_bottom], color="black", linewidth=1.5)

    for x in col_edges[1:-1]:
        ax.plot([x, x], [y_min, footer_bottom], color="gray", linewidth=0.8)

    for y in row_edges[1:-1]:
        is_header_line = abs(y - row_edges[1]) < 1e-3
        is_footer_line = abs(y - row_edges[-2]) < 1e-3
        lw = 1.5 if (is_header_line or is_footer_line) else 0.8
        ax.plot([x_min, x_max], [y, y], color="black", linewidth=lw)

    row_centers = [(row_edges[i] + row_edges[i+1]) / 2 for i in range(n_rows)]
    col_centers = [(col_edges[i] + col_edges[i+1]) / 2 for i in range(n_cols)]

    for b in boxes:
        cx, cy = b.center
        nearest_row = min(row_centers, key=lambda r: abs(cy - r))
        nearest_col = min(col_centers, key=lambda c: abs(cx - c))

        is_header = any(h.lower() in b.text.lower() for h in headers)
        is_total = "total" in b.text.lower()

        fontweight = "bold" if (is_header or is_total) else "normal"
        fontsize = 8 if (is_header or is_total) else 7

        ax.text(
            nearest_col, nearest_row, b.text,
            fontsize=fontsize, weight=fontweight,
            color="black", ha="center", va="center"
        )
    ax.set_title(title)
    ax.set_xlim(x_min - 0.02, x_max + 0.02)
    ax.set_ylim(y_min - 0.02, footer_bottom + 0.02)
    ax.invert_yaxis()
    ax.axis("off")


# ────────────────────────────────
# Main
# ────────────────────────────────
if __name__ == "__main__":
    boxes = load_ocr_json("sample_data/ocr_output.json")
    corrected = correct_slope(boxes)

    headers = ["Units", "Pieces", "Weight", "Description", "Total"]
    footers = ["Total Charge", "Total Chg."]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    plot_table_grid(ax1, boxes, headers, footers, "Skewed Table")
    plot_table_grid_auto(ax2, corrected, headers, footers, "Reconstructed Tabular Data")
    plt.tight_layout()
    plt.show()
