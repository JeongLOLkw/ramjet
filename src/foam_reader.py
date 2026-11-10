"""Minimal reader for ASCII OpenFOAM fields and thermo dictionaries.

Scope: benchmark/validation post-processing (I2). Not a general parser.
"""
import re
from pathlib import Path

import numpy as np

# OpenFOAM universal gas constant [J/(kmol K)] (OpenFOAM's `RR`).
# Used only to decode a case's own molWeight; project gas constants for
# physical cases live in src/constants.py (CLAUDE.md rule 4).
_OPENFOAM_RR = 8314.47

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def read_internal_field(path, n=None):
    """Return internalField as ndarray: (N,) for scalars, (N,3) for vectors.

    `uniform` fields need `n` (number of cells) to be expanded.
    """
    text = Path(path).read_text()
    m = re.search(r"internalField\s+uniform\s+(\([^)]*\)|" + _NUM + r")\s*;", text)
    if m:
        if n is None:
            raise ValueError("uniform field requires n")
        val = m.group(1)
        if val.startswith("("):
            vec = np.array(val.strip("()").split(), dtype=float)
            return np.tile(vec, (n, 1))
        return np.full(n, float(val))
    m = re.search(r"internalField\s+nonuniform\s+List<(\w+)>\s*(\d+)\s*\(", text)
    if not m:
        raise ValueError(f"no internalField found in {path}")
    kind, count = m.group(1), int(m.group(2))
    body = text[m.end():]
    if kind == "scalar":
        vals = np.array(re.findall(_NUM, body.split("\n)", 1)[0]), dtype=float)
        return vals[:count]
    if kind == "vector":
        triples = re.findall(r"\(\s*(" + _NUM + r")\s+(" + _NUM + r")\s+(" + _NUM + r")\s*\)", body)
        return np.array(triples[:count], dtype=float)
    raise ValueError(f"unsupported list type {kind}")


def gas_from_thermo(path):
    """Return (R, gamma) from a constant/thermophysicalProperties file.

    R = RR / molWeight [J/(kg K)]; gamma = Cp / (Cp - R) with constant Cp.
    """
    text = Path(path).read_text()
    mw = float(re.search(r"molWeight\s+(" + _NUM + r")", text).group(1))
    cp = float(re.search(r"\bCp\s+(" + _NUM + r")", text).group(1))
    R = _OPENFOAM_RR / mw
    return R, cp / (cp - R)
