#!/usr/bin/env python3
"""Figure -> numbers digitizer (axis calibration + colour-mask point extraction).

Purpose: read values off published figures (pressure distributions, frequency
plots, separation lengths, ...) as a CSV with uncertainties, so the numbers can
be used in validation cases.  Tests: tests/test_digitize.py (synthetic
matplotlib figures with known values).

Pixel convention (everywhere): pixel-INDEX coordinates of the numpy image
array.  Column c, row r; the centre of the top-left pixel is (0, 0); rows grow
downward.  This is what an image viewer that shows integer pixel indices
reports.  Calibration needs two reference pixels and their true values, for x
and y separately (linear or log10 axis).

Uncertainty: each extracted point carries x_unc and y_unc = the value spanned
by ONE pixel at that point, |v(p+0.5) - v(p-0.5)|.  On a log axis this is
evaluated locally.  It does NOT include the error of the user's calibration
pixels or of the figure itself; read the reference ticks carefully.

Run with the project environment:
    PYTHONNOUSERSITE=1 ~/miniforge3/envs/inlet/bin/python scripts/digitize.py \\
        fig.png --x-cal PX1 V1 PX2 V2 --y-cal PY1 V1 PY2 V2 \\
        --color R G B --tol 40 --mode markers --out fig.csv
(--x-cal takes pixel COLUMNS, --y-cal takes pixel ROWS.)
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# data classes
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    x_unc: float
    y_unc: float


@dataclass(frozen=True)
class AxisCal:
    """One axis: two reference pixels p1, p2 with true values v1, v2.

    Linear: v = v1 + (p - p1) * (v2 - v1) / (p2 - p1).
    Log:    log10(v) is linear in p (v1, v2 must be > 0).
    """

    p1: float
    v1: float
    p2: float
    v2: float
    log: bool = False

    def __post_init__(self):
        if self.p1 == self.p2:
            raise ValueError("calibration pixels must differ (p1 == p2)")
        if self.v1 == self.v2:
            raise ValueError("calibration values must differ (v1 == v2)")
        if self.log and (self.v1 <= 0 or self.v2 <= 0):
            raise ValueError("log axis needs positive calibration values")

    def _f(self, v: float) -> float:
        return math.log10(v) if self.log else v

    def _finv(self, u: float) -> float:
        return 10.0 ** u if self.log else u

    def to_value(self, p: float) -> float:
        u1, u2 = self._f(self.v1), self._f(self.v2)
        return self._finv(u1 + (p - self.p1) * (u2 - u1) / (self.p2 - self.p1))

    def to_pixel(self, v: float) -> float:
        u1, u2 = self._f(self.v1), self._f(self.v2)
        return self.p1 + (self._f(v) - u1) * (self.p2 - self.p1) / (u2 - u1)

    def pixel_value(self, p: float) -> float:
        """Value spanned by one pixel at pixel position p (uncertainty unit)."""
        return abs(self.to_value(p + 0.5) - self.to_value(p - 0.5))


@dataclass(frozen=True)
class Calibration:
    x: AxisCal  # p = column index
    y: AxisCal  # p = row index

    def point(self, col: float, row: float) -> Point:
        return Point(self.x.to_value(col), self.y.to_value(row),
                     self.x.pixel_value(col), self.y.pixel_value(row))


# --------------------------------------------------------------------------
# image -> mask -> points
# --------------------------------------------------------------------------


def load_image(path) -> np.ndarray:
    """Load an image as uint8 RGB (H, W, 3); transparency is put on white."""
    from PIL import Image

    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or "transparency" in im.info:
        rgba = im.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, rgba)
    return np.asarray(im.convert("RGB"), dtype=np.uint8)


def color_mask(img: np.ndarray, rgb, tol: float = 40) -> np.ndarray:
    """True where every channel is within +-tol of rgb (per-channel box)."""
    diff = np.abs(img.astype(np.int16) - np.asarray(rgb, dtype=np.int16))
    return np.all(diff <= tol, axis=-1)


def extract_markers(mask: np.ndarray, cal: Calibration, min_area: int = 10,
                    ) -> list[Point]:
    """Centroid of each 8-connected blob of mask pixels with >= min_area pixels.

    Touching markers merge into one blob (limitation); choose a colour that
    separates series and check the count against the figure.
    """
    from scipy import ndimage

    labels, n = ndimage.label(mask, structure=np.ones((3, 3), dtype=int))
    pts: list[Point] = []
    for i in range(1, n + 1):
        rows, cols = np.nonzero(labels == i)
        if rows.size < min_area:
            continue
        pts.append(cal.point(float(cols.mean()), float(rows.mean())))
    pts.sort(key=lambda p: (p.x, p.y))
    return pts


def extract_curve(mask: np.ndarray, cal: Calibration, x_values=None,
                  ) -> list[Point]:
    """Curve y(x) from a mask: per pixel column, the mean row of mask pixels.

    x_values=None: one point per column that has mask pixels.
    x_values=[...]: values at those x (linear interpolation between the two
    neighbouring columns, both of which must contain curve pixels; x with no
    curve there is skipped, never invented).
    Assumes a single-valued function of x; a vertical segment or two branches
    in one column are averaged.
    """
    h, w = mask.shape
    col_row = np.full(w, np.nan)
    for c in range(w):
        rows = np.nonzero(mask[:, c])[0]
        if rows.size:
            col_row[c] = rows.mean()
    if x_values is None:
        return [cal.point(float(c), col_row[c]) for c in range(w)
                if not np.isnan(col_row[c])]
    pts: list[Point] = []
    for xv in x_values:
        c = cal.x.to_pixel(xv)
        c0 = math.floor(c)
        frac = c - c0
        if c0 < 0 or c0 >= w or np.isnan(col_row[c0]):
            continue
        if frac < 1e-9:
            row = col_row[c0]
        else:
            if c0 + 1 >= w or np.isnan(col_row[c0 + 1]):
                continue
            row = col_row[c0] * (1 - frac) + col_row[c0 + 1] * frac
        yv = cal.y.to_value(row)
        pts.append(Point(float(xv), yv, cal.x.pixel_value(c),
                         cal.y.pixel_value(row)))
    return pts


# --------------------------------------------------------------------------
# CSV output
# --------------------------------------------------------------------------


def script_git_hash() -> str:
    """Short git hash of the repo containing this script ('-dirty' if the
    script itself has uncommitted changes; 'unknown' if git is unavailable)."""
    here = Path(__file__).resolve()
    try:
        h = subprocess.run(["git", "-C", str(here.parent), "rev-parse",
                            "--short", "HEAD"], capture_output=True, text=True,
                           check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(here.parent), "status",
                                "--porcelain", "--", str(here)],
                               capture_output=True, text=True,
                               check=True).stdout.strip()
        if not h:
            return "unknown"
        return h + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _axis_line(name: str, ax: AxisCal) -> str:
    kind = "log10" if ax.log else "linear"
    return (f"# {name}: {kind}; pixel {ax.p1:g} -> {ax.v1:g}, "
            f"pixel {ax.p2:g} -> {ax.v2:g}")


def write_csv(path, points, cal: Calibration, image: str, mode: str, color,
              tol: float, script_hash: str | None = None) -> None:
    """CSV with columns x,y,x_unc,y_unc and '#' header comments (rule 9)."""
    if script_hash is None:
        script_hash = script_git_hash()
    lines = [
        "# digitize.py output (figure -> numbers)",
        f"# image: {image}",
        f"# script: scripts/digitize.py  git: {script_hash}",
        f"# mode: {mode}  color_rgb: {color[0]} {color[1]} {color[2]}  "
        f"tol: {tol:g}",
        "# pixel convention: index coords, centre of top-left pixel = (0,0), "
        "rows downward",
        _axis_line("x_cal", cal.x),
        _axis_line("y_cal", cal.y),
        "# x_unc, y_unc = value spanned by one pixel (excludes calibration "
        "and figure errors)",
        "x,y,x_unc,y_unc",
    ]
    for p in points:
        lines.append(f"{p.x!r},{p.y!r},{p.x_unc!r},{p.y_unc!r}")
    Path(path).write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Digitize markers or a curve of one colour from a figure "
                    "image into CSV (x, y, x_unc, y_unc).")
    ap.add_argument("image")
    ap.add_argument("--x-cal", nargs=4, type=float, required=True,
                    metavar=("COL1", "VAL1", "COL2", "VAL2"),
                    help="two reference pixel COLUMNS and their x values")
    ap.add_argument("--y-cal", nargs=4, type=float, required=True,
                    metavar=("ROW1", "VAL1", "ROW2", "VAL2"),
                    help="two reference pixel ROWS and their y values")
    ap.add_argument("--xlog", action="store_true", help="x axis is log10")
    ap.add_argument("--ylog", action="store_true", help="y axis is log10")
    ap.add_argument("--color", nargs=3, type=int, required=True,
                    metavar=("R", "G", "B"), help="series colour (0-255)")
    ap.add_argument("--tol", type=float, default=40,
                    help="per-channel colour tolerance (default 40)")
    ap.add_argument("--mode", choices=("markers", "curve"), default="markers")
    ap.add_argument("--min-area", type=int, default=10,
                    help="markers: minimum blob size in pixels (default 10)")
    ap.add_argument("--x-values", nargs="+", type=float, default=None,
                    help="curve: sample at these x values instead of every "
                         "pixel column")
    ap.add_argument("--out", required=True, help="output CSV path")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cal = Calibration(
            x=AxisCal(args.x_cal[0], args.x_cal[1], args.x_cal[2],
                      args.x_cal[3], log=args.xlog),
            y=AxisCal(args.y_cal[0], args.y_cal[1], args.y_cal[2],
                      args.y_cal[3], log=args.ylog))
    except ValueError as e:
        print(f"error: bad calibration: {e}", file=sys.stderr)
        return 2
    img = load_image(args.image)
    mask = color_mask(img, args.color, args.tol)
    if args.mode == "markers":
        pts = extract_markers(mask, cal, args.min_area)
    else:
        pts = extract_curve(mask, cal, args.x_values)
    if not pts:
        print("error: no pixels matched the colour; check --color/--tol",
              file=sys.stderr)
        return 3
    write_csv(args.out, pts, cal, image=Path(args.image).name, mode=args.mode,
              color=args.color, tol=args.tol)
    print(f"{len(pts)} points -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
