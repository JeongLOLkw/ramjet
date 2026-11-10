# prior_work.md — 흡입구 실험 I1: 선행연구 점검

작성: Claude Science · 2026-11-10 · 대상: `docs/science_prompt_I1.md` §3

조사 방법: OpenAlex 키워드 검색 16회, 웹 검색 4회, Crossref/NTRS 서지 조회. 찾은 문헌은 초록(OpenAlex)으로 1차 판정했고, 공개 전문은 읽었다. 표기: [전문] · [초록] · [검색 요약] = 검색 결과에 나온 문단만 봄 · [제목] = 제목만 확인.
**한계**: 영어권 색인 DB 위주라서 중국어 학술지(예: 推进技术, 航空学报 국문판)와 학위논문은 거의 다루지 못했다. 아래 "차별점" 판단은 이 범위 안에서만 유효하다.

---

## 1. 하나의 흡입구를 연속 스윕하며 시동·불시동 경로와 열유속을 함께 다룬 연구가 있는가

### 1a. 가장 가까운 선행연구

| 연구 | 무엇을 했나 | 이 프로젝트와의 차이 | 수준 |
|---|---|---|---|
| Galaktionov, Yang, Wu, Ni, Le, EUCASS 2019, "The numerical simulation techniques research and preliminary experimental validation of the start characteristics for a two-dimensional hypersonic inlet" https://doi.org/10.1051/eucass/201911729 | 2D 극초음속 흡입구의 **시동·불시동 히스테리시스 루프**를 얻으려고 마하수를 단계적으로 올리고(불시동 → 시동) 내리며(시동 → 불시동), 초기장(균일 유입, 정지장, 직전 수렴해)과 마하 간격에 따른 차이를 비교. 예비 실험 검증 포함. 자체 코드 AHL3D(CARDC) | **I9의 방법(직전 마하 해로 초기화하는 연속 추적)과 거의 같다.** 열유속은 초록에 없음. 마하 범위 미확인(극초음속 구간으로 보임) | [초록] |
| Wu, Yu, He, Le, *J. Appl. Fluid Mech.* 13(6), 2020, "Self-starting Simulation of a Hypersonic Inlet with Variable Free Stream Condition" https://doi.org/10.36884/jafm.13.06.31389 | 가속 궤적에서 불시동 → 시동 전이를 준정상·비정상 2D와 준정상 3D로 비교. 2D 준정상과 비정상이 같은 자기시동 마하수를 줌, 비정상은 공력 주기 변동을 포착 | 상승 방향만, 열유속 없음. **준정상 스윕이 자기시동 마하수 판정에 충분하다는 근거**로 I7·I9 계획을 뒷받침 | [초록] |
| Wang, Guo, *Chin. J. Aeronaut.* 26(3):563–571, 2013, "Numerical study of unsteady starting characteristics of a hypersonic inlet" https://doi.org/10.1016/j.cja.2013.04.018 | 설계 M 6.5 혼합압축 흡입구의 impulse start와 self start를 비정상 SST RANS로 계산. 자유류를 가속해 시동 마하수에 이를 때까지 입구 박리 기포가 유지됨 | 극초음속 한 구간, 열유속 없음 | [초록] |
| Van Wie, Kwok, Walsh, AIAA 96-2914, "Starting Characteristics of Supersonic Inlets" https://doi.org/10.2514/6.1996-2914 | M 3 직사각 흡입구 실험: 최대·재시동 수축비, hard/soft unstart, Kantrowitz 한계가 hard unstart 재시동 수축비를 예측 | 실험, 한 마하수. Q2(I8)의 이론 한계 비교 방식 근거 | [초록] |
| Tang, Xiong, Fan, Wang, *Appl. Sci.* 13(17):9752, 2023, "Self-Start Characteristics of Hypersonic Inlet When Multiple Unstart Modes Exist" https://doi.org/10.3390/app13179752 | 여러 불시동 모드(작은/큰 몸체 박리, 몸체+립 이중 박리)의 자기시동 경로가 다름을 실험으로 보임 | "고전적 이중해 이론"만으로는 히스테리시스가 설명되지 않는다는 근거 — I9 해석에 필요 | [초록] |
| Fu, Bose, Moin, *Theor. Comput. Fluid Dyn.* 36(2):345–368 (OpenAlex 출판연도 2021), "Prediction of aerothermal characteristics of a generic hypersonic inlet flow" https://doi.org/10.1007/s00162-021-00587-7 (arXiv:2009.02411) | 일반 극초음속 흡입구의 공력 가열 예측 | 초록을 받지 못함 — 단일 조건으로 보이나 **미확인** | [제목] |
| Wang, Wu, Li, Gao, *Thermal Science* 28(4A):2791–2804, 2024 https://doi.org/10.2298/TSCI230628279W | 벽 온도 Tw/T∞가 아이솔레이터 경계층·충격파열 위치·길이에 주는 영향 | 열 벽 조건이 의사충격파열을 바꾼다는 근거 → I11a 벽 조건 3종과 I10의 연결 고리 | [초록] |

