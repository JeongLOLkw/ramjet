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
- 남은 문제: (해소 2026-11-10) `.wslconfig` memory는 10GB 유지로 결정(D-003), 문서의 12GB를 10GB로 고침
- 소요: 벽시계 수 분 / 클라우드 $0 / /usage 미기록 (사용자 확인: 이번 단계 기록 안 함)

## I2 — 설치·속도 실측 (2026-11-10) — 완료 (np 6 추가 실측 포함)
- 모델·노력·UT: 계획상 Sonnet 5.5 · 중간 · UT X. **실제 실행 모델은 Haiku 5.5** (배정과 다름)
- 한 일:
  1. 환경 점검 (아래 기록)
  2. 저장소 골격: §7 구조 생성, `CLAUDE.md`(계획 §2 복사), `docs/plan.md`·`docs/science_prompt_I1.md` 이동, `.gitignore`, 본 파일 생성, `git init`
  3. HiSA 소스 clone(`~/src/hisa`, 태그 validated-v2512) 및 기능 정적 확인 → decisions.md D-004
  4. conda 환경 `inlet` 생성 (numpy, scipy, matplotlib, pyvista, fluidfoam, pytest; `PYTHONNOUSERSITE=1` 필요)
  5. 사용자가 v2512 설치 → HiSA 빌드(오류 0건)
  6. forwardStep 예제 2종 실행 완료 (아래 결과). 밀도장 그림: `docs/benchmarks/I2_forwardStep_*.png`
  7. `src/foam_reader.py` + `tests/test_foam_reader.py`(pytest 4개 통과 후 구현), `scripts/plot_forwardstep.py`
  8. 속도 실측: `scripts/bench.py`(+`src/bench_tools.py`, pytest) · `scripts/run_bench_sweep.sh`. 19.8만 셀, 두 솔버 같은 격자, np 1/2/4/8. 결과 `docs/benchmarks/I2.md`, 원자료 `I2_raw.csv`, 케이스 설정 `I2_cases/`
  9. 점검 후 `I2.md` 작성(속도표·I7 예상 시간·메모리 판정), 본 항목 갱신
  10. (2026-11-10 후속) 사용자 승인 반영 후 np 6 실측: `scripts/run_bench_np6.sh`(커밋 a401a66). rcf 0.0744 s/스텝(np 4 0.063, np 8 0.066), HiSA 8.82 s(np 4 8.55, np 8 8.15) — **np 6이 np 4·8보다 느림.** 기본 np = 4 확정(D-009). `I2.md` 표·관찰·한계 갱신
  11. 결정 문서 반영: D-003(10 GB 유지), D-006 #1·#10, D-008, D-009 승인 기록. `CLAUDE.md`·`docs/plan.md`의 WSL 12→10 GB, MPI "8" → "최대 8·기본 4", `plan.md` §6 I9 기준 추가와 검증 자료(Reinartz→Emami) 각주
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
  - [x] forwardStep(rhoCentralFoam)과 HiSA 예제 오류 없이 종료 — rhoCentralFoam 직렬 6,694스텝 123 s(1.6만 셀);
        HiSA 4 MPI 437 s(3.7만 셀). 두 해 모두 Mach 3 forward step의 활꼴 충격파·Mach stem·반사 구조. 셀 수·해상도가 달라 두 해의
        정량 비교(밀도 최대 6.5 vs 8.2)는 하지 않음 — 검증이 아니라 '실행 확인'
  - [x] `docs/benchmarks/I2.md` MPI 1/2/4/8 속도표 + I7 예상 시간 — 작성. 단 I7 시간은 **가정 기반 추정**(정상 모드 미실행, 반복 수·난류 비용 미측정): 12점 합계 7~54 h
  - [x] HiSA 비정상 지원 여부 `decisions.md` 기록 — D-004, D-007 (소스 + 예제 실행)
  - [x] WSL 최대 메모리 10 GB 이내 — 통과. 최대 RSS 합 1.32 GB, 가용 최저 6.75 GB (19.8만 셀)
  - [x] 커밋 — 이 항목과 함께 커밋
  - 속도 요약(np 4 기준): rhoCentralFoam 0.063 s/스텝, HiSA 8.55 s/스텝(가상 시간 반복 21회). 물리시간당 HiSA가 약 14배 비쌈(무점성 예제 한정). **np 4 이상은 빨라지지 않음**: np 6(rcf 0.0744, HiSA 8.82 s)이 np 4·np 8보다 느리고 np 8은 np 4와 거의 같다(효율 41~43%). 원인은 측정하지 않음. np 5·7은 미측정(하지 않기로 함)
- 남은 문제:
  1. (해소) OpenFOAM v2512 설치됨
  2. (부분 해소) 속도 실측 완료. 한계: HiSA 12스텝·1회, 정상 모드·난류 미실행(I4에서 측정), 배터리 모드 미측정
  3. (해소) `.wslconfig` 10 GB 유지, 문서 정정 (D-003)
  4. (해소) 계획 모순(12 GB vs 10 GB) — 10 GB로 통일
  5. (해소) 비정상 솔버 선택은 I9 직전 실제 흡입구 격자로 재측정해 결정, 그때까지 둘 다 후보 (D-008 승인)
  6. (해소) MPI 기본 np 4, 8은 상한 (D-009 승인, np 6 실측으로 확인)
  7. 사용자 몫: `git push` (자격증명 필요)
