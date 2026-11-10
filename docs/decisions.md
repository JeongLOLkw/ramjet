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

## D-003 `.wslconfig` 메모리 — **결정: 10 GB 유지 (사용자 승인 2026-11-10)**
- 계획 §8 전제는 `memory=12GB`였고 실제 값은 `memory=10GB`. 계획 §2 CLAUDE.md의 "WSL 12 GB"와 §8 성공 기준 "10 GB 이내"도 서로 달랐음.
- 결정: 현재 값 10 GB 유지. 근거: I2 실측 최대 RSS 합 1.32 GB(19.8만 셀)로 여유가 큼.
- 반영: `CLAUDE.md`, `docs/plan.md` §2 사본·§8 `.wslconfig` 예시의 12 GB → 10 GB (같은 날 커밋). `.wslconfig`는 건드리지 않음.
- 재검토: I4 이후 점성·난류 케이스에서 메모리를 다시 측정(I2.md 메모리 절).

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

## D-006 I1 후속 처리안 — #1·#10 승인 (2026-11-10), 나머지 진행 중
- **승인 2026-11-10**: #1(검증 케이스 Reinartz → Emami TP-3502) → `docs/plan.md` §6 각주에 반영. #10(I9에 마하 간격·초기장 민감도 보고 추가) → `docs/plan.md` §6 I9 행에 반영.
- #7은 이미 완료. #3·#6의 일부는 I1b 후속(`docs/i1b_followup.md`)으로 확인 수준이 올라갔고 Code 점검은 `docs/checks/i1b_check.md`. 벽 조건 선택(#6)은 아직 사용자 결정 전 — I4(Settles), I7·I10(Emami, Wagner, Trapier) 시작 때 묻는다.
- 아래 표는 제안 당시 원문이다.

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

## D-008 비정상 솔버 선택 — **승인: I9 직전으로 연기, 그때까지 둘 다 후보 (사용자 승인 2026-11-10)**
- plan.md 표: 비정상 솔버는 "rhoCentralFoam, 또는 HiSA가 비정상을 지원하면 HiSA, I2에서 결정". HiSA 비정상은 지원 확인됨(D-004, D-007).
- 실측(`docs/benchmarks/I2.md`, 19.8만 셀 무점성 forwardStep, np 4): 물리시간 1 s당 rhoCentralFoam ≈ 280 s, HiSA(이중 시간) ≈ 4,000 s. HiSA ≈ 14배 비쌈.
- 이 비교의 한계: 무점성·층류. I9·I10은 벽 격자(y+ ≤ 5) 포함 점성 계산이라, 얇은 셀에서 명시적 rhoCentralFoam의 dt가 크게 줄 수 있음. 이 예제만으로 결론 내리지 않음.
- 제안: I9 직전에 실제 흡입구 격자(또는 근사 격자)에서 두 솔버의 물리시간당 비용을 한 번 더 재서 결정. 그때까지 둘 다 후보 유지. 사용자 승인 필요.

## D-009 MPI 프로세스 수 — **승인 (사용자 2026-11-10): 8은 상한, 기본값은 실측 최적 = np 4**
- CLAUDE.md 환경 항목은 "로컬 실행은 MPI 8 프로세스". 실측상 np 8은 np 4와 속도가 같고 효율 41~43%.
- 승인 후 np 6 실측 수행(같은 날, `scripts/run_bench_np6.sh`): rcf 0.0744 s/스텝(np 4 0.063, np 8 0.066), HiSA 8.82 s(np 4 8.55, np 8 8.15). np 6이 가장 느리다. → np 4 확정. 상세 `docs/benchmarks/I2.md`.
- HiSA는 np 8이 np 4보다 5% 빠르나 12스텝·1회 측정의 차이이고 메모리·코어 점유가 더 크다. np 8을 쓰고 싶은 단계(I6 등)는 그 단계에서 짧게 재측정한 뒤 정한다.
- 반영: `CLAUDE.md`·`docs/plan.md` §2 사본의 "MPI 8 프로세스" → "최대 8, 기본 4".

