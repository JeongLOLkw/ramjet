import numpy as np
import pytest

from scripts import i4_analyze as ia
from src import validation_tools as vt


# --------------------------------------------------------------------------- info_change (ramp)

def _hist():
    its = np.array([0, 1000, 2000, 3000, 4000, 5000])
    s = np.array([-0.1, -0.05, 0.1, 0.2])                      # two plate faces, two ramp faces
    q = np.array([[-1.0, -1.0, -1.0, -1.0]] * 6)
    return its, q, s


def test_info_change_constant_history_is_zero():
    its, q, s = _hist()
    r = ia.info_change(its, q, s, 2000)
    assert r == dict(q_pointwise=0.0, q_ramp_peak=0.0)


def test_info_change_pointwise_uses_window_and_last_value():
    its, q, s = _hist()
    q[:, 0] = [-9.0, -9.0, -9.0, -1.0, -1.1, -1.0]            # it 3000..5000 in the window of 2000: range 0.1
    q[0, 2] = -50.0                                            # outside the window (it 0): ignored
    r = ia.info_change(its, q, s, 2000)
    assert r["q_pointwise"] == pytest.approx(0.1 / 1.0)
    # face 0 is on the plate (s < 0) and must not enter the ramp peak
    assert r["q_ramp_peak"] == 0.0


def test_info_change_pointwise_is_max_over_faces():
    its, q, s = _hist()
    q[:, 1] = [-1, -1, -1, -2.0, -1.5, -2.0]                  # range 0.5, last 2.0 -> 0.25
    q[:, 3] = [-1, -1, -1, -1.0, -1.1, -1.0]                  # range 0.1, last 1.0 -> 0.1
    assert ia.info_change(its, q, s, 2000)["q_pointwise"] == pytest.approx(0.25)


def test_info_change_ramp_peak_matches_relative_change_of_ramp_max_magnitude():
    its, q, s = _hist()
    q[:, 0] = [-100.0, -80.0, -60.0, -40.0, -20.0, -10.0]     # plate face with the largest magnitude, drifting
    q[:, 2] = [-1, -1, -1, -2.0, -2.2, -2.0]
    q[:, 3] = [-1, -1, -1, -1.0, -1.0, -1.0]
    expect = vt.relative_change(its, np.abs(q[:, 2:]).max(axis=1), 2000)
    assert ia.info_change(its, q, s, 2000)["q_ramp_peak"] == pytest.approx(expect)
    assert expect == pytest.approx(0.2 / 2.0)


def test_info_change_short_history_raises_like_relative_change():
    its, q, s = _hist()
    with pytest.raises(ValueError):
        ia.info_change(its, q, s, 10000)


def test_info_change_zero_wall_flux_face_is_not_nan():
    its, q, s = _hist()
    q[:, 2] = 0.0                                              # exactly zero everywhere (e.g. adiabatic stretch)
    assert ia.info_change(its, q, s, 2000)["q_pointwise"] == 0.0


# --------------------------------------------------------------------------- summary

def _res(info):
    r = dict(case="ramp24/L0", iterations=20000, y_plus_max=0.5, y_plus_ok=True, mass_imbalance=1e-6,
             rel_change=dict(L_sep=1e-6, q_max=8.0e-3), steady=False, sep=-0.1, reatt=0.07, L_sep=0.19, bubble_open=False)
    if info is not None:
        r["info_change"] = info
    return r


def test_summary_prints_info_after_verdict_only_when_present():
    line = ia.summary(_res(dict(q_pointwise=2.0e-2, q_ramp_peak=2.8e-3)))
    assert "not steady  info[q_pointwise 2.0e-02, q_ramp_peak 2.8e-03]" in line
    assert "info[" not in ia.summary(_res(None))
    assert "q_pointwise n/a" in ia.summary(_res(dict(q_pointwise=None, q_ramp_peak=1e-3)))


# --------------------------------------------------------------------------- mass-flux file selection

HDR = "# Surface field value\n# Time  sum(phi)\n"


def _dat(path, rows, header=HDR):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "".join(f"{t}\t{v}\n" for t, v in rows))


def test_latest_flux_picks_largest_last_time_across_start_time_dirs(tmp_path):
    _dat(tmp_path / "0/surfaceFieldValue.dat", [(1, 5.0), (2000, 6.0)])
    _dat(tmp_path / "1000/surfaceFieldValue.dat", [(1001, 7.0), (3000, -2.5)])
    assert ia.latest_flux(tmp_path) == -2.5


def test_latest_flux_stale_file_is_not_first_match(tmp_path):
    _dat(tmp_path / "0/surfaceFieldValue.dat", [(1, 1.0), (5000, 2.0)])     # stale: longer name order/first, older end
    _dat(tmp_path / "5000/surfaceFieldValue.dat", [(5001, 3.0), (9000, 4.0)])
    assert ia.latest_flux(tmp_path) == 4.0


def test_latest_flux_time_suffix_naming(tmp_path):
    _dat(tmp_path / "0/surfaceFieldValue.dat", [(1, 1.0), (500, 2.0)])
    _dat(tmp_path / "0/surfaceFieldValue_500.dat", [(501, 3.0), (800, 9.0)])
    assert ia.latest_flux(tmp_path) == 9.0


def test_latest_flux_takes_last_column_and_skips_comments(tmp_path):
    p = tmp_path / "0/surfaceFieldValue.dat"
    p.parent.mkdir()
    p.write_text("# Time a b\n1 0.1 0.2\n# comment in the middle\n2 0.3 0.4\n# trailing comment\n")
    assert ia.latest_flux(tmp_path) == 0.4


def test_latest_flux_ignores_empty_and_comment_only_files(tmp_path):
    _dat(tmp_path / "0/surfaceFieldValue.dat", [(1, 1.0), (10, 2.0)])
    (tmp_path / "10").mkdir()
    (tmp_path / "10/surfaceFieldValue.dat").write_text("")
    _dat(tmp_path / "20/surfaceFieldValue.dat", [], header=HDR)
    assert ia.latest_flux(tmp_path) == 2.0


def test_latest_flux_no_data_raises(tmp_path):
    (tmp_path / "0").mkdir()
    (tmp_path / "0/surfaceFieldValue.dat").write_text("")
    with pytest.raises(ValueError):
        ia.latest_flux(tmp_path)
