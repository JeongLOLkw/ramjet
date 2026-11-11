"""Tests for geometry.inlet_param (parametric 2D mixed-compression inlet, I5).

Independent references:
- docs/i5/oblique_M5_two_ramp.csv and detach_mach_two_ramp.csv: Claude Science's own script
  (docs/i5/i5_oblique_tables.py), a separate implementation of the NACA 1135 relations.
  Values there are rounded, so tolerances are half a unit of the last printed digit.
- Plane geometry computed here directly from the returned points (not from the module's formulas).
"""
import csv
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from geometry import inlet_param as ip
from src import gasdynamics as gd

ROOT = Path(__file__).resolve().parents[1]
G = 1.4
P0 = ip.InletParams()


def rows(name):
    with open(ROOT / "docs/i5" / name) as f:
        return list(csv.DictReader(f))


def half_digit(text):
    """Tolerance = 0.51 units of the last printed decimal."""
    return 0.51 * 10.0 ** (-len(text.split(".")[1]) if "." in text else 0)


def perp_distance(P, A, B):
    """Distance of P from the line A-B."""
    P, A, B = (np.asarray(v, float) for v in (P, A, B))
    t = (B - A) / np.linalg.norm(B - A)
    return abs(t[0] * (P - A)[1] - t[1] * (P - A)[0])


# --- defaults (decisions.md D-016) -------------------------------------------

def test_defaults_are_the_approved_values():
    assert (P0.M_design, P0.delta1_deg, P0.delta2_deg) == (5.0, 8.0, 10.0)
    assert (P0.H_capture, P0.cr_int, P0.iso_L_over_H) == (0.100, 1.30, 10.0)
    assert (P0.lip_radius, P0.lip_dy, P0.cowl_ext_deg, P0.cowl_thickness) == (0.5e-3, 0.0, 10.0, 0.010)
    assert P0.T_wall == 300.0


# --- shock-on-lip --------------------------------------------------------------

@pytest.mark.parametrize("p", [P0, replace(P0, delta1_deg=10.0, delta2_deg=12.0), replace(P0, M_design=6.0),
                               replace(P0, H_capture=0.25)])
def test_lip_focus_lies_on_both_ramp_shocks(p):
    d = ip.design(p)
    s1 = gd.oblique_shock(p.M_design, np.radians(p.delta1_deg), G)
    s2 = gd.oblique_shock(s1["M2"], np.radians(p.delta2_deg), G)
    F, K = np.array(d["F"]), np.array(d["K"])
    assert F[1] == pytest.approx(p.H_capture, rel=1e-12)
    assert np.arctan2(F[1], F[0]) == pytest.approx(s1["beta"], abs=1e-12)                 # shock 1 from the leading edge
    assert np.arctan2(*(F - K)[::-1]) == pytest.approx(np.radians(p.delta1_deg) + s2["beta"], abs=1e-12)
    assert np.arctan2(K[1], K[0]) == pytest.approx(np.radians(p.delta1_deg), abs=1e-12)   # kink on ramp 1


def test_against_science_table():
    n = 0
    for r in rows("oblique_M5_two_ramp.csv"):
        p = replace(P0, M_design=float(r["Minf"]), delta1_deg=float(r["d1"]), delta2_deg=float(r["d2"]))
        d = ip.design(p)
        L1 = np.hypot(*d["K"])
        got = dict(beta1=np.degrees(d["beta1"]), M1=d["M1"], p1_pinf=d["p1"], beta2_rel=np.degrees(d["beta2"]),
                   beta2_abs=np.degrees(d["beta2_abs"]), M2=d["M2"], p2_pinf=d["p2"], pt2_ptinf=d["pt2"],
                   xlip_L1=d["F"][0] / L1, ylip_L1=d["F"][1] / L1, cowl_flat_margin_deg=d["cowl_margin_deg"],
                   kantrowitz_Ath_Ai_at_M2=gd.kantrowitz_limit(d["M2"], G),
                   isentropic_Ath_Ai_at_M2=gd.isentropic_limit(d["M2"], G),
                   d2_equal_strength=d["delta2_equal_strength_deg"])
        for k, v in got.items():
            assert v == pytest.approx(float(r[k]), abs=half_digit(r[k])), (r["d1"], r["d2"], k)
        if r["M3_flat_cowl"] == "detached":
            assert np.isnan(d["M3"]) and d["cowl_margin_deg"] < 0
        else:
            assert d["M3"] == pytest.approx(float(r["M3_flat_cowl"]), abs=half_digit(r["M3_flat_cowl"]))
            assert d["p3"] == pytest.approx(float(r["p3_pinf_flat_cowl"]), abs=half_digit(r["p3_pinf_flat_cowl"]))
        n += 1
    assert n == 32


def test_detachment_boundaries_against_science_table():
    for r in rows("detach_mach_two_ramp.csv"):
        p = replace(P0, delta1_deg=float(r["d1"]), delta2_deg=float(r["d2"]))
        m1, m2, m3 = ip.detachment_machs(p)
        assert m1 == pytest.approx(float(r["Mmin_ramp1"]), abs=6e-4)
        assert m2 == pytest.approx(float(r["Mmin_ramp2"]), abs=6e-4)
        assert m3 == pytest.approx(float(r["Mmin_flat_cowl"]), abs=6e-4)


# --- internal contraction, throat, isolator ------------------------------------

