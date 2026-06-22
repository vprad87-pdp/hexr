import math
import numpy as np
from PIL import Image
from scipy import ndimage

from hexr.traversal import spiral_traversal
from hexr.finder import finder_cells, timing_cells
from hexr.reed_solomon import decode as rs_decode


# ── Block 1: Find the 3 finder blobs ─────────────────────────────────────────
#
# Each finder has: ring0 (dark blue) — ring1 (PALE, not detected) — ring2 (dark blue)
# So one finder appears as TWO disconnected blue blobs in the mask.
# Fix: cluster nearby blobs together; each cluster = one finder.

def _find_finder_centroids(img_arr):
    r = img_arr[:, :, 0].astype(float)
    g = img_arr[:, :, 1].astype(float)
    b = img_arr[:, :, 2].astype(float)

    # Exclude timing_b (#4a148c, R=74>G*1.5) while keeping finder_b (#1a237e, R=26<G*1.5)
    blue_mask = (b > 100) & (b > r * 1.5) & (b > g * 1.3) & ~(r > g * 1.5)

    labeled, n_labels = ndimage.label(blue_mask)

    # Collect ring-0 and ring-2 cell blobs (each ≥ ~1600 px); drop tiny edge blobs
    pts = []
    for i in range(1, n_labels + 1):
        blob = labeled == i
        if int(blob.sum()) < 100:
            continue
        ys, xs = np.where(blob)
        pts.append((float(xs.mean()), float(ys.mean())))

    if len(pts) < 3:
        raise ValueError("Not enough blue blobs found — is this a HexR image?")

    # Single-linkage clustering with distance threshold 200 px.
    # Adjacent ring cells of one finder are ~45 px apart (S·√3) — always connected.
    # Ring-2 "diameter" ≤ 182 px at N=9 (minimum grid), so all 13 blobs chain together.
    # Nearest cross-finder blob pair ≥ 370 px apart — no cross-cluster edges.
    _LINK_SQ = 200 ** 2
    n_b = len(pts)
    adj = [[] for _ in range(n_b)]
    for i in range(n_b):
        for j in range(i + 1, n_b):
            dx = pts[i][0] - pts[j][0]
            dy = pts[i][1] - pts[j][1]
            if dx * dx + dy * dy < _LINK_SQ:
                adj[i].append(j)
                adj[j].append(i)

    visited = [False] * n_b
    components = []
    for start in range(n_b):
        if visited[start]:
            continue
        comp = [start]
        stack = [start]
        visited[start] = True
        while stack:
            v = stack.pop()
            for u in adj[v]:
                if not visited[u]:
                    visited[u] = True
                    comp.append(u)
                    stack.append(u)
        components.append(comp)

    components.sort(key=lambda c: -len(c))
    if len(components) < 3:
        raise ValueError(f"Found {len(components)} finder cluster(s), need 3")
    components = components[:3]

    # Mean position per cluster (equal-weight; ring-2 symmetry → centroid = finder centre)
    centroids = []
    for comp in components:
        cx_c = sum(pts[i][0] for i in comp) / len(comp)
        cy_c = sum(pts[i][1] for i in comp) / len(comp)
        centroids.append((cx_c, cy_c))

    return centroids


# ── Block 2: Compute grid centre and scale ────────────────────────────────────
#
# Finders in numpy pixel space (y-down):
#   f0 (N,  0 ) → rightmost x,  upper half   (smallest y among f0,f2)
#   f2 (-N, N ) → leftmost  x,  upper half
#   f4 (0,  -N) → middle    x,  lower half   (largest y)
#
# Relations:
#   cx  = (f0.x + f2.x) / 2
#   sN  = (f0.x - f2.x) / 3          where sN = S*N
#   cy  = f0.y + sN*√3/2             (f0 is above centre in image)

def _compute_grid_params(centroids):
    by_x = sorted(centroids, key=lambda p: p[0])
    f2_cand, mid, f0_cand = by_x[0], by_x[1], by_x[2]

    # f4 is the one with the largest numpy-y (lowest in image)
    all3 = [f2_cand, mid, f0_cand]
    f4   = max(all3, key=lambda p: p[1])
    rest = [p for p in all3 if p is not f4]
    f0   = max(rest, key=lambda p: p[0])
    f2   = min(rest, key=lambda p: p[0])

    cx = (f0[0] + f2[0]) / 2
    sN = (f0[0] - f2[0]) / 3
    cy = f0[1] + sN * math.sqrt(3) / 2

    return cx, cy, sN, f0


# ── Block 3: Detect cell scale from timing spoke ──────────────────────────────
#
# Timing_b colour: #4a148c = RGB(74, 20, 140)
# Key distinction from finder blue: R > G*1.5 (purple) vs R < G (blue)
#
# Instead of a line scan (which can miss cells or detect the wrong one),
# we enumerate candidate N values, compute exactly where timing cells (1,0)
# and (3,0) would be, and sample those pixels directly.
# The correct N gives purple pixels at both positions.