## D-010 I3 솔버 검증 A — 케이스 설정과 판정 기준 (실행 전 고정, 2026-11-10)
사용자 지시("물을 것이 생기면 알아서 판단")에 따라 Claude Code가 정함. 아래 기준은 **본 실행 전에** 적었고 결과를 보고 바꾸지 않는다.
- **기체**: 열량적 완전기체 공기, `src/constants.py`(이번에 신설): γ = 1.4, M_air = 28.9644 kg/kmol(US Std Atm 1976),
  RR = OpenFOAM v2512 값(1e3·NA·k) → R = 287.05 J/(kg·K), Cp = γR/(γ−1). 전진 계단만 Woodward–Colella 무차원 기체(R = 1/γ, 같은 γ).
  Sutherland 계수는 I4(첫 점성 케이스)에서 승인 받아 추가 — 지금은 넣지 않음.
- **수치 설정 = 튜토리얼/예제 기본값 그대로**(새로 고른 계수 없음). rcf: Kurganov, vanLeer(V), Euler, maxCo 0.2 (v2512 `rhoCentralFoam/shockTube`, `forwardStep`).
  HiSA: AUSMPlusUp, wVanLeer; 비정상 dualTime CN 0.9(`examples/shockTube`, `forwardStep`의 fvSolution 그대로, forwardStep은 음향 Co ≈ 2.4 유지하도록 dt만 격자에 비례),
  정상 `bounded dualTime steadyState` + 국소 시간 간격(`examples/flatPlate`에서 점성·난류 항목만 뺌, pseudoCoNum 10→200은 예제 값 = 사전 승인 (a)·(d)에 해당).
  이 설정을 I4 이후 템플릿 기준으로 삼을지는 별도 사용자 결정.
- **경계**: 초음속 유입 고정값, 출구 p zeroGradient·U/T inletOutlet(압력 지정 없음, 규칙 6), 비점성 벽 = slip
  (HiSA는 예제와 같은 `characteristicWallPressure/Temperature`), 위·아래 경계 symmetryPlane. 초기장 = 균일 자유류(사전 승인 (c)).
- **케이스**: `scripts/i3_cases.py`가 생성.
  - Sod(Toro 2009 Test 1, SI 환산 ρL 1, pL 1e5 / ρR 0.125, pR 1e4, t = 0.2/√(pL/ρL)): rcf N 100~1600(5단계), HiSA N 100~800(4단계)
  - 쐐기 A: M 2.5 / 15°(I1 연습 3), B: M 5 / 10° — n = 50, 100, 200 × 두 솔버
  - 팽창 코너 A: M 2.5 / 15° — n = 50, 100, 200 × 두 솔버
  - 전진 계단(Woodward & Colella 1984, M 3, t = 4): rcf Δ = 1/40, 1/80, 1/160, HiSA 1/80, 1/160 (같은 blockMesh → 셀 단위 비교 가능)
- **판정 기준**:
  1. 쐐기(plan §6): **최세 격자 n200**, 두 솔버 모두 β와 p₂/p₁가 이론(NACA 1135 식 138, `src/gasdynamics.py`)과 1% 이내.
     β = 0.3 ≤ x ≤ 0.95 열마다 p 중간값(벽 셀과 맨 위 셀 평균) 교차점을 선형 보간 → 직선 맞춤. p₂/p₁ = 충격파 아래 5셀 이상 떨어진 셀 평균.
  2. 충격파관(plan §6 "격자 세분화에 따라 해석해에 수렴"): 밀도 L1 오차(정확 리만 해, Toro 2009 4장)가 **모든 세분화 단계에서 단조 감소**하고
     **최세 두 단계 관측 차수 ≥ 0.5**. 두 솔버 모두.
  3. 팽창 코너(§6에 기준 없음 → 쐐기와 같은 1% 적용): 최세 격자에서 M₂, p₂/p₁가 Prandtl–Meyer 이론과 1% 이내.
     표본 영역: 모서리 기준 0.6 ≤ r ≤ 1.1, 벽+1° ≤ ψ ≤ 이론 후방 마하선 − 3Δ/r.
  4. 정상 판정(규칙 5를 검증 케이스에 맞게 적용): 위 지표(β·p₂/p₁ 또는 M₂·p₂/p₁)가 마지막 2,000 스텝 동안 0.2% 이내 + 유입/유출 질량 유량 불균형 0.5% 미만.
     통과 못 한 케이스의 수치는 '수렴'으로 보고하지 않음.
  5. 전진 계단(해석해 없음 → 강건성·일관성 확인): 모든 격자가 t = 4까지 p, T > 0으로 완주; rcf 3격자에서 활꼴 충격파 이격 거리(y ≈ 0.1)와
     위 벽 충격파 위치의 격자 간 차이가 줄어듦(|세−중| ≤ |중−조|). rcf–HiSA 같은 격자 밀도 L1 차이와 계단 앞면 평균 압력 vs Rayleigh 피토압은 **정보로만** 보고(통과 기준 아님).
