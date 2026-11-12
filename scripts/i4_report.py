"""I4 report products: grid-convergence table (CSV) and figures from docs/benchmarks/I4_metrics.json.

Usage:  python -s scripts/i4_report.py [--root cases/validation] [--metrics docs/benchmarks/I4_metrics.json]
                                       [--out docs/benchmarks] [--settles SEP,REATT] [--no-figs]
Run scripts/i4_analyze.py first (without --no-json) to produce the metrics file.  Writes into --out:
  I4_grid.csv                 per metric and case family: values on L0/L1/L2, p, phi_ext, GCI21 or the flag
  I4_cf_flatplate.png         (i)   C_f vs Re_theta, M2aw and M5tw05, three grids, Van Driest II +-10 %
  I4_m6tw076_profiles.png     (ii)  reference-station profiles vs Duan DNS
  I4_ramp_wall.png            (iii) ramp wall C_f, p/p_inf, q_w vs arc length s
  I4_ramp_L2_history.png      (iv)  ramp L2: L_sep per saved time directory and outlet mass flux per step
--settles SEP,REATT (metres, relative to the corner) draws the Settles experimental separation / reattachment as
vertical markers; there is no default (no reference value has been entered yet).

Grid convergence uses src/validation_tools.grid_convergence (Celik et al. 2008).  h is taken from the cell count of
each case (case_info.txt "mesh cells"), 2D: h ~ N^(-1/2).  Level 0 = coarse, 2 = fine.
"""
import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import validation_tools as vt  # noqa: E402

OUT = ROOT / "docs/benchmarks"
LEVELS = (0, 1, 2)

# metric name -> extractor of one analysis result (entries of I4_metrics.json)
EXTRACT = {
    "cf_ref": lambda r: r["ref"]["cf"] if "ref" in r else r["last"]["cf_ref"],   # M6Tw076: ref.cf (same value)
    "minus_bq": lambda r: r["ref"]["minus_bq"],
    "two_st_over_cf": lambda r: r["two_st_over_cf"],
    "L_sep": lambda r: r["L_sep"],
    "sep": lambda r: r["sep"],
    "reatt": lambda r: r["reatt"],
    "q_max": lambda r: r["last"]["q_max"],            # ramp: max |q_w| (D-017)
}
METRICS = {
    "M2aw": ["cf_ref"],
    "M5tw05": ["cf_ref"],
    "M6Tw076": ["cf_ref", "minus_bq", "two_st_over_cf"],
    "ramp24": ["L_sep", "sep", "reatt", "q_max"],
}
CSV_COLUMNS = ["family", "metric", "n_L0", "n_L1", "n_L2", "phi_L0", "phi_L1", "phi_L2", "r21", "r32", "p",
               "phi_ext", "e_a21", "e_ext21", "gci21", "gci32", "asymptotic_ratio", "status", "band_min",
               "band_max", "iter_L2", "steady_L2"]


# --------------------------------------------------------------------------- small parsers

def family_level(case):
    """'flatplate/M2aw_L1' -> ('M2aw', 1); 'ramp24/L2' -> ('ramp24', 2).  Anything else raises ValueError."""
    m = re.fullmatch(r"flatplate/(\w+)_L(\d)", case)
    if m:
        return m.group(1), int(m.group(2))
    m = re.fullmatch(r"ramp24/L(\d)", case)
    if m:
        return "ramp24", int(m.group(1))
    raise ValueError(f"not a graded I4 case name: {case}")


def parse_cells(case_info_text):
    """Cell count from the 'mesh cells N ...' line of case_info.txt."""
    m = re.search(r"^mesh cells (\d+)", case_info_text, re.M)
    if not m:
        raise ValueError("no 'mesh cells' line")
    return int(m.group(1))


def parse_settles(s):
    """'SEP,REATT' (metres relative to the corner) -> (sep, reatt); None -> None."""
    if s is None:
        return None
    parts = s.split(",")
    if len(parts) != 2:
        raise ValueError("--settles expects SEP,REATT")
    return float(parts[0]), float(parts[1])


def _num(x):
    return float("nan") if x is None else float(x)


# --------------------------------------------------------------------------- grid table