def _find_scale(img_arr, f0, cx, cy, sNe):
    """
    Scan from finder centroid f0 toward the grid centre.
    The ring-0 hexagon (dark blue, size 0.95·S) ends at S·√3/2·0.95 pixels
    in the inward direction (flat-top hex boundary at 210° = edge midpoint).
    The first non-blue pixel gives S directly; N = round(sNe/S) + FINDER_RADIUS.
    """
    from hexr.finder import FINDER_RADIUS as FR
    fx, fy = f0
    dist = math.hypot(cx - fx, cy - fy)
    dx   = (cx - fx) / dist          # ≈ -√3/2
    dy   = (cy - fy) / dist          # ≈ +0.5

    h, w = img_arr.shape[:2]
    # Extent of ring-0 hex in the inward direction = 0.95 · S · cos(30°)
    _SCALE_FACTOR = 0.95 * math.sqrt(3) / 2   # ≈ 0.822

    for d in range(2, min(int(dist), int(sNe))):
        px = int(round(fx + d * dx))
        py = int(round(fy + d * dy))
        if not (0 <= px < w and 0 <= py < h):
            break
        rv = int(img_arr[py, px, 0])
        gv = int(img_arr[py, px, 1])
        bv = int(img_arr[py, px, 2])
        is_blue = bv > 100 and bv > rv * 1.5 and bv > gv * 1.3
        if not is_blue:
            # Actual boundary is between d-1 (last blue) and d (first non-blue).
            # Best estimate: d - 0.5.
            S = (d - 0.5) / _SCALE_FACTOR
            N = round(sNe / S) + FR
            return S, N

    raise ValueError("Could not measure ring-0 boundary — is this a valid HexR image?")


# ── Block 4: Sample + decode ──────────────────────────────────────────────────

def _sample_bit(img_arr, cx, cy, S, q, r):
    """
    Average a 3×3 pixel region at cell (q,r) centre.
    Returns: 1 = dark (data bit 1), 0 = white (data bit 0), -1 = unused padding cell.
    Unused cells are '#e8e8e8' (mean ≈ 232), white data-0 cells are '#ffffff' (mean ≈ 255).
    """
    px = cx + S * 1.5 * q
    py = cy - S * (math.sqrt(3) / 2 * q + math.sqrt(3) * r)   # minus: y-flip

    x, y = int(round(px)), int(round(py))
    h, w = img_arr.shape[:2]
    region = img_arr[max(0,y-1):y+2, max(0,x-1):x+2, :3]
    if region.size == 0:
        return -1
    m = region.mean()
    if m > 244:   # white  (#ffffff ≈ 255) → data bit 0
        return 0
    if m > 200:   # grey   (#e8e8e8 ≈ 232) → unused padding cell
        return -1
    return 1      # dark   (#111111 ≈ 17)  → data bit 1


def decode_hexr(image_path):
    """Load a HexR PNG and return the decoded text string."""
    img     = Image.open(image_path).convert('RGB')
    img_arr = np.array(img)

    # 1. Locate finders
    centroids          = _find_finder_centroids(img_arr)
    cx, cy, sN, f0     = _compute_grid_params(centroids)

    # 2. Scale and radius
    S, N = _find_scale(img_arr, f0, cx, cy, sN)

    print(f"  Finder centroids : {[(round(p[0],1), round(p[1],1)) for p in centroids]}")
    print(f"  Grid centre      : ({cx:.1f}, {cy:.1f})")
    print(f"  Cell scale S     : {S:.2f} px")
    print(f"  Grid radius N    : {N}")

    # 3. Reserved cells (finders + timing — same logic as encoder)
    reserved = set(finder_cells(N)) | set(timing_cells(N))

    # 4. Sample data cells in spiral order; stop at first unused padding cell
    all_cells  = spiral_traversal(N)
    data_cells = [(q, r) for (q, r) in all_cells if (q, r) not in reserved]
    bits = []
    for q, r in data_cells:
        bit = _sample_bit(img_arr, cx, cy, S, q, r)
        if bit < 0:
            break
        bits.append(bit)

    # 5. Bits → bytes (truncate to whole bytes) → Reed-Solomon
    n_bytes   = len(bits) // 8
    byte_list = []
    for i in range(0, n_bytes * 8, 8):
        val = 0
        for j in range(8):
            val = (val << 1) | bits[i + j]
        byte_list.append(val)

    original = rs_decode(bytes(byte_list))
    return original.decode('utf-8')


if __name__ == "__main__":
    tests = [
        ("hexr_Hi.png",    "Hi"),
        ("hexr_hello.png", "Hello, HexR!"),
        ("hexr_long.png",  "Pradeep built HexR — a hexagonal alternative to QR codes."),
    ]
    for filename, expected in tests:
        path = f"C:/Users/prava/hexr/backend/{filename}"
        print(f"\nDecoding: {filename}")
        try:
            result = decode_hexr(path)
            match  = result == expected
            print(f"  Decoded : {repr(result)}")
            print(f"  Result  : {'PASS' if match else 'FAIL'}")
            if not match:
                print(f"  Expected: {repr(expected)}")
        except Exception as e:
            print(f"  ERROR   : {e}")
