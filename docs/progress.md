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
  5. 사용자가 v2512 설치 → HiSA 빌드(오류 0건)
  6. forwardStep 예제 2종 실행 완료 (아래 결과). 밀도장 그림: `docs/benchmarks/I2_forwardStep_*.png`
  7. `src/foam_reader.py` + `tests/test_foam_reader.py`(pytest 4개 통과 후 구현), `scripts/plot_forwardstep.py`
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
  - [ ] `docs/benchmarks/I2.md` MPI 속도표 — 미작성
  - [x] HiSA 비정상 지원 여부 `decisions.md` 기록 — D-004, D-006 (소스 + 예제 실행)
  - [ ] WSL 최대 메모리 10 GB 이내 — 현재 설정 10 GB, 판정은 실측 후
  - [ ] 커밋 — 진행 중(속도 실측 후 최종)
- 남은 문제:
  1. (해소) OpenFOAM v2512 설치됨
  2. 속도 실측(20만 셀, MPI 1/2/4/8) 미실시 — 다음 작업
  3. `.wslconfig` memory 10 GB vs 계획 12 GB 불일치
  4. 계획 자체 모순: §2 CLAUDE.md "WSL 12 GB" vs §8 성공 기준 "10 GB 이내"
- 소요: 벽시계 — / 클라우드 $0 / /usage — 기록 예정

## I1 — 문헌·검증 자료 (2026-11-10) — 산출물 도착, Claude Code 점검 완료
- 모델·노력·UT: 계획상 Fable 5.2 · 높음 (Claude Science). 산출물은 Claude Science가 작성, 점검은 Claude Code(Sonnet 5.5)
- 한 일: Science 산출물 4개 + Wieting RUN 21 CSV 2개를 `docs/`에 반입, Claude Code가 독립 점검
- 결과:
  - `references.md` · `validation_data.md` · `prior_work.md` · `exercises.md` · `wieting1987_run21_cylinder*.csv`
  - 연습 문제 7개 답을 Python으로 재계산 → 모두 일치 (정체조건, 수직충격파, θ-β-M, Kantrowitz, 회복온도, Van Driest II→St, Waltrup–Billig)
  - Wieting SI 환산, Wagner·Settles p₀/T₀ 환산, CSV의 q/Q₀↔W/m² 환산 일치
  - 문서에 적힌 DOI 50개를 Crossref로 조회 → 전부 실재, 제목·연도 일치
- 남은 문제 (해결안은 decisions.md D-006):
  1. 검증 케이스 교체 제안(Reinartz → Emami TP-3502; 열유속은 Häberle & Gülhan 전문 확보 후) — 계획 변경이라 승인 필요
  2. 서지 미확인: Anderson MCF 판본, Van Wie 장 저자, Edney FFA 보고서 번호, Celik 외 저자, Waltrup–Billig 계수 50·170 원문 확인
  3. 디지털 자료 없음(디지타이저 필요): Settles 24°, Emami 압력, Wagner, Trapier
  4. 벽 조건 미확인: Settles, Emami, Trapier
  5. Wieting Table 11 쐐기각 오식 판단(12.5°) — 원문 PDF로 재확인 필요
  6. I4 정량 허용치는 사용자 결정
  7. 선행연구 조사는 영어권 DB 위주 (중국어 학술지·학위논문 미포함)
- 소요: 벽시계 수 분(점검) / 클라우드 $0 / /usage 미기록 (사용자 확인 필요)

## 오류 기록
- 없음
