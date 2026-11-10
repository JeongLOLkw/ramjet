# decisions.md — 설계 결정 기록

## D-001 저장소 위치 (2026-11-10)
- 계획 §7의 이름은 `inlet-mach-sweep/`이지만, 실제 저장소는 `~/ramjet`에 둔다 (사용자가 계획 파일을 이 경로에 둠).
- 이름 변경이 필요하면 사용자 결정.

## D-002 OpenFOAM 판본 — 보류 (승인 대기)
- 계획: ESI v2512 (CLAUDE.md 환경 항목, 다른 판본은 사용자 승인 필요).
- 현 상태: `openfoam2412` (2412.260127-1) 설치됨. v2512 미설치.
- 선택지:
  - (a) v2512 설치 (권장, 계획 준수). 사용자가 아래 명령 실행 필요
  - (b) 2412로 진행 — HiSA 지원 범위(v2006~v2512) 안이지만 계획 위반이므로 사용자 승인 필요
- 결정 전까지 HiSA 빌드·속도 실측은 시작하지 않음.

## D-003 `.wslconfig` 메모리 — 보류
- 계획 §8 전제: `memory=12GB`. 현재: `memory=10GB`.
- 계획 §2 CLAUDE.md의 "WSL 12 GB"와 §8 성공 기준의 "10 GB 이내"도 서로 다름.
- 결정 전까지 현재 값(10 GB)으로 진행. 값을 바꾸면 `wsl --shutdown` 필요 (사용자 실행).

## D-004 HiSA 기능 (소스 정적 확인, 빌드·실행 전 — 2026-11-10)
- 출처: `~/src/hisa` (https://gitlab.com/hisa/hisa, 태그 `validated-v2512`, 커밋 271b449). 태그 `validated-v2406/v2412/v2506/v2512/v2606` 존재.
- **시간 정확 비정상 지원: 있음(소스상).** `src/finiteVolume/dualTimeDdtScheme/dualTimeDdtScheme.H` (이중 시간 간격),
  예제 `examples/shockTube`, `examples/forwardStep`의 `fvSchemes`: `default dualTime rPseudoDeltaT CrankNicolson 0.9;`,
  `fvSolution`의 `pseudoTime { nPseudoCorr; pseudoTol; pseudoCoNum ... }`. 정상은 `bounded dualTime rPseudoDeltaT steadyState` (예: flatPlate).
- **난류 모델:** 예제에서 `SpalartAllmaras`(flatPlate, agardB, oneraM6), `kOmegaSST`(basicFinner, modifiedFinner) 사용.
  `boundaryCorrectedNutLowReWallFunction` BC 존재(규칙 2: 벽 함수 사용 금지 → 사용하지 않음).
- **경계조건:** `src/finiteVolume/boundaryConditions/characteristic/` 아래 `characteristicFarfield`, `characteristicPressureInletOutlet`,
  `characteristicVelocityInletOutlet`, `characteristicWall`. 그 외 `movingWallSlip`, `boundaryCorrectedFixedValue`, `constraint`.
- 미확인(빌드 후 확인 예정): 실제 지원 모델 목록(OpenFOAM 라이브러리 의존), 초음속 출구 처리 상세, 예제 실행 결과.
- 이 내용은 정적 확인이다. 예제가 실제로 끝까지 도는지는 I2 6단계에서 판정.

## D-005 사용자 답변 반영 (2026-11-10)
- Fable 사용 가능 (I0 항목 해소).
- GitHub 저장소: `https://github.com/JeongLOLkw/ramjet` 확인(초기 README 커밋만 있음). 로컬 `origin` 추가, 병합 완료.
  push는 자격증명이 없어 사용자 실행 대기.
- OpenFOAM: 사용자 안내 "이미 설치"는 2412 기준으로 확인됨. v2512는 미설치이나 이미 등록된 apt 저장소(`dl.openfoam.com noble`)에
  `openfoam2512 2512.0-2` 후보가 있음 → 2412와 병존 설치 가능(2412를 지우지 않음). D-002 선택지 (a) 권장 유지.
- 파이썬 환경 `inlet` 생성(conda-forge). 주의: `~/.local`의 numpy 2.5.4가 환경을 가림 → `PYTHONNOUSERSITE=1` 또는 `python -s` 필요.