- 실행: 직렬 케이스를 동시에 최대 4개(코어 4개, D-009 기본 4와 같은 점유).

## D-011 I3 Sod 불합격 → 2차 시도 설정 (실행 전 기록, 2026-11-10)
- **1차 결과(D-010 설정, 기록 보존)**: Sod 밀도 L1이 단조 감소하지 않음 → 기준 2 **불합격**(두 솔버, 같은 원인 계수 1회째).
  rcf N800→N1600에서 1.92e-3 → 3.08e-3, HiSA N400→N800에서 2.06e-3 → 2.45e-3.
- **원인 진단(스크래치 복사본, 케이스 설정 불변)**:
  - rcf: 접촉면–충격파 사이 압력 진동이 시간에 따라 **성장**(N1600: t = 0.13 ms ±1.8% → 0.63 ms ±15%; N800 최종 ±5%).
    maxCo 0.1 → ±0.3%에서 멈춤(L1 5.1e-4), Tadmor flux → ±0.4%(6.5e-4), 1차 upwind → 진동 없음(3.1e-3).
    판단: Kurganov + vanLeer 재구성 + 전진 Euler 시간 적분이 maxCo 0.2에서 안정 한계를 넘는 모드가 있음(확신도 중 — 변형 실험 근거, 이론 증명 없음).
  - HiSA: 내부 반복 허용오차 `pseudoTol 1e-4`(examples/shockTube 값)로 대부분 스텝이 2~5회에 '수렴' 처리되어 평탄 영역 압력이 −2% 치우침.
    `1e-6` → 치우침 ≈ 0, L1 2.45e-3 → 1.12e-3(모든 스텝 20회 안에 수렴). CN 0.9 → 0(Euler 암시)은 개선 없음(3.09e-3).
- **2차 시도(Claude Code 판단, 사용자 위임에 따름)**: 공간 이산화(flux, 리미터, 재구성)는 그대로 두고
  rcf는 **maxCo 0.2 → 0.1**(CFL 축소 = 사전 승인 (a)와 같은 계열), HiSA는 **pseudoTol 1e-4 → 1e-6**(내부 반복을 더 정확히 풂; 규칙 1의 계수 목록에 없음, 소산을 더하지 않음).
  어느 쪽도 인공 점성·리미터를 키워 진동을 감추는 변경이 아님. 판정 기준(D-010)은 바꾸지 않는다.
  - 케이스: `sod/rcf_co01_N*`, `sod/hisa_tol6_N*`(1차와 같은 격자), 전진 계단 `forwardStep/rcf_co01_dx40·80·160`(rcf 비정상 해가 같은 문제를 갖는지 확인),
    `forwardStep/hisa_tol6_dx80`(예제 pseudoTol 5e-3에 대한 민감도, 정보용).
  - 쐐기·팽창 코너(정상 해)는 1차에서 기준 통과·정상 판정 통과 → 재실행하지 않음.
- 이 설정을 이후 비정상 템플릿(I9·I10) 기본값으로 쓸지는 **사용자 결정** 사항으로 남긴다.
