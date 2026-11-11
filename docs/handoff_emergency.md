# 긴급 복원 안내 — 등교 시간 이양(07:40)·복원(08:30)

Claude 없이 도는 예약 스크립트가 처리한다(D-018). 아래는 **예약이 안 돌았거나 이상할 때 직접 치는 명령**이다.
모든 명령은 WSL 터미널에서, 어느 폴더에서든 그대로 붙여 넣으면 된다.

## 0. 평소에 지킬 것
- 노트북은 **덮개만 닫는다**. Windows 종료·재시작, WSL 터미널 창 닫기는 하지 않는다(예약 프로세스가 죽는다).
- 07:40 이후 화면에 `ramjet: handoff OK - you can close the laptop` 창이 뜨면 닫아도 된다(보통 07:50 전후).
  창이 안 떠도 08:00에는 그냥 닫아도 된다 — 덮개를 닫으면 스크립트가 멈췄다가 다시 열 때 이어서 한다.
- 08:30 이후 노트북을 열면 복원이 알아서 시작된다. 인터넷이 될 때까지 1분마다 다시 시도한다.

## 1. 지금 상태 보기 (가장 먼저)
```bash
~/ramjet/scripts/cloud/handoff_status.sh
```
맨 위 `STATUS` 줄이 현재 상태다. 자주 나오는 문구:
| 문구 | 뜻 | 할 일 |
|---|---|---|
| `HANDOFF OK` | 클라우드(VM B)가 이어서 계산 중 | 없음 |
| `cloud busy/unreachable — local run left untouched` | 이양하지 않음. 로컬 계산은 그대로(덮개를 닫으면 멈췄다가 열면 계속) | 없음 |
| `HANDOFF FAILED — resumed locally` | 클라우드 시작 실패, 로컬에서 다시 계산 중 | 없음 |
| `nothing running — nothing to hand off` | 07:40에 로컬 계산이 이미 끝나 있었음 | 없음 |
| `recall requested` | 로컬로 되돌리는 중(클라우드가 다음 체크포인트를 쓴 뒤 넘겨줌, 보통 10~15분) | 기다림 |
| `left in the cloud` | 클라우드가 빠르거나 비슷해서 그대로 둠. 끝나면 결과만 받아 온다 | 없음 |
| `cloud result READY/FINISHED ... handled` | 받아 와서 로컬에서 이어 계산(또는 마무리) 시작 | 없음 |
| `VM ... is off without a result marker` | VM이 중간에 꺼짐. 버킷의 마지막 체크포인트로 로컬 재개 | 없음 |
| `RESTORE DONE` | 복원 끝 | 없음 |
| `SHIP OK: ramp24/L2 is running on ramjet-i4-a` | 램프 L2가 클라우드(VM A)에서 시작됨 | 없음 |

## 2. 예약이 안 돌았을 때 손으로 실행
```bash
~/ramjet/scripts/cloud/handoff.sh          # 이양 (07:40에 돌았어야 하는 것)
~/ramjet/scripts/cloud/restore.sh          # 복원 (08:30에 돌았어야 하는 것)
```
이미 한 번 돈 뒤 다시 돌리려면 뒤에 `--force`를 붙인다.

## 3. 클라우드를 포기하고 로컬에서 바로 이어 계산
인터넷이 안 되거나 클라우드가 이상할 때. 로컬에 남은 마지막 체크포인트(이양 시점)부터 다시 계산한다.
```bash
~/ramjet/scripts/cloud/restore.sh --force --local-only
```
이 경우 **VM이 계속 켜져 있을 수 있으니** 인터넷이 되면 4번으로 끈다.

## 4. 클라우드 VM 끄기 (요금 차단)
```bash
~/google-cloud-sdk/bin/gcloud compute instances stop ramjet-i4-b --zone us-central1-a
~/google-cloud-sdk/bin/gcloud compute instances list      # STATUS가 TERMINATED면 꺼진 것
```
휴대폰: <https://console.cloud.google.com/compute/instances> → 프로젝트 `project-03050886-e5fd-4c6a-a2a` → `ramjet-i4-b` 선택 → **중지**.
끄지 않아도 VM은 계산이 끝나면 3분 뒤 스스로 꺼지고, 늦어도 12시간 뒤(하드 스톱)에는 멈춘다. **삭제는 누르지 않는다**(디스크에 결과가 있다).

## 5. 예약 취소
```bash
pkill -f handoff_sched.sh
systemctl --user stop ramjet-handoff.timer ramjet-restore.timer
pkill -f ship_ramp_L2.sh        # 램프 L2 클라우드 자동 시작도 취소하려면
```
예약은 이중이다: 30초마다 시계를 보는 프로세스(`handoff_sched.sh`, 07:40·08:30)와 systemd 타이머(07:41·08:31, 예비). 어느 쪽이 먼저 돌든 한 번만 실행된다.

## 5-1. 램프 L2 (L1이 끝난 뒤 자동)
L1이 `rc 0` + y+ 통과로 끝나면 `ship_ramp_L2.sh`가 L2를 준비해 VM A(`ramjet-i4-a`)로 보낸다. VM A가 평판 계산을 끝낼 때까지 5분마다 다시 확인한다(최대 10시간).
손으로 실행: `~/ramjet/scripts/cloud/ship_ramp_L2.sh`. VM A를 끄려면 4번 명령에서 이름만 `ramjet-i4-a`로 바꾼다(하드 스톱 40시간).

## 6. 어디에 무엇이 있나
| 무엇 | 위치 |
|---|---|
| 이양·복원 기록 | `~/ramjet/cases/runs/handoff.log` |
| 상태 표지 | `~/ramjet/cases/runs/handoff/` (`STATUS`, `HANDOFF_DONE`, `RESTORE_DONE` 등) |
| 덮어쓰기 전 로컬 로그 백업 | `~/ramjet/cases/runs/handoff/backup_*` |
| 클라우드 쪽 최신 체크포인트 | `gs://ramjet-i4-336381269092/handoff/<VM 이름>/out/latest.tar.gz` (새 체크포인트가 생기면 5분 안에 갱신) |
| 램프 L1 케이스 | `~/ramjet/cases/validation/ramp24/L1` (`run_info.txt`에 `handoff-stop`·`restart` 줄이 남는다) |

## 7. 그래도 모르겠으면
아무것도 지우지 말고 1번 출력과 `handoff.log` 마지막 30줄을 Claude에게 보여준다. 로컬 체크포인트와 버킷 사본이 둘 다 남아 있으므로 계산은 잃지 않는다.