def grid_table(results, cells):
    """Rows (dicts with CSV_COLUMNS) of the grid-convergence analysis.

    results: list of analysis results (I4_metrics.json); cells: {case name: cell count}.
    status: monotone / oscillatory / zero_change / diverging (from vt.grid_convergence), or
            missing_level (fewer than three levels available) / missing_value (a value is None/NaN)."""
    by = {}
    for r in results:
        try:
            fam, lev = family_level(r["case"])
        except ValueError:
            continue
        by.setdefault(fam, {})[lev] = r
    rows = []
    for fam, names in METRICS.items():
        if fam not in by:
            continue
        lv = by[fam]
        for name in names:
            row = {c: float("nan") for c in CSV_COLUMNS}
            row.update(family=fam, metric=name, status="", band_min=float("nan"), band_max=float("nan"))
            for k in LEVELS:
                if k in lv:
                    row[f"n_L{k}"] = cells.get(lv[k]["case"], float("nan"))
                    try:
                        row[f"phi_L{k}"] = _num(EXTRACT[name](lv[k]))
                    except (KeyError, TypeError):
                        row[f"phi_L{k}"] = float("nan")
            if 2 in lv:
                row["iter_L2"], row["steady_L2"] = lv[2].get("iterations"), lv[2].get("steady")
            phi = [row[f"phi_L{k}"] for k in LEVELS]
            n = [row[f"n_L{k}"] for k in LEVELS]
            if not all(k in lv for k in LEVELS):
                row["status"] = "missing_level"
            elif any(math.isnan(v) for v in phi) or any(math.isnan(v) for v in n):
                row["status"] = "missing_value"
            else:
                g = vt.grid_convergence(phi, n, dim=2)
                row.update({k: g[k] for k in ("p", "phi_ext", "e_a21", "e_ext21", "gci21", "gci32",
                                              "asymptotic_ratio", "r21", "r32")})
                row["status"] = g["status"]
                row["band_min"], row["band_max"] = g["band"]
            rows.append(row)
    return rows


def write_grid_csv(rows, path):
    def fmt(v):
        if isinstance(v, float):
            return "nan" if math.isnan(v) else f"{v:.6g}"
        return "" if v is None else v

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for r in rows:
            w.writerow([fmt(r[c]) for c in CSV_COLUMNS])


# --------------------------------------------------------------------------- outlet mass-flux series

def _read_dat(f):
    rows = [l.split() for l in f.read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]
    return np.array([float(r[0]) for r in rows]), np.array([float(r[-1]) for r in rows])


def read_flux_series(d):
    """(time, value) of all surfaceFieldValue*.dat under d, concatenated by time.
    After a restart OpenFOAM starts a new file (new start-time folder or a _<time> suffix); a file whose first time
    t0 lies inside the range of the earlier ones replaces them from t0 on (latest file wins on overlap)."""
    parts = []
    for f in d.rglob("surfaceFieldValue*.dat"):
        t, v = _read_dat(f)
        if len(t):
            parts.append((t[0], f, t, v))
    if not parts:
        raise ValueError(f"no surfaceFieldValue data under {d}")
    parts.sort(key=lambda p: (p[0], str(p[1].parent.name).zfill(12), p[1].name))
    ts, vs = np.array([]), np.array([])
    for t0, _, t, v in parts:
        keep = ts < t0
        ts, vs = np.r_[ts[keep], t], np.r_[vs[keep], v]
    return ts, vs


# --------------------------------------------------------------------------- figures

INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d3"
LEVEL_COL = {0: "#2a78d6", 1: "#eb6834", 2: "#1baf7a"}        # same colours as scripts/i3_plots.py
LEVEL_LS = {0: ":", 1: "--", 2: "-"}                            # secondary encoding (aqua is < 3:1 on white)
LEVEL_LAB = {0: "L0 (coarse)", 1: "L1", 2: "L2 (fine)"}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: F401
    plt.rcParams.update({
        "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
        "axes.spines.right": False, "font.size": 9, "legend.frameon": False, "lines.linewidth": 1.4,
        "savefig.dpi": 150})
    return plt


def _by_case(results):
    return {r["case"]: r for r in results}


