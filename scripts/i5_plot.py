"""I5 figures: inlet geometry with the inviscid design shocks, block layout, and mesh close-ups.

Usage:  python -s scripts/i5_plot.py [--set cr_int=1.2 ...] [--mesh-case cases/runs/i5_regen/base_L0]
                                     [--out docs/benchmarks]
Writes I5_geometry.png, I5_blocks.png and (if --mesh-case has a polyMesh) I5_mesh.png.
The shock lines are the inviscid design-point pattern only (no boundary layer, the cowl shock is drawn
straight to the wall without the shoulder expansion) — a drawing of the design intent, not a result.
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from geometry import inlet_mesh as im  # noqa: E402
from geometry import inlet_param as ip  # noqa: E402
from src.foam_mesh import read_boundary, read_faces, read_points  # noqa: E402

# colours: validated categorical slots 1-3 (dataviz default palette, light surface) + ink tokens
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
C_S1, C_S2, C_S3 = "#2a78d6", "#eb6834", "#1baf7a"
MM = 1e3


def style(ax, xlabel=True):
    ax.set_facecolor(SURFACE)
    ax.set_aspect("equal")
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, labelsize=8)
    if xlabel:
        ax.set_xlabel("x [mm]", color=INK2, fontsize=9)
    ax.set_ylabel("y [mm]", color=INK2, fontsize=9)


def lip_arc(p, d, n=60):
    phi = np.radians(np.linspace(270.0, 90.0 + p.cowl_ext_deg, n))
    return d["Cn"][0] + p.lip_radius * np.cos(phi), d["Cn"][1] + p.lip_radius * np.sin(phi)


def draw_walls(ax, p, d, lw=1.6):
    body = np.array([d["LE"], d["K"], d["S"], d["E0"]]) * MM
    ax.fill_between(body[:, 0], body[:, 1], -1e3, color="#e9e8e2", lw=0)
    ax.plot(body[:, 0], body[:, 1], color=INK, lw=lw, solid_joinstyle="miter")
    ax_, ay = lip_arc(p, d)
    cowl = np.column_stack([np.r_[d["E_in"][0], ax_, d["Tc"][0], d["Eo"][0]],
                            np.r_[d["E_in"][1], ay, d["Tc"][1], d["Eo"][1]]]) * MM
    ax.fill(cowl[:, 0], cowl[:, 1], color="#e9e8e2", lw=0)
    ax.plot(cowl[:, 0], cowl[:, 1], color=INK, lw=lw, solid_joinstyle="miter")


def cowl_shock_end(d):
    """Where the straight (inviscid, expansion ignored) cowl shock from the lip meets ramp 2 or the floor."""
    F, K, S = np.array([d["F"][0], d["y_cowl"]]), np.array(d["K"]), np.array(d["S"])
    a = d["beta3"] - d["delta_tot"]                     # angle below the horizontal
    x_floor = F[0] + (F[1] - S[1]) / np.tan(a)
    if x_floor >= S[0]:
        return np.array([x_floor, S[1]])
    t = np.tan(d["delta_tot"])                          # hits ramp 2 ahead of the shoulder
    x = (F[1] + F[0] * np.tan(a) - K[1] + K[0] * t) / (t + np.tan(a))
    return np.array([x, K[1] + (x - K[0]) * t])


def draw_shocks(ax, p, d, labels=True):
    F, K = np.array(d["F"]) * MM, np.array(d["K"]) * MM
    ax.plot([0, F[0]], [0, F[1]], color=C_S1, lw=1.4, label=f"ramp-1 shock ($\\beta$ {np.degrees(d['beta1']):.2f}°)")
    ax.plot([K[0], F[0]], [K[1], F[1]], color=C_S2, lw=1.4, ls=(0, (6, 2)),
            label=f"ramp-2 shock ({np.degrees(d['beta2_abs']):.2f}° from x)")
    if np.isfinite(d["M3"]):
        e = cowl_shock_end(d) * MM
        ax.plot([F[0], e[0]], [d["y_cowl"] * MM, e[1]], color=C_S3, lw=1.4, ls=(0, (2, 1.5)),
                label="cowl shock (inviscid, shoulder expansion ignored)")


def fig_geometry(p, out):
    d = ip.design(p)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 8.6), gridspec_kw=dict(height_ratios=[1.0, 1.15]), facecolor=SURFACE)
    for ax in (a1, a2):
        style(ax)
        draw_walls(ax, p, d)
        draw_shocks(ax, p, d)
    xE, yc = d["x_exit"] * MM, d["y_cowl"] * MM
    a1.set_xlim(-0.06 * xE, 1.03 * xE), a1.set_ylim(-0.08 * yc, 1.55 * yc)
    a1.legend(loc="upper left", fontsize=8, frameon=False, labelcolor=INK2)
    a1.set_title(f"Inlet geometry, design Mach {p.M_design:g} (shock-on-lip) — inviscid design pattern, not a CFD result",
                 color=INK, fontsize=10, loc="left")
    K, S, F = (np.array(d[k]) * MM for k in ("K", "S", "F"))
    t = dict(color=INK2, fontsize=8)
    a1.annotate(f"ramp 1: {p.delta1_deg:g}°, {d['L1'] * MM:.1f} mm", (0.5 * K[0], 0.5 * K[1]), (0.42 * K[0], -0.06 * yc), **t,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    a1.annotate(f"ramp 2: +{p.delta2_deg:g}° (total {p.delta1_deg + p.delta2_deg:g}°)", (0.5 * (K[0] + S[0]), 0.5 * (K[1] + S[1])),
                (K[0] + 10, 0.12 * yc), **t, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    a1.annotate(f"kink ({K[0]:.1f}, {K[1]:.1f})", K, (K[0] - 95, K[1] + 52), **t, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    a1.annotate(f"lip focus ({F[0]:.1f}, {F[1]:.1f})\nR_lip {p.lip_radius * MM:g} mm", F, (F[0] - 95, F[1] + 26), **t,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    a1.annotate(f"isolator: H_th {d['H_th'] * MM:.2f} mm, L {d['L_iso'] * MM:.1f} mm (L/H {p.iso_L_over_H:g}), constant area",
                (S[0] + 0.5 * d["L_iso"] * MM, S[1] + 0.5 * d["H_th"] * MM), (S[0] + 5, S[1] - 34), **t,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    a1.text(0.99, 0.97, f"M1 {d['M1']:.3f}   M2 {d['M2']:.3f}   M3 {d['M3']:.3f}\np2/p∞ {d['p2']:.2f}   p3/p∞ {d['p3']:.2f}   "
            f"pt3/pt∞ {d['pt3']:.3f}\nA_i/A_th {p.cr_int:g}  (Kantrowitz limit {d['cr_kantrowitz']:.3f})\n"
            f"H_capture {p.H_capture * MM:g} mm   H_c/H_th {p.H_capture / d['H_th']:.2f}",
            transform=a1.transAxes, ha="right", va="top", fontsize=8, color=INK2, family="monospace")
    # close-up: lip, internal contraction, shoulder
    x0, x1 = F[0] - 12, cowl_shock_end(d)[0] * MM + 14
    a2.set_xlim(x0, x1), a2.set_ylim(S[1] - 8, yc + p.cowl_thickness * MM + 6)
    a2.set_title("Close-up: cowl lip, internal contraction, shoulder (throat)", color=INK, fontsize=10, loc="left")
    G = np.array([d["F"][0], d["y_cowl"]]) * MM + d["A_i"] * MM * np.array([np.sin(d["delta_tot"]), -np.cos(d["delta_tot"])])
    a2.plot([F[0], G[0]], [yc, G[1]], color=MUTED, lw=0.9, ls=":")
    a2.text(*(0.5 * (np.array([F[0], yc]) + G) + [1.0, 0]), f"A_i {d['A_i'] * MM:.2f} mm", **t)
    a2.plot([S[0], S[0]], [S[1], yc], color=MUTED, lw=0.9, ls=":")
    a2.text(S[0] + 1.0, S[1] + 0.45 * d["H_th"] * MM, f"A_th = H_th {d['H_th'] * MM:.2f} mm", **t)
    a2.annotate(f"shoulder ({S[0]:.2f}, {S[1]:.2f}), sharp", S, (S[0] - 6, S[1] - 5.5), **t, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    e = cowl_shock_end(d) * MM
    a2.annotate(f"cowl shock reaches the floor {(e[0] - S[0]) / (d['H_th'] * MM):.2f} H_th\nbehind the shoulder", e,
                (e[0] - 16, e[1] - 6.5), **t, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    a2.annotate(f"cowl outer surface {p.cowl_ext_deg:g}°, thickness {p.cowl_thickness * MM:g} mm", (F[0] + 25, yc + 5.0),
                (F[0] + 30, yc + 12.0), **t, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    a2.text(S[0] + 12, yc - 2.2, "cowl inner surface: horizontal", **t)
    fig.tight_layout()
    fig.savefig(out / "I5_geometry.png", dpi=170)
    plt.close(fig)


def block_segments(m, n_arc=24):
    segs = []
    for _, (a, b, c, d) in m.blocks:
        for u, v in ((a, b), (b, c), (c, d), (d, a)):
            k = (u, v) if u < v else (v, u)
            if k in m.arcs:
                C = np.array(m.arcs[k])
                A, B = np.array(m.v[u]) - C, np.array(m.v[v]) - C
                t0, t1 = np.arctan2(A[1], A[0]), np.arctan2(B[1], B[0])
                dt = (t1 - t0 + np.pi) % (2 * np.pi) - np.pi
                th = t0 + dt * np.linspace(0, 1, n_arc)
                segs.append(np.column_stack([C[0] + np.hypot(*A) * np.cos(th), C[1] + np.hypot(*A) * np.sin(th)]) * MM)
            else:
                segs.append(np.array([m.v[u], m.v[v]]) * MM)
    return segs


def fig_blocks(p, out):
    d = ip.design(p)
    m, info = im.build(p)
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 5.6), gridspec_kw=dict(width_ratios=[1.55, 1.0]), facecolor=SURFACE)
    segs = block_segments(m)
    for ax in axs:
        style(ax)
        draw_walls(ax, p, d, lw=1.2)
        ax.add_collection(LineCollection(segs, colors=C_S1, linewidths=0.8))
    axs[0].set_xlim(-p.x_up * MM - 10, d["x_exit"] * MM + 10), axs[0].set_ylim(-10, p.y_top * MM + 10)
    axs[0].set_title(f"Block layout: {info['blocks']} blocks (blue = block edges)", color=INK, fontsize=10, loc="left")
    Cn = np.array(d["Cn"]) * MM
    w = 2.6 * (p.lip_radius + im.MeshParams().d_c) * MM
    axs[1].set_xlim(Cn[0] - 1.3 * w, Cn[0] + 0.9 * w), axs[1].set_ylim(Cn[1] - 1.1 * w, Cn[1] + 1.1 * w)
    axs[1].set_title("Lip: C-layer of four polar blocks, two strips upstream", color=INK, fontsize=10, loc="left")
    for name, dx, dy in (("Qa", -1.5, -1.0), ("Qb", -1.5, 0.6)):
        q = np.array(m.v[name]) * MM
        axs[1].annotate("5-block point", q, q + [dx - 2.0, dy * 2.2], color=INK2, fontsize=8,
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    fig.tight_layout()
    fig.savefig(out / "I5_blocks.png", dpi=170)
    plt.close(fig)


def mesh_lines(case):
    md = Path(case) / "constant/polyMesh"
    b = read_boundary(md)["frontAndBack"]
    pts = read_points(md)
    faces = read_faces(md)[b["startFace"]:b["startFace"] + b["nFaces"]]
    return [pts[f][:, :2] * MM for f in faces if pts[f[0], 2] < 0]


def fig_mesh(p, case, out):
    d = ip.design(p)
    quads = mesh_lines(case)
    cen = np.array([q.mean(axis=0) for q in quads])
    Cn, S, R = np.array(d["Cn"]) * MM, np.array(d["S"]) * MM, p.lip_radius * MM
    yc = d["y_cowl"] * MM
    views = [("Internal contraction and throat", (Cn[0] - 14, S[0] + 22), (S[1] - 6, yc + 16)),
             ("Cowl lip", (Cn[0] - 3.4, Cn[0] + 3.4), (Cn[1] - 3.0, Cn[1] + 3.0)),
             ("Lip, near-wall layer", (Cn[0] - 1.25 * R, Cn[0] + 0.25 * R), (Cn[1] - 0.75 * R, Cn[1] + 0.75 * R)),
             ("Shoulder", (S[0] - 3.5, S[0] + 3.5), (S[1] - 1.0, S[1] + 5.0))]
    fig, axs = plt.subplots(2, 2, figsize=(12.5, 9.2), facecolor=SURFACE)
    for ax, (title, xl, yl) in zip(axs.ravel(), views):
        style(ax)
        ax.grid(False)
        pad = 0.2 * (xl[1] - xl[0])
        k = (cen[:, 0] > xl[0] - pad) & (cen[:, 0] < xl[1] + pad) & (cen[:, 1] > yl[0] - pad) & (cen[:, 1] < yl[1] + pad)
        lw = 0.25 if k.sum() > 6000 else 0.4
        ax.add_collection(LineCollection([np.vstack([q, q[:1]]) for q, kk in zip(quads, k) if kk], colors=INK2, linewidths=lw))
        ax.set_xlim(*xl), ax.set_ylim(*yl)
        ax.set_title(f"{title}  ({int(k.sum())} cells in view)", color=INK, fontsize=10, loc="left")
    fig.suptitle(f"Mesh close-ups — {Path(case).name}, {len(quads)} cells", color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(out / "I5_mesh.png", dpi=170)
    plt.close(fig)


def fig_flow(p, case, time, out, tag):
    """Mach number and pressure of a (smoke) solution on the cell centres — a picture for checking where the
    shocks sit, not a converged result. One-hue sequential ramp (light = low)."""
    from matplotlib.colors import LinearSegmentedColormap
    from src import constants as C
    from src.foam_reader import read_internal_field as rd
    case = Path(case)
    d = ip.design(p)
    x, y = rd(case / "0/Cx") * MM, rd(case / "0/Cy") * MM
    T, pr, U = rd(case / time / "T"), rd(case / time / "p"), rd(case / time / "U")
    mach = np.hypot(U[:, 0], U[:, 1]) / np.sqrt(C.GAMMA_AIR * C.R_AIR * T)
    cmap = LinearSegmentedColormap.from_list("blue", ["#f3f8fe", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
    F, S = np.array(d["F"]) * MM, np.array(d["S"]) * MM
    views = [((-p.x_up * MM, d["x_exit"] * MM), (0, 1.9 * F[1])), ((F[0] - 45, S[0] + 95), (S[1] - 12, F[1] + 22))]
    fig, axs = plt.subplots(2, 2, figsize=(13.5, 7.6), facecolor=SURFACE, gridspec_kw=dict(width_ratios=[1.25, 1.0]))
    for row, (val, name) in enumerate(((mach, "Mach number"), (pr / pr.max(), "p / p_max"))):
        for ax, (xl, yl) in zip(axs[row], views):
            style(ax, xlabel=row == 1)
            ax.grid(False)
            k = (x > xl[0] - 5) & (x < xl[1] + 5) & (y > yl[0] - 5) & (y < yl[1] + 5)
            cs = ax.tricontourf(x[k], y[k], val[k], levels=np.linspace(0, float(val[k].max()), 25), cmap=cmap)
            draw_walls(ax, p, d, lw=1.0)
            ax.set_xlim(*xl), ax.set_ylim(*yl)
            cb = fig.colorbar(cs, ax=ax, fraction=0.035, pad=0.02)
            cb.ax.tick_params(labelsize=7, colors=MUTED)
            ax.set_title(name, color=INK, fontsize=10, loc="left")
    fig.suptitle(f"{case.name}, iteration {time} — smoke run, not a converged result", color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(out / f"I5_smoke_{tag}.png", dpi=150)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--set", nargs="*", default=[], metavar="NAME=VALUE")
    ap.add_argument("--mesh-case", type=Path)
    ap.add_argument("--flow-case", type=Path, help="case with a solution: writes I5_smoke_<tag>.png only")
    ap.add_argument("--time", help="time directory of --flow-case")
    ap.add_argument("--tag", default="flow")
    ap.add_argument("--out", type=Path, default=ROOT / "docs/benchmarks")
    a = ap.parse_args(argv)
    p = ip.with_overrides(ip.InletParams(), a.set)
    a.out.mkdir(parents=True, exist_ok=True)
    if a.flow_case:
        fig_flow(p, a.flow_case, a.time, a.out, a.tag)
        print("wrote", a.out / f"I5_smoke_{a.tag}.png")
        return 0
    fig_geometry(p, a.out)
    fig_blocks(p, a.out)
    if a.mesh_case and (a.mesh_case / "constant/polyMesh/points").exists():
        fig_mesh(p, a.mesh_case, a.out)
    print("wrote figures to", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
