# progress.md — 흡입구 실험 (inlet-mach-sweep)

## I0 — 환경 준비 (2026-11-10 ~ )
- 모델·노력·UT: 사용자 단계. Claude Code는 점검만 수행 (Haiku 5.5 · 낮음 · UT X)
- 한 일: 사용자 측 전제 점검 (아래 결과)
- 결과:
  - `.wslconfig` (`C:\Users\User\.wslconfig`): `memory=10GB`, `swap=8GB`, `processors=12`
    → **계획 §8 전제는 `memory=12GB`**. 현재 값과 다름. 사용자 결정 필요 (아래 "남은 문제" 참고)
  - 홈 여유 공간: 826 GB (기준 20 GB 이상 통과)
  - GitHub 저장소: 확인됨 (JeongLOLkw/ramjet, push는 사용자 인증 대기)
  - Fable 사용 조건: 사용자 확인 — 사용 가능
- 남은 문제: `.wslconfig` memory 10GB vs 12GB 결정 (D-003)
- 소요: 벽시계 수 분 / 클라우드 $0 / /usage 미기록

## I2 — 설치·속도 실측 (2026-11-10 ~ ) — 진행 중
- 모델·노력·UT: 계획상 Sonnet 5.5 · 중간 · UT X. **실제 실행 모델은 Haiku 5.5** (배정과 다름)
- 한 일:
  1. 환경 점검 (아래 기록)
  2. 저장소 골격: §7 구조 생성, `CLAUDE.md`(계획 §2 복사), `docs/plan.md`·`docs/science_prompt_I1.md` 이동, `.gitignore`, 본 파일 생성, `git init`
  3. HiSA 소스 clone(`~/src/hisa`, 태그 validated-v2512) 및 기능 정적 확인 → decisions.md D-004
  4. conda 환경 `inlet` 생성 (numpy, scipy, matplotlib, pyvista, fluidfoam, pytest; `PYTHONNOUSERSITE=1` 필요)
  5. v2512 설치 명령 준비 — 사용자 실행 대기 (sudo)
- 환경 점검 기록 (2026-11-10):
  - OS: Ubuntu 24.04.5 LTS (noble) / WSL2 (Linux 6.6.87.2-microsoft-standard-WSL2)
  - CPU: 12 논리 코어 (`nproc` = 12)
  - 메모리: 9.7 GiB 보임 (WSL 설정 10 GB), 스왑 8 GiB
  - 디스크: `/` 여유 826 GB
  - OpenFOAM: **ESI v2512 아님.** `openfoam2412` (OpenCFD 2412.260127-1) 설치되어 있음, `/usr/lib/openfoam/openfoam2412`
    - `~/.bashrc`의 `program_OF` alias가 2412를 source함
  - HiSA: 미설치
  - 도구: git, mpirun, gcc, cmake, python3 3.12.3 있음
- 결과 (성공 기준별):
  - [ ] forwardStep(rhoCentralFoam)과 HiSA 예제 오류 없이 종료 — 미실행
  - [ ] `docs/benchmarks/I2.md` MPI 속도표 — 미작성
  - [ ] HiSA 비정상 지원 여부 `decisions.md` 기록 — 미완 (HiSA 미설치)
  - [ ] WSL 최대 메모리 10 GB 이내 — 현재 설정 10 GB, 판정은 실측 후
  - [ ] 커밋 — 골격 커밋 예정
- 남은 문제:
  1. **OpenFOAM 판본 결정**: 계획은 ESI v2512 (사용자 승인 없이 다른 판본 금지). 현재 2412만 설치됨. 승인 필요
  2. sudo 필요 설치 명령은 사용자가 직접 실행 (Claude 실행 불가)
  3. `.wslconfig` memory 10 GB vs 계획 12 GB 불일치
  4. 계획 자체 모순: §2 CLAUDE.md "WSL 12 GB" vs §8 성공 기준 "10 GB 이내"
- 소요: 벽시계 — / 클라우드 $0 / /usage — 기록 예정

## 오류 기록
- 없음
