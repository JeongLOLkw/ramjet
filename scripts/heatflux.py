"""Wall heat flux — the ONLY place in this project where it is computed (CLAUDE.md rule 3).

Sign: q_w > 0 means heat flows INTO the wall (fluid hotter than the wall).

    q_w = kappa(T_w) (T_c - T_w) / d

T_c: temperature at the first cell centre, T_w: wall temperature, d: wall distance of
that cell centre (Fourier's law, one-sided difference — the same wall-normal gradient
the solver uses for a wall face on an orthogonal mesh). kappa is the laminar conductivity
the solver uses (modified Eucken, src/boundary_layer.kappa_eucken); the turbulent
contribution vanishes at a no-slip wall without wall functions (alphat = 0, rule 2).
Valid only when the first cell is inside the viscous sublayer (y+ < 1, rule 2).

Usage:  python -s scripts/heatflux.py CASE TIME PATCH [PATCH ...] [--csv out.csv]
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import boundary_layer as bl  # noqa: E402
from src.wall import wall_data  # noqa: E402


def heat_flux(T_cell, T_wall, d):
    """q_w [W/m^2], positive into the wall."""
    T_cell, T_wall, d = (np.asarray(v, float) for v in (T_cell, T_wall, d))
    if np.any(d <= 0):
        raise ValueError("wall distance must be positive")
    return bl.kappa_eucken(T_wall) * (T_cell - T_wall) / d


def case_heat_flux(case, time, patch):
    """wall_data(case, time, patch) with q_w added."""
    w = wall_data(case, time, patch)
    w["q_w"] = heat_flux(w["T_c"], w["T_w"], w["d"])
    return w


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case"), ap.add_argument("time"), ap.add_argument("patches", nargs="+")
    ap.add_argument("--csv")
    a = ap.parse_args(argv)
    rows = []
    for patch in a.patches:
        w = case_heat_flux(a.case, a.time, patch)
        i = int(np.argmax(w["q_w"]))
        print(f"{patch}: q_w max {w['q_w'][i]:.6g} W/m2 at x = {w['x'][i]:.6g}, min {w['q_w'].min():.6g}")
        rows += [(patch, x, y, q) for x, y, q in zip(w["x"], w["y"], w["q_w"])]
    if a.csv:
        with open(a.csv, "w") as f:
            f.write("# q_w positive into the wall [W/m2] — scripts/heatflux.py\npatch,x,y,q_w\n")
            f.writelines(f"{p},{x:.10g},{y:.10g},{q:.10g}\n" for p, x, y, q in rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
