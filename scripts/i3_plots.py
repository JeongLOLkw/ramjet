"""I3 figures (docs/benchmarks/I3_*.png). Run after scripts/i3_analyze.py.

Usage:  python -s scripts/i3_plots.py
Colours: categorical slots 1-3 of the dataviz reference palette (rcf blue, HiSA orange,
third series aqua); exact/theory in near-black; fields in a single-hue sequential map.
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.tri import Triangulation  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.i3_analyze import VAL, load, time_dirs  # noqa: E402
from scripts.i3_cases import EXPANSION, SOD_L, SOD_R, WEDGE  # noqa: E402
from src import constants as C  # noqa: E402
from src import gasdynamics as gd  # noqa: E402

OUT = ROOT / "docs/benchmarks"
G = C.GAMMA_AIR
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d3"
COL = {"rcf": "#2a78d6", "hisa": "#eb6834", "third": "#1baf7a"}
LABEL = {"rcf": "rhoCentralFoam", "hisa": "HiSA"}
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#f3f7fc", "#9cc2ee", "#2a78d6", "#0d2f5c"])

plt.rcParams.update({
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 9, "legend.frameon": False, "lines.linewidth": 1.4,
})


def sod_fig(m):
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8))
    xe = np.linspace(-0.5, 0.5, 4001)
    t = m["sod"]["rcf"][0]["t"]
    rho_e, _, _ = gd.riemann_profile(xe, t, SOD_L, SOD_R, G)
    a.plot(xe, rho_e, color=INK, lw=1.0, label="exact (Toro 2009)")
    for case, col, lab in (("rcf_N100", COL["rcf"], "rcf N=100"), ("rcf_N1600", COL["third"], "rcf N=1600"),
                           ("hisa_N100", COL["hisa"], "HiSA N=100")):
        d = VAL / "sod" / case
        f = load(d, time_dirs(d)[-1])
        o = np.argsort(f["x"])
        a.plot(f["x"][o], f["rho"][o], color=col, lw=1.2, label=lab, ls="-" if "rcf" in case else "--")
    a.set(xlabel="x [m]", ylabel="density [kg/m³]", title=f"Sod shock tube, t = {t*1e3:.3f} ms")
    a.legend(loc="lower left")
    for s in ("rcf", "hisa"):
        rows = m["sod"][s]
        h = np.array([r["dx"] for r in rows])
        e = np.array([r["L1_rho"] for r in rows])
        b.loglog(h, e, "o-", color=COL[s], ms=5, label=LABEL[s])
    h = np.array([r["dx"] for r in m["sod"]["rcf"]])
    e0 = m["sod"]["rcf"][0]["L1_rho"]
    for p, ls in ((1, ":"), (0.5, "-.")):
        b.loglog(h, e0 * (h / h[0]) ** p, color=INK2, lw=0.8, ls=ls, label=f"slope {p}")
    b.set(xlabel="Δx [m]", ylabel="L1(ρ) [kg/m²]", title="density L1 error vs grid")
    b.legend()
    fig.tight_layout()
    fig.savefig(OUT / "I3_sod.png", dpi=140)
    plt.close(fig)


def field_ax(ax, d, q, title, cmap=SEQ, solid=None):
    """solid(x, y) -> bool mask of triangle centroids inside a solid body (not plotted)."""
    f = load(d, time_dirs(d)[-1])
    tri = Triangulation(f["x"], f["y"])
    cx, cy = f["x"][tri.triangles].mean(axis=1), f["y"][tri.triangles].mean(axis=1)
    if solid is not None:
        tri.set_mask(solid(cx, cy))
    tc = ax.tricontourf(tri, f[q], levels=40, cmap=cmap)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_title(title)
    return tc, f


def wedge_fig(m):
    rows = m["wedge"]
    fig, axs = plt.subplots(2, 2, figsize=(10, 7.5))
    for k, (cid, (M1, th)) in enumerate(WEDGE.items()):
        ax = axs[0, k]
        tc, _ = field_ax(ax, VAL / "wedge" / f"rcf_{cid}_n200", "p", f"wedge {cid}: M {M1}, θ {th}° — p, rcf n200",
                         solid=lambda x, y, t=np.tan(np.radians(th)): (x > 0) & (y < x * t))
        beta = gd.oblique_shock(M1, np.radians(th), G)["beta"]
        xs = np.array([0, 1.0])
        ax.plot(xs, xs * np.tan(beta), color=INK, lw=1.0, ls="--", label=f"theory β = {np.degrees(beta):.2f}°")
        ax.legend(loc="upper left")
        fig.colorbar(tc, ax=ax, shrink=0.8, label="p [Pa]")
        ax2 = axs[1, k]
        for s in ("rcf", "hisa"):
            rr = sorted([r for r in rows if r["cond"] == cid and r["solver"] == s], key=lambda r: r["n"])
            n = [r["n"] for r in rr]
            ax2.plot(n, [100 * r["err_beta"] for r in rr], "o-", color=COL[s], ms=5, label=f"{LABEL[s]} β")
            ax2.plot(n, [100 * r["err_p"] for r in rr], "s--", color=COL[s], ms=5, label=f"{LABEL[s]} p₂/p₁")
        ax2.axhspan(-1, 1, color=GRID, alpha=0.5, lw=0, label="±1 % (criterion)")
        ax2.axhline(0, color=INK2, lw=0.6)
        ax2.set(xscale="log", xticks=[50, 100, 200], xticklabels=["50", "100", "200"],
                xlabel="cells per unit length n", ylabel="error vs theory [%]", title=f"wedge {cid}: error vs grid")
        ax2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "I3_wedge.png", dpi=140)
    plt.close(fig)


def expansion_fig(m):
    cid, (M1, th) = next(iter(EXPANSION.items()))
    theta = np.radians(th)
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4.2))
    tc, _ = field_ax(a, VAL / "expansion" / f"rcf_{cid}_n200", "M", f"expansion: M {M1}, {th}° — Mach, rcf n200",
                     solid=lambda x, y: (y < 0) & (y < -x * np.tan(theta)))
    M2 = gd.expansion_corner(M1, theta, G)["M2"]
    for ang, lab in ((np.arcsin(1 / M1), "leading Mach line"), (np.arcsin(1 / M2) - theta, "trailing Mach line")):
        a.plot([0, 1.15 * np.cos(ang)], [0, 1.15 * np.sin(ang)], color=INK, lw=0.9, ls="--")
    a.text(0.75, 0.42, "theory fan edges (dashed)", color=INK, fontsize=8)
    fig.colorbar(tc, ax=a, shrink=0.8, label="Mach")
    psi_e = np.linspace(-theta, np.radians(35), 400)
    b.plot(np.degrees(psi_e), [gd.fan_mach_at_ray(p, M1, theta, G) for p in psi_e], color=INK, lw=1.0,
           label="theory (Prandtl–Meyer)")
    for s, n in (("rcf", 200), ("hisa", 200), ("rcf", 50)):
        d = VAL / "expansion" / f"{s}_{cid}_n{n}"
        f = load(d, time_dirs(d)[-1])
        r, psi = np.hypot(f["x"], f["y"]), np.arctan2(f["y"], f["x"])
        sel = (np.abs(r - 1.0) < 0.5 / n) & (f["x"] > 0)
        o = np.argsort(psi[sel])
        col = COL["third"] if n == 50 else COL[s]
        b.plot(np.degrees(psi[sel][o]), f["M"][sel][o], color=col, lw=1.2, ls="-" if s == "rcf" else "--",
               label=f"{LABEL[s]} n{n}")
    b.set(xlabel="ray angle ψ from corner [deg]", ylabel="Mach", title="Mach on arc r = 1")
    b.legend()
    fig.tight_layout()
    fig.savefig(OUT / "I3_expansion.png", dpi=140)
    plt.close(fig)


def fs_fig():
    fig, axs = plt.subplots(2, 1, figsize=(9, 6.4))
    for ax, case in zip(axs, ("rcf_dx160", "hisa_dx160")):
        tc, f = field_ax(ax, VAL / "forwardStep" / case, "rho",
                         f"forward step M 3, t = 4 — density, {LABEL[case.split('_')[0]]}, Δx = 1/160",
                         solid=lambda x, y: (x > 0.6) & (y < 0.2))
        ax.fill_between([0.6, 3.0], 0, 0.2, color="#9a9994")
        fig.colorbar(tc, ax=ax, shrink=0.9, label="ρ (normalised)")
    fig.tight_layout()
    fig.savefig(OUT / "I3_forwardStep.png", dpi=140)
    plt.close(fig)


def main():
    m = json.loads((OUT / "I3_metrics.json").read_text())
    sod_fig(m)
    wedge_fig(m)
    expansion_fig(m)
    fs_fig()
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
