"""Block-structured mesh of the parametric inlet (geometry/inlet_param.py) for blockMesh (I5).

Topology (32 blocks, 2D):
  - H-type columns between the stations: inflow boundary | leading edge | ramp kink | A | N | shoulder | exit.
    A and N are the two stations just ahead of / at the cowl lip (below the C-layer corners Qa, Qin).
  - A wall layer of thickness d_wall along the symmetry line, ramps and isolator floor; its edges are normal
    to the wall (bisector at the kink and at the shoulder).
  - A C-layer of thickness d_c wrapped around the blunt lip (four polar blocks: 3 x 45 deg and the rest up to
    the outer-surface tangent point) and continued along the cowl inner and outer surfaces.
  - Two fan-shaped strips run upstream from the two front lip blocks to the inflow boundary (the C-topology
    "wake" of the lip); the region above them and above the cowl goes to the top boundary.
  Vertices Qa and Qb (C-layer corners at 225 and 135 deg) are the only irregular (5-block) points.

Resolution: MeshParams holds the level-0 (coarse) values. Level k multiplies every cell count by 2^(k/2)
and divides every cell size, including the first-cell heights, by the same factor; layer thicknesses stay.
The first-cell height is the same on all wall-normal edges of a wall (per-edge grading).
Wall-tangential spacing is continuous around the lip onto both cowl surfaces; the unavoidable polar jump
(factor (R + d_c)/R) is placed at the outer edge of the C-layer and on the ramp at station N.
"""
from dataclasses import asdict, dataclass

import numpy as np

from geometry import inlet_param as ip
from src.blockmesh import BlockMesh

TOP_BLEND = 0.5
WALL_PATCHES = ("ramp", "floor", "cowl_in", "lip", "cowl_out")
PATCHES = ("inlet", "top", "outlet_ext", "outlet_duct", "sym") + WALL_PATCHES


@dataclass(frozen=True)
class MeshParams:
    level: int = 0
    dy_wall: float = 0.8e-6      # first-cell height on ramp, floor, cowl surfaces (level 0) [m]
    dy_lip: float = 0.3e-6       # first-cell height on the lip arc (level 0) [m]
    d_wall: float = 2.0e-3       # wall-layer thickness [m]
    d_c: float = 2.0e-3          # C-layer thickness around the cowl [m]
    n_wall: int = 32             # cells across the wall layer (level 0)
    n_c: int = 37                # cells across the C-layer
    n_core: int = 56             # cells between wall layer and lip level / C-layer
    n_top: int = 40              # cells from lip level / cowl to the top boundary
    n_arc: int = 8               # cells per 45 deg of lip arc
    dx_in: float = 7.0e-3        # streamwise cell size at the inflow boundary (level 0) [m]
    dx_le: float = 0.7e-3        # ... at the leading edge
    dx_k: float = 3.5e-3         # ... at the ramp kink
    dx_s: float = 0.7e-3         # ... at the shoulder (throat)
    dx_e: float = 1.1e-3         # ... at the isolator exit
    dx_wedge: float = 2.1e-3     # ... at the end of the cowl outer wedge
    dx_ext: float = 5.6e-3       # ... at the exit on the cowl outer surface
    fan_deg: float = 7.5         # half-angle of the strips running upstream from the lip


def n_for(length, s_a, s_b):
    """Number of cells of a geometric progression from size s_a to size s_b filling `length`
    (sum of the series: r = (L - s_a)/(L - s_b), n = 1 + ln(s_b/s_a)/ln r)."""
    if not (0 < s_a < length and 0 < s_b < length):
        raise ValueError(f"cell sizes {s_a:.3g}, {s_b:.3g} do not fit in length {length:.3g}")
    if abs(s_a - s_b) < 1e-9 * s_a:
        return max(2, int(round(length / s_a)))
    r = (length - s_a) / (length - s_b)
    return max(2, int(round(1 + np.log(s_b / s_a) / np.log(r))))


