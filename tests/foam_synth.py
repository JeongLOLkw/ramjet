"""Hand-built ASCII OpenFOAM case (no OpenFOAM needed) for wall post-processing tests.

Structured nx x ny x 1 channel of height H, length L, rotated by `alpha` about z.
Patch `wall` = lower wall, `top` = upper boundary. Only boundary faces are written
(startFace 0); the readers under test never touch internal faces.
"""
import numpy as np

HDR = "FoamFile\n{{\n    version 2.0;\n    format ascii;\n    class {cls};\n    object {obj};\n}}\n// synthetic\n"


def _lst(items):
    return f"{len(items)}\n(\n" + "\n".join(items) + "\n)\n"


def build(case, nx, ny, L, H, alpha, y_edges=None):
    """Write mesh + 0/Cx, 0/Cy. Returns (cell-centre wall distance y_c (ncell,), rotation matrix)."""
    ye = np.linspace(0, H, ny + 1) if y_edges is None else np.asarray(y_edges, float)
    xe = np.linspace(0, L, nx + 1)
    c, s = np.cos(alpha), np.sin(alpha)
    R = np.array([[c, -s], [s, c]])
    pid = lambda i, j, k: i + (nx + 1) * j + (nx + 1) * (ny + 1) * k  # noqa: E731
    pts = []
    for k in (0.0, 1.0):
        for j in range(ny + 1):
            for i in range(nx + 1):
                x, y = R @ np.array([xe[i], ye[j]])
                pts.append(f"({x:.15g} {y:.15g} {k})")
    faces, owner = [], []
    for i in range(nx):  # wall: outward normal = -y (rotated)
        faces.append(f"4({pid(i,0,0)} {pid(i+1,0,0)} {pid(i+1,0,1)} {pid(i,0,1)})")
        owner.append(str(i))
    for i in range(nx):  # top: outward normal = +y (rotated)
        faces.append(f"4({pid(i,ny,0)} {pid(i,ny,1)} {pid(i+1,ny,1)} {pid(i+1,ny,0)})")
        owner.append(str(i + nx * (ny - 1)))
    md = case / "constant/polyMesh"
    md.mkdir(parents=True)
    (md / "points").write_text(HDR.format(cls="vectorField", obj="points") + _lst(pts))
    (md / "faces").write_text(HDR.format(cls="faceList", obj="faces") + _lst(faces))
    (md / "owner").write_text(HDR.format(cls="labelList", obj="owner") + _lst(owner))
    (md / "boundary").write_text(HDR.format(cls="polyBoundaryMesh", obj="boundary") + _lst([
        f"    wall\n    {{\n        type wall;\n        nFaces {nx};\n        startFace 0;\n    }}",
        f"    top\n    {{\n        type patch;\n        nFaces {nx};\n        startFace {nx};\n    }}"]))
    xc = 0.5 * (xe[1:] + xe[:-1])
    yc = 0.5 * (ye[1:] + ye[:-1])
    X, Y = np.meshgrid(xc, yc)          # row j, column i  -> cell id i + nx*j
    cc = (R @ np.vstack([X.ravel(), Y.ravel()])).T
    scalar(case, "0", "Cx", cc[:, 0])
    scalar(case, "0", "Cy", cc[:, 1])
    return Y.ravel(), R


def scalar(case, time, name, vals, wall=None):
    """wall: None -> zeroGradient (no value); float -> fixedValue uniform."""
    bc = "type zeroGradient;" if wall is None else f"type fixedValue; value uniform {wall:.15g};"
    (case / time).mkdir(exist_ok=True)
    (case / time / name).write_text(
        HDR.format(cls="volScalarField", obj=name) + "dimensions [0 0 0 0 0 0 0];\n"
        f"internalField nonuniform List<scalar> {len(vals)}\n(\n" + "\n".join(f"{v:.15g}" for v in vals)
        + f"\n)\n;\nboundaryField\n{{\n    wall {{ {bc} }}\n    top {{ type zeroGradient; }}\n}}\n")


def vector(case, time, name, vals):
    (case / time).mkdir(exist_ok=True)
    (case / time / name).write_text(
        HDR.format(cls="volVectorField", obj=name) + "dimensions [0 1 -1 0 0 0 0];\n"
        f"internalField nonuniform List<vector> {len(vals)}\n(\n"
        + "\n".join(f"({v[0]:.15g} {v[1]:.15g} 0)" for v in vals)
        + "\n)\n;\nboundaryField\n{\n    wall { type fixedValue; value uniform (0 0 0); }\n    top { type zeroGradient; }\n}\n")


def couette(case, alpha=0.0, nx=4, ny=10, L=0.1, H=1e-3, T_w=300.0, T_top=350.0, U_top=5.0, p=1e4,
            adiabatic=False):
    """Linear T and u_t profiles: the one-sided wall gradients are exact."""
    yc, R = build(case, nx, ny, L, H, alpha)
    T = (np.full_like(yc, T_w) if adiabatic else T_w + (T_top - T_w) * yc / H)
    scalar(case, "1", "T", T, wall=None if adiabatic else T_w)
    scalar(case, "1", "p", np.full_like(yc, p))
    ut = U_top * yc / H
    vector(case, "1", "U", np.outer(ut, R @ np.array([1.0, 0.0])))
    return dict(H=H, T_w=T_w, T_top=T_top, U_top=U_top, p=p)
