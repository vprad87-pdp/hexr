import matplotlib
matplotlib.use('Agg')   # headless backend — required on servers with no display
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from PIL import Image

from hexr.reed_solomon import encode, ECC_SYMBOLS
from hexr.traversal import spiral_traversal
from hexr.grid import hex_to_pixel, hex_corners
from hexr.finder import finder_cells, timing_cells


# Cell colours
_COLORS = {
    'data_1':    '#111111',   # data bit 1 — black
    'data_0':    '#ffffff',   # data bit 0 — white
    'unused':    '#e8e8e8',   # padding cells
    'finder_b':  '#1a237e',   # finder black — deep blue, visually distinct from data
    'finder_w':  '#e8eaf6',   # finder white — pale blue
    'timing_b':  '#4a148c',   # timing black — purple
    'timing_w':  '#f3e5f5',   # timing white — pale purple
}


# ── Block 1: Grid sizing (accounts for reserved cells) ───────────────────────

def minimum_radius(n_bits):
    """Smallest radius where (total cells − reserved cells) >= n_bits."""
    r = max(3, FINDER_RADIUS_MIN)
    while True:
        reserved = set(finder_cells(r)) | set(timing_cells(r))
        total    = 3 * r * r + 3 * r + 1
        if (total - len(reserved)) >= n_bits:
            return r
        r += 1

FINDER_RADIUS_MIN = 9   # finders need N≥9 so timing stop≥3 (required for scale detection)


# ── Block 2: Text → bitstream ─────────────────────────────────────────────────

def text_to_bits(text):
    """UTF-8 encode, Reed-Solomon protect, return list of bits (MSB first)."""
    raw     = text.encode('utf-8')
    encoded = encode(raw)
    bits = []
    for byte in encoded:
        for bit_pos in range(7, -1, -1):
            bits.append((byte >> bit_pos) & 1)
    return bits


# ── Block 3: Render ───────────────────────────────────────────────────────────

def render_hexr(text, output_path="hexr_encoded.png", cell_size=14):
    """Encode text and render a HexR image with finder hexagons and timing spoke."""
    bits   = text_to_bits(text)
    n_bits = len(bits)

    radius  = minimum_radius(n_bits)
    finders = finder_cells(radius)    # {(q,r): 'black'|'white'}
    timing  = timing_cells(radius)    # {(q,r): 'black'|'white'}
    reserved = {**finders, **timing}

    # Data cells in spiral order, skipping reserved
    all_cells  = spiral_traversal(radius)
    data_cells = [(q, r) for (q, r) in all_cells if (q, r) not in reserved]

    bit_map = {cell: bits[i] for i, cell in enumerate(data_cells) if i < n_bits}

    print(f"Text      : {repr(text)}")
    print(f"Bytes     : {len(text.encode('utf-8'))} data + {ECC_SYMBOLS} ECC")
    print(f"Bits      : {n_bits}")
    print(f"Grid      : radius {radius} -> {len(all_cells)} cells total")
    print(f"Reserved  : {len(reserved)} cells (finders + timing)")
    print(f"Data cells: {len(data_cells)} available, {n_bits} used")

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_aspect('equal')
    ax.axis('off')

    for (q, r) in all_cells:
        cx, cy   = hex_to_pixel(q, r, cell_size)
        corners  = hex_corners(cx, cy, cell_size * 0.95)

        if (q, r) in finders:
            face = _COLORS['finder_b'] if finders[(q,r)] == 'black' else _COLORS['finder_w']
            edge = '#3949ab'
        elif (q, r) in timing:
            face = _COLORS['timing_b'] if timing[(q,r)] == 'black' else _COLORS['timing_w']
            edge = '#7b1fa2'
        elif (q, r) in bit_map:
            face = _COLORS['data_1'] if bit_map[(q,r)] == 1 else _COLORS['data_0']
            edge = '#bbbbbb'
        else:
            face = _COLORS['unused']
            edge = '#cccccc'

        patch = Polygon(corners, closed=True,
                        facecolor=face, edgecolor=edge, linewidth=0.3)
        ax.add_patch(patch)

    all_px = [hex_to_pixel(q, r, cell_size) for q, r in all_cells]
    xs = [p[0] for p in all_px]
    ys = [p[1] for p in all_px]
    margin = cell_size * 2
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)

    plt.title(f'HexR — {repr(text)}', fontsize=11)
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#f0f0f0')
    plt.close()
    Image.open(output_path).convert('RGB').save(output_path)   # strip alpha channel
    print(f"Saved     : {output_path}\n")
    return output_path


if __name__ == "__main__":
    render_hexr("Hi",           output_path="hexr_Hi.png")
    render_hexr("Hello, HexR!", output_path="hexr_hello.png")
    render_hexr("Pradeep built HexR — a hexagonal alternative to QR codes.",
                output_path="hexr_long.png")
