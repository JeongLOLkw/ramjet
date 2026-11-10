# Claude Science 프롬프트 — 흡입구 실험 I1 (문헌·검증 자료)

아래 전체를 Claude Science에 붙여 넣는다.

---

나는 OpenFOAM으로 램·스크램제트 흡입구 하나를 마하 0.6~7로 스윕하며 시동·불시동, 히스테리시스, 의사충격파열·버즈, 벽면 열유속을 계산하는 개인 탐구 프로젝트를 한다. 계산은 별도로 Claude Code가 진행하고, 너에게는 그 전에 필요한 **문헌 확인과 검증 자료 준비(I1 단계)**를 맡긴다.

## 연구 개요
- 형상: 2D 혼합압축 흡입구(외부 램프 2단, 카울, 일정 단면 아이솔레이터), 설계 마하 약 5
- 솔버: OpenFOAM ESI v2512, HiSA(정상), rhoCentralFoam(비정상), k-ω SST, 완전기체
- 질문: (Q1) 마하 구간별 유동 구조·성능 (Q2) 시동 경계 vs Kantrowitz 한계, 히스테리시스 (Q3) 스로틀링 시 의사충격파열 → 버즈 → 불시동 (Q4) Edney IV·SBLI·천이에 따른 열유속 정점 (Q5) 열 질식과 이중 모드 전이

## 할 일

### 1. 참고문헌 서지 확인 → `references.md`
아래 목록은 기억으로 정리한 것이라 틀릴 수 있다. 각 항목의 정확한 저자, 연도, 제목, 학술지·권·쪽(또는 보고서 번호), DOI 또는 NASA NTRS 링크를 확인해라. 존재가 확인되지 않거나 내용이 다르면 그렇게 표시하고, 같은 목적에 맞는 대체 문헌을 제안해라.

- 교과서: Anderson *Modern Compressible Flow*, Anderson *Hypersonic and High-Temperature Gas Dynamics*, Heiser & Pratt *Hypersonic Airbreathing Propulsion*, Segal *The Scramjet Engine*, Seddon & Goldsmith *Intake Aerodynamics*
- Kantrowitz & Donaldson (1945) NACA 보고서 — 흡입구 시동 한계
- Van Wie 외, 스크램제트 흡입구 장(Curran & Murthy 편 *Scramjet Propulsion*)
- Edney (1968) — 충격파 간섭 6유형
- Waltrup & Billig (1973) — 의사충격파열 길이 상관식
- Settles, Fitzpatrick & Bogdonoff (1979) — 압축 코너 SBLI
- Wieting & Holden (1989) — 충격파 간섭 가열
- Emami 외 (1995) NASA TP-3502 — 이중 모드 아이솔레이터
- Reinartz 외 (2003) — 극초음속 흡입구
- Trapier, Duveau & Deck (2006) — 초음속 흡입구 버즈
- Wagner 외 (2009) — 마하 5 흡입구 불시동
- Kurganov & Tadmor (2000), Greenshields 외 (2010, rhoCentralFoam), Menter (1994, SST), Langtry & Menter (2009), Roache (1994)·Celik 외 (2008, GCI)

### 2. 검증 데이터 조건 추출 → `validation_data.md`
아래 검증 케이스마다, 계산을 그대로 설정할 수 있을 만큼의 조건을 표로 뽑아라: 자유류 마하수, 정체압·정체온도(또는 정압·정온), 단위 레이놀즈수, 벽 온도 조건(등온 값 또는 단열), 형상 치수, 측정 항목(벽압, 마찰, 열유속, 박리 길이, 주파수), 수치 데이터 공개 여부(표·디지털 파일·그림만).

| 케이스 | 쓰는 단계 |
|---|---|
| 압축성 평판 난류 경계층(마찰·열유속 기준 자료, Van Driest II 비교용) | I4 |
| 24° 압축 램프 (Settles 계열) | I4 |
| 원통·카울 립 충격파 간섭 가열 (Wieting & Holden 계열) | I11a |
| 2D 램프형 극초음속 흡입구 (Reinartz 계열) | I7, I11a |
| 마하 5 흡입구 불시동 (Wagner 계열) | I9, I10 |
| 초음속 흡입구 버즈 (Trapier 계열) | I10 |

NASA Turbulence Modeling Resource, NASA NTRS, AGARD·NATO RTO 보고서 등 공개 검증 데이터베이스에 이미 정리된 자료가 있으면 우선 알려줘라. 그림에서만 값을 얻을 수 있으면 "디지타이저 필요"로 표시해라.

### 3. 선행연구 점검 → `prior_work.md`
- 하나의 흡입구를 아음속부터 극초음속까지 연속으로 스윕하며 시동·불시동 경로와 열유속을 함께 다룬 연구가 있는지 찾아라. 있으면 무엇이 다르고 내 계획의 차별점이 남는지 판단해라.
- OpenFOAM(rhoCentralFoam, HiSA 등)으로 스크램제트 흡입구 시동·불시동이나 버즈를 계산한 사례를 3~5건 찾아, 격자 규모·난류 모델·경계조건 처리(특히 배압·스로틀링 방법)를 정리해라.
- HiSA가 시간 정확 비정상 계산(이중 시간 간격 등)을 지원하는지 문헌·문서에서 확인되면 근거와 함께 적어라.

### 4. 손계산 연습지 → `exercises.md`
아래 7개 식으로 연습 문제를 하나씩 만들고(값은 이 프로젝트 조건에서), 풀이와 답을 접어 둘 수 있게 문제 아래에 따로 적어라.
1. 정체온도·정체압력 (고도 25 km, M 6)
2. 수직충격파 후 마하수·압력비
3. θ-β-M 관계 (M 2.5, θ 15°의 약한 충격파 β)
4. Kantrowitz 한계와 등엔트로피 한계 (M 2, 4, 6에서 A_t/A_i)
5. 회복온도 (층류·난류 회복계수)
6. 레이놀즈 유사로 C_f에서 Stanton 수 추정
7. Waltrup–Billig 의사충격파열 길이(분모는 √(D·θ))

## 규칙
- 존재를 확인하지 못한 문헌·수치를 만들어내지 마라. 확인 못 한 것은 "미확인"으로 적는다.
- 각 주장 옆에 출처 링크를 단다. 전문을 못 읽고 초록만 봤으면 그렇게 표시한다.
- 원문 문장을 길게 옮기지 말고 요약한다.
- 수식은 단위를 확인하고, 연습 문제 답은 직접 계산해 검산한다.
- 결과는 위 4개 Markdown 파일로 내고, 끝에 "계획에 반영할 점" 3~5줄을 따로 적어라(예: 검증 케이스 교체, 성공 기준 수정).
