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

## D-006 I1 후속 처리안 — 제안, 승인 대기 (2026-11-10)
I1 점검에서 나온 문제와 담당 제안. 담당: **Code** = Claude Code, **Science** = Claude Science, **User** = 사용자.

| # | 문제 | 제안 | 담당 | 시점 |
|---|---|---|---|---|
| 1 | Reinartz는 정압만 측정, 열유속 없음 | I7·I10 압력/스로틀링 검증을 Emami TP-3502로 교체. 열유속 검증은 Häberle & Gülhan 전문 확보 후 채택 여부 결정 | User 승인 → Code가 plan.md 반영 | I7 전 |
| 2 | Häberle & Gülhan 전문 유료 | AIAA 접근 가능하면 PDF를 `docs/papers/`(gitignore)에 넣고 Science가 조건·치수·데이터 공개 여부 추출 | User(PDF 제공) → Science | I7 전 |
| 3 | 서지 미확인(MCF 판본, Van Wie 저자, FFA 번호, Celik 저자) | 보유 판본은 User가 알려줌. 나머지는 Science가 학술지 사이트·출판사 페이지로 확인해 references.md 갱신 | Science + User | I18 전, 낮은 우선순위 |
| 4 | Waltrup–Billig 계수 50·170이 2차 인용 | 원문(AIAA J. 11(10), 식 번호 포함) 확인. 확인 전에는 I10 비교에 쓰지 않음(규칙 11) | User(PDF) → Science | I10 전 |
| 5 | 그림에서만 얻는 자료(Settles, Emami, Wagner, Trapier) | `scripts/digitize.py`(축 보정 + 점 추출)를 pytest로 먼저 검증(합성 그림, 규칙 10) 후 사용. 우선순위: Emami(I7·I10) > Wagner 주파수·속도(I9) > Settles 박리 길이(I4) > Trapier(정성만, 후순위). 추출값은 CSV로 저장하고 불확도를 함께 적음 | Code(스크립트) + User(축 눈금 육안 확인) | 각 단계 직전 |
| 6 | 벽 조건 미확인(Settles, Emami, Trapier) | 원문에서 확인. 못 찾으면 가정(단열/등온)을 사용자가 정하고 케이스 설정에 기록(규칙 1) | Science(원문 확인) → User(가정 결정) | I4, I7 전 |
| 7 | Wieting 쐐기각 12.5°(Table 11은 10°) | NTRS PDF를 내려받아 Table 11·그림 82·본문 3.x절을 직접 확인. 일치하면 케이스 설정에 근거 기록 | Code | **완료 2026-11-10: 12.5° 맞음.** 근거 `docs/checks/wieting_wedge_angle.md`. 새로 나온 점: 본문 최대 열전달 증폭 10.14 vs 부록 E 표 9.52 (원인 판단 불가 → 검증 기준은 표 값 9.52만 사용, 본문 10.14와 섞어 인용하지 않음) |
| 8 | I4 성공 기준 정량화 | TMR 2DZPH `cf_vandriestII.dat`, Duan M6Tw076 대비 C_f·2St/C_f 오차 허용치를 사용자가 정함. 제안 값은 Code가 첫 실행 결과를 보고 제시 | User 결정 | I4 시작 때 |
| 9 | 선행연구 범위(영어 DB 위주) | I18 전에 Science가 중국어 학술지·학위논문 보강 검색. 결론의 "없음"은 그때까지 잠정 표기 | Science | I18 전 |
| 10 | I9 차별점 | Galaktionov 외(2019)의 방법과 겹침을 인정하고 마하 간격·초기장 민감도 보고를 I9 성공 기준에 추가 제안 | User 승인 → Code | I9 전 |

원칙: 위 1·10은 plan.md(계획 변경)에 해당하므로 사용자 승인 전에는 plan.md를 고치지 않는다.

## D-007 OpenFOAM v2512 설치·HiSA 빌드 확인 (2026-11-10)
- (번호 정정: 원래 D-006으로 적혔으나 I1 후속 처리안과 겹쳐 D-007로 바꿈)
- 사용자가 별도 터미널에서 `openfoam2512-default`, `openfoam2512-dev` (2512.0-2) 설치. 2412와 병존. D-002는 선택지 (a)로 해소.
- HiSA `validated-v2512`(커밋 271b449)를 v2512에서 `./Allwmake -j 8`로 빌드: 오류 0건, `hisa` 등 설치됨
  (`~/OpenFOAM/toto-v2512/platforms/linux64GccDPInt32Opt/`). 로그 `docs/benchmarks/I2_build.log`
  (`wmkdepend parse error ... setSolidFields.H`는 의존성 스캔 경고, 링크에 영향 없음).
- **HiSA 비정상 지원 실행 확인:** `examples/forwardStep`(fvSchemes `dualTime rPseudoDeltaT CrankNicolson 0.9`, `adjustTimeStep no`, deltaT 0.005)이
  t=4까지 오류 없이 종료. D-004(소스 정적 확인)를 실행으로 뒷받침. 비정상 솔버는 후보 2개 모두 사용 가능; 최종 선택은 I2 속도 실측 후.

## D-008 비정상 솔버 선택 자료 — 제안, 승인 대기 (2026-11-10)
- plan.md 표: 비정상 솔버는 "rhoCentralFoam, 또는 HiSA가 비정상을 지원하면 HiSA, I2에서 결정". HiSA 비정상은 지원 확인됨(D-004, D-007).
- 실측(`docs/benchmarks/I2.md`, 19.8만 셀 무점성 forwardStep, np 4): 물리시간 1 s당 rhoCentralFoam ≈ 280 s, HiSA(이중 시간) ≈ 4,000 s. HiSA ≈ 14배 비쌈.
- 이 비교의 한계: 무점성·층류. I9·I10은 벽 격자(y+ ≤ 5) 포함 점성 계산이라, 얇은 셀에서 명시적 rhoCentralFoam의 dt가 크게 줄 수 있음. 이 예제만으로 결론 내리지 않음.
- 제안: I9 직전에 실제 흡입구 격자(또는 근사 격자)에서 두 솔버의 물리시간당 비용을 한 번 더 재서 결정. 그때까지 둘 다 후보 유지. 사용자 승인 필요.

## D-009 MPI 프로세스 수 — 제안, 승인 대기 (2026-11-10)
- CLAUDE.md 환경 항목은 "로컬 실행은 MPI 8 프로세스". 실측상 np 8은 np 4와 속도가 같고 효율 41~43%.
- 제안: 8은 상한으로 읽고, 기본값은 np 4로 한다. 최적(np 5~7)을 알려면 np 6 실측 필요 — 사용자가 요청할 때만 수행.