def fig_cf_flatplate(results, path):
    from scripts import i4_analyze as ia
    from scripts.i4_cases import FLATPLATE
    from src import boundary_layer as bl
    from matplotlib.ticker import ScalarFormatter
    plt = _plt()
    by = _by_case(results)
    conds = [c for c in ("M2aw", "M5tw05") if f"flatplate/{c}_L2" in by or f"flatplate/{c}_L0" in by]
    fig, axs = plt.subplots(2, len(conds), figsize=(5.2 * len(conds), 6.6), sharex="col", squeeze=False)
    lo, hi = ia.RE_THETA_RANGE
    for j, cond in enumerate(conds):
        c = FLATPLATE[cond]
        fs, T_w = c["fs"], c["T_w"]
        re = np.geomspace(2000.0, 16000.0, 200)
        cf_vd = bl.cf_van_driest_ii(re, fs["M"], T_w / fs["T"], T_e=fs["T"])
        top, bot = axs[0, j], axs[1, j]
        for ax in (top, bot):
            ax.axvspan(lo, hi, color=GRID, alpha=0.45, lw=0)
        top.fill_between(re, 0.9 * cf_vd, 1.1 * cf_vd, color=INK, alpha=0.12, lw=0, label="Van Driest II ±10 %")
        top.plot(re, cf_vd, color=INK, lw=1.0, label="Van Driest II")
        bot.axhline(0, color=INK, lw=0.8)
        bot.axhspan(-ia.CF_TOL * 100, ia.CF_TOL * 100, color=INK, alpha=0.12, lw=0)
        for k in LEVELS:
            r = by.get(f"flatplate/{cond}_L{k}")
            if r is None:
                continue
            d = r["dist"]
            x_, rt_, cf_ = (np.asarray(d[key]) for key in ("x", "re_theta", "cf"))
            vd_ = bl.cf_van_driest_ii(np.clip(rt_, 1.0, None), fs["M"], T_w / fs["T"], T_e=fs["T"])
            m_all = (rt_ > re[0]) & (rt_ < re[-1])
            m = m_all & (x_ > 0.25 * c["L"])      # stations used by scripts/i4_analyze.py (x > 0.25 L)
            kw = dict(color=LEVEL_COL[k], ls=LEVEL_LS[k])
            for ax, y in ((top, cf_), (bot, 100 * (cf_ / vd_ - 1))):
                ax.plot(rt_[m_all], y[m_all], alpha=0.35, lw=0.8, **kw)    # whole plate, faint
                ax.plot(rt_[m], y[m], label=f"{LEVEL_LAB[k]}, {r['iterations']} it" if ax is top else None, **kw)
        top.set(xscale="log", ylabel="$C_f$", title=f"{cond}: M {fs['M']:g}, $T_w/T_\\infty$ = {T_w / fs['T']:.3f}")
        top.set_ylim(0.8 * cf_vd.min(), 1.2 * cf_vd.max())
        top.text(np.sqrt(lo * hi), top.get_ylim()[1], "evaluation range", ha="center",
                 va="top", color=INK2, fontsize=8)
        top.legend(fontsize=8, loc="lower left")
        bot.set(xscale="log", xlabel=r"$Re_\theta$", ylabel="$C_f$ / Van Driest II − 1 [%]", ylim=(-25, 25))
        bot.set_xticks([2000, 4000, 8000, 13000])
        bot.xaxis.set_major_formatter(ScalarFormatter())
        bot.minorticks_off()
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.text(0.5, 0.008, "bold lines: stations x > 0.25 L (used for the verdict); faint: rest of the plate",
             ha="center", fontsize=8, color=INK2)
    fig.savefig(path)
    plt.close(fig)


def fig_m6_profiles(results, path):
    from scripts import i4_analyze as ia
    plt = _plt()
    by = _by_case(results)
    duan = ia.duan_profile()
    fig, (a, b) = plt.subplots(1, 2, figsize=(10.5, 4.4))
    a.plot(duan["zplus"], duan["Uvd"], color=INK, lw=1.0, label="Duan DNS (Zhang et al. 2018)")
    b.plot(duan["zod"], duan["t_tinf"], color=INK, lw=1.0, label="Duan DNS (Zhang et al. 2018)")
    for k in LEVELS:
        r = by.get(f"flatplate/M6Tw076_L{k}")
        if r is None:
            continue
        p = r["profile"]
        kw = dict(color=LEVEL_COL[k], ls=LEVEL_LS[k], label=f"{LEVEL_LAB[k]} ($Re_\\theta$ = {p['re_theta']:.0f})")
        a.plot(p["y_plus"], p["u_vd_plus"], **kw)
        b.plot(p["y_over_delta"], p["T_over_Tinf"], **kw)
    a.set(xscale="log", xlim=(0.5, 3000), ylim=(0, 30), xlabel="$y^+$", ylabel="$u^+_{VD}$",
          title="Van Driest transformed velocity")
    b.set(xlim=(0, 1.5), xlabel=r"$y/\delta_{99}$", ylabel=r"$T/T_\infty$", title="Mean temperature")
    a.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _settles_vlines(ax, settles, label=True):
    if settles:
        for v, lab in zip(settles, ("Settles separation", "Settles reattachment")):
            ax.axvline(v, color=INK, lw=1.0, ls="-.", label=lab if label else None)


