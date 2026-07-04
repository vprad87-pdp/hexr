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
    r = img_arr[:, :, 0].astype(np.float32)
    g = img_arr[:, :, 1].astype(np.float32)
    b = img_arr[:, :, 2].astype(np.float32)

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

def _find_scale(img_arr, cx, cy, sN):
    """
    Determine S and N by trying each candidate N and verifying the timing spoke.
    Timing cells at (step, 0): odd steps are purple (timing_b), even are pale.
    Only the correct N gives S = sN/(N-FR) that lands on the right pixels.

    Anti-resonance guard: wrong N with S = k*S_correct (integer k≥3) also passes
    the alternating check, but has extra purple cells between sampled steps.
    Scanning t ∈ {0.6,0.7,0.8,0.9} between step-1 and step-2 detects these.
    """
    from hexr.finder import FINDER_RADIUS as FR

    h, w = img_arr.shape[:2]
    sqrt3_2 = math.sqrt(3) / 2

    def _sample_purple(x, y):
        ix, iy = int(round(x)), int(round(y))
        if not (0 <= ix < w and 0 <= iy < h):
            return None
        rv = int(img_arr[iy, ix, 0])
        gv = int(img_arr[iy, ix, 1])
        bv = int(img_arr[iy, ix, 2])
        return rv > gv * 1.5 and bv > 100  # timing_b = #4a148c

    def _is_purple(step, S):
        return _sample_purple(cx + S * 1.5 * step, cy - S * sqrt3_2 * step)

    # Return the LARGEST N that passes, not the first. A small candidate N only
    # has to validate a few timing steps (stop = N-2·FR-1), so with a coincidental
    # large S those few can alternate purple/pale by luck (observed: N=9,S=112 on a
    # real N=51 grid). The true N validates the whole spoke; any N larger than the
    # true one fails because it samples past the spoke's end. So the largest passing
    # N is the correct one.
    best = None
    for N in range(8, 80):
        k = N - FR
        if k <= 0:
            continue
        S = sN / k
        if S < 4:
            break

        stop = N - 2 * FR - 1
        if stop < 3:
            continue

        # All timing cells must alternate: odd=purple, even=pale
        ok = True
        for step in range(1, stop + 1):
            result = _is_purple(step, S)
            if result is None:
                ok = False
                break
            if result != (step % 2 == 1):
                ok = False
                break
        if not ok:
            continue

        # Anti-resonance check at step 0.25 (well inside the centre data cell).
        # Distance from centre = 0.25·1.732·S = 0.433·S < 0.823·S (apothem).
        # For correct N: always inside (0,0) data cell — never purple.
        # For resonant false-positive (S = k·S_true, k odd ≥ 3): step 0.25
        # maps to actual q = 0.25·k ≥ 0.75 — inside the actual q=1 timing cell.
        if _is_purple(0.25, S):
            continue

        best = (S, N)   # keep overwriting → ends up as the largest passing N

    if best is not None:
        return best

    raise ValueError("Could not determine grid scale from timing cells")


# ── Block 4: Sample + decode ──────────────────────────────────────────────────

def _sample_bit(img_arr, cx, cy, S, q, r):
    """
    Sample a 5×5 pixel region at cell (q,r) centre; classify by median.
    Returns: 1 = dark (data bit 1), 0 = white (data bit 0), -1 = unused padding cell.
    Colours: dark=#111111 (≈17), white=#ffffff (≈255), grey-pad=#e8e8e8 (≈232).
    5×5 median outvotes isolated edge/corner artefacts (apothem ≈0.82S > 3px half-size).
    Threshold ≥244 for white and ≤100 for dark leave a gap (100..244) for grey-pad (232).
    """
    px = cx + S * 1.5 * q
    py = cy - S * (math.sqrt(3) / 2 * q + math.sqrt(3) * r)   # minus: y-flip

    x, y = int(round(px)), int(round(py))
    h, w = img_arr.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return -1
    half = 4
    patch = img_arr[max(0, y - half):y + half + 1, max(0, x - half):x + half + 1, 0]
    if patch.size == 0:
        return -1
    ph, pw = patch.shape
    cy_off = min(half, y)
    cx_off = min(half, x)
    ys = np.arange(ph) - cy_off
    xs = np.arange(pw) - cx_off
    mask = (ys[:, None] ** 2 + xs[None, :] ** 2) <= half * half
    pixels = patch[mask]
    if pixels.size == 0:
        return -1
    m = float(np.median(pixels))
    if m >= 244:
        return 0   # white
    if m <= 100:
        return 1   # dark
    return -1      # grey pad (≈232)


# Cap the working resolution. A HexR grid needs ~1500px to resolve every cell;
# phone photos are 4000px+, which would blow the server's memory (three float64
# channel copies of a 12MP image are ~288MB). Downscale before any processing.
MAX_DECODE_DIM = 1600


def decode_hexr(image_path):
    """Load a HexR image and return the decoded text string."""
    img = Image.open(image_path)
    # draft() lets JPEG decode straight to a reduced size (memory-efficient for
    # large camera photos); thumbnail() finishes the job for any format.
    img.draft('RGB', (MAX_DECODE_DIM, MAX_DECODE_DIM))
    img = img.convert('RGB')
    if max(img.size) > MAX_DECODE_DIM:
        img.thumbnail((MAX_DECODE_DIM, MAX_DECODE_DIM), Image.LANCZOS)
    img_arr = np.array(img)

    # 1. Locate finders
    centroids          = _find_finder_centroids(img_arr)
    cx, cy, sN, f0     = _compute_grid_params(centroids)

    # 2. Scale and radius
    S, N = _find_scale(img_arr, cx, cy, sN)

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
