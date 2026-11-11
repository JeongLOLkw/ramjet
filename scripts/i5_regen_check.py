"""I5 success criterion: regenerate the inlet mesh after changing ONE parameter, for a list of changes.

Each row writes a mesh-only case (scripts/i5_mesh.py), runs blockMesh + checkMesh and applies the
criteria fixed in the I5 plan:
  non-orthogonality max < 60 deg, skewness max < 4, no negative volumes, and no failed checkMesh test
  other than the aspect-ratio test (wall-resolved first cells make aspect ratios > 1000 unavoidable;
  the I4 meshes fail the same single test).
Usage:  python -s scripts/i5_regen_check.py [--out cases/runs/i5_regen] [--md docs/benchmarks/I5_regen.md]
Exit code 0 only if every row passes.
"""
import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from geometry import inlet_mesh as im  # noqa: E402
from geometry import inlet_param as ip  # noqa: E402
from scripts import i5_mesh  # noqa: E402

# (label, inlet-parameter changes, mesh level) — one change per row, base = D-016 defaults at level 0
ROWS = [("base L0", {}, 0), ("level 1", {}, 1), ("level 2", {}, 2),
        ("cr_int 1.15", dict(cr_int=1.15), 0), ("cr_int 1.44", dict(cr_int=1.44), 0),
        ("delta2 8", dict(delta2_deg=8.0), 0), ("delta2 12", dict(delta2_deg=12.0), 0),
        ("L_iso/H 5", dict(iso_L_over_H=5.0), 0), ("L_iso/H 15", dict(iso_L_over_H=15.0), 0),
        ("lip R 0.25 mm", dict(lip_radius=0.25e-3), 0), ("lip R 1.0 mm", dict(lip_radius=1.0e-3), 0),
        ("M_design 4.5", dict(M_design=4.5), 0), ("M_design 6", dict(M_design=6.0), 0)]
LIMITS = dict(non_ortho_max=60.0, skewness_max=4.0)


def judge(q):
    return (q["non_ortho_max"] < LIMITS["non_ortho_max"] and q["skewness_max"] < LIMITS["skewness_max"]
            and not q["negative_volumes"] and q["only_aspect_ratio_failed"] and q["failed_checks"] <= 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "cases/runs/i5_regen")
    ap.add_argument("--md", type=Path, help="write the table as markdown")
    a = ap.parse_args(argv)
    head = ("| 바꾼 매개변수 | 단계 | 셀 수 | H_th (mm) | 비직교 최대/평균 (°) | 왜도 최대 | 종횡비 최대 | 실패한 검사 | 생성 시간 (s) | 판정 |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n")
    lines, ok_all = [], True
    for label, change, level in ROWS:
        p, mp = replace(ip.InletParams(), **change), replace(im.MeshParams(), level=level)
        case = a.out / label.replace(" ", "_").replace("/", "_")
        t0 = time.time()
        i5_mesh.write_mesh_case(case, p, mp)
        q = i5_mesh.run_mesh(case)
        ok = judge(q)
        ok_all &= ok
        failed = "없음" if not q["problems"] else ("종횡비만" if q["only_aspect_ratio_failed"] else "; ".join(q["problems"]))
        lines.append(f"| {label} | {level} | {q['cells']} | {ip.design(p)['H_th'] * 1e3:.2f} | "
                     f"{q['non_ortho_max']:.1f} / {q['non_ortho_avg']:.1f} | {q['skewness_max']:.2f} | "
                     f"{q['aspect_ratio_max']:.0f} | {failed} | {time.time() - t0:.1f} | {'통과' if ok else '**실패**'} |")
        print(lines[-1], flush=True)
    if a.md:
        a.md.write_text(head + "\n".join(lines) + "\n")
    print("ALL PASS" if ok_all else "FAILED")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
