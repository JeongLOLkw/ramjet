"""Minimal ASCII polyMesh / boundary-field reader for wall post-processing (I4 onward).

Scope: patch geometry (face centres, outward unit normals, areas, owner cells) and
patch values of volume fields, for serial (reconstructed) ASCII cases. Not a general parser.
"""
import re
from pathlib import Path

import numpy as np

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def _body(path):
    """Text after the FoamFile header, comments removed."""
    t = Path(path).read_text()
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"//[^\n]*", "", t)
    m = re.search(r"FoamFile\s*\{.*?\}", t, flags=re.S)
    return t[m.end():] if m else t


def _list_span(body):
    """(count, text between the outer parentheses) of the first `N ( ... )` list."""
    m = re.search(r"(\d+)\s*\(", body)
    if not m:
        raise ValueError("no list found")
    return int(m.group(1)), body[m.end():body.rindex(")")]


def read_points(mesh_dir):
    n, txt = _list_span(_body(Path(mesh_dir) / "points"))
    pts = np.array(re.findall(_NUM, txt), float).reshape(-1, 3)
    if len(pts) != n:
        raise ValueError(f"points: expected {n}, got {len(pts)}")
    return pts


def read_faces(mesh_dir):
    """List of integer arrays (point labels per face)."""
    n, txt = _list_span(_body(Path(mesh_dir) / "faces"))
    faces = [np.array(m.split(), int) for m in re.findall(r"\d+\(([^)]*)\)", txt)]
    if len(faces) != n:
        raise ValueError(f"faces: expected {n}, got {len(faces)}")
    return faces


def read_labels(path):
    n, txt = _list_span(_body(path))
    v = np.array(txt.split(), int)
    if len(v) != n:
        raise ValueError(f"{path}: expected {n}, got {len(v)}")
    return v


def read_boundary(mesh_dir):
    """{patch: dict(type, nFaces, startFace)} in file order."""
    _, txt = _list_span(_body(Path(mesh_dir) / "boundary"))
    out = {}
    for name, blk in re.findall(r"(\w+)\s*\{([^{}]*)\}", txt):
        g = lambda k: re.search(rf"\b{k}\s+([^;]+);", blk).group(1).strip()  # noqa: E731
        out[name] = dict(type=g("type"), nFaces=int(g("nFaces")), startFace=int(g("startFace")))
    return out


def patch_geometry(case, patch):
    """Face centres (n,3), outward unit normals (n,3), areas (n,), owner cells (n,)."""
    md = Path(case) / "constant/polyMesh"
    b = read_boundary(md)[patch]
    sl = slice(b["startFace"], b["startFace"] + b["nFaces"])
    pts, faces, owner = read_points(md), read_faces(md)[sl], read_labels(md / "owner")[sl]
    cf, nrm, area = [], [], []
    for f in faces:
        p = pts[f]
        c0 = p.mean(axis=0)
        # area-weighted triangle fan about the vertex average (OpenFOAM's face::centre/areaNormal)
        a_sum, c_sum = np.zeros(3), np.zeros(3)
        w_sum = 0.0
        for i in range(len(f)):
            p1, p2 = p[i], p[(i + 1) % len(f)]
            a = 0.5 * np.cross(p1 - c0, p2 - c0)
            w = np.linalg.norm(a)
            a_sum += a
            c_sum += w * (p1 + p2 + c0) / 3.0
            w_sum += w
        cf.append(c_sum / w_sum)
        area.append(np.linalg.norm(a_sum))
        nrm.append(a_sum / np.linalg.norm(a_sum))
    return np.array(cf), np.array(nrm), np.array(area), owner


def _patch_block(text, patch):
    i = text.index("boundaryField")
    m = re.search(rf"(?<![\w|(]){re.escape(patch)}\s*\{{", text[i:])
    if not m:
        raise KeyError(f"patch {patch} not in boundaryField")
    j = i + m.end()
    depth, k = 1, j
    while depth:
        c = text[k]
        depth += (c == "{") - (c == "}")
        k += 1
    return text[j:k - 1]


def read_patch_field(path, patch, n):
    """Patch values of a volume field: (n,) or (n,3). Returns None if the patch entry
    stores no `value` (e.g. zeroGradient) — the caller then uses the owner-cell values."""
    blk = _patch_block(Path(path).read_text(), patch)
    m = re.search(r"\bvalue\s+uniform\s+(\([^)]*\)|" + _NUM + r")\s*;", blk)
    if m:
        v = m.group(1)
        if v.startswith("("):
            return np.tile(np.array(v.strip("()").split(), float), (n, 1))
        return np.full(n, float(v))
    m = re.search(r"\bvalue\s+nonuniform\s+List<(\w+)>\s*(\d+)\s*\(", blk)
    if not m:
        return None
    kind, count = m.group(1), int(m.group(2))
    vals = np.array(re.findall(_NUM, blk[m.end():]), float)
    if kind == "scalar":
        out = vals[:count]
    elif kind == "vector":
        out = vals[:3 * count].reshape(-1, 3)
    else:
        raise ValueError(f"unsupported list type {kind}")
    if len(out) != n:
        raise ValueError(f"{path}:{patch}: expected {n} values, got {len(out)}")
    return out
