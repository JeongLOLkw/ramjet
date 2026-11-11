import numpy as np
import pytest

from scripts import heatflux as hf
from src import boundary_layer as bl
from tests import foam_synth as fs


def test_sign_into_wall_positive():
    assert hf.heat_flux(350.0, 300.0, 1e-5) > 0     # fluid hotter than wall -> into the wall
    assert hf.heat_flux(250.0, 300.0, 1e-5) < 0
    assert hf.heat_flux(300.0, 300.0, 1e-5) == 0


def test_fourier_value_uses_wall_conductivity():
    q = hf.heat_flux(310.0, 300.0, 2e-6)
    assert q == pytest.approx(bl.kappa_eucken(300.0) * 10.0 / 2e-6, rel=1e-12)


def test_rejects_non_positive_distance():
    with pytest.raises(ValueError):
        hf.heat_flux(310.0, 300.0, 0.0)


@pytest.mark.parametrize("alpha_deg", [0.0, 24.0])
def test_couette_case_exact(tmp_path, alpha_deg):
    c = fs.couette(tmp_path, alpha=np.radians(alpha_deg))
    w = hf.case_heat_flux(tmp_path, "1", "wall")
    q_exact = bl.kappa_eucken(c["T_w"]) * (c["T_top"] - c["T_w"]) / c["H"]
    assert w["q_w"] == pytest.approx(q_exact, rel=1e-9)
    assert np.all(np.diff(w["x"]) > 0)
    assert w["tau_w"] == pytest.approx(bl.mu_sutherland(c["T_w"]) * c["U_top"] / c["H"], rel=1e-9)
    assert w["d"] == pytest.approx(c["H"] / 20, rel=1e-9)


def test_adiabatic_wall_gives_zero(tmp_path):
    fs.couette(tmp_path, adiabatic=True)
    w = hf.case_heat_flux(tmp_path, "1", "wall")
    assert np.all(w["q_w"] == 0)


def test_cli_writes_csv(tmp_path, capsys):
    fs.couette(tmp_path)
    out = tmp_path / "q.csv"
    assert hf.main([str(tmp_path), "1", "wall", "--csv", str(out)]) == 0
    lines = out.read_text().splitlines()
    assert lines[1] == "patch,x,y,q_w" and len(lines) == 2 + 4
