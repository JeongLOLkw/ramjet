"""Tests for src.foam_reader (ASCII OpenFOAM internalField parsing)."""
import numpy as np
import pytest

from src import foam_reader as fr

SCALAR = """FoamFile { version 2.0; format ascii; class volScalarField; object p; }
dimensions [1 -1 -2 0 0 0 0];
internalField   nonuniform List<scalar>
3
(
1.5
2.5
-3e-2
)
;
boundaryField { }
"""
VECTOR = """internalField   nonuniform List<vector>
2
(
(1 2 3)
(-4 5e-1 6)
)
;
"""
UNIFORM = "internalField   uniform 0.7;\n"
THERMO = """mixture
{
    specie { nMoles 1; molWeight 11640.3; }
    thermodynamics { Cp 2.5; Hf 0; }
}
"""


def test_scalar_list(tmp_path):
    f = tmp_path / "p"
    f.write_text(SCALAR)
    np.testing.assert_allclose(fr.read_internal_field(f), [1.5, 2.5, -0.03])


def test_vector_list(tmp_path):
    f = tmp_path / "U"
    f.write_text(VECTOR)
    np.testing.assert_allclose(fr.read_internal_field(f), [[1, 2, 3], [-4, 0.5, 6]])


def test_uniform_needs_n(tmp_path):
    f = tmp_path / "T"
    f.write_text(UNIFORM)
    np.testing.assert_allclose(fr.read_internal_field(f, n=4), [0.7] * 4)
    with pytest.raises(ValueError):
        fr.read_internal_field(f)


def test_gas_from_thermo(tmp_path):
    f = tmp_path / "thermophysicalProperties"
    f.write_text(THERMO)
    R, gamma = fr.gas_from_thermo(f)
    assert R == pytest.approx(8314.47 / 11640.3, rel=1e-6)
    # Cp = gamma R / (gamma-1)  ->  gamma = Cp/(Cp-R)
    assert gamma == pytest.approx(2.5 / (2.5 - R), rel=1e-9)
    assert gamma == pytest.approx(1.4, abs=1e-3)
