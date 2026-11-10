"""Tests for scripts/digitize.py (figure -> numbers tool).

Rule 10: these tests were written before the implementation.  They build
synthetic matplotlib figures with known data, run the digitizer on the PNG and
compare with the known values.

Pixel convention used everywhere (tests and tool): pixel-INDEX coordinates,
column index c and row index r of the numpy image array, where the centre of the
top-left pixel is (0, 0) and rows grow downward.  matplotlib display
coordinates (X, Y) (origin bottom-left, pixel i covers [i, i+1)) map to
    c = X - 0.5,   r = (H - Y) - 0.5.

Tolerance (why):
  One pixel is the smallest thing the image can resolve, so the natural unit of
  error is "the value spanned by one pixel", u = |v(p+0.5) - v(p-0.5)| at the
  point in question (for a log axis this is evaluated locally, so it scales
  with the value).  Error budget with the calibration pixels rounded to
  integers (a human reads integer pixel indices off a viewer):
    marker snapping                         0 (markers are drawn as patches
                                              at exact sub-pixel positions, see
                                              _markers; matplotlib's own
                                              plot/scatter markers are snapped
                                              to whole pixels by Agg, which is a
                                              property of the renderer, not of
                                              the tool under test)
    rounding of each calibration pixel     <= 0.5 px  (interior: <= 0.5 px
                                                       after interpolation)
    centroid of an anti-aliased marker      ~ 0.1-0.2 px
    column-mean of a 2-px-wide gentle line  ~ 0.2 px
  Sum < 1 px, so we require |error| <= 1 pixel-value (TOL_PX = 1.0) for every
  extracted point.  We do not use anything looser; the tool must also report a
  per-point uncertainty that is itself ~ one pixel-value, which is tested
  separately.
"""
import csv
import importlib.util
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "digitize.py"
TOL_PX = 1.0
DPI = 100


