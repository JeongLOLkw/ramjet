"""Tests for src.bench_tools (I2 benchmark helpers)."""
import pytest

from src import bench_tools as bt

RCF_LOG = """Time = 0.002

Courant Number mean: 0 max: 0
ExecutionTime = 0.10 s  ClockTime = 0 s

Time = 0.004

ExecutionTime = 0.25 s  ClockTime = 0 s

Time = 0.006

ExecutionTime = 0.45 s  ClockTime = 1 s

End
"""

HISA_LOG = """Time = 0.005

pseudoTime: iteration 1
pseudoTime: iteration 2
pseudoTime: converged in 2 iterations
ExecutionTime = 1.0 s  ExecutionStepTime = 1.0 s  ClockTime = 1 s

Time = 0.01

pseudoTime: iteration 1
pseudoTime: iteration 2
pseudoTime: iteration 3
pseudoTime: converged in 3 iterations
ExecutionTime = 3.0 s  ExecutionStepTime = 2.0 s  ClockTime = 3 s

End
"""

BMD = """blocks
(
    hex (0 1 3 2 8 9 11 10) (48 16 1) simpleGrading (1 1 1)
    hex (2 3 6 5 10 11 14 13) (48 64 1) simpleGrading (1 1 1)
    hex (3 4 7 6 11 12 15 14) (192 64 1) simpleGrading (1 1 1)
);
"""


def test_step_times_rcf():
    steps = bt.parse_steps(RCF_LOG)
    assert [s["time"] for s in steps] == [0.002, 0.004, 0.006]
    # per-step wall = difference of cumulative ExecutionTime (first step: its own value)
    assert [s["wall"] for s in steps] == pytest.approx([0.10, 0.15, 0.20])
    assert all(s["pseudo_iters"] is None for s in steps)


def test_step_times_hisa():
    steps = bt.parse_steps(HISA_LOG)
    assert [s["wall"] for s in steps] == pytest.approx([1.0, 2.0])
    assert [s["pseudo_iters"] for s in steps] == [2, 3]


def test_mean_wall_skips_warmup():
    steps = bt.parse_steps(RCF_LOG)
    assert bt.mean_step_wall(steps, skip=1) == pytest.approx(0.175)
    with pytest.raises(ValueError):
        bt.mean_step_wall(steps, skip=3)


def test_scale_blocks():
    text, n = bt.scale_blocks(BMD, 1.0)
    assert n == 48 * 16 + 48 * 64 + 192 * 64 == 16128
    text, n = bt.scale_blocks(BMD, 3.5)
    assert "(168 56 1)" in text and "(168 224 1)" in text and "(672 224 1)" in text
    assert n == 168 * 56 + 168 * 224 + 672 * 224


def test_set_entry():
    d = "endTime         4;\nwriteInterval   0.1;\n"
    out = bt.set_entry(d, "endTime", "0.5")
    assert "endTime         0.5;" in out and "writeInterval   0.1;" in out
    with pytest.raises(KeyError):
        bt.set_entry(d, "nothere", "1")
