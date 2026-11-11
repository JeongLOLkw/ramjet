#!/usr/bin/env python3
"""I4 실행 상태 한 줄 요약 (읽기 전용). 모니터 에이전트가 5분마다 호출한다.

출력 첫 줄이 판정: STATUS=OK | STATUS=DONE | STATUS=ANOMALY(<이유>).
아무것도 수정·재시작하지 않는다.
"""
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNLOG = REPO / "cases/runs/i4_run.log"
VAL = REPO / "cases/validation"


def tail(path, n=40):
    try:
        return path.read_text(errors="replace").splitlines()[-n:]
    except OSError:
        return []


def main():
    lines = tail(RUNLOG, 200)
    if not lines:
        print("STATUS=ANOMALY(i4_run.log 없음)")
        return 1
    done_all = any("ALL DONE" in line for line in lines)
    state = {}
    for line in lines:
        m = re.match(r"\S+ (\S+) (RUNNING|DONE|MISSING)(.*)", line)
        if m and m.group(1) != "ALL":  # "<time> ALL DONE" is the end-of-script marker, not a case
            state[m.group(1)] = (m.group(2), m.group(3).strip())
    running = [c for c, (s, _) in state.items() if s == "RUNNING"]
    failed = [(c, x) for c, (s, x) in state.items() if s == "DONE" and not x.startswith("rc=0")]
    bad_yplus = [(c, x) for c, (s, x) in state.items() if s == "DONE" and "yplus_rc=" in x and "yplus_rc=0" not in x]
    notes, anomalies = [], []
    for c, x in failed:
        anomalies.append(f"{c} 비정상 종료 {x}")
    for c, x in bad_yplus:
        anomalies.append(f"{c} y+ 검사 실패 {x}")
    for c in running:
        d = VAL / c
        sol = tail(d / "log.solver", 400)
        step = next((int(m.group(1)) for line in reversed(sol) for m in [re.match(r"Time = (\d+)$", line)] if m), None)
        clock = next((m.group(1) for line in reversed(sol) for m in [re.search(r"ClockTime = (\d+) s", line)] if m), None)
        txt = "\n".join(sol)
        if re.search(r"nan|Floating point exception|FOAM FATAL|negative (temperature|pressure)|Maximum number of iterations exceeded", txt, re.I):
            anomalies.append(f"{c} 로그에 NaN/치명 오류 문구")
        nbound = len(re.findall(r"bounding", txt))
        mtime = (d / "log.solver").stat().st_mtime if (d / "log.solver").exists() else 0
        stale = (datetime.now().timestamp() - mtime) if mtime else None
        if stale is not None and stale > 600:
            anomalies.append(f"{c} log.solver가 {int(stale)}초째 갱신 없음")
        notes.append(f"{c}: step {step}/20000 clock {clock}s bounding(최근400줄) {nbound}")
    mem = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout.splitlines()
    avail = int(mem[1].split()[6]) if len(mem) > 1 else -1
    if 0 <= avail < 1500:
        anomalies.append(f"가용 메모리 {avail} MB")
    nproc = subprocess.run("pgrep -c -x hisa", shell=True, capture_output=True, text=True).stdout.strip()
    if done_all and not anomalies:
        print("STATUS=DONE")
    elif anomalies:
        print("STATUS=ANOMALY(" + "; ".join(anomalies) + ")")
    else:
        print("STATUS=OK")
    print(datetime.now().strftime("%H:%M:%S"), "hisa 프로세스", nproc or 0, "가용메모리MB", avail)
    for n in notes:
        print(n)
    print("run.log 끝:", " | ".join(lines[-3:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
