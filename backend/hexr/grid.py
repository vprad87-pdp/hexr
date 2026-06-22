import math
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection


# ── Block 1: Coordinate generation ───────────────────────────────────────────

def hex_cells(radius):
    """Return all (q, r) axial coordinates inside a hex grid of given radius."""
    cells = []
    for q in range(-radius, radius + 1):
        for r in range(-radius, radius + 1):
            if abs(q + r) <= radius:
                cells.append((q, r))
    return cells


# ── Block 2: Coordinate conversion ───────────────────────────────────────────

def hex_to_pixel(q, r, size=20):
    """Convert axial (q, r) to pixel (x, y). Flat-top hex orientation."""
    x = size * (3 / 2 * q)
    y = size * (math.sqrt(3) / 2 * q + math.sqrt(3) * r)
    return x, y


def hex_corners(cx, cy, size):
    """Return the 6 corner points of a flat-top hexagon centered at (cx, cy)."""
    corners = []
    for i in range(6):
        angle_rad = math.radians(60 * i)
        x = cx + size * math.cos(angle_rad)
        y = cy + size * math.sin(angle_rad)
        corners.append((x, y))
    return corners


# ── Block 3: Rendering ────────────────────────────────────────────────────────

def render_grid(radius=5, cell_size=20, output_path="hexr_grid.png"):
    """Render a blank HexR grid and save it as a PNG."""
    cells = hex_cells(radius)

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')
    ax.axis('off')

    for (q, r) in cells:
        cx, cy = hex_to_pixel(q, r, cell_size)
        corners = hex_corners(cx, cy, cell_size * 0.95)   # 0.95 leaves a small gap
        patch = Polygon(corners, closed=True,
                        facecolor='white', edgecolor='black', linewidth=0.5)
        ax.add_patch(patch)

    # Fit the axes tightly around all drawn cells
    all_pixels = [hex_to_pixel(q, r, cell_size) for q, r in cells]
    xs = [p[0] for p in all_pixels]
    ys = [p[1] for p in all_pixels]
    margin = cell_size * 2
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)

    total = len(cells)
    plt.title(f"HexR Grid — Radius {radius} — {total} cells", fontsize=13)
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#f5f5f5')
    print(f"Saved: {output_path}  ({total} cells)")


if __name__ == "__main__":
    render_grid(radius=5, cell_size=20, output_path="hexr_grid_r5.png")
    render_grid(radius=10, cell_size=12, output_path="hexr_grid_r10.png")