- 환경 변경 기록: I1b 점검용으로 `inlet` conda 환경에 `pypdf`를 `pip install`함(PDF 텍스트 추출용, 저장소 코드는 쓰지 않음)
- 소요: 벽시계 — 기록 안 함(사용자 결정; 속도 스윕 자체는 약 18분, np 6 추가 실측은 약 3분) / 클라우드 $0 / /usage 기록 안 함(사용자 결정)

## I1 — 문헌·검증 자료 (2026-11-10) — 산출물 도착, Claude Code 점검 완료
- 모델·노력·UT: 계획상 Fable 5.2 · 높음 (Claude Science). 산출물은 Claude Science가 작성, 점검은 Claude Code(Sonnet 5.5)
- 한 일: Science 산출물 4개 + Wieting RUN 21 CSV 2개를 `docs/`에 반입, Claude Code가 독립 점검
- 결과:
  - `references.md` · `validation_data.md` · `prior_work.md` · `exercises.md` · `wieting1987_run21_cylinder*.csv`
  - 연습 문제 7개 답을 Python으로 재계산 → 모두 일치 (정체조건, 수직충격파, θ-β-M, Kantrowitz, 회복온도, Van Driest II→St, Waltrup–Billig)
  - Wieting SI 환산, Wagner·Settles p₀/T₀ 환산, CSV의 q/Q₀↔W/m² 환산 일치
  - 문서에 적힌 DOI 50개를 Crossref로 조회 → 전부 실재, 제목·연도 일치
- 남은 문제 (해결안은 decisions.md D-006):
  1. (해소 2026-11-10) 검증 케이스 교체(Reinartz → Emami TP-3502) 사용자 승인, plan.md 반영. 열유속 검증은 Häberle & Gülhan 전문 확보 후 채택 여부 결정
  2. 서지 미확인: Anderson MCF 판본, Van Wie 장 저자, Edney FFA 보고서 번호, Celik 외 저자, Waltrup–Billig 계수 50·170 원문 확인
  3. 디지털 자료 없음(디지타이저 필요): Settles 24°, Emami 압력, Wagner, Trapier
  4. 벽 조건 미확인: Settles, Emami, Trapier
  5. (해소 2026-11-10) Wieting 쐐기각 12.5° — NTRS 원문 쪽 이미지로 확인 완료. 새 문제: 본문 최대 열전달 증폭 10.14 vs 부록 E 표 9.52 (원인 판단 불가, 표 값 사용)
  6. I4 정량 허용치는 사용자 결정
  7. 선행연구 조사는 영어권 DB 위주 (중국어 학술지·학위논문 미포함)
- 후속 (2026-11-10):
  - Claude Code 담당 2건 완료: (1) `docs/checks/wieting_wedge_angle.md` — 12.5° 확인, CSV 열유속 49행·압력 24행 전부 원문 표와 대조해 불일치 0건. (2) `scripts/digitize.py` + `tests/test_digitize.py` (테스트 먼저, 변이 6종으로 테스트 강도 확인, 전체 pytest 37개 통과). 실제 논문 그림에는 아직 미적용(PDF 없음)
  - `validation_data.md` §3의 런 번호 서술을 원문에 맞게 정정 (15°는 런 27–30, 런 23은 없음, δ=10 인쇄는 런 10–30만)
  - Science 후속 프롬프트 `docs/science_prompt_I1b.md` 작성(PDF 첨부 없는 조건). 결과 대기
  - Science 후속 결과 `docs/i1b_followup.md` 도착(2026-11-10). 요약: Waltrup–Billig 원형 덕트 식 확인·직사각 변형 불일치, 서지 3/4 확인, 중국어권 선행연구 못 찾음
  - **Code 독립 점검 완료(2026-11-10)** — `docs/checks/i1b_check.md`: (1) 숫자 11항목 재계산 전부 일치 (2) DOI 11개 Crossref 실재·제목·연도 일치 (3) 로컬 PDF 원문 대조: Emami p.8·10·13(총온도·시험시간·단열/Pr=1 가정), Edelman 식 (7)·(8) 일치, Smart 파일은 PDF가 아닌 HTML 확인. 불일치 0건. 한계: 웹 문헌(Kitamura, Arakawa, Gillespie 등)의 식 렌더링과 2차 인용 건수는 재확인하지 않고 Science 표기를 [2차]로 유지
  - 확인된 서지 정정을 `references.md`(T1, R2, R3, R16)와 `validation_data.md`(Settles 벽 조건·경계층 위치 불일치 병기, Emami 벽 조건 "명시 없음" 확정)에 확인 수준을 붙여 반영. 벽 조건 선택 자체는 하지 않음(사용자 결정, I4·I7·I10 전)
  - 사용자 승인 2026-11-10: D-006 #1(Emami 교체), #10(I9 민감도 보고) → `plan.md` 반영
  - 사용자 PDF 접근 불가 → 유료 논문(Waltrup–Billig 원문, Häberle & Gülhan)은 공개 사본·독립 2차 인용으로만 확인
- 소요: 벽시계 수 분(점검) / 클라우드 $0 / /usage 미기록 (사용자 확인 필요)

## 오류 기록
- 없음
