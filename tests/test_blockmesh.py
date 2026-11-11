"""Tests for src.blockmesh (2D multi-block blockMeshDict writer). Pure geometry/topology — no OpenFOAM.

Analytic references: geometric series (sum and first/last term), arc length R*angle, and
hand-countable two-block layouts.
"""
import numpy as np
import pytest

from src.blockmesh import BlockMesh


def two_blocks(h_left=1.0, h_mid=1.0, h_right=2.0):
    """Two blocks side by side on y = 0; the vertical edges have different lengths."""
    m = BlockMesh()
    for name, x, y in (("a", 0, 0), ("b", 1, 0), ("c", 3, 0), ("d", 0, h_left), ("e", 1, h_mid), ("f", 3, h_right)):
        m.vertex(name, x, y)
    m.block("L", "a", "b", "e", "d")
    m.block("R", "b", "c", "f", "e")
    m.count("a", "b", 4), m.count("b", "c", 6), m.count("a", "d", 10)
    m.patch("wall", "wall", [("a", "b"), ("b", "c")])
    m.patch("top", "patch", [("d", "e"), ("e", "f")])
    m.patch("inlet", "patch", [("a", "d")])
    m.patch("outlet", "patch", [("c", "f")])
    return m


def test_counts_propagate_through_families():
    m = two_blocks()
    assert m.n("d", "e") == 4 and m.n("e", "f") == 6
    assert m.n("b", "e") == 10 and m.n("f", "c") == 10
    assert m.n_cells() == 4 * 10 + 6 * 10
    assert sorted(map(sorted, m.family_edges("a", "d"))) == [["a", "d"], ["b", "e"], ["c", "f"]]


def test_family_edges_are_oriented_parallel():
    m = two_blocks()
    assert set(m.family_edges("d", "a")) == {("d", "a"), ("e", "b"), ("f", "c")}


def test_first_cell_is_constant_on_edges_of_different_length():
    m = two_blocks(h_left=1.0, h_mid=1.5, h_right=2.0)
    m.grade_family("a", "d", start=1e-3)
    for (u, v), L in ((("a", "d"), 1.0), (("b", "e"), 1.5), (("c", "f"), 2.0)):
        s = m.sizes(u, v)
        assert s[0] == pytest.approx(1e-3, rel=1e-9)
        assert s.sum() == pytest.approx(L, rel=1e-12)
        assert np.allclose(s[1:] / s[:-1], s[1] / s[0])                 # geometric
        assert m.expansion(u, v) == pytest.approx(s[-1] / s[0], rel=1e-9)
        assert m.expansion(v, u) == pytest.approx(s[0] / s[-1], rel=1e-9)
        assert m.sizes(v, u) == pytest.approx(s[::-1], rel=1e-9)
    assert m.cell_ratio("a", "d") < m.cell_ratio("c", "f")


def test_end_specification_and_uniform_default():
    m = two_blocks()
    m.grade("a", "b", end=0.1)
    assert m.sizes("a", "b")[-1] == pytest.approx(0.1, rel=1e-9)
    assert m.sizes("b", "a")[0] == pytest.approx(0.1, rel=1e-9)
    assert m.sizes("b", "c") == pytest.approx(np.full(6, 2.0 / 6))
    assert m.expansion("d", "e") == 1.0                                  # not graded: only (a, b) was
    with pytest.raises(ValueError):
        m.grade("a", "b", start=1.0, end=1.0)


def test_arc_length_and_midpoint():
    m = BlockMesh()
    R = 0.5
    for name, x, y in (("p", -R, 0), ("q", 0, -R), ("o", -2, 0), ("s", 0, -2)):
        m.vertex(name, x, y)
    m.block("B", "o", "s", "q", "p")
    m.arc("p", "q", (0, 0))
    assert m.length("p", "q") == pytest.approx(R * np.pi / 2, rel=1e-12)
    assert m.arc_midpoint("q", "p") == pytest.approx([-R / np.sqrt(2), -R / np.sqrt(2)], rel=1e-12)
    assert m.length("o", "s") == pytest.approx(2 * np.sqrt(2))


def test_check_passes_and_reports():
    r = two_blocks().check()
    assert (r["blocks"], r["vertices"], r["cells"], r["families"]) == (2, 6, 100, 3)
    assert r["max_cell_ratio"] == 1.0


def test_check_detects_topology_errors():
    m = two_blocks()
    m.patches["top"][1].pop()                       # boundary edge in no patch
    with pytest.raises(ValueError, match="in no patch"):
        m.check()
    m = two_blocks()
    m.patch("bad", "patch", [("b", "e")])           # interior edge in a patch
    with pytest.raises(ValueError, match="interior edge"):
        m.check()
    m = two_blocks()
    m.patch("dup", "patch", [("a", "d")])           # edge in two patches
    with pytest.raises(ValueError, match="is in patches"):
        m.check()
    m = two_blocks()
    m.patch("bad", "patch", [("a", "e")])           # diagonal: not an edge
    with pytest.raises(ValueError, match="not a block edge"):
        m.check()


def test_check_detects_orientation_and_count_errors():
    m = BlockMesh()
    for name, x, y in (("a", 0, 0), ("b", 1, 0), ("c", 1, 1), ("d", 0, 1)):
        m.vertex(name, x, y)
    m.block("cw", "a", "d", "c", "b")               # clockwise
    m.count("a", "b", 2), m.count("a", "d", 2)
    m.patch("all", "patch", [("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")])
    with pytest.raises(ValueError, match="counter-clockwise"):
        m.check()
    m = two_blocks()
    m.count("e", "f", 7)                            # conflicts with (b, c) = 6
    with pytest.raises(ValueError, match="cell counts"):
        m.check()
    m = two_blocks()
    del m.counts[("a", "d")]                        # family without a count
    with pytest.raises(ValueError, match="cell counts"):
        m.check()
    with pytest.raises(ValueError):
        BlockMesh().block("x", "a", "b", "c", "d")  # unknown vertices


def test_render_structure_and_outward_faces():
    m = two_blocks(h_mid=1.5)
    m.grade_family("a", "d", start=1e-2)
    txt = m.render()
    assert txt.count("hex (") == 2 and "edgeGrading" in txt
    # block L = (a b e d) -> indices (0 1 4 3), back plane +6
    assert "hex (0 1 4 3 6 7 10 9) (4 10 1)" in txt
    # wall edge a->b in the block's CCW order: face (a b b' a') = (0 1 7 6) points to -y (outward)
    assert "wall { type wall; faces ((0 1 7 6) (1 2 8 7)); }" in txt
    # top edge given as (d, e) but CCW direction in block L is e->d: (4 3 9 10)
    assert "top { type patch; faces ((4 3 9 10) (5 4 10 11)); }" in txt
    assert "frontAndBack { type empty;" in txt
    # x2 gradings of block L: edges a->d (length 1) and b->e (length 1.5) differ
    line = next(ln for ln in txt.splitlines() if "// L" in ln)
    g = [float(t) for t in line.split("edgeGrading (")[1].split(")")[0].split()]
    assert g[:4] == [1.0] * 4 and g[8:] == [1.0] * 4
    assert g[4] == g[7] == pytest.approx(m.expansion("a", "d"), rel=1e-9)
    assert g[5] == g[6] == pytest.approx(m.expansion("b", "e"), rel=1e-9)
    assert g[5] > g[4] > 1
