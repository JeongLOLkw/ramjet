import csv
import math

import numpy as np
import pytest

from scripts import i4_report as rp


# --------------------------------------------------------------------------- small parsers

def test_case_family_level():
    assert rp.family_level("flatplate/M2aw_L1") == ("M2aw", 1)
    assert rp.family_level("flatplate/M6Tw076_L2") == ("M6Tw076", 2)
    assert rp.family_level("ramp24/L0") == ("ramp24", 0)
    with pytest.raises(ValueError):
        rp.family_level("ramp24/L0_failed_Lramp018")


def test_parse_cells_from_case_info():
    txt = ("case ramp24/L1\noptions x\nM 2.84  T_inf 1 K\nT_w 275.1 K\n"
           "mesh cells 171430  nx 1085  ny 158  dy1 7.07107e-07\n")
    assert rp.parse_cells(txt) == 171430
    with pytest.raises(ValueError):
        rp.parse_cells("no mesh line")


def test_parse_settles():
    assert rp.parse_settles(None) is None
    assert rp.parse_settles("-0.11,0.08") == (-0.11, 0.08)
    with pytest.raises(ValueError):
        rp.parse_settles("0.1")


# --------------------------------------------------------------------------- grid table

def _plate(cond, level, cf):
    return dict(case=f"flatplate/{cond}_L{level}", iterations=8000, steady=True, last=dict(cf_ref=cf, q_max=1.0))


def _ramp(level, **kw):
    r = dict(case=f"ramp24/L{level}", iterations=20000, steady=False, sep=-0.1, reatt=0.1, L_sep=0.2,
             last=dict(L_sep=0.2, q_max=3.0e4))
    r.update(kw)
    return r


def _m6(level, cf, bq, st_cf):
    return dict(case=f"flatplate/M6Tw076_L{level}", iterations=8000, steady=True, last=dict(cf_ref=cf, q_max=1.0),
                ref=dict(cf=cf, minus_bq=bq), two_st_over_cf=st_cf)


CELLS = {0: 1000, 1: 4000, 2: 16000}


def _cells(prefix):
    return {f"{prefix}_L{k}" if prefix.startswith("flatplate") else f"ramp24/L{k}": n for k, n in CELLS.items()}


def test_grid_table_plate_power_law_recovers_order():
    h = np.array([4.0, 2.0, 1.0])               # N ratio 4 in 2D -> h ratio 2
    cf = 1e-3 + 2e-4 * h ** 2
    res = [_plate("M2aw", k, cf[k]) for k in range(3)]
    rows = rp.grid_table(res, _cells("flatplate/M2aw"))
    r = next(r for r in rows if r["family"] == "M2aw" and r["metric"] == "cf_ref")
    assert r["status"] == "monotone"
    assert r["p"] == pytest.approx(2.0, rel=1e-9)
    assert r["phi_ext"] == pytest.approx(1e-3, rel=1e-9)
    assert [r["phi_L0"], r["phi_L1"], r["phi_L2"]] == pytest.approx(list(cf))
    assert [r["n_L0"], r["n_L1"], r["n_L2"]] == [1000, 4000, 16000]
    # M2aw has no M6-only metrics
    assert not any(x["family"] == "M2aw" and x["metric"] == "minus_bq" for x in rows)


def test_grid_table_m6_metrics_and_ramp_metrics_present():
    res = [_m6(k, 2e-3 + 1e-4 * 4 ** (1 - k), 0.017 + 1e-3 * 4 ** (1 - k), 1.0 + 0.01 * 4 ** (1 - k)) for k in range(3)]
    res += [_ramp(k, L_sep=0.2 + 0.01 * 4 ** (1 - k), sep=-0.1, reatt=0.1 + 0.01 * 4 ** (1 - k),
                  last=dict(L_sep=0.2, q_max=3e4 + 100 * 4 ** (1 - k))) for k in range(3)]
    cells = {**_cells("flatplate/M6Tw076"), **_cells("ramp24")}
    rows = rp.grid_table(res, cells)
    keys = {(r["family"], r["metric"]) for r in rows}
    assert keys == {("M6Tw076", "cf_ref"), ("M6Tw076", "minus_bq"), ("M6Tw076", "two_st_over_cf"),
                    ("ramp24", "L_sep"), ("ramp24", "sep"), ("ramp24", "reatt"), ("ramp24", "q_max")}
    sep = next(r for r in rows if r["metric"] == "sep")
    assert sep["status"] == "zero_change"           # sep identical on all levels: flagged, no NaN crash
    assert math.isnan(sep["p"])