### 1b. 판단
- 이번 조사 범위에서는 **마하 0.6(아음속)부터 7까지 하나의 흡입구를 연속으로 올리고 내리며, 시동·불시동 경로와 벽 열유속(특히 카울 립 Edney 간섭 위치 이동)을 같은 해 집합에서 함께 추적한 연구는 찾지 못했다.** 각 요소는 따로 존재한다: 히스테리시스 루프(Galaktionov 2019), 가속 자기시동(Wu 2020, Wang & Guo 2013), 불시동 모드(Tang 2023), 단일 조건 공력 가열(Fu 2021, Wieting 1987).
- 남는 차별점(주장 가능한 범위):
  1. 아음속·천음속(M 0.6–1.5)에서 극초음속(M 7)까지 **한 형상**에서 유동 구간 지도와 성능 곡선을 연속으로 그림.
  2. 시동 경로(상승·하강)와 열유속 정점 위치·크기 변화를 같은 해에서 짝지음 — 예: 불시동 시 카울 립 정점이 어떻게 이동하는가.
  3. 공개 코드(OpenFOAM v2512 + HiSA)와 재현 가능한 스크립트.
- 차별점이 아닌 것: "직전 마하 해로 초기화해 히스테리시스를 찾는 방법" 자체는 Galaktionov 외(2019)가 이미 썼다. I9 보고서는 이 문헌을 인용하고, 그들처럼 **마하 간격과 초기장에 대한 민감도**를 함께 보이는 것이 좋다.

---

## 2. OpenFOAM으로 스크램제트 흡입구 시동·불시동·버즈를 계산한 사례

| # | 연구 | 솔버·수치 | 난류 | 격자 | 경계조건·배압 방법 | 결과 | 수준 |
|---|---|---|---|---|---|---|---|
| 1 | Lee, J., Kang, S. H., *PLoS ONE* 14(11):e0224994, 2019 https://doi.org/10.1371/journal.pone.0224994 | rhoCentralFoam, 시간 1차 암시적 Euler, 중앙-풍상 KNP + van Leer 제한자, Sutherland 점성 | k-ω SST | 2D. 영역 1 약 23,000점, 영역 2 약 99,000점, 영역 3 약 81,000점. 격자 2배 시 결과 차이 작음 | Wagner 실험(M 4.9, p₀ 2.5 MPa, T₀ 330 K) 조건. 유입 경계층 19.05 mm를 이론 분포로 부여, 모든 벽 단열, 출구 초음속 유출 조건. **배압은 모형 끝 플랩 형상**(시동 시 완전히 접음) | 시동 유동 벽압은 실험·LES와 대체로 일치(SST가 경계층·재순환을 약간 과대). 불시동·buzz는 **노즐 출구 부근까지 포함한 확장 영역**이어야 재현됨(작은 영역은 유입 경계가 충격파 배출을 막음). buzz 127–151 Hz(유입 경계층 형태에 따라) vs 실험 약 124 Hz | [전문] |
| 2 | Lee, J., Lee, S. G., Kang, S. H., Namkoung, H.-J., *Aerospace* 9(3):162, 2022 https://doi.org/10.3390/aerospace9030162 | RANS 기반 OpenFOAM 솔버(솔버 이름은 초록에 없음, 검색 요약에는 rhoCentralFoam이 함께 언급됨) | 미확인 | 미확인 | 모형 후단 **플랩/플러그**로 배압(검색 요약) | 비진동 불시동 유동: 모형 출구 부근 압력 진폭·평균이 실험과 일치. 경계층 유동의 방향 전환과 벽 재순환이 질식 영역에 불규칙하게 작용 | [초록]+[검색 요약] (MDPI 서버가 자동 다운로드를 403으로 거부) |
| 3 | Arjun, P. A., Nagaraja, S. R., "Unstart Phenomenon in a Scramjet Engine Isolator," *Lecture Notes in Mechanical Engineering*, pp. 195–204, 2022 https://doi.org/10.1007/978-981-19-4388-1_18 | rhoCentralFoam(과도 해석) | 미확인 | 미확인 | 입구 램프 6/8/10/12° 아이솔레이터. 시동 유동을 세운 뒤 **출구를 부분적으로 닫아**(출구 일부 패치를 벽으로 전환) 배압 | 불시동 전파 속도·평균 불시동 속도, 아이솔레이터 끝 부근 압력 변동이 큼 | [검색 요약] |
| 4 | Balaji, V., Venkatasubbaiah, K., *Eur. J. Mech. B/Fluids* 114:204290, 2025 https://doi.org/10.1016/j.euromechflu.2025.204290 | rhoCentralFoam | 미확인 | 미확인 | **하류 연소기에 열 첨가**로 연소 유발 불시동을 재현(열 질식). 검증 케이스는 출구 압력 조건, 입구 M 1.61 | 열 첨가 배압과 아음속 박리 기포의 생성·상호작용이 불시동의 주원인, 높은 열유속이 불시동을 앞당김 | [검색 요약] — **Q5(I16)와 직접 관련** |
| 5 | Ruikar, M., Dongari, N., IIT Hyderabad 석사논문, 2019, "Numerical Analysis of a Scramjet Inlet using OpenFOAM" https://raiith.iith.ac.in/5589/ | rhoCentralFoam 기반 다화학종 수송 확장 솔버 | 미확인 | 미확인 | 정상 흡입구, 시동·불시동 아님 | 앞전 무딤 반경이 포획 유량·전압 회복·**벽 열유속**에 큰 영향 | [검색 요약] |

