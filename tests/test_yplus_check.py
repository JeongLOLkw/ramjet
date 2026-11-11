import numpy as np
import pytest

from scripts import yplus_check as yp
from src import boundary_layer as bl
from src import constants as C
from tests import foam_synth as fs


def test_limits():
    assert yp.check([0.2, 0.99]) == (True, 0.99)
    assert yp.check([0.2, 1.0])[0] is False                 # steady rule: strictly below 1
    assert yp.check([0.2, 5.0], limit=5, inclusive=True)[0] is True
    assert yp.check([0.2, 5.01], limit=5, inclusive=True)[0] is False
    assert yp.check([0.2, np.nan])[0] is False
    assert yp.check([])[0] is False


def _yplus_exact(c, ny):
    d = c["H"] / (2 * ny)
    rho = c["p"] / (C.R_AIR * c["T_w"])
    mu = bl.mu_sutherland(c["T_w"])
    tau = mu * c["U_top"] / c["H"]
    return d * np.sqrt(tau / rho) * rho / mu


def test_case_value_and_exit_codes(tmp_path, capsys):
    a, b = tmp_path / "a", tmp_path / "b"
    c = fs.couette(a, alpha=np.radians(24.0), ny=10, U_top=5.0)
    exact = _yplus_exact(c, 10)
    assert exact < 1
    from src.wall import wall_data
    assert wall_data(a, "1", "wall")["y_plus"] == pytest.approx(exact, rel=1e-9)
    assert yp.main([str(a), "1", "wall"]) == 0
    c2 = fs.couette(b, ny=2, U_top=400.0, p=1e5)
    assert _yplus_exact(c2, 2) > 1
    assert yp.main([str(b), "1", "wall"]) == 1
    assert yp.main([str(b), "1", "wall", "--limit", "5", "--inclusive"]) == (0 if _yplus_exact(c2, 2) <= 5 else 1)
    assert "FAIL" in capsys.readouterr().out