def test_grid_table_oscillatory_and_missing_level():
    res = [_ramp(0, L_sep=0.30), _ramp(1, L_sep=0.20), _ramp(2, L_sep=0.25)]
    for r in res:
        r["last"]["L_sep"] = r["L_sep"]
    rows = rp.grid_table(res, _cells("ramp24"))
    ls = next(r for r in rows if r["metric"] == "L_sep")
    assert ls["status"] == "oscillatory"
    assert (ls["band_min"], ls["band_max"]) == (0.20, 0.30)
    # only two levels -> missing_level, values filled for the existing ones, no exception
    rows = rp.grid_table(res[:2], _cells("ramp24"))
    ls = next(r for r in rows if r["metric"] == "L_sep")
    assert ls["status"] == "missing_level"
    assert ls["phi_L0"] == 0.30 and ls["phi_L1"] == 0.20 and math.isnan(ls["phi_L2"])


def test_grid_table_none_metric_value_is_nan_not_crash():
    res = [_ramp(k, sep=None, reatt=None, L_sep=float("nan")) for k in range(3)]
    rows = rp.grid_table(res, _cells("ramp24"))
    sep = next(r for r in rows if r["metric"] == "sep")
    assert sep["status"] == "missing_value"


def test_write_grid_csv_roundtrip(tmp_path):
    res = [_plate("M2aw", k, 1e-3 + 2e-4 * (4.0 / 2 ** k) ** 2) for k in range(3)]
    rows = rp.grid_table(res, _cells("flatplate/M2aw"))
    out = tmp_path / "g.csv"
    rp.write_grid_csv(rows, out)
    back = list(csv.DictReader(out.open()))
    assert back[0]["family"] == "M2aw" and back[0]["metric"] == "cf_ref"
    assert float(back[0]["p"]) == pytest.approx(2.0, rel=1e-6)
    assert set(rp.CSV_COLUMNS) == set(back[0])


# --------------------------------------------------------------------------- outlet-flux series

HDR = "# Region type : patch outlet\n# Time\tsum(phi)\n"


def _dat(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HDR + "".join(f"{t}\t{v}\n" for t, v in rows))


def test_read_flux_series_concatenates_and_latest_folder_wins(tmp_path):
    _dat(tmp_path / "0/surfaceFieldValue.dat", [(1, 1.0), (2, 2.0), (3, 3.0), (4, 4.0)])
    _dat(tmp_path / "3/surfaceFieldValue.dat", [(3, 30.0), (4, 40.0), (5, 50.0)])       # restart at step 3: overlap
    t, v = rp.read_flux_series(tmp_path)
    assert list(t) == [1, 2, 3, 4, 5]
    assert list(v) == [1.0, 2.0, 30.0, 40.0, 50.0]


def test_read_flux_series_sorted_numerically_not_lexically(tmp_path):
    _dat(tmp_path / "9/surfaceFieldValue.dat", [(10, 1.0)])
    _dat(tmp_path / "10/surfaceFieldValue.dat", [(11, 2.0)])
    _dat(tmp_path / "0/surfaceFieldValue.dat", [(1, 0.0)])
    t, v = rp.read_flux_series(tmp_path)
    assert list(t) == [1, 10, 11]


def test_read_flux_series_takes_last_column_ignores_comments_and_empty_files(tmp_path):
    p = tmp_path / "0/surfaceFieldValue.dat"
    p.parent.mkdir(parents=True)
    p.write_text("# Time a b\n1 0.1 0.2\n# c\n2 0.3 0.4\n")
    (tmp_path / "5").mkdir()
    (tmp_path / "5/surfaceFieldValue.dat").write_text("# only header\n")
    t, v = rp.read_flux_series(tmp_path)
    assert list(t) == [1, 2] and list(v) == [0.2, 0.4]


def test_read_flux_series_no_data_raises(tmp_path):
    with pytest.raises(ValueError):
        rp.read_flux_series(tmp_path)


def test_read_flux_series_unsorted_times_inside_stale_file_are_cut(tmp_path):
    _dat(tmp_path / "0/surfaceFieldValue.dat", [(1, 1.0), (2, 2.0), (3, 3.0), (4, 4.0), (5, 5.0)])
    _dat(tmp_path / "2/surfaceFieldValue.dat", [(3, 9.0)])        # restart at 2 reached only step 3 so far
    t, v = rp.read_flux_series(tmp_path)
    assert list(t) == [1, 2, 3] and list(v) == [1.0, 2.0, 9.0]
