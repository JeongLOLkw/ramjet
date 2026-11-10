"""I3 solver-validation analysis: metrics vs analytic references.

Usage:  python -s scripts/i3_analyze.py [--families sod wedge expansion forwardStep] [--plots]
Writes docs/benchmarks/I3_metrics.json (machine-readable) and prints tables.
Pass/fail criteria are fixed in docs/decisions.md D-010 (registered before the runs).
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.i3_cases import (EXPANSION, P_INF, SOD_L, SOD_R, SOD_T, T_INF,  # noqa: E402
                              WEDGE)
from src import constants as C  # noqa: E402
from src import gasdynamics as gd  # noqa: E402
from src import validation_tools as vt  # noqa: E402
from src.foam_reader import read_internal_field  # noqa: E402

VAL = ROOT / "cases/validation"
OUT = ROOT / "docs/benchmarks"
G = C.GAMMA_AIR

STEADY_WINDOW = 2000      # CLAUDE.md rule 5 (applied to validation metrics)
STEADY_TOL = 2e-3
MASS_TOL = 5e-3


# --------------------------------------------------------------------------- IO

def time_dirs(case):
    ts = []
    for d in case.iterdir():
        if d.is_dir() and re.fullmatch(r"[0-9.eE+-]+", d.name) and d.name != "0":
            ts.append((float(d.name), d.name))
    return [n for _, n in sorted(ts)]


def blocks(case):
    """[(nx, ny), ...] from blockMeshDict, in block order (= cell order)."""
    txt = (case / "system/blockMeshDict").read_text()
    return [(int(a), int(b)) for a, b in re.findall(r"hex \([^)]*\) \((\d+) (\d+) 1\)", txt)]


def gas_R(case):
    # forwardStep uses the normalised gas of scripts/i3_cases.thermo(normalised=True): R = 1/gamma
    return 1.0 / C.GAMMA_AIR if "forwardStep" in str(case) else C.R_AIR


def load(case, t):
    cx = read_internal_field(case / "0/Cx")
    cy = read_internal_field(case / "0/Cy")
    n = len(cx)
    p = read_internal_field(case / t / "p", n)
    T = read_internal_field(case / t / "T", n)
    U = read_internal_field(case / t / "U", n)
    R = gas_R(case)
    rho = p / (R * T)
    M = np.linalg.norm(U, axis=1) / np.sqrt(G * R * T)
    return dict(x=cx, y=cy, p=p, T=T, U=U, rho=rho, M=M)


def step_index(case, names):
    """Map written time names to solver step numbers."""
    if case.name.startswith("hisa") and case.parent.name in ("wedge", "expansion"):
        return [int(float(n)) for n in names]
    times = [float(m) for m in re.findall(r"^Time = (\S+)", (case / "log.solver").read_text(), re.M)]
    times = np.array(times)
    return [int(np.argmin(np.abs(times - float(n)))) + 1 for n in names]


def mass_imbalance(case):
    pp = case / "postProcessing"
    flux = {}
    for p in ("inlet", "outlet"):
        f = next((pp / f"mf_{p}").rglob("surfaceFieldValue.dat"))
        flux[p] = float(f.read_text().strip().splitlines()[-1].split()[-1])
    return vt.mass_imbalance(flux)


def run_meta(case):
    info = dict(l.split(" ", 1) for l in (case / "run_info.txt").read_text().strip().splitlines())
    lt = (case / "log.time").read_text()
    wall = re.search(r"Elapsed \(wall clock\) time .*: (\S+)", lt).group(1)
    rss = int(re.search(r"Maximum resident set size \(kbytes\): (\d+)", lt).group(1))
    return dict(commit=info.get("commit", "?")[:10], dirty=info.get("dirty_files"), wall=wall, rss_MB=rss // 1024)


# --------------------------------------------------------------------------- Sod

def sod_case(case):
    t = time_dirs(case)[-1]
    f = load(case, t)
    order = np.argsort(f["x"])
    x = f["x"][order]
    dx = x[1] - x[0]
    rho_e, u_e, p_e = gd.riemann_profile(x, float(t), SOD_L, SOD_R, G)
    u = f["U"][order, 0]
    return dict(N=len(x), t=float(t), dx=dx,
                L1_rho=vt.l1_error(f["rho"][order], rho_e, dx),
                L1_u=vt.l1_error(u, u_e, dx) / np.sqrt(SOD_L[2] / SOD_L[0]),
                L1_p=vt.l1_error(f["p"][order], p_e, dx) / SOD_L[2],
                min_p=float(f["p"].min()), min_T=float(f["T"].min()),
                **run_meta(case))


def sod(prefix):
    cases = sorted((VAL / "sod").glob(f"{prefix}_N*"), key=lambda d: int(d.name.split("_N")[1]))
    rows = [sod_case(c) | {"case": c.name} for c in cases if time_dirs(c)]
    if len(rows) >= 2:
        h = [r["dx"] for r in rows]
        for k in ("rho", "u", "p"):
            o = vt.observed_order(h, [r[f"L1_{k}"] for r in rows])
            for r, oo in zip(rows[1:], o):
                r[f"order_{k}"] = float(oo)
    return rows


# --------------------------------------------------------------------------- wedge

def wedge_metrics(case, t, theta):
    f = load(case, t)
    (nx1, ny), (nx2, _) = blocks(case)
    off = nx1 * ny
    idx = off + np.arange(ny)[:, None] * nx2 + np.arange(nx2)[None, :]  # [j, i]
    X, Y, P, Mf = f["x"][idx], f["y"][idx], f["p"][idx], f["M"][idx]
    xs, ys, p2, m2 = [], [], [], []
    for i in range(nx2):
        xc = X[:, i].mean()
        if not (0.3 <= xc <= 0.95):
            continue
        prof = P[:, i]
        level = 0.5 * (prof[0] + prof[-1])
        s = vt.crossing(np.arange(ny), prof, level)
        if s is None:
            continue
        j0 = int(s)
        w = s - j0
        xs.append(X[j0, i] * (1 - w) + X[j0 + 1, i] * w)
        ys.append(Y[j0, i] * (1 - w) + Y[j0 + 1, i] * w)
        dy = Y[1, i] - Y[0, i]
        below = Y[:, i] < ys[-1] - 5 * dy
        p2.extend(P[below, i])
        m2.extend(Mf[below, i])
    beta, x_int, resid = vt.fit_line_angle(xs, ys)
    return dict(beta=float(np.degrees(beta)), x_int=float(x_int), fit_rms=float(resid),
                p2_p1=float(np.mean(p2) / P_INF), p2_std=float(np.std(p2) / P_INF),
                M2=float(np.mean(m2)), min_p=float(f["p"].min()), min_T=float(f["T"].min()))


def expansion_metrics(case, t, theta, M1):
    f = load(case, t)
    (nx1, ny), (nx2, _) = blocks(case)
    off = nx1 * ny
    sel = np.arange(off, off + nx2 * ny)
    x, y = f["x"][sel], f["y"][sel]
    r, psi = np.hypot(x, y), np.arctan2(y, x)
    ex = gd.expansion_corner(M1, theta, G)
    psi_tr = np.arcsin(1 / ex["M2"]) - theta           # trailing Mach line (region choice only)
    delta = 1.0 / ny                                    # nominal cell size (H = 1)
    reg = (r >= 0.6) & (r <= 1.1) & (x <= 1.15) & (psi >= -theta + np.radians(1.0)) \
        & (psi <= psi_tr - 3 * delta / np.maximum(r, 1e-9))
    p2 = f["p"][sel][reg] / P_INF
    m2 = f["M"][sel][reg]
    # fan profile on the arc 0.95 <= r <= 1.05 (information only)
    arc = (np.abs(r - 1.0) <= 0.05) & (x <= 1.15)
    m_ex = np.array([gd.fan_mach_at_ray(pp, M1, theta, G) for pp in psi[arc]])
    fan_l1 = float(np.mean(np.abs(f["M"][sel][arc] - m_ex)))
    return dict(M2=float(m2.mean()), M2_std=float(m2.std()), p2_p1=float(p2.mean()), p2_std=float(p2.std()),
                n_region=int(reg.sum()), fan_meanabs_dM=fan_l1,
                min_p=float(f["p"].min()), min_T=float(f["T"].min()))


def steady_family(fam, conds, metric_fn, keys):
    rows = []
    for cid, (M1, th) in conds.items():
        theta = np.radians(th)
        for case in sorted((VAL / fam).glob(f"*_{cid}_n*"), key=lambda d: (d.name.split("_")[0], int(d.name.split("_n")[1]))):
            names = time_dirs(case)
            if not names:
                continue
            args = (theta,) if fam == "wedge" else (theta, M1)
            hist = [metric_fn(case, n, *args) for n in names]
            steps = step_index(case, names)
            last = hist[-1]
            try:
                chg = {k: vt.relative_change(steps, [h[k] for h in hist], STEADY_WINDOW) for k in keys}
            except ValueError as e:
                chg = {k: float("nan") for k in keys}
                last["steady_note"] = str(e)
            mi = mass_imbalance(case)
            steady = all(v < STEADY_TOL for v in chg.values()) and mi < MASS_TOL
            rows.append(dict(case=case.name, cond=cid, M1=M1, theta=th, n=int(case.name.split("_n")[1]),
                             solver=case.name.split("_")[0], steps=steps[-1], mass_imb=mi,
                             change=chg, steady=bool(steady), **last, **run_meta(case)))
    return rows


# --------------------------------------------------------------------------- forward step

def fs_case(case):
    t = time_dirs(case)[-1]
    f = load(case, t)
    (n1x, n1y), (n2x, n2y), (n3x, n3y) = blocks(case)
    dx = 0.6 / n1x
    # bow shock on the line y ~ 0.1 (block 1 row closest to 0.1)
    idx1 = np.arange(n1x * n1y).reshape(n1y, n1x)
    j = int(np.argmin(np.abs(f["y"][idx1[:, 0]] - 0.1)))
    row = idx1[j]
    pr = f["p"][row]
    x_bow = vt.crossing(f["x"][row], pr, 1.0 + 0.5 * (pr.max() - 1.0))
    # step-face pressure: last column of block 1 (cells adjacent to x = 0.6, 0 < y < 0.2)
    p_face = float(f["p"][idx1[:, -1]].mean())
    # top wall: row adjacent to y = 1 across blocks 2 and 3, first jump from free stream
    o2, o3 = n1x * n1y, n1x * n1y + n2x * n2y
    top = np.concatenate([o2 + (n2y - 1) * n2x + np.arange(n2x), o3 + (n3y - 1) * n3x + np.arange(n3x)])
    pt = f["p"][top]
    x_top = vt.crossing(f["x"][top], pt, 1.0 + 0.5 * (pt.max() - 1.0))
    return dict(case=case.name, t=float(t), dx=dx, cells=len(f["x"]), x_bow=x_bow, standoff=0.6 - x_bow,
                x_top_shock=x_top, p_face_mean=p_face, p_pitot=gd.rayleigh_pitot(3.0, G),
                min_p=float(f["p"].min()), min_T=float(f["T"].min()), max_rho=float(f["rho"].max()),
                **run_meta(case)), f


def forward_step():
    rows, fields = [], {}
    for case in sorted((VAL / "forwardStep").glob("*_dx*")):
        if not time_dirs(case):
            continue
        r, f = fs_case(case)
        rows.append(r)
        fields[case.name] = f
    # identical meshes -> cell-by-cell relative L1 of density between pairs of runs
    pairs = {}
    for a, b in (("rcf_dx80", "hisa_dx80"), ("rcf_dx160", "hisa_dx160"), ("rcf_co01_dx80", "hisa_tol6_dx80"),
                 ("rcf_co01_dx160", "hisa_dx160"), ("rcf_dx80", "rcf_co01_dx80"), ("rcf_dx160", "rcf_co01_dx160"),
                 ("hisa_dx80", "hisa_tol6_dx80")):
        if a in fields and b in fields:
            pairs[f"{a} vs {b}"] = float(np.sum(np.abs(fields[a]["rho"] - fields[b]["rho"])) / np.sum(fields[b]["rho"]))
    return {"cases": rows, "rel_L1_rho_pairs": pairs}


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", nargs="*", default=["sod", "wedge", "expansion", "forwardStep"])
    a = ap.parse_args()
    res = {}
    if "sod" in a.families:
        res["sod"] = {s: sod(s) for s in ("rcf", "hisa", "rcf_co01", "hisa_tol6")}
    if "wedge" in a.families:
        res["wedge"] = steady_family("wedge", WEDGE, wedge_metrics, ("beta", "p2_p1"))
        for r in res["wedge"]:
            o = gd.oblique_shock(r["M1"], np.radians(r["theta"]), G)
            r["beta_th"], r["p2_p1_th"], r["M2_th"] = float(np.degrees(o["beta"])), float(o["p2_p1"]), float(o["M2"])
            r["err_beta"] = r["beta"] / r["beta_th"] - 1
            r["err_p"] = r["p2_p1"] / r["p2_p1_th"] - 1
            r["err_M2"] = r["M2"] / r["M2_th"] - 1
    if "expansion" in a.families:
        res["expansion"] = steady_family("expansion", EXPANSION, expansion_metrics, ("M2", "p2_p1"))
        for r in res["expansion"]:
            e = gd.expansion_corner(r["M1"], np.radians(r["theta"]), G)
            r["M2_th"], r["p2_p1_th"] = float(e["M2"]), float(e["p2_p1"])
            r["err_M2"] = r["M2"] / r["M2_th"] - 1
            r["err_p"] = r["p2_p1"] / r["p2_p1_th"] - 1
    if "forwardStep" in a.families:
        res["forwardStep"] = forward_step()
    OUT.mkdir(exist_ok=True)
    out = OUT / "I3_metrics.json"
    old = json.loads(out.read_text()) if out.exists() else {}
    old.update(res)
    out.write_text(json.dumps(old, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
