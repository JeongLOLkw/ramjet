"""First-cell y+ check on no-slip walls (CLAUDE.md rule 2). Wall functions are not used.

Limits:  steady / heat-flux cases  y+ < 1   (default)
         unsteady shock-motion cases (I9, I10)  y+ <= 5  (--limit 5 --inclusive)
Exit code 0 = pass, 1 = violation (the run must then be treated as failed).

Usage:  python -s scripts/yplus_check.py CASE TIME PATCH [PATCH ...] [--limit 1] [--inclusive]
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.wall import wall_data  # noqa: E402


def check(y_plus, limit=1.0, inclusive=False):
    """(ok, max y+). ok iff max < limit (or <= limit when inclusive). NaN fails."""
    y_plus = np.asarray(y_plus, float)
    if y_plus.size == 0 or not np.all(np.isfinite(y_plus)):
        return False, float("nan")
    m = float(y_plus.max())
    return (m <= limit if inclusive else m < limit), m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case"), ap.add_argument("time"), ap.add_argument("patches", nargs="+")
    ap.add_argument("--limit", type=float, default=1.0)
    ap.add_argument("--inclusive", action="store_true")
    a = ap.parse_args(argv)
    ok_all = True
    for patch in a.patches:
        w = wall_data(a.case, a.time, patch)
        ok, m = check(w["y_plus"], a.limit, a.inclusive)
        i = int(np.nanargmax(w["y_plus"])) if np.isfinite(m) else 0
        print(f"{patch}: y+ max {m:.4g} at x = {w['x'][i]:.6g}, mean {np.mean(w['y_plus']):.4g} "
              f"-> {'PASS' if ok else 'FAIL'} (limit {'<=' if a.inclusive else '<'} {a.limit:g})")
        ok_all &= ok
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
