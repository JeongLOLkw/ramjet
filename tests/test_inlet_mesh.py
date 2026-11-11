"""Tests for geometry.inlet_mesh (block layout of the parametric inlet, I5).

Pure-Python checks use plane geometry computed here from the vertex coordinates. The last test runs
blockMesh/checkMesh (skipped if OpenFOAM v2512 is not installed) and reads the wall-adjacent cells back
from the generated polyMesh with src.foam_mesh — an end-to-end check of the first-cell height.
"""
import re
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from geometry import inlet_mesh as im
from geometry import inlet_param as ip
from src.foam_mesh import patch_geometry, read_labels, read_points, read_faces

P0, M0 = ip.InletParams(), im.MeshParams()
FOAM_BASHRC = Path("/usr/lib/openfoam/openfoam2512/etc/bashrc")


def dist_to_line(P, A, B):
    P, A, B = (np.asarray(v, float) for v in (P, A, B))
    t = (B - A) / np.linalg.norm(B - A)
    return abs(t[0] * (P - A)[1] - t[1] * (P - A)[0])


def test_n_for_geometric_series():
    # 10 cells of ratio 1.2 starting at 1: sum = (1.2^10 - 1)/0.2, last = 1.2^9
    L, last = (1.2**10 - 1) / 0.2, 1.2**9
    assert im.n_for(L, 1.0, last) == 10
    assert im.n_for(L, last, 1.0) == 10
    assert im.n_for(5.0, 0.5, 0.5) == 10
    with pytest.raises(ValueError):
        im.n_for(1.0, 2.0, 0.1)


def test_default_layout_passes_topology_check():
    m, info = im.build(P0, M0)
    assert info["blocks"] == 32 and info["vertices"] == 48
    assert set(m.patches) == set(im.PATCHES)
    assert {k: m.patches[k][0] for k in im.WALL_PATCHES} == {k: "wall" for k in im.WALL_PATCHES}
    assert m.patches["sym"][0] == "symmetryPlane"
    assert 80_000 < info["cells"] < 110_000              # plan: level 0 about 90k cells
    assert info["max_cell_ratio"] < 1.25


def test_levels_scale_counts_and_first_cell():
    cells, dyw, dyl = [], [], []
    for lvl in (0, 1, 2):
        m, info = im.build(P0, replace(M0, level=lvl))
        cells.append(info["cells"]), dyw.append(info["dy_wall"]), dyl.append(info["dy_lip"])
    assert cells[1] / cells[0] == pytest.approx(2.0, rel=0.05)
    assert cells[2] / cells[1] == pytest.approx(2.0, rel=0.05)
    assert dyw == pytest.approx([M0.dy_wall, M0.dy_wall / np.sqrt(2), M0.dy_wall / 2])
    assert dyl == pytest.approx([M0.dy_lip, M0.dy_lip / np.sqrt(2), M0.dy_lip / 2])


@pytest.mark.parametrize("lvl", [0, 2])
def test_first_cell_height_is_constant_along_each_wall(lvl):
    m, info = im.build(P0, replace(M0, level=lvl))
    for a, b in (("I0", "Iw"), ("O", "Ow"), ("K", "Kw"), ("A0", "Aw"), ("N0", "Nw"), ("S", "Sw"), ("E0", "Ew"),
                 ("Si", "Sc"), ("Ei", "Ec"), ("Tc", "Tcq"), ("Eo", "Eoq")):
        assert m.sizes(a, b)[0] == pytest.approx(info["dy_wall"], rel=1e-8), (a, b)
    for k in "namb":
        assert m.sizes("P" + k, "Q" + k)[0] == pytest.approx(info["dy_lip"], rel=1e-8)
    assert m.sizes("Pt", "Qt")[0] == pytest.approx(info["dy_lip"], rel=1e-8)