비교용(OpenFOAM 아님): Raja Sekar, Karthick, Jegadheeswaran, Kannan, *Phys. Fluids* 32(12), 2020, arXiv:2010.05004 https://doi.org/10.1063/5.0032740 — Ansys Fluent 압력 기반 연성 솔버, URANS SST, 2D 3-램프 혼합압축 M 5 흡입구, y⁺ < 1, 정밀 격자 1.1×10⁵ 셀, **출구 플러그 삽입으로 스로틀비 ζ = 0–0.7**, ζ ≤ 0.2 정상, ζ ≥ 0.3 강한 비정상 [전문]. (논문 번호는 확인하지 않았다 — 권·호만 OpenAlex로 확인.)

### 2a. 정리 — 이 프로젝트 설정에 주는 시사점
- 배압: 확인된 OpenFOAM 사례는 모두 **플랩·플러그·출구 부분 폐쇄** 같은 형상 스로틀을 썼다. CLAUDE.md 규칙 6과 맞는다. 하류 저항 영역(fvOptions) 방식으로 흡입구 불시동을 다룬 OpenFOAM 사례는 이번에 찾지 못했다(**미확인**).
- 계산 영역: buzz·불시동은 흡입구 **상류 자유류 영역을 충분히 넓게** 두어야 재현된다(Lee & Kang 2019). I10 격자 설계에 반영할 것.
- 격자: 2D 사례들은 10⁴–10⁵ 셀 규모. 계획의 I7 20만–40만 셀은 이보다 크다(y⁺ < 1 + 열유속 목적이면 타당).
- HiSA로 흡입구 시동·불시동·버즈를 계산한 문헌은 **찾지 못했다**.

---

## 3. HiSA의 시간 정확 비정상 계산(이중 시간 간격) 지원

| 근거 | 내용 | 수준 |
|---|---|---|
| HiSA User Guide (Heyns & Oxtoby, 2021-07 판) §2.3 `ddtSchemes` https://hisa.gitlab.io/downloads/userManual.pdf | "dual-timestepping/pseudo-timestepping" 방식을 일반형 `ddtSchemes { default dualTimestepping rPseudoDeltaT <real-time scheme>; }`로 설명(권장 설정 예시는 `dualTime` 키워드 사용). real-time scheme에 `steadyState`를 주면 정상 해석, **비정상 권장 설정은 `default dualTime rPseudoDeltaT backward;`** | [전문] |
| 같은 문서 §2.3.1 `controlDict` | 정상 해석에서는 시간 값이 반복 수, 비정상 해석에서는 **실제 시간**. 예시: `endTime 4.0e-03; deltaT 0.5e-05; adjustTimeStep yes; maxCo 200; maxDeltaT 1e-3;` | [전문] |
| 같은 문서 `pseudoTime` 사전 | 이중 시간 간격의 가상 시간 반복(외부 보정자) 제어: `nPseudoCorr`(기본 20, 정상 해석에서는 무시), `nPseudoCorrMin`(1), `pseudoTol`, `pseudoTolRel` 등 | [전문] |
| 같은 문서 §1.2.3 튜토리얼 | `forwardStep`(M 3 전진 계단): "비정상 해석 설정을 자세히 보임". `shockTube`: 비정상 충격파 추적 | [전문] |
| 같은 문서 §2.2 난류 | `kOmegaSST`, `SpalartAllmaras`가 HiSA로 시험됨, 원칙적으로 모델 제한 없음. 튜토리얼 `supersonicFlatPlate`(M 4.5 RANS 평판) | [전문] |
| 같은 문서 §2.1 경계조건 | `characteristicFarfield*`(무반사 원방), `characteristicPressureInletOutputVelocity` 등 압력/속도 지정 유입·유출, 벽 `characteristicWallPressure`, 단열 벽 온도 조건 | [전문] |
| ParCFD 2020 HiSA DLR-F6 검증 발표 | 이중 시간 간격을 국소 또는 전역 가상 시간으로 쓸 수 있다고 기술 | [검색 요약] |