def fig_ramp_wall(results, path, settles=None, window=(-0.3, 0.5)):
    plt = _plt()
    by = _by_case(results)
    spec = [("cf", "$C_f$", 1.0), ("p_ratio", r"$p_w/p_\infty$", 1.0), ("q_w", r"$q_w$ [kW/m²] (into wall > 0)", 1e-3)]
    fig, axs = plt.subplots(3, 1, figsize=(8.2, 9.0), sharex=True)
    for ax, (key, lab, scale) in zip(axs, spec):
        lo, hi = np.inf, -np.inf
        for k in LEVELS:
            r = by.get(f"ramp24/L{k}")
            if r is None:
                continue
            s, y = np.asarray(r["dist"]["s"]), scale * np.asarray(r["dist"][key])
            o = np.argsort(s)
            ax.plot(s[o], y[o], color=LEVEL_COL[k], ls=LEVEL_LS[k], label=f"{LEVEL_LAB[k]}, {r['iterations']} it")
            m = (s >= window[0]) & (s <= window[1])
            if m.any():
                lo, hi = min(lo, y[m].min()), max(hi, y[m].max())
        if lo < hi:
            pad = 0.06 * (hi - lo)
            ax.set_ylim(lo - pad, hi + pad)
        if key == "cf":
            ax.axhline(0, color=INK, lw=0.8)
        ax.axvline(0, color=INK2, lw=0.8, ls=":")
        _settles_vlines(ax, settles, label=key == "cf")
        ax.set_ylabel(lab)
    axs[0].legend(fontsize=8, loc="upper left")
    axs[0].set_title("24° compression ramp, wall distributions (corner at s = 0)")
    axs[-1].set(xlim=window, xlabel="arc length from the corner s [m] (negative upstream)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def lsep_history(case):
    """[(step, sep, reatt, L_sep)] for every saved time directory of the ramp case."""
    from scripts import i4_analyze as ia
    from scripts.i3_analyze import time_dirs
    out = []
    for t in time_dirs(case):
        d = ia.ramp_distribution(case, t)[0]
        out.append((int(float(t)), d["sep"], d["reatt"], d["L_sep"]))
    return out


def fig_ramp_history(case, path, settles=None, window=2000):
    plt = _plt()
    hist = lsep_history(case)
    it = np.array([h[0] for h in hist], float)
    sep, reatt, L = (np.array([np.nan if h[i] is None else h[i] for h in hist], float) for i in (1, 2, 3))
    try:
        t, m = read_flux_series(case / "postProcessing/mf_outlet")
    except ValueError:
        t = m = None
    fig, axs = plt.subplots(3, 1, figsize=(8.2, 8.6), sharex=True)
    axs[0].plot(it, L, color=LEVEL_COL[2], marker="o", ms=4)
    axs[0].set(ylabel="$L_{sep}$ [m]", title=f"{case.parent.name}/{case.name}: iteration history ({len(it)} saved times)")
    if settles:
        axs[0].axhline(settles[1] - settles[0], color=INK, lw=1.0, ls="-.", label="Settles")
        axs[0].legend(fontsize=8)
    axs[1].plot(it, sep, color=LEVEL_COL[2], marker="o", ms=4, label="separation")
    axs[1].plot(it, reatt, color=LEVEL_COL[1], ls="--", marker="s", ms=4, label="reattachment")
    axs[1].set(ylabel="wall position s [m]")
    axs[1].legend(fontsize=8)
    if t is not None:
        ref = m[-1]
        axs[2].plot(t, 100 * (m - ref) / abs(ref), color=INK, lw=1.0)
        axs[2].set(ylabel=f"outlet mass flux − last [%]\n(last = {ref:.6g})")
        axs[2].axvspan(t[-1] - window, t[-1], color=GRID, alpha=0.5, lw=0)
        late = t > 200                      # the start-up transient (first steps) would flatten the rest
        dev = 100 * (m[late] - ref) / abs(ref)
        pad = 0.08 * (dev.max() - dev.min())
        axs[2].set_ylim(dev.min() - pad, dev.max() + pad)
    axs[2].set_xlabel("pseudo-time step (shaded: last 2,000 steps)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# --------------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT / "cases/validation")
    ap.add_argument("--metrics", type=Path, default=OUT / "I4_metrics.json")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--settles", help="SEP,REATT in metres relative to the corner (Settles experiment)")
    ap.add_argument("--no-figs", action="store_true")
    a = ap.parse_args(argv)
    settles = parse_settles(a.settles)
    results = json.loads(a.metrics.read_text())
    cells = {}
    for r in results:
        info = a.root / r["case"] / "case_info.txt"
        if info.exists():
            cells[r["case"]] = parse_cells(info.read_text())
    rows = grid_table(results, cells)
    a.out.mkdir(parents=True, exist_ok=True)
    write_grid_csv(rows, a.out / "I4_grid.csv")
    print(f"wrote {a.out / 'I4_grid.csv'} ({len(rows)} rows)")
    if not a.no_figs:
        fig_cf_flatplate(results, a.out / "I4_cf_flatplate.png")
        fig_m6_profiles(results, a.out / "I4_m6tw076_profiles.png")
        fig_ramp_wall(results, a.out / "I4_ramp_wall.png", settles)
        fig_ramp_history(a.root / "ramp24/L2", a.out / "I4_ramp_L2_history.png", settles)
        print("wrote figures to", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