def build(p, mp=MeshParams()):
    """(BlockMesh, info) for inlet parameters p and mesh parameters mp. Raises ValueError if the
    layout does not fit (e.g. shoulder too close to the lip station)."""
    d = ip.design(p)
    f = 2.0 ** (mp.level / 2.0)
    N = lambda n0: max(2, int(round(n0 * f)))  # noqa: E731
    d1, dt, te = np.radians(p.delta1_deg), d["delta_tot"], np.radians(p.cowl_ext_deg)
    dw, dc, R = mp.d_wall, mp.d_c, p.lip_radius
    K, S, Cn, Tc = (np.array(d[k]) for k in ("K", "S", "Cn", "Tc"))
    yc, xE, x0, yt = d["y_cowl"], d["x_exit"], -p.x_up, p.y_top
    y_ct = yc + p.cowl_thickness
    nrm = lambda a: np.array([-np.sin(a), np.cos(a)])  # noqa: E731  unit normal of a wall inclined by a
    bis = lambda a0, a1: nrm(0.5 * (a0 + a1)) / np.cos(0.5 * (a1 - a0))  # noqa: E731  offset-corner direction
    rho = R + dc
    pol = lambda r, deg: Cn + r * np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg))])  # noqa: E731
    phi = dict(n=270.0, a=225.0, m=180.0, b=135.0, t=90.0 + p.cowl_ext_deg)   # iN, a, m, b, ouT
    P = {k: pol(R, a) for k, a in phi.items()}
    Q = {k: pol(rho, a) for k, a in phi.items()}
    ramp2 = lambda x: K[1] + (x - K[0]) * np.tan(dt)  # noqa: E731

    def below(xq):
        """Ramp-2 wall point and wall-layer point (at x = xq) of the station under the lip point xq."""
        x = xq + dw * np.sin(dt)
        w = np.array([x, ramp2(x)])
        return w, w + dw * nrm(dt)

    Ow, Kw, Sw = dw * nrm(d1), K + dw * bis(d1, dt), S + dw * bis(dt, 0.0)
    A0, Aw = below(Q["a"][0])
    N0, Nw = below(Q["n"][0])
    Tcq = Tc + dc * bis(te, 0.0)

    # --- does the layout fit?
    if dc < R or rho > 12 * R:
        raise ValueError("C-layer thickness d_c must be between 1 and 11 lip radii")
    if A0[0] - K[0] < 10 * dw:
        raise ValueError("ramp 2 too short ahead of the lip for the block layout")
    if Sw[0] - Nw[0] < 2 * dw:
        raise ValueError("shoulder too close to the lip station for the block layout (increase cr_int)")
    if Q["a"][1] - Aw[1] < 3 * dw or (yc - dc) - (S[1] + dw) < 2 * dw:
        raise ValueError("duct too narrow for wall layer + C-layer (reduce d_wall / d_c)")
    if Tc[0] - P["t"][0] < 5 * dc or xE - Tc[0] < 5 * dc:
        raise ValueError("cowl outer surface too short for the block layout")

    # --- strips running upstream from the lip
    tan_f = np.tan(np.radians(mp.fan_deg))
    t_lo = min(tan_f, 0.6 * Q["a"][1] / (Q["a"][0] - x0))
    t_hi = min(tan_f, 0.5 * (yt - Q["b"][1]) / (Q["b"][0] - x0))
    m0 = lambda x: Q["a"][1] - (Q["a"][0] - x) * t_lo  # noqa: E731
    m2 = lambda x: Q["b"][1] + (Q["b"][0] - x) * t_hi  # noqa: E731
    m1 = Cn[1]
    for name, w in (("leading edge", Ow), ("kink", Kw)):
        if m0(w[0]) - w[1] < 5 * dw:
            raise ValueError(f"no room between the wall layer and the lip strip at the {name}")
    if yt - max(m2(x0), y_ct + dc) < 10 * dc:
        raise ValueError("top boundary too low (y_top)")

    m = BlockMesh()
    V = m.vertex
    for tag, x, wall, wl in (("I", x0, (x0, 0.0), (x0, dw)), ("L", Ow[0], (0.0, 0.0), Ow), ("K", Kw[0], K, Kw)):
        V({"I": "I0", "L": "O", "K": "K"}[tag], *wall)
        V({"I": "Iw", "L": "Ow", "K": "Kw"}[tag], *wl)
        for lvl, y in (("m0", m0(x)), ("m1", m1), ("m2", m2(x)), ("t", yt)):
            V(("I" if tag == "I" else tag) + lvl, x, y)
    for name, xy in (("A0", A0), ("Aw", Aw), ("N0", N0), ("Nw", Nw)):
        V(name, *xy)
    for k in phi:
        V("P" + k, *P[k]), V("Q" + k, *Q[k])
    V("Bt", Q["b"][0], yt), V("Qtt", Q["t"][0], yt)
    V("S", *S), V("Sw", *Sw), V("Sc", Sw[0], yc - dc), V("Si", Sw[0], yc)
    V("E0", xE, S[1]), V("Ew", xE, S[1] + dw), V("Ec", xE, yc - dc), V("Ei", xE, yc)
    V("Tc", *Tc), V("Tcq", *Tcq), V("Tct", Tcq[0], yt)
    V("Eo", xE, y_ct), V("Eoq", xE, y_ct + dc), V("Eot", xE, yt)

    B = m.block
    for tag, l, r in (("U", ("I0", "Iw", "Im0", "Im1", "Im2", "It"), ("O", "Ow", "Lm0", "Lm1", "Lm2", "Lt")),
                      ("R1", ("O", "Ow", "Lm0", "Lm1", "Lm2", "Lt"), ("K", "Kw", "Km0", "Km1", "Km2", "Kt")),
                      ("R2", ("K", "Kw", "Km0", "Km1", "Km2", "Kt"), ("A0", "Aw", "Qa", "Qm", "Qb", "Bt"))):
        for j, layer in enumerate(("w", "c", "m0", "m1", "t")):
            B(f"{tag}_{layer}", l[j], r[j], r[j + 1], l[j + 1])
    B("AN_w", "A0", "N0", "Nw", "Aw"), B("AN_c", "Aw", "Nw", "Qn", "Qa")
    B("nose_l", "Qa", "Qn", "Pn", "Pa"), B("nose_fl", "Qm", "Qa", "Pa", "Pm")
    B("nose_fu", "Qb", "Qm", "Pm", "Pb"), B("nose_u", "Qt", "Qb", "Pb", "Pt")
    B("NS_w", "N0", "S", "Sw", "Nw"), B("NS_c", "Nw", "Sw", "Sc", "Qn"), B("NS_cl", "Qn", "Sc", "Si", "Pn")
    B("SE_w", "S", "E0", "Ew", "Sw"), B("SE_c", "Sw", "Ew", "Ec", "Sc"), B("SE_cl", "Sc", "Ec", "Ei", "Si")
    B("BQ_t", "Qb", "Qt", "Qtt", "Bt")
    B("W_cl", "Pt", "Tc", "Tcq", "Qt"), B("W_t", "Qt", "Tcq", "Tct", "Qtt")
    B("F_cl", "Tc", "Eo", "Eoq", "Tcq"), B("F_t", "Tcq", "Eoq", "Eot", "Tct")
    lip_arcs = (("Pn", "Pa"), ("Pa", "Pm"), ("Pm", "Pb"), ("Pb", "Pt"))
    for a, b in lip_arcs:
        m.arc(a, b, Cn)

    m.patch("inlet", "patch", [("I0", "Iw"), ("Iw", "Im0"), ("Im0", "Im1"), ("Im1", "Im2"), ("Im2", "It")])
    m.patch("top", "patch", [("It", "Lt"), ("Lt", "Kt"), ("Kt", "Bt"), ("Bt", "Qtt"), ("Qtt", "Tct"), ("Tct", "Eot")])
    m.patch("outlet_ext", "patch", [("Eo", "Eoq"), ("Eoq", "Eot")])
    m.patch("outlet_duct", "patch", [("E0", "Ew"), ("Ew", "Ec"), ("Ec", "Ei")])
    m.patch("sym", "symmetryPlane", [("I0", "O")])
    m.patch("ramp", "wall", [("O", "K"), ("K", "A0"), ("A0", "N0"), ("N0", "S")])
    m.patch("floor", "wall", [("S", "E0")])
    m.patch("cowl_in", "wall", [("Pn", "Si"), ("Si", "Ei")])
    m.patch("lip", "wall", list(lip_arcs))
    m.patch("cowl_out", "wall", [("Pt", "Tc"), ("Tc", "Eo")])

    # --- cell counts
    dy_w, dy_l = mp.dy_wall / f, mp.dy_lip / f
    na = N(mp.n_arc)
    nu = max(2, int(round(na * (45.0 - p.cowl_ext_deg) / 45.0)))
    s_arc = m.length("Pn", "Pa") / na          # wall-tangential cell on the lip
    s_arc_u = m.length("Pb", "Pt") / nu
    dx_a = m.length("A0", "N0") / na
    m.count("O", "Ow", N(mp.n_wall)), m.count("Ow", "Lm0", N(mp.n_core)), m.count("Pm", "Qm", N(mp.n_c))
    m.count("Im2", "It", N(mp.n_top))
    m.count("Pn", "Pa", na), m.count("Pa", "Pm", na), m.count("Pm", "Pb", na), m.count("Pb", "Pt", nu)
    m.count("I0", "O", n_for(m.length("I0", "O"), mp.dx_in / f, mp.dx_le / f))
    m.count("O", "K", n_for(m.length("O", "K"), mp.dx_le / f, mp.dx_k / f))
    m.count("K", "A0", n_for(m.length("K", "A0"), mp.dx_k / f, dx_a))
    m.count("Pn", "Si", n_for(m.length("Pn", "Si"), s_arc, mp.dx_s / f))
    m.count("S", "E0", n_for(m.length("S", "E0"), mp.dx_s / f, mp.dx_e / f))
    m.count("Pt", "Tc", n_for(m.length("Pt", "Tc"), s_arc_u, mp.dx_wedge / f))
    m.count("Tc", "Eo", n_for(m.length("Tc", "Eo"), mp.dx_wedge / f, mp.dx_ext / f))

    # --- wall-normal distributions
    m.grade_family("O", "Ow", start=dy_w)
    m.grade_family("Ow", "Lm0", start=m.sizes("O", "Ow")[-1])
    for k in phi:
        m.grade("P" + k, "Q" + k, start=dy_l)
    for a, b in (("Si", "Sc"), ("Ei", "Ec"), ("Tc", "Tcq"), ("Eo", "Eoq")):
        m.grade(a, b, start=dy_w)
    c_last = float(m.sizes("Pm", "Qm")[-1])
    for a, b, c in (("Im2", "It", "Im1"), ("Lm2", "Lt", "Lm1"), ("Km2", "Kt", "Km1")):
        # between the strip cell height there and the C-layer cell at the lip (limits the slope of the grid lines)
        m.grade(a, b, start=(m.length(c, a) / na) ** (1 - TOP_BLEND) * c_last ** TOP_BLEND)
    for a, b, c in (("Qb", "Bt", "Pb"), ("Qt", "Qtt", "Pt"), ("Tcq", "Tct", "Tc"), ("Eoq", "Eot", "Eo")):
        m.grade(a, b, start=m.sizes(c, a)[-1])

    # --- streamwise distributions
    m.grade_family("I0", "O", end=mp.dx_le / f)
    m.grade_family("O", "K", start=mp.dx_le / f)
    m.grade_family("K", "A0", end=dx_a)
    m.grade_family("N0", "S", start=s_arc)
    for a, b, c in (("S", "E0", "N0"), ("Sw", "Ew", "Nw"), ("Sc", "Ec", "Qn"), ("Si", "Ei", "Pn")):
        m.grade(a, b, start=m.sizes(c, a)[-1])
    m.grade("Pt", "Tc", start=s_arc_u), m.grade("Qt", "Tcq", start=s_arc_u)
    m.grade("Qtt", "Tct", start=s_arc_u)   # same as the bottom edge: columns of constant width up to the top
    for a, b, c in (("Tc", "Eo", "Pt"), ("Tcq", "Eoq", "Qt"), ("Tct", "Eot", "Qtt")):
        m.grade(a, b, start=m.sizes(c, a)[-1])

    rep = m.check()
    info = dict(rep, level=mp.level, dy_wall=dy_w, dy_lip=dy_l,
                n=dict(wall=m.n("O", "Ow"), core=m.n("Ow", "Lm0"), c_layer=m.n("Pm", "Qm"), top=m.n("Im2", "It"),
                       arc45=na, arc_upper=nu, upstream=m.n("I0", "O"), ramp1=m.n("O", "K"), ramp2=m.n("K", "A0"),
                       contraction=m.n("Pn", "Si"), isolator=m.n("S", "E0"), wedge=m.n("Pt", "Tc"),
                       cowl_top=m.n("Tc", "Eo")),
                ratio=dict(wall=m.cell_ratio("O", "Ow"), lip=m.cell_ratio("Pm", "Qm"), core=m.cell_ratio("Sw", "Sc"),
                           top=m.cell_ratio("Qb", "Bt")),
                size=dict(lip_tangential=s_arc, under_lip=dx_a, wall_layer_last=float(m.sizes("O", "Ow")[-1]),
                          c_layer_last=float(m.sizes("Pm", "Qm")[-1]), throat=float(m.sizes("N0", "S")[-1]),
                          exit=float(m.sizes("S", "E0")[-1])),
                mesh_params=asdict(mp))
    return m, info