**판정**: HiSA는 문서상 **이중 시간 간격으로 시간 정확 비정상 계산을 지원한다.**
**주의 (I2에서 확인할 것)**:
1. 같은 안내서 안에서 키워드가 `dualTimestepping`과 `dualTime` 두 가지로 적혀 있다 → v2512용 HiSA 소스에서 `ddtScheme` 등록 이름을 확인.
2. 안내서는 2021-07 판이다. 현재 HiSA 판과 OpenFOAM ESI v2512 호환 범위(계획서의 "v2006~v2512")는 이번에 확인하지 않았다(**미확인**) → 저장소 README·릴리스 노트로 확인.
3. 비정상 해석의 시간 정확도는 `nPseudoCorr`·`pseudoTol`에 달려 있다. I10 결과 보고 시 이 값과 가상 시간 수렴 여부를 함께 남길 것.
4. CLAUDE.md 규칙 6: 초음속 출구에는 압력을 지정하지 않는다. HiSA의 characteristic 유출 조건에서 압력을 지정하는 형식은 아음속 출구에만 써야 한다.

---

## 4. 계획에 반영할 점 (I1 종합)
1. **검증 케이스 교체(I7·I11a)**: Reinartz(2003)는 M 4·5 비행 조건 정압만 측정(열유속 없음, 시험 조건 미확인)이다. I7 압력 분포와 I10 스로틀링 검증은 공개 전문이 있는 **Emami 외 NASA TP-3502**(M 4.03, 2D, 스로틀 플랩, CLAUDE.md 규칙 6과 같은 배압 방식)로 바꾸고, 흡입구 열유속은 **Häberle & Gülhan(2008, M 7, IR Stanton 수)** 전문을 확보한 뒤 채택 여부를 정하는 것을 제안한다.
2. **I4 성공 기준 정량화**: "열유속 경향 일치"를 TMR 2DZPH(`cf_vandriestII.dat`)와 Duan DNS M6Tw076(Tw = 300 K, B_q 제공)에 대한 C_f·2St/C_f의 정량 오차로 바꿀 것을 제안한다(허용치는 사용자 결정). 24° 램프는 디지털 자료가 없어 박리 길이를 디지타이저로 얻어야 하며, SST가 이 계열 흐름에서 박리 시작을 이르게 예측한다는 NASA 보고를 판정에 참고한다.
3. **I11a 설정**: Wieting RUN 21(M 8.03, Type IV)의 쐐기 각은 **12.5°**(Table 11의 10°는 오식)이고, 자유류는 Table 11의 정압·정온·속도로 직접 지정해야 한다(p₀·T₀에서 γ = 1.4로 환산하면 T∞가 9% 낮게 나옴). M 7, 25 km에서는 수직충격파 뒤 정온이 약 2320 K로 완전기체 경고 조건(2000 K)을 넘는다.
4. **I9 차별점과 방법**: 마하 상승·하강 연속 추적으로 히스테리시스 루프를 얻는 방법은 Galaktionov 외(EUCASS 2019)가 이미 썼다. I9의 차별점은 "M 0.6–7 전 범위 + 열유속 결합"으로 두고, 그들처럼 **마하 간격·초기장 민감도**를 함께 보고하도록 단계에 추가하는 것을 제안한다.
5. **I2·I10 확인 사항**: HiSA 이중 시간 간격은 문서로 확인됐으나 키워드(`dualTime` / `dualTimestepping`)와 v2512 호환 범위는 소스로 확인해야 한다. buzz 재현에는 흡입구 상류 자유류 영역을 충분히 넓혀야 하며(Lee & Kang 2019), Waltrup–Billig 비교는 원형 덕트·M 1.53–2.72 상관식의 외삽임을 I10 성공 기준에 명시한다.
