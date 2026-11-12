"""I4 solver-validation analysis: flat-plate skin friction / heat flux and the 24 deg ramp.

Usage:  python -s scripts/i4_analyze.py [--root cases/validation] [--cases flatplate/M2aw_L0 ...] [--no-json]
Writes docs/benchmarks/I4_metrics.json and prints tables.
Pass/fail criteria are fixed in docs/decisions.md D-013 (registered before the runs).
Heat flux comes from scripts/heatflux.py only (CLAUDE.md rule 3); y+ from scripts/yplus_check.py (rule 2).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import yplus_check  # noqa: E402
from scripts.heatflux import case_heat_flux  # noqa: E402
from scripts.i3_analyze import blocks, run_meta, time_dirs  # noqa: E402
from scripts.i4_cases import FLATPLATE, RAMP  # noqa: E402
from src import boundary_layer as bl  # noqa: E402
from src import constants as C  # noqa: E402
from src import validation_tools as vt  # noqa: E402
from src.foam_reader import read_internal_field  # noqa: E402

DATA = ROOT / "docs/validation_data"
OUT = ROOT / "docs/benchmarks"

STEADY_WINDOW, STEADY_TOL, MASS_TOL = 2000, 2e-3, 5e-3      # CLAUDE.md rule 5
RE_THETA_RANGE = (4000.0, 13000.0)                          # TMR 2DZPH comparison range
CF_TOL = 0.10                                               # plan §6 / D-013 criterion 3
EDGE_FACTOR = 3.0                                           # integrals to 3 delta99 (D-013 criterion 3)
DUAN = dict(re_theta=9455.0, theta=0.95e-3, H=13.6, delta=23.8e-3, u_tau=45.1, minus_bq=0.02)  # file header


# --------------------------------------------------------------------------- reference data

def tmr_zone(fname, M, tw_ratio):
    """(x, y) arrays of the TMR zone for M and Tw/Tini."""
    zones, cur = {}, None
    for line in open(DATA / fname):
        if line.startswith("ZONE"):
            cur = line.split('"')[1]
            zones[cur] = []
        elif cur and line.strip() and line[0] not in "#V":
            zones[cur].append([float(v) for v in line.split()])
    key = next(k for k in zones if f"M={M:.1f}" in k and f"Tw/Tini={tw_ratio:.3f}" in k)
    return np.array(zones[key]).T


def duan_profile():
    """Dict of wall-normal profiles of case M6Tw076 (column names from the file's '#variables=' line)."""
    lines = (DATA / "M6Tw076_Stat.dat").read_text().splitlines()
    i = next(n for n, l in enumerate(lines) if l.startswith("#variables="))
    names = lines[i][len("#variables="):].strip().split(",")
    arr = np.array([[float(v) for v in l.split()] for l in lines[i + 1:] if l.strip()])
    return dict(zip(names, arr.T))


# --------------------------------------------------------------------------- case IO

def load_fields(case, t):
    n = len(read_internal_field(case / "0/Cx"))
    f = dict(x=read_internal_field(case / "0/Cx"), y=read_internal_field(case / "0/Cy"))
    for name in ("p", "T", "U"):
        f[name] = read_internal_field(case / t / name, n)
    f["rho"] = f["p"] / (C.R_AIR * f["T"])
    return f


def wall_columns(case, w):
    """Cell indices (n_faces, ny) of the grid column above each wall face (structured blockMesh blocks)."""
    off, col0 = 0, {}
    for nx, ny in blocks(case):
        for i in range(nx):
            col0[off + i] = (off, nx, ny, i)
        off += nx * ny
    cols = []
    for own in w["owner"]:
        o, nx, ny, i = col0[int(own)]
        cols.append(o + i + nx * np.arange(ny))
    return np.array(cols)


def station(f, w, cols, i, fs):
    """Boundary-layer quantities at wall face i. Reference = free stream (D-013)."""
    c = cols[i]
    n = np.array([-(w["y"][min(i + 1, len(cols) - 1)] - w["y"][max(i - 1, 0)]),
                  w["x"][min(i + 1, len(cols) - 1)] - w["x"][max(i - 1, 0)]])
    n /= np.linalg.norm(n)                       # wall normal into the fluid (2D)
    t = np.array([n[1], -n[0]])
    yn = (f["x"][c] - w["x"][i]) * n[0] + (f["y"][c] - w["y"][i]) * n[1]
    ut = f["U"][c, 0] * t[0] + f["U"][c, 1] * t[1]
    u_loc = ut.max()
    d99 = bl.delta99(yn, ut, u_loc)
    dstar, theta = bl.integral_thicknesses(yn, f["rho"][c], ut, fs["rho"], fs["U"], y_max=EDGE_FACTOR * d99)
    return dict(yn=yn, ut=ut, T=f["T"][c], rho=f["rho"][c], delta99=d99, dstar=dstar, theta=theta,
                re_theta=fs["rho"] * fs["U"] * theta / fs["mu"], u_edge_ratio=u_loc / fs["U"])


def latest_flux(d):
    """Last-column value of the last data row of the surfaceFieldValue*.dat under d with the largest last time.
    After a solver restart OpenFOAM writes a new file (new start-time dir or surfaceFieldValue_<time>.dat); the
    first match can be stale. Files without data rows are ignored."""
    best = None
    for f in d.rglob("surfaceFieldValue*.dat"):
        rows = [l.split() for l in f.read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]
        if rows and (best is None or float(rows[-1][0]) > best[0]):
            best = (float(rows[-1][0]), float(rows[-1][-1]))
    if best is None:
        raise ValueError(f"no surfaceFieldValue data under {d}")
    return best[1]


def mass_imbalance(case):
    flux = {d.name[3:]: latest_flux(d) for d in sorted((case / "postProcessing").glob("mf_*"))}
    return vt.mass_imbalance(flux), flux


def steady(case, times, monitor):
    """Rule 5: monitors within STEADY_TOL over the last STEADY_WINDOW steps + mass imbalance < MASS_TOL.
    monitor(t) -> dict of floats. Returns dict with per-monitor relative change (None if it cannot be judged)."""
    its = [int(float(t)) for t in times]
    hist = [monitor(t) for t in times]
    out = {}
    for key in hist[0]:
        try:
            out[key] = vt.relative_change(its, [h[key] for h in hist], STEADY_WINDOW)
        except ValueError:
            out[key] = None
    imb, flux = mass_imbalance(case)
    ok = all(v is not None and v <= STEADY_TOL for v in out.values()) and imb < MASS_TOL
    return dict(rel_change=out, mass_imbalance=imb, mass_flux=flux, steady=bool(ok), last=hist[-1], iterations=its[-1])


# --------------------------------------------------------------------------- flat plate

def plate_distribution(case, t, fs, T_w):
    w = case_heat_flux(case, t, "wall")
    f = load_fields(case, t)
    cols = wall_columns(case, w)
    st = [station(f, w, cols, i, fs) for i in range(len(cols))]
    T_aw = bl.recovery_temperature(fs["T"], fs["M"])
    d = dict(x=w["x"], cf=bl.skin_friction(w["tau_w"], fs["rho"], fs["U"]), q_w=w["q_w"], y_plus=w["y_plus"],
             re_theta=np.array([s["re_theta"] for s in st]), delta99=np.array([s["delta99"] for s in st]),
             H=np.array([s["dstar"] / s["theta"] for s in st]),
             u_edge_ratio=np.array([s["u_edge_ratio"] for s in st]),
             minus_bq=bl.minus_b_q(w["q_w"], w["rho_w"], w["tau_w"], w["T_w"]))
    if abs(T_aw - T_w) > 1e-6 * T_aw:
        d["st"] = bl.stanton(w["q_w"], fs["rho"], fs["U"], T_w, T_aw)
    return d, w, f, cols, st


def at_re_theta(d, key, target):
    """Value of d[key] where Re_theta first crosses `target` going downstream (NaN if never)."""
    r = d["re_theta"]
    i = np.nonzero((r[:-1] < target) & (r[1:] >= target))[0]
    if len(i) == 0:
        return float("nan")
    i = i[-1]      # last upward crossing: downstream of transition
    s = (target - r[i]) / (r[i + 1] - r[i])
    return float(d[key][i] + s * (d[key][i + 1] - d[key][i]))


def cf_verdict_mask(re_theta):
    """Stations of the C_f verdict, D-013 criterion 3 as written: 4,000 <= Re_theta <= 13,000 (whole plate)."""
    re_theta = np.asarray(re_theta, float)
    return (re_theta >= RE_THETA_RANGE[0]) & (re_theta <= RE_THETA_RANGE[1])


def cf_restricted_mask(re_theta, x, L):
    """The narrower selection used up to 2026-11-13 (additionally x > 0.25 L, a choice of commit 8c75c85 that is not
    in D-013). Kept as information only (cf_err_max_x025)."""
    return cf_verdict_mask(re_theta) & (np.asarray(x, float) > 0.25 * L)


def flatplate(case):
    cond = case.name.split("_L")[0]
    c = FLATPLATE[cond]
    fs, T_w = c["fs"], c["T_w"]
    times = time_dirs(case)
    target = DUAN["re_theta"] if cond == "M6Tw076" else 10000.0

    def monitor(t):
        d = plate_distribution(case, t, fs, T_w)[0]
        return dict(cf_ref=at_re_theta(d, "cf", target), q_max=float(d["q_w"].max()))

    res = dict(case=str(case.relative_to(case.parents[1])), cond=cond, **run_meta(case))
    res.update(steady(case, times, monitor))
    d, w, f, cols, st = plate_distribution(case, times[-1], fs, T_w)
    ok, ymax = yplus_check.check(d["y_plus"])
    res.update(y_plus_max=ymax, y_plus_ok=bool(ok), re_theta_max=float(d["re_theta"].max()),
               u_edge_dev_max=float(np.max(np.abs(d["u_edge_ratio"] - 1))))
    sel = cf_verdict_mask(d["re_theta"])
    sel_x = cf_restricted_mask(d["re_theta"], d["x"], c["L"])
    if cond != "M6Tw076":
        cf_vd = bl.cf_van_driest_ii(d["re_theta"], fs["M"], T_w / fs["T"], T_e=fs["T"])
        err = d["cf"] / cf_vd - 1
        res.update(n_in_range=int(sel.sum()),
                   cf_err_max=float(np.max(np.abs(err[sel]))) if sel.any() else None,
                   cf_err_max_x025=float(np.max(np.abs(err[sel_x]))) if sel_x.any() else None,
                   cf_err_at_ref=float(at_re_theta(dict(re_theta=d["re_theta"], e=err), "e", target)),
                   cf_pass=bool(sel.any() and np.max(np.abs(err[sel])) <= CF_TOL))
    else:
        T_aw = bl.recovery_temperature(fs["T"], fs["M"])
        ref = {k: at_re_theta(d, k, target) for k in ("x", "cf", "st", "minus_bq", "H", "delta99")}
        rho_w = fs["p"] / (C.R_AIR * T_w)
        duan_cf = 2 * (rho_w / fs["rho"]) * (DUAN["u_tau"] / fs["U"]) ** 2     # from u_tau and rho_w (file header)
        res.update(ref=ref, two_st_over_cf=2 * ref["st"] / ref["cf"], T_aw=T_aw,
                   duan=dict(cf=duan_cf, minus_bq=DUAN["minus_bq"], H=DUAN["H"], delta=DUAN["delta"]),
                   cf_vs_duan=ref["cf"] / duan_cf - 1)
    res["dist"] = {k: v.tolist() for k, v in d.items()}
    # profile at the reference Re_theta (nearest wall face) for u+ / T plots
    i = int(np.nanargmin(np.abs(np.where(d["x"] > 0.25 * c["L"], d["re_theta"], np.nan) - target)))
    s = st[i]
    u_tau = np.sqrt(abs(w["tau_w"][i]) / w["rho_w"][i])
    nu_w = bl.mu_sutherland(w["T_w"][i]) / w["rho_w"][i]
    # Van Driest (I) transformed velocity u_VD = int sqrt(rho/rho_w) du (TMR 2DZPH page), trapezoidal in u
    rho_mid = 0.5 * (np.r_[w["rho_w"][i], s["rho"][:-1]] + s["rho"])
    u_vd = np.cumsum(np.sqrt(rho_mid / w["rho_w"][i]) * np.diff(np.r_[0.0, s["ut"]])) / u_tau
    res["profile"] = dict(x=float(d["x"][i]), re_theta=float(d["re_theta"][i]), y_plus=(s["yn"] * u_tau / nu_w).tolist(),
                          u_plus=(s["ut"] / u_tau).tolist(), u_vd_plus=u_vd.tolist(),
                          y_over_delta=(s["yn"] / s["delta99"]).tolist(), u_over_uinf=(s["ut"] / fs["U"]).tolist(),
                          T_over_Tinf=(s["T"] / fs["T"]).tolist())
    return res


# --------------------------------------------------------------------------- ramp

def ramp_distribution(case, t):
    fs = RAMP["fs"]
    w = case_heat_flux(case, t, "wall")
    # arc length from the corner (x = 0): negative upstream, positive along the ramp
    s = np.where(w["x"] < 0, w["x"], np.hypot(w["x"], w["y"]))
    # whole wall except the first 0.1 m after the plate leading edge (the old |s| < 0.19 m window silently
    # missed a bubble that started further upstream); open = reversed flow still at the outlet
    o = np.argsort(s)
    ext = bl.separation_extent(s[o], w["tau_w"][o], x_min=-RAMP["L_plate"] + 0.1)
    return dict(s=s, x=w["x"], cf=bl.skin_friction(w["tau_w"], fs["rho"], fs["U"]), p_ratio=w["p_w"] / fs["p"],
                q_w=w["q_w"], y_plus=w["y_plus"], sep=ext["sep"], reatt=ext["reatt"], L_sep=ext["L_sep"],
                bubble_open=ext["open"]), w


def info_change(its, q, s, window):
    """Information-only wall-heat-flux changes over the last `window` steps (same window as vt.relative_change).
    q[time, face], its = iteration numbers, s = arc length (ramp surface: s > 0). Not part of the steady verdict.
    q_pointwise: max over faces of (max - min over the window) / |q at the last time| (0/0 -> 0);
    q_ramp_peak: vt.relative_change of max|q_w| over the ramp faces. ValueError if the history is shorter than window."""
    its, q, s = np.asarray(its, float), np.asarray(q, float), np.asarray(s, float)
    q_ramp_peak = vt.relative_change(its, np.abs(q[:, s > 0]).max(axis=1), window)
    w = q[its >= its[-1] - window]
    rng, last = w.max(axis=0) - w.min(axis=0), np.abs(q[-1])
    return dict(q_pointwise=float(np.max(np.divide(rng, last, out=np.zeros_like(rng), where=last > 0))),
                q_ramp_peak=q_ramp_peak)


def ramp(case):
    fs = RAMP["fs"]
    times = time_dirs(case)
    cache = {}

    def dist(t):
        if t not in cache:
            cache[t] = ramp_distribution(case, t)
        return cache[t]

    def monitor(t):
        d = dist(t)[0]
        # q_max = magnitude of the peak wall heat flux, D-017 (docs/decisions.md); identical to max(q_w) on a wall
        # with q_w > 0, and (unlike max(q_w)) the largest magnitude on the hot ramp wall where q_w < 0
        return dict(L_sep=d["L_sep"], q_max=abs(bl.peak_heat_flux(d["q_w"])[0]))

    res = dict(case=str(case.relative_to(case.parents[1])), **run_meta(case))
    res.update(steady(case, times, monitor))
    try:
        res["info_change"] = info_change([int(float(t)) for t in times], [dist(t)[0]["q_w"] for t in times],
                                         dist(times[-1])[0]["s"], STEADY_WINDOW)
    except ValueError:
        pass
    d, w = dist(times[-1])
    ok, ymax = yplus_check.check(d["y_plus"])
    f = load_fields(case, times[-1])
    cols = wall_columns(case, w)
    inc = {}
    for xr in (-0.0635, -0.0508):          # the two reported positions of the incoming-layer survey (validation_data.md §2)
        try:
            s = station(f, w, cols, int(np.argmin(np.abs(w["x"] - xr))), fs)
        except ValueError as e:      # e.g. the station lies inside reversed flow (no 0.99 u_e edge)
            inc[f"{xr * 1e3:.1f}mm"] = dict(error=str(e))
            continue
        inc[f"{xr * 1e3:.1f}mm"] = dict(delta99=s["delta99"], dstar=s["dstar"], theta=s["theta"], re_theta=s["re_theta"])
    res.update(y_plus_max=ymax, y_plus_ok=bool(ok), sep=d["sep"], reatt=d["reatt"], L_sep=d["L_sep"],
               bubble_open=d["bubble_open"], incoming=inc,
               settles_incoming=dict(delta=23e-3, dstar=6.1e-3, theta=1.2e-3),
               dist={k: v.tolist() for k, v in d.items() if isinstance(v, np.ndarray)})
    return res


# --------------------------------------------------------------------------- main

def summary(r):
    rc = ", ".join(f"{k} {v:.2e}" if v is not None else f"{k} n/a" for k, v in r["rel_change"].items())
    line = (f"{r['case']:<28} it {r['iterations']:>6}  y+max {r['y_plus_max']:.3f} {'ok' if r['y_plus_ok'] else 'FAIL'}"
            f"  mass {r['mass_imbalance']:.2e}  d2000[{rc}]  {'STEADY' if r['steady'] else 'not steady'}")
    if "info_change" in r:
        ic = ", ".join(f"{k} {v:.1e}" if v is not None else f"{k} n/a" for k, v in r["info_change"].items())
        line += f"  info[{ic}]"
    if "cf_err_max" in r and r["cf_err_max"] is not None:
        line += f"  |Cf/VDII-1|max {100 * r['cf_err_max']:.2f}% ({r['n_in_range']} pts) {'PASS' if r['cf_pass'] else 'FAIL'}"
    if "two_st_over_cf" in r:
        line += (f"  Cf {r['ref']['cf']:.3e} (Duan {r['duan']['cf']:.3e})  2St/Cf {r['two_st_over_cf']:.3f}"
                 f"  -Bq {r['ref']['minus_bq']:.4f} (Duan {r['duan']['minus_bq']})")
    if "L_sep" in r:
        line += f"  sep {r['sep']}  reatt {r['reatt']}  L_sep {r['L_sep']:.4g} m"
        if r["bubble_open"]:
            line += "  BUBBLE OPEN AT OUTLET (reversed flow leaves no reattachment in the domain)"
    return line


def default_cases(root):
    """Default case list: flat plates then ramp levels. Archived failed runs (`..._failed_...`) are excluded;
    they can still be analysed by naming them in --cases."""
    found = sorted((root / "flatplate").glob("*_L*")) + sorted((root / "ramp24").glob("L*"))
    return [c for c in found if "_failed_" not in c.name]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT / "cases/validation")
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--no-json", action="store_true")
    a = ap.parse_args(argv)
    cases = [a.root / c for c in a.cases] if a.cases else default_cases(a.root)
    results = []
    for case in cases:
        if not (case / "run_info.txt").exists() or not time_dirs(case):
            print(f"{case}: not run — skipped")
            continue
        r = ramp(case) if case.parent.name == "ramp24" else flatplate(case)
        results.append(r)
        print(summary(r))
    if not a.no_json:
        OUT.mkdir(exist_ok=True)
        (OUT / "I4_metrics.json").write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
