from PIL import Image, ImageDraw

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

def render_hexr(text, output_path="hexr_encoded.png", cell_size=16):
    """Encode text and render a HexR image with finder hexagons and timing spoke.

    Rendered with PIL (ImageDraw) rather than matplotlib: PIL fills polygons with
    NO anti-aliasing, so every interior pixel is a pure colour. Matplotlib blends a
    5–6px gradient across cell edges, which pushed the centre pixels of white cells
    adjacent to dark cells into the grey band (100..244) and made the decoder stop
    early. Pure fills eliminate that entirely. ``cell_size`` is now the pixel scale
    directly (1 hex unit = cell_size px), so the decoder recovers S ≈ cell_size.
    """
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

    # Cell centres in hex-pixel space (y-up).
    positions = {(q, r): hex_to_pixel(q, r, cell_size) for (q, r) in all_cells}
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    margin = cell_size * 2
    min_x, max_x = min(xs) - margin, max(xs) + margin
    min_y, max_y = min(ys) - margin, max(ys) + margin
    width  = int(round(max_x - min_x))
    height = int(round(max_y - min_y))

    def to_img(px, py):
        # Map hex-pixel (y-up) to image pixel (y-down); matches decoder's y-flip.
        return (px - min_x, max_y - py)

    img  = Image.new('RGB', (width, height), '#f0f0f0')
    draw = ImageDraw.Draw(img)
    circ = cell_size * 0.95   # 0.95 leaves a thin gap between adjacent cells

    for (q, r) in all_cells:
        cx, cy      = positions[(q, r)]
        corners     = hex_corners(cx, cy, circ)
        img_corners = [to_img(x, y) for (x, y) in corners]

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

        draw.polygon(img_corners, fill=face, outline=edge)

    img.save(output_path)
    print(f"Saved     : {output_path}\n")
    return output_path


if __name__ == "__main__":
    render_hexr("Hi",           output_path="hexr_Hi.png")
    render_hexr("Hello, HexR!", output_path="hexr_hello.png")
    render_hexr("Pradeep built HexR — a hexagonal alternative to QR codes.",
                output_path="hexr_long.png")
