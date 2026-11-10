#!/usr/bin/env python3
"""I2 speed benchmark: scaled forwardStep with rhoCentralFoam or HiSA, MPI np.

Re-runnable:  python -s scripts/bench.py --solver hisa --np 4 --steps 60
Appends one row to docs/benchmarks/I2_raw.csv. Case settings are copied to
docs/benchmarks/I2_cases/<solver>_np<N>/ (CLAUDE.md rule 9: settings + commit).

Only run controls are changed (mesh counts, dt, endTime, write control,
decomposition). Numerical/physical settings of the example cases are untouched.
"""
import argparse
import csv
import datetime as dt_
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from src import bench_tools as bt

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "cases/validation/forwardStep"
OUT = ROOT / "docs/benchmarks"
RUNS = ROOT / "cases/runs/bench"
OF_RC = "/usr/lib/openfoam/openfoam2512/etc/bashrc"
CSV = OUT / "I2_raw.csv"

SOLVERS = {
    # base case dir, executable, dt/dx ratio, initial-field dir
    # rhoCentralFoam: example uses maxCo 0.2 -> dt = 0.05 dx  (|U|+c ~ 4)
    # HiSA: example dt 0.005 on dx = 3/288  -> dt/dx = 0.48
    "rcf": dict(base=BASE / "rcf", exe="rhoCentralFoam", ratio=0.05, init="0", mesh=1.0),
    # HiSA example base mesh is 1.5x the rhoCentralFoam one (72x24 vs 48x16) -> 2/3 gives the identical mesh
    "hisa": dict(base=BASE / "hisa/simulation", exe="hisa", ratio=0.48, init="0.org", mesh=2 / 3),
}
DECOMP = """FoamFile {{ version 2.0; format ascii; class dictionary; object decomposeParDict; }}
numberOfSubdomains {n};
method scotch;
"""


def sh(cmd, cwd, log=None):
    full = f"source {OF_RC} >/dev/null 2>&1; {cmd}"
    out = open(log, "w") if log else subprocess.DEVNULL
    r = subprocess.run(["bash", "-c", full], cwd=cwd, stdout=out, stderr=subprocess.STDOUT)
    if log:
        out.close()
    return r.returncode


def sample_memory(exe, stop, peak):
    """Peak of summed VmRSS (GB) over processes named `exe`, plus min MemAvailable (GB)."""
    while not stop.is_set():
        tot = 0
        for p in Path("/proc").glob("[0-9]*"):
            try:
                if (p / "comm").read_text().strip() != exe:
                    continue
                for line in (p / "status").read_text().splitlines():
                    if line.startswith("VmRSS:"):
                        tot += int(line.split()[1])
            except OSError:
                pass
        peak["rss_gb"] = max(peak["rss_gb"], tot / 1e6)
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                peak["avail_gb"] = min(peak["avail_gb"], int(line.split()[1]) / 1e6)
        stop.wait(0.5)


def git_state():
    h = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    return h + ("+dirty" if dirty else "")


def power_state():
    try:
        return "AC" if Path("/sys/class/power_supply/AC1/online").read_text().strip() == "1" else "battery"
    except OSError:
        return "unknown"


def build_case(spec, solver, np_, scale, steps, dt):
    case = RUNS / f"{solver}_np{np_}"
    if case.exists():
        shutil.rmtree(case)
    case.mkdir(parents=True)
    for sub in ("system", "constant"):
        shutil.copytree(spec["base"] / sub, case / sub, ignore=shutil.ignore_patterns("polyMesh"))
    shutil.copytree(spec["base"] / spec["init"], case / "0")
    bm = case / "system/blockMeshDict"
    text, cells = bt.scale_blocks(bm.read_text(), scale * spec["mesh"])
    bm.write_text(text)
    cd = case / "system/controlDict"
    t = cd.read_text()
    for k, v in [("startFrom", "startTime"), ("startTime", "0"), ("endTime", f"{steps * dt:.10g}"),
                 ("deltaT", f"{dt:.10g}"), ("adjustTimeStep", "no"),
                 ("writeControl", "timeStep"), ("writeInterval", "100000000")]:
        t = bt.set_entry(t, k, v)
    cd.write_text(t)
    (case / "system/decomposeParDict").write_text(DECOMP.format(n=np_))
    return case, cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solver", choices=SOLVERS, required=True)
    ap.add_argument("--np", type=int, required=True)
    ap.add_argument("--steps", type=int, required=True)
    ap.add_argument("--scale", type=float, default=3.5, help="cell-count factor per direction (3.5 -> ~198k cells)")
    ap.add_argument("--dt", type=float, help="override dt (default: ratio * dx)")
    ap.add_argument("--skip", type=int, default=None, help="warm-up steps to ignore (default 10%%)")
    a = ap.parse_args()

    spec = SOLVERS[a.solver]
    dx = 3.0 / (192 * a.scale)
    dt = a.dt or round(spec["ratio"] * dx, 6)
    case, cells = build_case(spec, a.solver, a.np, a.scale, a.steps, dt)
    assert sh("blockMesh", case, case / "log.blockMesh") == 0, "blockMesh failed"
    cmd = spec["exe"]
    if a.np > 1:
        assert sh("decomposePar", case, case / "log.decomposePar") == 0, "decomposePar failed"
        cmd = f"mpirun -np {a.np} --oversubscribe --bind-to none {spec['exe']} -parallel"
    stop, peak = threading.Event(), {"rss_gb": 0.0, "avail_gb": 1e9}
    th = threading.Thread(target=sample_memory, args=(spec["exe"], stop, peak), daemon=True)
    th.start()
    t0 = time.time()
    rc = sh(cmd, case, case / "log.solver")
    wall = time.time() - t0
    stop.set()
    th.join()
    steps = bt.parse_steps((case / "log.solver").read_text())
    ok = rc == 0 and len(steps) == a.steps
    skip = a.skip if a.skip is not None else max(1, a.steps // 10)
    row = dict(
        date=dt_.datetime.now().isoformat(timespec="seconds"), commit=git_state(),
        openfoam="v2512", solver=a.solver, np=a.np, cells=cells, dt=dt, steps_done=len(steps),
        steps_req=a.steps, skip=skip, exit_ok=ok, total_wall_s=round(wall, 1),
        mean_step_s=bt.mean_step_wall(steps, skip) if len(steps) > skip else "",
        pseudo_iters_mean=(sum(s["pseudo_iters"] for s in steps[skip:]) / len(steps[skip:]))
        if a.solver == "hisa" and len(steps) > skip else "",
        peak_rss_gb=round(peak["rss_gb"], 2), min_avail_gb=round(peak["avail_gb"], 2), power=power_state(),
    )
    ms = row["mean_step_s"]
    row["us_per_cell_step"] = round(ms / cells * a.np * 1e6, 3) if ms != "" else ""  # core-us
    OUT.mkdir(exist_ok=True)
    new = not CSV.exists()
    with open(CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    dst = OUT / "I2_cases" / f"{a.solver}_np{a.np}"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(case, dst, ignore=shutil.ignore_patterns("processor*", "polyMesh", "[1-9]*", "0.[0-9]*", "0"))
    print(row)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
