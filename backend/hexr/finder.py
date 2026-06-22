from hexr.grid import hex_cells

FINDER_RADIUS = 2   # each finder is a mini-hex of radius 2 (19 cells)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ring_dist(q, r, cq, cr):
    """Axial distance (ring number) from (cq,cr) to (q,r)."""
    dq, dr = q - cq, r - cr
    return max(abs(dq), abs(dr), abs(dq + dr))


# ── Block 1: Corner positions ─────────────────────────────────────────────────

def grid_corners(grid_radius):
    """
    Return the 3 finder centre positions, inset by FINDER_RADIUS from each corner.
    Inset ensures all 19 ring cells stay inside the main grid boundary,
    so the detected centroid equals the finder centre exactly.
    Corners 0, 2, 4 of the hex are used (alternating) to break rotational symmetry.
    """
    N = grid_radius
    R = FINDER_RADIUS
    return [
        ( N-R,    0),   # inset from corner 0 — right
        (-(N-R),  N-R), # inset from corner 2 — bottom-left
        ( 0,   -(N-R)), # inset from corner 4 — top-left
    ]


# ── Block 2: Finder cell map ──────────────────────────────────────────────────

def finder_cells(grid_radius):
    """
    Return {(q,r): 'black'|'white'} for every cell belonging to a finder hexagon.
    Pattern: centre=black, ring1=white, ring2=black (bullseye).
    With inset placement all cells are guaranteed inside the grid — no clipping.
    """
    valid    = set(hex_cells(grid_radius))
    corners  = grid_corners(grid_radius)
    reserved = {}

    for (cq, cr) in corners:
        for dq in range(-FINDER_RADIUS, FINDER_RADIUS + 1):
            for dr in range(-FINDER_RADIUS, FINDER_RADIUS + 1):
                if abs(dq + dr) <= FINDER_RADIUS:
                    q, r = cq + dq, cr + dr
                    if (q, r) in valid:
                        ring = _ring_dist(q, r, cq, cr)
                        reserved[(q, r)] = 'black' if ring % 2 == 0 else 'white'

    return reserved


# ── Block 3: Timing spoke ─────────────────────────────────────────────────────

def timing_cells(grid_radius):
    """
    Alternating black/white cells along the q-axis toward finder 0.
    Stops one step before the finder's nearest ring-2 cell so there's no overlap.
    stop = N - 2*FINDER_RADIUS - 1
    """
    stop  = grid_radius - 2 * FINDER_RADIUS - 1
    cells = {}
    for step in range(1, stop + 1):
        cells[(step, 0)] = 'black' if step % 2 == 1 else 'white'
    return cells
