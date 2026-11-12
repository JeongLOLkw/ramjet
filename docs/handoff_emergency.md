# 긴급 안내 — 클라우드 전용 실행 (D-019, 2026-11-12부터)

로컬(노트북)에서는 솔버·격자·초기화 연산을 하지 않는다. 계산은 GCP VM에서 끝까지 가고, 결과를 버킷에 올린 뒤 VM이 스스로 꺼진다.
**노트북은 꺼도, 덮어도 된다.** 아래는 상태를 보고 싶거나 이상할 때 직접 치는 명령이다(WSL 터미널, 어느 폴더에서든).

## 1. 지금 상태 보기
```bash
VM=ramjet-i4-a ~/ramjet/scripts/cloud/handoff_status.sh
```
`HEARTBEAT` 줄이 VM이 30초마다 올리는 현황이다: `step=현재/ end=목표, sps=스텝당 초, state=running|done, tag=케이스`.
버킷 `handoff/ramjet-i4-a/out/`에 생기는 표지:
| 표지 | 뜻 |
|---|---|
| `FINISHED_ramp24_L1` | 램프 L1 끝(rc 0). 이어서 y+ 검사 → L2 준비 → L2 실행 |
| `log.yplus_ramp24_L1` | L1의 y+ 검사 결과(PASS여야 L2가 시작됨) |
| `FINISHED` | 연결된 작업 전체가 끝남(마지막 케이스 rc 0). 3분 뒤 VM 전원 종료 |
| `READY` | 하드 스톱(42시간)에 걸려 체크포인트에서 멈춤. 이어 하려면 Claude에게 |
| `FAILED` | 실패(내용에 이유). VM은 꺼진다. 아무것도 지우지 말고 Claude에게 |
| `LATEST`, `latest.tar.gz` | 가장 최근 체크포인트(5분 안에 갱신) |

## 2. VM 끄기 (요금 차단)
```bash
~/google-cloud-sdk/bin/gcloud compute instances stop ramjet-i4-a --zone us-central1-a
~/google-cloud-sdk/bin/gcloud compute instances list      # STATUS가 TERMINATED면 꺼진 것
```
휴대폰: <https://console.cloud.google.com/compute/instances> → 프로젝트 `project-03050886-e5fd-4c6a-a2a` → VM 선택 → **중지**.
끄지 않아도 VM은 계산이 끝나면 3분 뒤 스스로 꺼지고, 늦어도 44시간 뒤에는 GCE가 강제로 멈춘다. **삭제는 누르지 않는다**(디스크에 결과가 있다).
중간에 꺼도 버킷의 마지막 체크포인트(`latest.tar.gz`)와 VM 디스크가 남으므로 계산은 잃지 않는다. 다시 켜면(`... instances start ...`) 디스크에 있는 곳부터 이어 계산한다.

## 3. 결과 내려받기 (계산이 끝난 뒤)
```bash
~/ramjet/scripts/cloud/pull.sh ramjet-i4-336381269092
```
내려받기만 한다(계산 없음). 판정(`scripts/i4_analyze.py`)은 Claude가 한다.

## 4. 로컬에서 다시 계산하고 싶을 때 (기본은 하지 않음)
```bash
~/ramjet/scripts/cloud/restore.sh --force --local-only --case ~/ramjet/cases/validation/ramp24/L1
```
로컬에 남은 체크포인트(이양 시점)부터 다시 계산한다. VM이 같은 케이스를 돌리고 있으면 먼저 2번으로 끈다.

## 5. 어디에 무엇이 있나
| 무엇 | 위치 |
|---|---|
| 이양 기록 | `~/ramjet/cases/runs/handoff.log` |
| 상태 표지 | `~/ramjet/cases/runs/handoff/` (`STATUS`, `HANDOFF_DONE`, `HANDOFF_FAILED`) |
| 클라우드 현황·체크포인트 | `gs://ramjet-i4-336381269092/handoff/<VM 이름>/out/` |
| 끝난 케이스 전체 | `gs://ramjet-i4-336381269092/results/validation/<케이스>/` |
| VM 시동 로그(전원 종료 진단 포함) | `gs://ramjet-i4-336381269092/diag/<VM 이름>/i4-startup.log` |

## 6. 그래도 모르겠으면
아무것도 지우지 말고 1번 출력과 `handoff.log` 마지막 30줄을 Claude에게 보여준다.