def test_wall_layer_and_c_layer_geometry():
    m, _ = im.build(P0, M0)
    d = ip.design(P0)
    v = {k: np.array(x) for k, x in m.v.items()}
    O, K, S = np.zeros(2), np.array(d["K"]), np.array(d["S"])
    dw, dc, R = M0.d_wall, M0.d_c, P0.lip_radius
    assert v["K"] == pytest.approx(K) and v["S"] == pytest.approx(S) and v["O"] == pytest.approx(O)
    # wall-layer vertices at distance d_wall from the wall(s) they belong to
    assert dist_to_line(v["Ow"], O, K) == pytest.approx(dw)
    assert dist_to_line(v["Kw"], O, K) == pytest.approx(dw) and dist_to_line(v["Kw"], K, S) == pytest.approx(dw)
    assert dist_to_line(v["Sw"], K, S) == pytest.approx(dw) and v["Sw"][1] - S[1] == pytest.approx(dw)
    for w, l in (("A0", "Aw"), ("N0", "Nw")):
        assert dist_to_line(v[w], K, S) == pytest.approx(0.0, abs=1e-15)          # on ramp 2
        assert dist_to_line(v[l], K, S) == pytest.approx(dw)
        assert (v[l] - v[w]) @ (S - K) == pytest.approx(0.0, abs=1e-15)           # edge normal to the wall
    assert v["Aw"][0] == pytest.approx(v["Qa"][0]) and v["Nw"][0] == pytest.approx(v["Qn"][0])
    # lip: P on the circle, Q on the concentric circle, radial edges
    Cn = np.array(d["Cn"])
    for k in "namb" + "t":
        assert np.linalg.norm(v["P" + k] - Cn) == pytest.approx(R)
        assert np.linalg.norm(v["Q" + k] - Cn) == pytest.approx(R + dc)
        a, b = v["P" + k] - Cn, v["Q" + k] - Cn
        assert a[0] * b[1] - a[1] * b[0] == pytest.approx(0.0, abs=1e-15)
    assert v["Pn"] == pytest.approx(np.array(d["P_in"])) and v["Pt"] == pytest.approx(np.array(d["P_out"]))
    assert v["Pm"] == pytest.approx(np.array(d["P_nose"]))
    for a, b in (("Pn", "Pa"), ("Pa", "Pm"), ("Pm", "Pb")):
        assert m.length(a, b) == pytest.approx(R * np.pi / 4)
    assert m.length("Pb", "Pt") == pytest.approx(R * np.radians(45 - P0.cowl_ext_deg))
    # C-layer on the flat cowl surfaces
    assert v["Si"][1] == v["Ei"][1] == pytest.approx(d["y_cowl"])
    assert v["Sc"][1] == v["Ec"][1] == pytest.approx(d["y_cowl"] - dc)
    assert dist_to_line(v["Tcq"], v["Pt"], v["Tc"]) == pytest.approx(dc)
    assert v["Eoq"][1] - v["Eo"][1] == pytest.approx(dc)


def test_wall_patches_trace_the_outline():
    m, _ = im.build(P0, M0)
    d = ip.design(P0)
    chain = lambda name: [e[0] for e in m.patches[name][1]] + [m.patches[name][1][-1][1]]  # noqa: E731
    assert chain("ramp") == ["O", "K", "A0", "N0", "S"]
    assert chain("floor") == ["S", "E0"]
    assert chain("cowl_in") == ["Pn", "Si", "Ei"]
    assert chain("lip") == ["Pn", "Pa", "Pm", "Pb", "Pt"]
    assert chain("cowl_out") == ["Pt", "Tc", "Eo"]
    assert m.v["E0"] == pytest.approx(d["E0"]) and m.v["Ei"] == pytest.approx(d["E_in"])
    assert m.v["Eo"] == pytest.approx(d["Eo"]) and m.v["Tc"] == pytest.approx(d["Tc"])
    assert m.v["I0"] == (-P0.x_up, 0.0) and m.v["Eot"] == pytest.approx((d["x_exit"], P0.y_top))