@pytest.mark.parametrize("cr", [1.15, 1.30, 1.44, 1.8])
def test_internal_contraction_equals_parameter(cr):
    p = replace(P0, cr_int=cr)
    d = ip.design(p)
    lip = (d["F"][0], d["y_cowl"])
    A_i = perp_distance(lip, d["K"], d["S"])          # lip to the ramp-2 surface, normal to the ramp
    H_th = d["y_cowl"] - d["S"][1]
    assert A_i == pytest.approx(d["A_i"], rel=1e-12)
    assert H_th == pytest.approx(d["H_th"], rel=1e-12)
    assert A_i / H_th == pytest.approx(cr, rel=1e-12)
    # shoulder on ramp 2, floor horizontal, isolator length
    K, S = np.array(d["K"]), np.array(d["S"])
    assert np.arctan2(*(S - K)[::-1]) == pytest.approx(np.radians(p.delta1_deg + p.delta2_deg), abs=1e-12)
    assert d["E0"][1] == S[1]
    assert d["E0"][0] - S[0] == pytest.approx(p.iso_L_over_H * H_th, rel=1e-12)
    assert d["x_exit"] == d["E0"][0]


def test_shock_on_shoulder_contraction_is_the_stream_tube_ratio():
    # mass conservation across the cowl shock: A_after/A_before = sin(beta - theta)/sin(beta)
    d = ip.design(P0)
    th = np.radians(P0.delta1_deg + P0.delta2_deg)
    assert d["cr_shock_on_shoulder"] == pytest.approx(np.sin(d["beta3"]) / np.sin(d["beta3"] - th), rel=1e-12)
    assert d["cr_shock_on_shoulder"] > d["cr_kantrowitz"]        # why shock-on-shoulder was not chosen (D-016)


def test_kantrowitz_numbers_for_default():
    d = ip.design(P0)
    assert d["cr_kantrowitz"] == pytest.approx(1 / gd.kantrowitz_limit(d["M2"], G), rel=1e-12)
    assert P0.cr_int < d["cr_kantrowitz"]                        # self-starting at the design point
    m = ip.kantrowitz_start_mach(P0)
    s1 = gd.oblique_shock(m, np.radians(P0.delta1_deg), G)
    s2 = gd.oblique_shock(s1["M2"], np.radians(P0.delta2_deg), G)
    assert gd.kantrowitz_limit(s2["M2"], G) == pytest.approx(1 / P0.cr_int, rel=1e-9)
    assert 3.0 < m < 4.0                                         # between sweep points 3 and 4 (D-016)
    assert np.isnan(ip.kantrowitz_start_mach(replace(P0, cr_int=1.70)))   # above the M -> inf limit 1/0.6


# --- cowl lip and outer surface -------------------------------------------------

@pytest.mark.parametrize("p", [P0, replace(P0, lip_radius=1e-3), replace(P0, lip_dy=1.2e-3, cowl_ext_deg=12.0)])
def test_lip_circle_is_tangent_to_both_cowl_surfaces(p):
    d = ip.design(p)
    R, C = p.lip_radius, np.array(d["Cn"])
    te = np.radians(p.cowl_ext_deg)
    assert d["y_cowl"] == pytest.approx(p.H_capture + p.lip_dy)
    for name in ("P_in", "P_nose", "P_out"):
        assert np.linalg.norm(np.array(d[name]) - C) == pytest.approx(R, rel=1e-12)
    assert d["P_nose"][0] == pytest.approx(d["F"][0], abs=1e-15)          # foremost point at the focus station
    assert d["P_in"][1] == pytest.approx(d["y_cowl"], abs=1e-15)          # inner surface is y = y_cowl
    assert (np.array(d["P_in"]) - C) @ np.array([1.0, 0.0]) == pytest.approx(0.0, abs=1e-15)
    t_out = np.array([np.cos(te), np.sin(te)])                            # outer surface direction
    assert (np.array(d["P_out"]) - C) @ t_out == pytest.approx(0.0, abs=1e-15)
    Tc, Po = np.array(d["Tc"]), np.array(d["P_out"])
    assert np.arctan2(*(Tc - Po)[::-1]) == pytest.approx(te, abs=1e-12)
    assert Tc[1] == pytest.approx(d["y_cowl"] + p.cowl_thickness)
    assert d["Eo"] == (pytest.approx(d["x_exit"]), pytest.approx(Tc[1]))


# --- scaling and validation -----------------------------------------------------

def test_lengths_scale_with_capture_height():
    a, b = ip.design(P0), ip.design(replace(P0, H_capture=0.2))
    for k in ("K", "F", "S", "E0"):
        assert np.array(b[k]) == pytest.approx(2 * np.array(a[k]), rel=1e-12)
    for k in ("M1", "M2", "M3", "p3", "beta1"):
        assert b[k] == pytest.approx(a[k], rel=1e-12)


@pytest.mark.parametrize("bad", [dict(delta1_deg=45.0), dict(delta2_deg=40.0), dict(cr_int=1.04), dict(cr_int=-1.0),
                                 dict(lip_radius=0.0), dict(cowl_thickness=0.5e-3), dict(M_design=0.9),
                                 dict(iso_L_over_H=0.0), dict(delta2_deg=0.0)])
def test_invalid_parameters_raise(bad):
    with pytest.raises(ValueError):
        ip.design(replace(P0, **bad))


def test_params_roundtrip_and_overrides():
    p = ip.with_overrides(P0, ["cr_int=1.2", "delta2_deg=12"])
    assert (p.cr_int, p.delta2_deg, p.delta1_deg) == (1.2, 12.0, 8.0)
    assert ip.InletParams(**ip.as_dict(p)) == p
    with pytest.raises(ValueError):
        ip.with_overrides(P0, ["no_such_parameter=1"])