def _load():
    spec = importlib.util.spec_from_file_location("digitize", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["digitize"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dg():
    return _load()


# --------------------------------------------------------------------------
# synthetic figure helpers
# --------------------------------------------------------------------------
def _display_to_index(fig, ax, x, y):
    """Data coords -> pixel-index coords (col, row) of the saved PNG."""
    H = fig.get_size_inches()[1] * DPI
    X, Y = ax.transData.transform((x, y))
    return X - 0.5, (H - Y) - 0.5


def _calib_pixels(fig, ax, pts):
    """Integer pixel indices of data points, as a human would read them."""
    out = []
    for x, y in pts:
        c, r = _display_to_index(fig, ax, x, y)
        out.append((int(round(c)), int(round(r))))
    return out


def _make_fig(xscale="linear", yscale="linear", xlim=(0, 10), ylim=(0, 100)):
    fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=DPI)
    ax.set_xscale(xscale)
    ax.set_yscale(yscale)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.grid(True, color="0.8", lw=0.8)  # distractor: light-grey grid
    return fig, ax


def _markers(ax, xs, ys, color, radius_px=4.5):
    """Draw disc markers at exact sub-pixel positions.

    ax.plot/ax.scatter markers are snapped to the pixel grid by the Agg
    backend (measured: up to ~1 px shift), which would put a property of the
    renderer into the 'truth'.  Circle patches in display coordinates
    (IdentityTransform) are anti-aliased at the exact position (measured
    centroid error < 0.1 px), also on log axes where a data-space circle
    would be distorted.
    """
    from matplotlib.patches import Circle
    from matplotlib.transforms import IdentityTransform
    for x, y in zip(xs, ys):
        X, Y = ax.transData.transform((x, y))
        ax.add_patch(Circle((X, Y), radius_px, color=color, lw=0,
                            transform=IdentityTransform(), snap=False, zorder=3,
                            clip_on=False))


def _save(fig, path):
    fig.savefig(path, dpi=DPI)  # not tight: keeps the transData mapping exact
    plt.close(fig)


def _px_value(cal_axis, p):
    """Value spanned by one pixel at pixel position p."""
    return abs(cal_axis.to_value(p + 0.5) - cal_axis.to_value(p - 0.5))


# --------------------------------------------------------------------------
# 1. axis calibration (pure maths, no image)
# --------------------------------------------------------------------------
class TestAxisCalibration:
    def test_linear_exact(self, dg):
        ax = dg.AxisCal(p1=100, v1=0.0, p2=500, v2=10.0)
        assert ax.to_value(100) == pytest.approx(0.0)
        assert ax.to_value(500) == pytest.approx(10.0)
        assert ax.to_value(300) == pytest.approx(5.0)
        assert ax.to_value(700) == pytest.approx(15.0)  # extrapolation

    def test_linear_inverted_pixel_axis(self, dg):
        """y axes: pixel rows grow downward, values grow upward."""
        ax = dg.AxisCal(p1=400, v1=0.0, p2=100, v2=100.0)
        assert ax.to_value(250) == pytest.approx(50.0)
        assert ax.to_value(100) == pytest.approx(100.0)

    def test_log_exact(self, dg):
        ax = dg.AxisCal(p1=100, v1=1.0, p2=500, v2=1000.0, log=True)
        assert ax.to_value(100) == pytest.approx(1.0)
        assert ax.to_value(500) == pytest.approx(1000.0)
        # 3 decades over 400 px: v = 10**(3 * (p - 100) / 400)
        assert ax.to_value(200) == pytest.approx(10 ** 0.75)
        assert ax.to_value(300) == pytest.approx(10 ** 1.5)

    def test_roundtrip(self, dg):
        for log in (False, True):
            ax = dg.AxisCal(p1=50, v1=2.0, p2=450, v2=200.0, log=log)
            for p in (50, 123.4, 300, 450, 600):
                assert ax.to_pixel(ax.to_value(p)) == pytest.approx(p)

    def test_pixel_value_helper(self, dg):
        ax = dg.AxisCal(p1=0, v1=0.0, p2=100, v2=50.0)
        assert ax.pixel_value(40) == pytest.approx(0.5)
        axl = dg.AxisCal(p1=0, v1=1.0, p2=100, v2=100.0, log=True)
        # local: one pixel is a larger value step where the value is larger
        assert axl.pixel_value(90) > axl.pixel_value(10)

    @pytest.mark.parametrize("kw", [
        dict(p1=10, v1=0.0, p2=10, v2=1.0),           # same pixel
        dict(p1=10, v1=1.0, p2=20, v2=1.0),           # same value
        dict(p1=10, v1=0.0, p2=20, v2=1.0, log=True),  # log of 0
        dict(p1=10, v1=-1.0, p2=20, v2=1.0, log=True),  # log of negative
    ])
    def test_invalid_calibration_rejected(self, dg, kw):
        with pytest.raises(ValueError):
            dg.AxisCal(**kw)


# --------------------------------------------------------------------------
# 2. colour mask
# --------------------------------------------------------------------------
class TestColourMask:
    def test_mask_selects_only_target_colour(self, dg):
        img = np.full((20, 20, 3), 255, dtype=np.uint8)
        img[2:5, 2:5] = (255, 0, 0)       # target
        img[10:13, 10:13] = (0, 0, 255)   # other series
        img[15, 15] = (230, 30, 30)       # near target, inside tol
        m = dg.color_mask(img, (255, 0, 0), tol=40)
        assert m[3, 3] and m[15, 15]
        assert not m[11, 11] and not m[0, 0]
        assert m.sum() == 9 + 1

    def test_tolerance_is_per_channel(self, dg):
        img = np.zeros((1, 2, 3), dtype=np.uint8)
        img[0, 0] = (100, 100, 100)
        img[0, 1] = (100, 100, 141)
        m = dg.color_mask(img, (100, 100, 100), tol=40)
        assert m[0, 0] and not m[0, 1]

    def test_load_image_drops_alpha_on_white(self, dg, tmp_path):
        from PIL import Image
        im = Image.new("RGBA", (4, 4), (0, 0, 0, 0))  # fully transparent
        p = tmp_path / "a.png"
        im.save(p)
        arr = dg.load_image(p)
        assert arr.shape == (4, 4, 3)
        assert (arr == 255).all()  # transparent -> white background


# --------------------------------------------------------------------------
# 3. marker extraction on synthetic figures
# --------------------------------------------------------------------------
def _match(true_pts, got_pts):
    """Nearest-neighbour matching (each true point gets one distinct match)."""
    got = list(got_pts)
    out = []
    for t in true_pts:
        j = int(np.argmin([(g[0] - t[0]) ** 2 + (g[1] - t[1]) ** 2 for g in got]))
        out.append(got.pop(j))
    return out


class TestMarkers:
    def _run(self, dg, tmp_path, xscale, yscale, xlim, ylim, true_pts,
             cal_x, cal_y):
        fig, ax = _make_fig(xscale, yscale, xlim, ylim)
        xs, ys = zip(*true_pts)
        _markers(ax, xs, ys, (0, 0, 1))                 # series to extract
        _markers(ax, [xs[0]], [ys[-1]], (1, 0, 0))      # other series
        px = _calib_pixels(fig, ax, [(cal_x[0], ylim[0]), (cal_x[1], ylim[0])])
        py = _calib_pixels(fig, ax, [(xlim[0], cal_y[0]), (xlim[1], cal_y[1])])
        img = tmp_path / "fig.png"
        _save(fig, img)
        arr = dg.load_image(img)
        cal = dg.Calibration(
            x=dg.AxisCal(px[0][0], cal_x[0], px[1][0], cal_x[1],
                         log=(xscale == "log")),
            y=dg.AxisCal(py[0][1], cal_y[0], py[1][1], cal_y[1],
                         log=(yscale == "log")))
        mask = dg.color_mask(arr, (0, 0, 255), tol=60)
        pts = dg.extract_markers(mask, cal, min_area=15)
        return cal, pts

    def test_linear_axes(self, dg, tmp_path):
        true = [(1.0, 10.0), (2.5, 80.0), (4.0, 35.0), (6.2, 60.0), (8.7, 5.0)]
        cal, pts = self._run(dg, tmp_path, "linear", "linear", (0, 10), (0, 100),
                             true, cal_x=(0, 10), cal_y=(0, 100))
        assert len(pts) == len(true)  # the red squares must not be picked up
        got = _match(true, [(p.x, p.y) for p in pts])
        for (tx, ty), (gx, gy) in zip(true, got):
            assert abs(gx - tx) <= TOL_PX * _px_value(cal.x, cal.x.to_pixel(tx))
            assert abs(gy - ty) <= TOL_PX * _px_value(cal.y, cal.y.to_pixel(ty))

    def test_log_log_axes(self, dg, tmp_path):
        true = [(1.5, 3.0), (7.0, 40.0), (30.0, 250.0), (120.0, 9.0),
                (600.0, 700.0)]
        cal, pts = self._run(dg, tmp_path, "log", "log", (1, 1000), (1, 1000),
                             true, cal_x=(1, 1000), cal_y=(1, 1000))
        assert len(pts) == len(true)
        got = _match([(np.log10(x), np.log10(y)) for x, y in true],
                     [(np.log10(p.x), np.log10(p.y)) for p in pts])
        for (tx, ty), (lx, ly) in zip(true, got):
            gx, gy = 10 ** lx, 10 ** ly
            assert abs(gx - tx) <= TOL_PX * _px_value(cal.x, cal.x.to_pixel(tx))
            assert abs(gy - ty) <= TOL_PX * _px_value(cal.y, cal.y.to_pixel(ty))

    def test_semilog_y_with_inner_calibration_points(self, dg, tmp_path):
        """Calibration points need not be the axis ends (ticks inside)."""
        true = [(0.5, 2.0), (3.0, 20.0), (5.5, 200.0), (9.0, 5000.0)]
        cal, pts = self._run(dg, tmp_path, "linear", "log", (0, 10), (1, 10000),
                             true, cal_x=(2, 8), cal_y=(10, 1000))
        got = _match([(x, np.log10(y)) for x, y in true],
                     [(p.x, np.log10(p.y)) for p in pts])
        for (tx, ty), (gx, gly) in zip(true, got):
            gy = 10 ** gly
            assert abs(gx - tx) <= TOL_PX * _px_value(cal.x, cal.x.to_pixel(tx))
            assert abs(gy - ty) <= TOL_PX * _px_value(cal.y, cal.y.to_pixel(ty))

    def test_uncertainty_is_one_pixel_value(self, dg, tmp_path):
        true = [(2.0, 20.0), (7.0, 70.0)]
        cal, pts = self._run(dg, tmp_path, "linear", "linear", (0, 10), (0, 100),
                             true, cal_x=(0, 10), cal_y=(0, 100))
        for p in pts:
            ux = _px_value(cal.x, cal.x.to_pixel(p.x))
            uy = _px_value(cal.y, cal.y.to_pixel(p.y))
            assert p.x_unc == pytest.approx(ux, rel=0.05)
            assert p.y_unc == pytest.approx(uy, rel=0.05)
            assert p.x_unc > 0 and p.y_unc > 0

    def test_min_area_rejects_specks(self, dg):
        mask = np.zeros((50, 50), dtype=bool)
        mask[10:20, 10:20] = True   # 100 px marker
        mask[40, 40] = True         # 1 px speck
        cal = dg.Calibration(dg.AxisCal(0, 0.0, 49, 49.0),
                             dg.AxisCal(49, 0.0, 0, 49.0))
        pts = dg.extract_markers(mask, cal, min_area=10)
        assert len(pts) == 1
        assert pts[0].x == pytest.approx(14.5)
        assert pts[0].y == pytest.approx(49 - 14.5)

    def test_no_pixels_returns_empty(self, dg):
        mask = np.zeros((10, 10), dtype=bool)
        cal = dg.Calibration(dg.AxisCal(0, 0.0, 9, 9.0), dg.AxisCal(9, 0.0, 0, 9.0))
        assert dg.extract_markers(mask, cal, min_area=1) == []


# --------------------------------------------------------------------------
# 4. curve extraction on synthetic figures
# --------------------------------------------------------------------------
class TestCurve:
    def test_linear_curve(self, dg, tmp_path):
        f = lambda x: 50 + 30 * np.sin(x / 2.0)   # gentle: max slope 15 /unit
        fig, ax = _make_fig("linear", "linear", (0, 10), (0, 100))
        xs = np.linspace(0, 10, 400)
        ax.plot(xs, f(xs), "-", color=(1, 0, 0), lw=1.5, snap=False)
        ax.plot(xs, 100 - xs * 5, "-", color=(0, 0.6, 0), lw=1.5, snap=False)  # other series
        px = _calib_pixels(fig, ax, [(0, 0), (10, 0)])
        py = _calib_pixels(fig, ax, [(0, 0), (0, 100)])
        _save(fig, tmp_path / "c.png")
        arr = dg.load_image(tmp_path / "c.png")
        cal = dg.Calibration(dg.AxisCal(px[0][0], 0, px[1][0], 10),
                             dg.AxisCal(py[0][1], 0, py[1][1], 100))
        mask = dg.color_mask(arr, (255, 0, 0), tol=60)
        pts = dg.extract_curve(mask, cal)
        assert len(pts) > 300  # roughly one point per pixel column in range
        # x must cover (nearly) the full drawn range
        assert min(p.x for p in pts) < 0.2 and max(p.x for p in pts) > 9.8
        for p in pts:
            # compare with the true curve at the extracted x: error in y only
            assert abs(p.y - f(p.x)) <= TOL_PX * _px_value(cal.y, cal.y.to_pixel(p.y))

    def test_log_curve_power_law(self, dg, tmp_path):
        f = lambda x: 2.0 * x ** 1.5          # straight line in log-log
        fig, ax = _make_fig("log", "log", (1, 100), (1, 10000))
        xs = np.logspace(0, 2, 400)
        ax.plot(xs, f(xs), "-", color=(1, 0, 0), lw=1.5, snap=False)
        px = _calib_pixels(fig, ax, [(1, 1), (100, 1)])
        py = _calib_pixels(fig, ax, [(1, 1), (1, 10000)])
        _save(fig, tmp_path / "cl.png")
        arr = dg.load_image(tmp_path / "cl.png")
        cal = dg.Calibration(dg.AxisCal(px[0][0], 1, px[1][0], 100, log=True),
                             dg.AxisCal(py[0][1], 1, py[1][1], 10000, log=True))
        pts = dg.extract_curve(dg.color_mask(arr, (255, 0, 0), tol=60), cal)
        assert len(pts) > 300
        # On a log axis one pixel is a constant number of decades, so compare
        # in log10 units: |log10(y_got) - log10(y_true)| <= 1 pixel.
        dec_per_px = 4.0 / abs(py[1][1] - py[0][1])   # y axis spans 4 decades
        for p in pts:
            assert abs(np.log10(p.y) - np.log10(f(p.x))) <= TOL_PX * dec_per_px

    def test_sample_at_requested_x(self, dg, tmp_path):
        f = lambda x: 10 + 8 * x
        fig, ax = _make_fig("linear", "linear", (0, 10), (0, 100))
        xs = np.linspace(0, 10, 300)
        ax.plot(xs, f(xs), "-", color=(1, 0, 0), lw=1.5, snap=False)
        px = _calib_pixels(fig, ax, [(0, 0), (10, 0)])
        py = _calib_pixels(fig, ax, [(0, 0), (0, 100)])
        _save(fig, tmp_path / "s.png")
        arr = dg.load_image(tmp_path / "s.png")
        cal = dg.Calibration(dg.AxisCal(px[0][0], 0, px[1][0], 10),
                             dg.AxisCal(py[0][1], 0, py[1][1], 100))
        mask = dg.color_mask(arr, (255, 0, 0), tol=60)
        want = [1.0, 2.0, 5.0, 9.0]
        pts = dg.extract_curve(mask, cal, x_values=want)
        assert [round(p.x, 9) for p in pts] == want
        for p in pts:
            # extract_curve interpolates between neighbouring pixel columns,
            # so the nominal x is hit exactly and the y error is again the
            # plain one-pixel budget.
            uy = _px_value(cal.y, cal.y.to_pixel(p.y))
            assert abs(p.y - f(p.x)) <= TOL_PX * uy

    def test_interpolation_between_columns_exact(self, dg):
        """Steep line (4 rows per column), identity calibration: x = column,
        y = row.  x = 5.5 lies between columns 5 (row 20) and 6 (row 24), so
        the answer must be 22 exactly, not 20 or 24."""
        mask = np.zeros((60, 12), dtype=bool)
        for c in range(10):
            mask[4 * c, c] = True
        cal = dg.Calibration(dg.AxisCal(0, 0.0, 11, 11.0),
                             dg.AxisCal(0, 0.0, 59, 59.0))
        pts = dg.extract_curve(mask, cal, x_values=[5.0, 5.5, 5.25])
        assert [p.x for p in pts] == [5.0, 5.5, 5.25]
        assert [p.y for p in pts] == pytest.approx([20.0, 22.0, 21.0])
        # x = 9.5 needs column 10, which has no curve pixel -> skipped
        assert dg.extract_curve(mask, cal, x_values=[9.5]) == []

    def test_x_outside_curve_skipped(self, dg):
        mask = np.zeros((20, 20), dtype=bool)
        mask[10, 5:15] = True
        cal = dg.Calibration(dg.AxisCal(0, 0.0, 19, 19.0), dg.AxisCal(19, 0.0, 0, 19.0))
        pts = dg.extract_curve(mask, cal, x_values=[1.0, 8.0, 18.0])
        assert [p.x for p in pts] == [8.0]


# --------------------------------------------------------------------------
# 5. CSV output (rule 9: record calibration, image name, script hash)
# --------------------------------------------------------------------------
class TestCsv:
    def _pts(self, dg):
        return [dg.Point(1.0, 2.0, 0.1, 0.2), dg.Point(3.0, 4.0, 0.1, 0.2)]

    def _cal(self, dg):
        return dg.Calibration(dg.AxisCal(100, 0.0, 500, 10.0),
                              dg.AxisCal(400, 1.0, 100, 1000.0, log=True))

    def test_header_comments_and_columns(self, dg, tmp_path):
        out = tmp_path / "o.csv"
        dg.write_csv(out, self._pts(dg), self._cal(dg), image="paper_fig7.png",
                     mode="markers", color=(0, 0, 255), tol=60,
                     script_hash="abc1234")
        lines = out.read_text().splitlines()
        head = [l for l in lines if l.startswith("#")]
        body = [l for l in lines if not l.startswith("#")]
        text = "\n".join(head)
        assert "paper_fig7.png" in text
        assert "abc1234" in text
        assert "x_cal" in text and "y_cal" in text
        assert "log" in text            # y axis is log
        assert "100" in text and "500" in text  # calibration pixels
        assert "1000" in text           # calibration value
        assert body[0] == "x,y,x_unc,y_unc"
        rows = list(csv.reader(body))
        assert len(rows) == 3
        assert [float(v) for v in rows[1]] == [1.0, 2.0, 0.1, 0.2]

    def test_roundtrip_with_comment_skipping_reader(self, dg, tmp_path):
        out = tmp_path / "o.csv"
        dg.write_csv(out, self._pts(dg), self._cal(dg), image="f.png",
                     mode="curve", color=(255, 0, 0), tol=40, script_hash="x")
        rows = list(csv.DictReader(l for l in out.read_text().splitlines()
                                   if not l.startswith("#")))
        assert float(rows[0]["x"]) == 1.0
        assert set(rows[0]) == {"x", "y", "x_unc", "y_unc"}

    def test_git_hash_of_script_is_returned(self, dg):
        h = dg.script_git_hash()
        # inside this repository it must be a short hex hash, optionally
        # followed by "-dirty"; never empty.
        assert isinstance(h, str) and h
        assert h == "unknown" or h.removesuffix("-dirty").isalnum()


# --------------------------------------------------------------------------
# 6. command-line interface end to end
# --------------------------------------------------------------------------
class TestCli:
    def test_markers_end_to_end(self, dg, tmp_path):
        true = [(1.0, 10.0), (3.0, 55.0), (5.0, 30.0), (8.0, 90.0)]
        fig, ax = _make_fig("linear", "linear", (0, 10), (0, 100))
        xs, ys = zip(*true)
        _markers(ax, xs, ys, (0, 0, 1))
        px = _calib_pixels(fig, ax, [(0, 0), (10, 0)])
        py = _calib_pixels(fig, ax, [(0, 0), (0, 100)])
        img = tmp_path / "fig.png"
        _save(fig, img)
        out = tmp_path / "out.csv"
        cmd = [sys.executable, str(SCRIPT), str(img),
               "--x-cal", str(px[0][0]), "0", str(px[1][0]), "10",
               "--y-cal", str(py[0][1]), "0", str(py[1][1]), "100",
               "--color", "0", "0", "255", "--tol", "60",
               "--mode", "markers", "--min-area", "15", "--out", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           env={"PYTHONNOUSERSITE": "1", "PATH": "/usr/bin:/bin",
                                "MPLBACKEND": "Agg"})
        assert r.returncode == 0, r.stderr
        text = out.read_text()
        assert "fig.png" in text and "# " in text
        rows = list(csv.DictReader(l for l in text.splitlines()
                                   if not l.startswith("#")))
        assert len(rows) == 4
        got = sorted((float(r_["x"]), float(r_["y"])) for r_ in rows)
        cal = dg.Calibration(dg.AxisCal(px[0][0], 0, px[1][0], 10),
                             dg.AxisCal(py[0][1], 0, py[1][1], 100))
        for (tx, ty), (gx, gy) in zip(sorted(true), got):
            assert abs(gx - tx) <= TOL_PX * _px_value(cal.x, cal.x.to_pixel(tx))
            assert abs(gy - ty) <= TOL_PX * _px_value(cal.y, cal.y.to_pixel(ty))

    def test_log_flag_and_bad_calibration_exit_nonzero(self, tmp_path):
        from PIL import Image
        img = tmp_path / "blank.png"
        Image.new("RGB", (50, 50), "white").save(img)
        cmd = [sys.executable, str(SCRIPT), str(img),
               "--x-cal", "10", "0", "10", "5",       # same pixel twice
               "--y-cal", "40", "0", "10", "5",
               "--color", "0", "0", "0", "--out", str(tmp_path / "o.csv")]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           env={"PYTHONNOUSERSITE": "1", "PATH": "/usr/bin:/bin"})
        assert r.returncode != 0
        assert "calibration" in r.stderr
        assert not (tmp_path / "o.csv").exists()