def test_tangential_spacing_is_continuous_from_lip_onto_cowl():
    m, info = im.build(P0, M0)
    s = info["size"]["lip_tangential"]
    assert m.sizes("Pn", "Si")[0] == pytest.approx(s, rel=1e-8)
    assert m.sizes("Qn", "Sc")[0] == pytest.approx(s, rel=1e-8)          # same on both sides of the C-layer
    assert m.sizes("Pt", "Tc")[0] == pytest.approx(m.length("Pb", "Pt") / m.n("Pb", "Pt"), rel=1e-8)
    assert m.sizes("Pt", "Tc")[0] == pytest.approx(m.sizes("Qt", "Tcq")[0], rel=1e-8)
    # isolator: each line continues with the last cell of the contraction section
    for a, b, c in (("S", "E0", "N0"), ("Si", "Ei", "Pn")):
        assert m.sizes(a, b)[0] == pytest.approx(m.sizes(c, a)[-1], rel=1e-8)


# every plan-listed single-parameter change must still give a valid layout ("regenerate with one parameter")
VARIANTS = [dict(cr_int=1.15), dict(cr_int=1.44), dict(delta2_deg=8.0), dict(delta2_deg=12.0),
            dict(iso_L_over_H=5.0), dict(iso_L_over_H=15.0), dict(lip_radius=0.25e-3), dict(lip_radius=1.0e-3),
            dict(M_design=4.5), dict(M_design=6.0), dict(H_capture=0.2), dict(x_up=1.0, y_top=3.0)]


@pytest.mark.parametrize("change", VARIANTS, ids=lambda c: ",".join(f"{k}={v}" for k, v in c.items()))
def test_single_parameter_variants_build(change):
    m, info = im.build(replace(P0, **change), M0)
    assert info["blocks"] == 32 and info["max_cell_ratio"] < 1.3
    txt = m.render()
    assert txt.count("hex (") == 32 and txt.count("    arc ") == 8


def test_layout_that_does_not_fit_raises():
    with pytest.raises(ValueError):
        im.build(replace(P0, cr_int=1.04), M0)                 # shoulder upstream of the lip normal
    with pytest.raises(ValueError):
        im.build(P0, replace(M0, d_wall=8e-3, d_c=8e-3))       # layers thicker than the duct
    with pytest.raises(ValueError):
        im.build(replace(P0, lip_radius=3e-3), M0)             # C-layer thinner than the lip radius


@pytest.mark.skipif(not FOAM_BASHRC.exists(), reason="OpenFOAM v2512 not installed")
def test_blockmesh_checkmesh_and_first_cell_height(tmp_path):
    from scripts import i5_mesh
    case = tmp_path / "case"
    info = i5_mesh.write_mesh_case(case, P0, M0)
    q = i5_mesh.run_mesh(case)
    assert q["cells"] == info["cells"]
    assert q["failed_checks"] <= 1 and q["only_aspect_ratio_failed"]     # wall-resolved cells: aspect ratio only
    assert q["non_ortho_max"] < 60 and q["skewness_max"] < 4
    md = case / "constant/polyMesh"
    pts, faces, owner = read_points(md), read_faces(md), read_labels(md / "owner")
    cells = {}
    for fi, c in enumerate(owner):                                      # owner faces are enough for a centroid estimate
        cells.setdefault(int(c), []).extend(faces[fi])
    for patch in im.WALL_PATCHES:
        cf, nrm, _, own = patch_geometry(case, patch)
        cc = np.array([pts[sorted(set(cells[int(c)]))].mean(axis=0) for c in own])   # hexahedra: vertex average
        h = 2 * np.einsum("ij,ij->i", cf - cc, nrm)                    # first-cell height = 2 x centre distance
        dyl, dyw = info["dy_lip"], info["dy_wall"]
        # Lip: the outer edge of each polar block is a chord, so at mid-block the layer is thinner than at the
        # block corners by ((R + d_c) cos(22.5 deg) - R)/d_c = 0.905 for d_c = 4R, and the first cell with it
        # (up to 9.5 % below dy_lip, never above).
        lo, hi = {"lip": (0.90 * dyl, 1.01 * dyl), "cowl_in": (0.99 * dyl, 1.01 * dyw),
                  "cowl_out": (0.90 * dyl, 1.01 * dyw)}.get(patch, (0.98 * dyw, 1.01 * dyw))   # bisector edges at kink/shoulder: cos(9 deg) = 0.988
        assert lo < h.min() and h.max() < hi, (patch, h.min(), h.max())
        if patch in ("ramp", "floor"):
            assert np.median(h) == pytest.approx(dyw, rel=0.01)
