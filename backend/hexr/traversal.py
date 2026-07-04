import math


# Six directions for walking clockwise around a hex ring (flat-top axial coords)
_DIRECTIONS = [
    (1, 0), (1, -1), (0, -1),
    (-1, 0), (-1, 1), (0, 1)
]


# ── Block 1: Spiral traversal ─────────────────────────────────────────────────

def spiral_traversal(radius):
    """
    Return all (q, r) coordinates in spiral order: center → ring 1 → ring 2 → ...
    Within each ring, cells are ordered clockwise from the bottom-left corner.
    The index of each cell in this list is its 'bit slot' during encoding.
    """
    cells = [(0, 0)]  # Ring 0: just the center cell

    for ring in range(1, radius + 1):
        # Bottom-left corner of this ring: direction 4 * ring steps from center
        q, r = -ring, ring

        for direction in range(6):
            for _ in range(ring):
                cells.append((q, r))
                dq, dr = _DIRECTIONS[direction]
                q += dq
                r += dr

    return cells


# ── Block 2: Verification ─────────────────────────────────────────────────────

def verify_traversal(radius):
    """Check that spiral covers every cell exactly once (no gaps, no duplicates)."""
    from hexr.grid import hex_cells

    expected = set(hex_cells(radius))
    actual   = spiral_traversal(radius)

    duplicates = len(actual) != len(set(actual))
    missing    = expected - set(actual)
    extra      = set(actual) - expected

    print(f"Radius {radius}: {len(actual)} cells traversed")
    print(f"  Duplicates : {duplicates}")
    print(f"  Missing    : {len(missing)}")
    print(f"  Extra      : {len(extra)}")
    print(f"  OK         : {not duplicates and not missing and not extra}")
    return not duplicates and not missing and not extra


# ── Block 3: Visualise the order ──────────────────────────────────────────────

def render_traversal(radius=4, cell_size=30, output_path="hexr_traversal.png"):
    """Draw the grid with each cell numbered in traversal order."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from hexr.grid import hex_to_pixel, hex_corners

    order = spiral_traversal(radius)

    fig, ax = plt.subplots(figsize=(12, 12))
    ax.set_aspect('equal')
    ax.axis('off')

    for idx, (q, r) in enumerate(order):
        cx, cy = hex_to_pixel(q, r, cell_size)
        corners = hex_corners(cx, cy, cell_size * 0.9)

        # Colour rings differently so the spiral pattern is obvious
        ring = max(abs(q), abs(r), abs(q + r))
        colors = ['#ffe0b2', '#fff9c4', '#c8e6c9', '#b3e5fc',
                  '#e1bee7', '#fce4ec', '#f0f4c3', '#e0f2f1']
        face = colors[ring % len(colors)]

        patch = Polygon(corners, closed=True,
                        facecolor=face, edgecolor='#555', linewidth=0.6)
        ax.add_patch(patch)
        ax.text(cx, cy, str(idx), ha='center', va='center',
                fontsize=7 if radius > 4 else 9, color='#222')

    all_px = [hex_to_pixel(q, r, cell_size) for q, r in order]
    xs = [p[0] for p in all_px]
    ys = [p[1] for p in all_px]
    margin = cell_size * 2
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)

    plt.title(f"HexR Spiral Traversal — Radius {radius} — {len(order)} cells", fontsize=13)
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#f9f9f9')
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    print("=== Verification ===")
    for r in [1, 5, 10]:
        verify_traversal(r)

    print("\n=== Rendering ===")
    render_traversal(radius=4, cell_size=30, output_path="hexr_traversal_r4.png")
    render_traversal(radius=7, cell_size=18, output_path="hexr_traversal_r7.png")
