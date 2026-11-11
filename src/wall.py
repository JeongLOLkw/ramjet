"""Wall-adjacent data of a (reconstructed, ASCII) OpenFOAM case — shared by
scripts/yplus_check.py, scripts/heatflux.py and the I4+ analysis scripts.

Requires cell centres written by `postProcess -func writeCellCentres -time 0` (0/Cx, 0/Cy).
2D cases in the x-y plane; the tangent t is the in-plane wall direction with t_x >= 0.
"""
from pathlib import Path

import numpy as np

from src import boundary_layer as bl
from src import constants as C
from src.foam_mesh import patch_geometry, read_patch_field
from src.foam_reader import read_internal_field


def wall_data(case, time, patch):
    """Dict of per-face arrays, sorted by x:
    x, y        face centre
    d           wall distance of the owner-cell centre (> 0)
    T_c, T_w    first-cell and wall temperature (T_w = T_c if the patch stores no value: adiabatic)
    p_w         wall pressure (= first-cell pressure, zero normal gradient)
    rho_w       p_w / (R T_w)
    u_t         first-cell velocity along t
    tau_w       mu(T_w) u_t / d (signed along t)
    y_plus      first-cell y+
    """
    case = Path(case)
    cf, n, _, own = patch_geometry(case, patch)
    cx = read_internal_field(case / "0/Cx")
    cy = read_internal_field(case / "0/Cy")
    nc = len(cx)
    cc = np.column_stack([cx[own], cy[own]])
    d = np.einsum("ij,ij->i", cf[:, :2] - cc, n[:, :2])
    if np.any(d <= 0):
        raise ValueError(f"{case}:{patch}: non-positive wall distance")
    t = np.column_stack([n[:, 1], -n[:, 0]])
    t *= np.where(t[:, :1] < 0, -1.0, 1.0)
    T = read_internal_field(case / time / "T", nc)
    p = read_internal_field(case / time / "p", nc)
    U = read_internal_field(case / time / "U", nc)
    T_c, p_w = T[own], p[own]
    T_w = read_patch_field(case / time / "T", patch, len(own))
    if T_w is None:
        T_w = T_c.copy()
    u_t = np.einsum("ij,ij->i", U[own][:, :2], t)
    rho_w = p_w / (C.R_AIR * T_w)
    tau_w = bl.wall_shear(u_t, d, T_w)
    out = dict(x=cf[:, 0], y=cf[:, 1], d=d, T_c=T_c, T_w=T_w, p_w=p_w, rho_w=rho_w, u_t=u_t,
               tau_w=tau_w, y_plus=bl.y_plus(d, tau_w, rho_w, T_w), owner=own)
    order = np.argsort(out["x"], kind="stable")
    return {k: v[order] for k, v in out.items()}
