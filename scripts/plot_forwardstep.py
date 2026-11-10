"""Density-field plots for the forwardStep examples (I2 step 6).

Usage: python -s scripts/plot_forwardstep.py
rhoCentralFoam writes rho; HiSA writes p,T -> rho = p/(R T), R from the case.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.tri import Triangulation

from src.foam_reader import gas_from_thermo, read_internal_field

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cases/validation/forwardStep"
OUT = ROOT / "docs/benchmarks"


def load(case, t, rho_direct):
    cx, cy = (read_internal_field(case / t / f"C{a}") for a in "xy")
    if rho_direct:
        rho = read_internal_field(case / t / "rho")
    else:
        n = len(cx)
        p = read_internal_field(case / t / "p", n)
        T = read_internal_field(case / t / "T", n)
        R, _ = gas_from_thermo(case / "constant/thermophysicalProperties")
        rho = p / (R * T)
    return cx, cy, rho


def main():
    specs = [
        ("rhoCentralFoam", CASES / "rcf", "4", True),
        ("HiSA", CASES / "hisa/simulation", "4", False),
    ]
    for name, case, t, direct in specs:
        x, y, rho = load(case, t, direct)
        fig, ax = plt.subplots(figsize=(7, 3))
        tri = Triangulation(x, y)
        # mask triangles whose centroid lies inside the solid step (x>0.6, y<0.2)
        cx, cy = x[tri.triangles].mean(axis=1), y[tri.triangles].mean(axis=1)
        tri.set_mask((cx > 0.6) & (cy < 0.2))
        tc = ax.tricontourf(tri, rho, levels=30, cmap="viridis")
        ax.fill_between([0.6, 3.0], 0, 0.2, color="0.6")
        fig.colorbar(tc, label="density (normalised)")
        ax.set_aspect("equal")
        ax.set_title(f"forwardStep, {name}, t={t}  ({len(x)} cells, rho {rho.min():.2f}-{rho.max():.2f})")
        fig.tight_layout()
        out = OUT / f"I2_forwardStep_{name}.png"
        fig.savefig(out, dpi=130)
        print(out, len(x), rho.min(), rho.max())


if __name__ == "__main__":
    main()
