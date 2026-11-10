# i1b_followup.md — 흡입구 실험 I1b: I1 미확인 항목 후속 확인

작성: Claude Science · 2026-11-10 · 대상: `docs/science_prompt_I1b.md`
첨부 PDF 없음. 공개 경로(NTRS, DLR elib, HAL, J-STAGE, Cambridge OA, 대학 저장소, arXiv)와 서지 DB(Crossref, OpenAlex)만 사용했다.

**확인 수준 표기**: **[원문]** 해당 문헌 자체를 읽음 · **[공개 사본]** 저자·기관이 올린 같은 내용의 사본 · **[2차 N건]** 다른 문헌의 인용으로만 확인, 서로 독립인 N건이 일치 · **[초록]** · **[메타]** · **[검색 스니펫]** 웹 검색 결과 요약문만 봄(전문 미열람) · **미확인**.
독립성 판정: 공저자가 겹치거나 같은 연구실이면 1건으로 셌다.

자동 접근이 막힌 공개 자료(봇 차단·약관 동의 페이지)는 우회하지 않았다. 사용자가 브라우저로 직접 받을 수 있는 것은 §6에 따로 적었다.

---

## 0. 항목별 상태

| 항목 | 상태 | 한 줄 요약 |
|---|---|---|
| **B** Waltrup–Billig | **확인됨**(원형 덕트) / **불일치**(직사각 변형) | 원형 덕트 식 `s(M₁²−1)Re_θ^¼/√(Dθ) = 50(p/p₁−1)+170(p/p₁−1)²`의 계수·지수는 독립 2차 4건이 일치. 직사각 덕트 변형은 Re_θ 지수(¼ vs ⅕)와 길이 척도가 문헌마다 다름. 원전 식 번호는 미확인 |
| **C** Häberle & Gülhan | **일부 확인** | 시험 조건 수치는 공개 자료로 미확인. 같은 GK-01 모형의 형상·H2K 조건(다른 캠페인)은 DLR 공개 사본으로 확인. Häberle 박사논문(2009)은 공개(OPUS Stuttgart)지만 자동 다운로드가 막혀 사용자가 브라우저로 받아야 함. 공개 대체 후보: NASA TN D-7150 |
| **A** 벽 조건 | **일부 확인** | Settles: "제어 안 함, 대략 1.05·T₀(hot wall)" [2차 1건, 미확정]. Emami: 명시 없음이 맞음(확정). Trapier·Wagner: 미확인 |
| **D** 서지 | **확인됨**(3/4) | Van Wie 장은 **단독 저자** D. M. Van Wie, PAA Vol. 189 [2차 2건]. Edney = FFA Report 115 [2차 5건]. Celik 외 6인 [2차 2건]. MCF 4판은 **Anderson 단독**(McGraw-Hill 2021) [출판사 페이지·검색 스니펫] |
| **E** 중국어권 선행연구 | **이번 검색 범위에서 못 찾음** | 연속 마하수 스윕 + 시동 경로 + 벽 열유속을 함께 다룬 연구는 못 찾음. 인접 연구 3건 [초록] |

## 1. 변경 사항 (이전 I1 산출물 대비)

| # | 항목 | 이전 값(파일) | 새 값 | 근거 |
|---|---|---|---|---|
| 1 | Van Wie 장 저자 | "Van Wie 외"(`references.md` R2) | **Van Wie, D. M. 단독** | Fujio & Ogawa 2025, Ribeiro 2019 참고문헌 [2차 2건] (§5.1) |
| 2 | Van Wie 장 권 번호 | "통상 Vol. 189, DB 미확인"(R2) | **Progress in Astronautics and Aeronautics Vol. 189**, pp. 447–511 | Arakawa 외 2020, Yanık 2023, Ribeiro 2019 [2차 3건] |
| 3 | Edney 보고서 번호 | "FFA Report 115, 미확인"(R3) | **FFA Report 115**, Aeronautical Research Institute of Sweden (Flygtekniska Försöksanstalten), Stockholm, 1968 | Wieting 1987, Holden 1991, Moss 1998, Ozawa 2009, Liu 2024 [2차 5건] |
| 4 | Celik 2008 저자 | "DB 미확인"(R16) | **Celik, I. B., Ghia, U., Roache, P. J., Freitas, C. J., Coleman, H., Raad, P. E.** | Rumsey 2010(NTRS), Wackers 2017(HAL) [2차 2건] |
| 5 | MCF 4판 저자 | "4판(Anderson & Cadou, 2021)"(T1) | **Anderson, J. D. Jr. 단독**, McGraw-Hill, ©2021, ISBN 978-1-260-47144-1 | McGraw-Hill 제품 페이지·변경 안내 PDF [검색 스니펫]. 출판사 페이지에 Cadou 없음 |
| 6 | MCF 3판 연도 | "3판(2003)"(T1) | **미확정**: 위키백과는 2002로 적음 | [검색 스니펫 1건]. 출판사 서지 미확인 |
| 7 | Settles 24° 벽 조건 | 미확인(`validation_data.md` §2) | 벽·모형 온도 **제어 안 함**, 관측값 **≈1.05·T₀**(hot wall). 24°: T₀ = 262 K → T_w ≈ 275 K(계산), T_w/T_aw ≈ 1.13(r = 0.89 가정) | Oliver 외 2007(NTRS 전문) [2차 1건, 미확정] (§4.1) |
| 8 | Settles 24° 입구 경계층 측정 위치 | 코너 상류 −63.5 mm(§2, Oliver 2006 Table 5) | **출처 간 불일치**: Oliver 2007 Table 1은 −50.8 mm(δ, δ*, θ 값은 같음) | 같은 연구진의 두 논문이 다름 → 원문 확인 전까지 둘 다 표기 |
| 9 | Emami 벽 조건 | "명시 없음" | **명시 없음 확정** + 보충: 피토 분포 환산에 단열벽(T_w = T_t)·Pr = 1을 **가정**했다는 서술만 있음. 측정한 벽온도 없음 | TP-3502 전문 재확인 (§4.2) |
| 10 | Häberle 흡입구 형상 | 미확인(§4c) | GK-01: 램프 7.5°/20.5°, 내부 압축비 16 %, 포획면 100 × 100 mm, L = 0.585 m, 목 x = 0.41 m, 목 뒤 30 mm 등단면 + 하부벽 1° 확산 | Hohn & Gülhan, AIAA 2010-938, DLR elib [공개 사본]. **같은 모형의 다른 캠페인** (§3) |
| 11 | Waltrup–Billig 직사각 변형 | "D를 높이/수력지름 중 무엇으로 둘지 문헌마다 다름"(exercises 7) | 추가로 **Re_θ 지수가 ¼(Billig 1993)인지 ⅕(Sullins & McLafferty 1992)인지도 문헌마다 다름** | §2.3 |

`exercises.md` 문제 7의 답(13.6 / 104.1 / 225 mm)은 식이 확인되어 **바뀌지 않는다**. 다시 계산한 결과와 지수 민감도는 §2.5에 있다.

---

## 2. B — Waltrup–Billig 의사충격파열 상관식

### 2.1 인용 문헌 비교표

| # | 문헌 | 식 형태(문헌 표기 그대로 요약) | 계수 | Re_θ 지수 | 길이 척도 | 원전 표기 | 수준 | 독립성 |
|---|---|---|---|---|---|---|---|---|
| 1 | Kitamura, Tomioka, Sakuranaka, Watanabe, Masuya, 日本航空宇宙学会論文集 57(661):47–55, 2009, 식 (1) https://www.jstage.jst.go.jp/article/jjsass/57/661/57_661_47/_pdf | `st(M∞²−1)Re_θ^0.25 / (D^0.5 θ^0.5) = 170(P_w/P_min − 1)² + 50(P_w/P_min − 1)` | 50, 170 | 0.25 | D = 시험부 관 지름, θ = 승압 시작점 운동량 두께, st = 승압 시작점부터의 거리 | Waltrup & Billig 1973 (AIAA J 11) | 인용 논문 [원문]. 식 영역을 렌더링해 확인 | 그룹 A |
| 2 | Arakawa, Nishiguchi, Kobayashi, Tomioka, Trans. JSASS 63(6), 2020, 식 (13)·(14), p.277 https://www.jstage.jst.go.jp/article/tjsass/63/6/63_T-19-77/_pdf | `X_PSW(M_st²−1)Re_θ,st^N / √(D_st θ_st) = 50(p/p_st−1) + 170(p/p_st−1)²` | 50, 170 | N. 원형은 0.25. 직사각은 0.25(Billig 1993) 또는 0.20(Sullins & McLafferty 1992)이 권장된다고 씀 | D_st = 의사충격파 시작점 수력 지름. 직사각에서는 폭·높이 중 작은 쪽으로 바꾼다고 씀(Billig 1993) | 참고문헌 7) W&B 1973, 8) Billig 1993, 9) S&M 1992 | 인용 논문 [원문]. 렌더링 확인 | 그룹 A(Tomioka 공저 → #1과 독립 아님) |
| 3 | Gillespie & Sandham, *Flow* 3:E12, 2023, 식 (4.4)–(4.6) https://doi.org/10.1017/flo.2023.6 (CC-BY) | 원형: `(s/h)(M₂²−1)Re_θ^¼ / (θ₂/D)^½ = 50(p/p₂) + 170(p/p₂)²`. 직사각(Billig 1993): 분모 `(2θ₂/h)^½` | 50, 170 | ¼(원형·직사각 모두) | s = x − x₂, x₂ = 벽압이 자유류보다 5 % 오른 위치. 직사각에서 θ₂ = 네 벽 중 최대 운동량 두께, h = 반폭·반높이 중 작은 값 | W&B 1973, Billig 1993 | 인용 논문 [원문]. 렌더링 확인 | 그룹 B |
| 4 | Edelman, Gamba, Hunt, Auslender, "Assessment of Pseudoshock Models…", NTRS 20220007426, 식 (7)·(8) https://ntrs.nasa.gov/citations/20220007426 | 직사각만: `50(P/P₀−1) + 170(P/P₀−1)² = x(M₀²−1)Re_θ^⅕ / √(Hθ)` | 50, 170 | **⅕**(Billig 1993 [14]에서 왔다고 씀) | H = 덕트 높이, 접근 조건(중심선 M₀·P₀, 벽 θ) | 원형 W&B 1973 [13], 직사각 Billig 1993 [14] | 인용 논문 [원문]. 렌더링 확인 | 그룹 C(같은 저자의 학위논문 식 4.16, NASA 세미나 자료와 같은 내용이라 1건으로 셈) |
| 5 | Dikmen, METU 석사논문, 2023, 식 28·29, p.42 https://open.metu.edu.tr/bitstream/handle/11511/102058/index.pdf | 원형: `St(M₂²−1)Re_θ^0.25 / (D^0.5θ^0.5) = 50(P₃/P₂) + 170(P₃/P₂−1)²`. 직사각: `Re_θ^0.2`, `H^0.5θ^0.5` | 50, 170 | 0.25 / 0.2 | D / H | 인용 형태 | 인용 논문 [원문] | 그룹 D |
| 6 | Smart, NATO RTO-EN-AVT-185 "Scramjet Isolators" https://publications.sto.nato.int/publications/STO%20Educational%20Notes/RTO-EN-AVT-185/EN-AVT-185-10.pdf | 본문 요약: s는 D^½θ^½에 비례하고 (M²−1)Re_θ^¼에 반비례, 우변 계수 50·170 | 50, 170 | ¼ | D = 덕트 지름. s = 충격파 구조(압력 상승)가 퍼진 거리 | W&B 1973 | **[검색 스니펫]**: Cloudflare 차단으로 전문 미열람 | (계산에서 제외) |

인용만 하고 식은 쓰지 않은 공개 전문: Leonard 외 *JFM* 2025 (https://doi.org/10.1017/jfm.2025.10474, 원형 덕트 측정 압력을 W&B 곡선과 비교), Riggins 외 2006(NTRS 20070000536), Rodriguez 외 2000(NTRS 20040086780).

### 2.2 변수 정의 (위 문헌 종합)
- **s**: 의사충격파열 **시작점**(벽압이 오르기 시작하는 곳)부터 하류로 잰 거리. 상관식은 **압력 분포** p(s)를 준다(#1–#4). 그러므로 s는 "시작점~압력 평탄 구간 끝"의 고정 길이가 아니다. p가 하류 배압에 도달하는 s가 충격파열 길이가 된다.
  - 시작점의 정량 정의는 Gillespie & Sandham(#3)만 적었다: 벽압이 자유류보다 5 % 오른 위치. 원전의 정의는 **미확인**.
- **p₂/p₁** (기존 표기): p₁ = 충격파열 바로 상류의 벽 정압. p₂ = 거리 s에서의 **국소 벽압**(#1 P_w/P_min, #2 p/p_st, #4 P/P₀).
- **M₁, θ, Re_θ**: 모두 충격파열 시작점(바로 상류) 값. θ = 벽 경계층 운동량 두께(#1–#4).
  - Re_θ를 어느 상태량으로 만드는지(경계층 외연 또는 중심선의 ρ, u, μ)는 읽은 문헌 어디에도 명시되지 않았다 → **미확인**. #4는 중심선 M₀·P₀를 접근 조건으로 쓴다.
- **D**: 원형 덕트 지름. #2는 "수력 지름"이라고 쓴다(원형이면 같음).
- **"−1" 항**: #1, #2, #4는 두 항 모두 (p/p₁ − 1)이다. #3(두 항 모두 −1 없음)과 #5(1차 항만 −1 없음)는 다르게 인쇄됐다. 하지만 −1이 없으면 s = 0(시작점)에서 우변이 0이 되지 않는다. 그래서 인쇄 오류 또는 표기 생략으로 판단했다. 그대로 계산하면 p₂/p₁ = 2에서 우변이 220이 아니라 780이 된다(계산).

### 2.3 적용 범위와 직사각 덕트
- **원전 시험 범위** [초록, I1에서 확인]: 원형 덕트, 1.53 ≤ M₁ ≤ 2.72, D = 1.0–6.1 in, θ = 0.007–0.036 in. 압력비 범위는 **미확인**.
- **직사각 변형은 문헌마다 다르다** → 판정 (나):
  1. Billig 1993: Arakawa(#2)는 지수 0.25, 길이 척도는 폭·높이 중 작은 쪽이라고 쓴다. Gillespie(#3)는 지수 ¼, `(2θ/h)^½`(h = 작은 쪽 반치수)라고 쓴다. 정리하면 `√(H_min θ)`이고, #2와 #3은 서로 일치한다.
  2. Edelman(#4)은 Billig 1993 식이 **Re_θ^⅕**, √(Hθ)라고 쓴다. Arakawa(#2)는 ⅕을 **Sullins & McLafferty 1992**의 값으로 본다. Dikmen(#5)도 직사각에 0.2와 H를 쓴다.
  3. ⅕ 지수가 Billig 1993의 것인지 S&M 1992의 것인지는 원문 없이는 판단할 수 없다.
- **적용성 경고**:
  - Edelman(#4): 저종횡비(낮은 AR) M 2 아이솔레이터에서 압력 상승을 과대평가한다. 보정 범위 밖에서는 쓰기 어렵다.
  - Leonard 외 2025: 원형 덕트에서 x/D ≈ 0.4까지는 맞지만, 하류에서는 상관식이 압력을 과대 예측한다.
  - Gillespie(#3): 직사각 식은 종횡비를 반영하지 못해 산포가 크다. 그래서 운동량 두께 기반 차폐비 B_θ를 쓴 수정식 (4.6)을 제안했다.
  - Lu 외 ISSW30(2016) [초록]: Bement 외가 원통 지름을 직사각 단면의 덕트 높이로 바꿔 적용할 수 있음을 보였다고 소개한다(차이는 있음). 같은 초록은 벽온도가 높을수록 충격파열이 길어진다고 보고한다. https://program.eventact.com/Agenda/Lecture/83837?code=1638947

### 2.4 결론
**(가) 계수 일치 (2차 4건)**: 원형 덕트 식의 계수 50·170, Re_θ^¼, √(Dθ) 척도는 독립 그룹 4곳이 같다. 그룹은 A(Kitamura/Arakawa), B(Gillespie & Sandham), C(Edelman 외; 계수와 (p/p₁−1) 형태만, 직사각 식), D(Dikmen)다.
- 두 항 모두에 −1까지 그대로 인쇄된 원형 덕트 식은 그룹 A뿐이다. 다만 B·D의 차이는 §2.2의 이유로 인쇄 오류로 판단했다.
- **원전(AIAA J 11(10), 1973)의 식 번호는 미확인**이다. CLAUDE.md 규칙 11(저자·연도·식 번호 명시) 때문에 I10 구현 주석에는 당분간 "Waltrup & Billig 1973, 식 번호 미확인. 형태는 Kitamura 외 2009 식 (1)·Arakawa 외 2020 식 (13) 인용"으로 적기를 권한다.
- **직사각 변형은 (나) 불일치**다(§2.3).

### 2.5 `exercises.md` 문제 7 재계산 (M₁ = 2.2, D = 20 mm, θ = 0.4 mm, Re_θ = 2×10⁴)
식이 이전과 같으므로 답도 같다. Re_θ 지수만 ⅕로 바꾼 민감도를 함께 적는다. s는 Re_θ^(¼−⅕) = (2×10⁴)^0.05 = 1.641배 길어진다.

| p₂/p₁ | s, Re_θ^¼ (기존 답) | s/D | s, Re_θ^⅕ (S&M/Edelman 형태) |
|---|---|---|---|
| 2 | 13.6 mm | 0.68 | 22.4 mm |
| 4 | 104.1 mm | 5.20 | 170.7 mm |
| 5.48 (정상 충격파, M₁ = 2.2) | 225.2 mm | 11.26 | 369.5 mm |

검산은 Python으로 했다. 정상 충격파 압력비는 1 + 2γ/(γ+1)(M₁²−1) = 5.480이다.

---

## 3. C — Häberle & Gülhan

### 3.1 찾은 공개 자료
| 자료 | 내용 | 수준 |
|---|---|---|
| 2008 *JPP* 24(3):446–459 (Mach 7), 2007 *JPP* 23(5):1007–1017 (Mach 6), 2008 *JPP* 24(5):1023–1034 (2D·3D 흡입구, M 7, doi 10.2514/1.33546) | DLR elib 서지(57293, 52410, 52419)는 "Open Access: Nein", 전문 없음 | [초록]/[메타] |
| Häberle, J., 박사논문 *Untersuchungen zum externen und internen Strömungsfeld eines Scramjet Triebwerkseinlaufs bei unterschiedlichen Betriebspunkten*, Univ. Stuttgart, 2009 (= DLR-FB-2009-14). OPUS: http://elib.uni-stuttgart.de/handle/11682/3826 , doi 10.18419/opus-3809 | **공개 저장소에 있음**. 자동 접근은 봇 확인 페이지(Anubis)로 막혀 **내용을 읽지 못함** → 사용자가 브라우저로 받아 `docs/papers/`에 넣으면 추출 가능 | [초록](OpenAlex) |
| Hohn & Gülhan, "Experimental Investigation on the Influence of Yaw Angle on the Inlet Performance at Mach 7", AIAA 2010-938, https://elib.dlr.de/67837/1/AIAA_2010-938.pdf | **같은 GK-01 모형**을 같은 H2K에서 시험(편요각 캠페인). Häberle 박사논문·2008 논문을 선행 자료로 인용 | [공개 사본](같은 기관, 다른 캠페인) |

박사논문 초록에서 확인한 것 [초록]:
- Ma 6과 Ma 7의 두 흡입구를 시험했다.
- 상·하벽 중심선 정압, 연소기 입구면 피토압, 스로틀로 포획 유량과 배압을 함께 바꿨다.
- 그림자 사진을 찍었다.
- 격리부 측벽과 외부 램프의 IR 열화상으로 시간에 따른 표면온도를 쟀고, 여기서 Stanton 수를 구했다. H2K에서 내부 유동에 IR을 쓴 첫 사례다.
- 목 부분에 수동 블리드를 선택적으로 달 수 있다.
- 열유속 환산은 1D 방법 외에 FEM(ANSYS) 3D 방법도 비교했다.

### 3.2 요청 항목 표 (찾은 만큼)
| 항목 | 값 | 근거·수준 |
|---|---|---|
| 풍동 | DLR Köln **H2K** 블로다운 극초음속 풍동. Ma 5.3/6/7/8.7/11.2 노즐(출구 지름 600 mm), Re 2.5–20×10⁶ /m, 전기 가열, 운전 시간 최대 30 s | AIAA 2010-938 [공개 사본] |
| 자유류 M | 7 (2008 JPP), 6 (2007 JPP) | [초록] |
| p₀, T₀, Re 3가지 | **Häberle 시험 값은 미확인**. 참고로 같은 GK-01의 편요각 캠페인 값: T₀ = 500 K, p₀ = 7.0×10⁵ Pa, p∞ = 170 Pa, T∞ = 46 K, ρ∞ = 0.0123 kg/m³, Re = 4.0×10⁶ /m | AIAA 2010-938 Table 1 [공개 사본]. 검산(γ = 1.4 이상기체): T∞ 46.3 K, p∞ 169.1 Pa, ρ∞ 0.0127 kg/m³(표와 3 % 차이), 표의 ρ∞로 Re 4.01×10⁶ /m |
| 모형 벽 온도 | **미확인**. 표면온도는 시간에 따라 변함(IR 과도 측정에서 열유속 산출). 같은 풍동의 다른 3D 흡입구 논문은 모형을 상온(300 K)으로 둔다고 씀 | 2008 초록 [초록]. Hohn & Gülhan *JPP* 38(1) 2022, elib 144891 [검색 스니펫] |
| 램프 각 | δ₁ = 7.5°, δ₂ = 20.5° (x축 기준), 2단 램프 + 측벽, 설계 비행 M 7.5, 목에 등엔트로피 팽창면 | AIAA 2010-938 [공개 사본] |
| 목·아이솔레이터 | 내부 압축비 I = 1 − A_th/A₀ ≈ 16 %, 목 x = 0.41 m, 목 뒤 30 mm 등단면 후 하부벽 1° 확산, 흡입구 앞전~연소기 경계면 L = 0.585 m. **목 높이 수치는 이 자료에 없음**(A₀와 I로 추정하면 약 84 mm인데, 이는 면적비 추정이지 측정 치수가 아님) | 같음 |
| 폭 | 포획면 A₀ = 0.01 m² (100 mm × 100 mm) | 같음 |
| 배압 방법 | 하류 **스로틀**(원뿔 플러그형 유량계 겸용)로 배압비 p/p∞ 변경 → CLAUDE.md 규칙 6과 같은 방식 | 같음 · Yanık 2023 [2차] |
| 측정 | 중심선 정압공 42개(하벽 25, 상벽 17), 피토·정압 레이크, 그림자 사진, IR 열화상(측벽 PEEK·ZnS 창), Stanton 수(r = 0.9로 T_rec 정의) | 같음 |
| 수치 표 공개 여부 | **미확인**. 공개 사본에는 결과가 그림으로만 있음 | — |

### 3.3 판단 (3줄)
1. 형상(램프 각·포획면·길이·스로틀)은 공개 사본으로 2D 격자를 만들 수 있는 수준까지 얻었다. 다만 목 높이·카울 위치의 정확한 치수는 **미확인**이다.
2. Häberle 시험 자체의 p₀·T₀·Re 3가지와 벽 초기온도가 없다. 그래서 I7(압력)·I11a(열유속) 정량 검증에 쓰기에는 **공개 자료(자동 접근 범위)로는 판단 불가**다.
3. 다만 박사논문이 **무료 공개**다. 이 논문을 브라우저로 받으면 유료 접근 없이 풀릴 가능성이 높다(§6). 수치가 표로 있는지도 그때 확인해야 한다.

### 3.4 공개 열유속 흡입구 대체 후보
| 후보 | 조건 요약 | 측정·형식 | 수준 | 평가 |
|---|---|---|---|---|
| **Gnos, Watson, Seebaugh, Sanator, DeCarlo, NASA TN D-7150 (1973)** "Investigation of flow fields within large scale hypersonic inlet models" https://ntrs.nasa.gov/citations/19730013178 | Ames 3.5-ft HWT, M∞ = 7.4, p₀ = 4.14×10⁶ N/m², T₀ = 811 K, Re = 8.86×10⁶ /m (일부 p₀ 1.38×10⁶까지). 운전 1–4 분. 모형 P2·P8·P12(내부 압축비 다름), 쐐기 전방체 + 무딘 카울 | 벽 정압, 표면온도(열전대). 열유속 게이지는 **각 통로 카울 한 위치뿐**(Table 3). 피토·총온 단면 탐침, 쉬리렌. 탐침 자료 전체 표는 별도 참고문헌 18에 있다고 씀 | [원문] (NTRS 174쪽) | **벽온도가 정의된다**: 계산은 일정 표면온도 303 K 기준, 측면 변동 무시 가능. 압력·경계층 자료가 풍부하다. 그러나 열유속은 점 1개이고, P2 카울 목 부근 경계층은 층류로 판정됐다 → I7 압력 검증 보조로는 좋고, I11a 열유속 분포 검증에는 약하다. 검산: 이상기체 환산 Re 9.6×10⁶ /m(보고값과 9 % 차이; 원문은 실기체 보정을 씀) → 보고값을 쓸 것. P8은 Kapoor 외 NASA TM-105720(1992, 2D PARC2D) 등 CFD 검증 사례가 있음 [원문 초록] |
| TMR Marvin 외 NASA/TM-2013-216604 묶음(Holden CUBRC·Coleman 2D 압축 코너, ASCII) | I1 `validation_data.md` §0·§2 참고 | 벽압·열유속 | I1에서 확인 | 흡입구는 아니지만 SBLI 열유속 ASCII. I11a 보조로 이미 제안됨 |
| Holland, NASA TP-3476 (1995) 3D 측벽 압축 흡입구 M 10 https://ntrs.nasa.gov/citations/19950014203 | Langley, M 10, 수축비·카울 위치·Re 변화 | 본문에 열유속 언급 없음(검색어 0건) | [원문 텍스트 검색] | 압력 전용이라 열유속 대체로는 부적합 |

---

## 4. A — 벽 조건

### 4.1 Settles 외 (1979) 압축 코너
| 구분 | 내용 | 수준 |
|---|---|---|
| 원전(AIAA J 17(6)) | 미열람 | 미확인 |
| Oliver, Lillard, Schwing, Blaisdell, Lyrintzis, "Assessment of Turbulent Shock-Boundary Layer Interaction Computations Using the OVERFLOW Code", AIAA 2007(NTRS 20070003681 전문) https://ntrs.nasa.gov/citations/20070003681 | 풍동 벽과 램프 모형 온도는 제어하지 않았다. 관측 온도는 정체온도의 약 1.05배(hot wall)였다. 출처는 Settles 외 1979와 Settles & Dodson DB로 인용됨. Table 1(24°): M∞ 2.84, T₀ 262 K, p₀ 6.90×10⁵ Pa, δ 23 mm, δ* 6.1 mm, θ 1.2 mm(측정 위치 −50.8 mm), Re∞ 68.3×10⁶ /m | [2차 1건, 미확정] |
| 같은 논문의 다른 자료 | Evans 외의 16° 박막 열전달 측정 런은 벽온도가 13 K(5 %) 높아 Settles 조건과 차이가 더 큼 | [2차 1건] |
| 주의 | Venkatachari 외 2018(NTRS 20180006189)의 "벽온도 260.24 K"는 Princeton **저레이놀즈수** M 2.9 24° 실험(Bookey 외)의 값이다. Settles 1979 고레이놀즈수 실험과 혼동하지 말 것 | [원문] |
| 2차 독립 확인 | Settles & Dodson DB(NASA CR-177638, 1994; CR-177577)는 NTRS에서 전문을 찾지 못함 | 미확인 |

계산(γ = 1.4): T∞ = 100.3 K, T_aw(r = 0.89) = 244.2 K, 1.05·T₀ = 275.1 K → T_w/T_aw ≈ 1.13.

### 4.2 Emami 외, NASA TP-3502 (1995) — 원문 재확인 [원문]
- **벽온도 측정·명시 없음 확정.** 시험 장치·모형 절(p.8–11)에는 다음만 있다.
  - 가열기 없는 냉기류다. T_t는 대기온도에 따라 500–540 °R ± 3 °R로 변했다.
  - 공칭 시험 시간은 2.0 분이다.
  - 모형은 쐐기·블록 조립식이다. 카울쪽 계단용 후방 카울 부품이 **알루미늄**이라는 기재가 있다. 다른 부품의 재질은 기재 없음.
- 피토 압력 분포를 속도·마하수 분포로 바꿀 때 **단열벽(T_w = T_t)과 Pr = 1을 가정**했다(p.13). 이것은 자료 처리상의 가정이지 측정한 벽 조건이 아니다.
- 시험 중 벽온도 변화에 대한 언급은 없다.

### 4.3 Trapier 외 (2006/2008)
- HAL API 검색("Sébastien Trapier", 흡입구 버즈 관련 제목)에서 Trapier의 학위논문·ONERA 보고서를 찾지 못함 → **공개 자료에 명시 없음(이번 검색 범위)**.
- Chima, "Analysis of Buzz in a Supersonic Inlet", NASA TM(NTRS 20120009203) [원문]은 Trapier 모형을 "ONERA의 정사각 단면 혼합압축 흡입구"로만 소개한다. 조건 수치는 없다.
- Lyubimov & Potekhina(2016, *High Temperature*)와 Lyubimov(2023, Матем. моделирование)가 Trapier 형상을 다시 계산했다. Math-Net.Ru 전문은 이용 약관 동의 페이지를 거쳐야 해서 사용자 동의 없이 진행하지 않았다.
- Hammachi 외 2022(HAL hal-03924931) [원문]은 Trapier가 아니라 "Chen의 실험"(M 2.41)을 재현했다. 그러므로 `validation_data.md` §6의 빈칸을 채우는 데 쓸 수 없다. 이 논문은 램프·카울을 단열 무미끄럼벽으로 두었다.
- `validation_data.md` §6의 "미확인" 칸은 **그대로 유지**한다.

### 4.4 Wagner 외 (2009) — 보너스
- UT Austin 저장소(repositories.lib.utexas.edu)는 자동 접근에 403(CloudFront WAF)을 돌려준다. OpenAlex에서도 Wagner 박사논문 레코드를 찾지 못했다 → **미확인**.
- 현재 값(M 4.9, p₀ 2.5 MPa, T₀ 330 K, δ₉₉ 19.05 mm)은 계속 Lee & Kang 2019의 2차 인용이다. Lee & Kang은 단열벽을 가정했다.

### 4.5 벽 조건 선택지 (가정은 정하지 않음 — §7에 사용자 결정으로 올림)
| 케이스 | 선택지 |
|---|---|
| Settles 24° (I4) | (a) 등온 T_w = 1.05·T₀ ≈ 275 K [2차 1건 근거] · (b) 단열 · (c) 등온 T_w = T₀ = 262 K |
| Emami (I7·I10) | (a) 단열 · (b) 등온 상온(T_t 278–300 K 범위의 값) |
| Wagner (I9·I10), Trapier (I10) | (a) 단열(Lee & Kang 2019와 같음) · (b) 등온 상온 |

---

## 5. D — 서지 보완

### 5.1 Van Wie, "Scramjet Inlets"
- **Van Wie, D. M.**, "Scramjet Inlets," in Curran, E. T., Murthy, S. N. B. (eds.), *Scramjet Propulsion*, Progress in Astronautics and Aeronautics **Vol. 189**, AIAA, Reston, VA, pp. 447–511.
  - 장 DOI https://doi.org/10.2514/5.9781600866609.0447.0511 · 책 DOI https://doi.org/10.2514/4.866609
  - ISBN 978-1-56347-322-7 / 978-1-60086-660-9 (Crossref)
- 저자 근거 **[2차 2건]**, 모두 단독 저자 D. M. Van Wie:
  1. Fujio & Ogawa, Trans. JSASS 68(1) 2025 참고문헌 5 — https://www.jstage.jst.go.jp/article/tjsass/68/1/68_T-24-07/_pdf
  2. Ribeiro, 박사논문, 2019, 참고문헌 180 — https://theses.hal.science/tel-02082214/document
- Crossref와 OpenAlex는 장 저자 필드가 비어 있다 → **[메타]로는 확인 불가**.
- Vol. 189 근거 **[2차 3건]**: Ribeiro 2019, Arakawa 외 2020 참고문헌 24(같은 책의 Penzin 장), Yanık 2023(METU) 참고문헌 7.
- 연도: 인용 문헌은 2000, Crossref는 2001이다. 판권 연도는 **미확인**.

### 5.2 Edney (1968)
- Edney, B., "Anomalous Heat Transfer and Pressure Distributions on Blunt Bodies at Hypersonic Speeds in the Presence of an Impinging Shock," **FFA Report 115**, Aeronautical Research Institute of Sweden (Flygtekniska Försöksanstalten), Stockholm, 1968. OSTI https://doi.org/10.2172/4480948 [메타]
- 보고서 번호 근거 **[2차 5건]**:
  1. Wieting, NASA TM-100484, 1987 — https://ntrs.nasa.gov/citations/19870017721
  2. Holden 외, NTRS 19920024580, 1991
  3. Moss 외, 1998 (NTRS)
  4. Ozawa 외, 日本航空宇宙学会論文集 57(664), 2009 — https://www.jstage.jst.go.jp/article/jjsass/57/664/57_664_175/_pdf
  5. Liu 외, arXiv:2310.17181, 2024
- 이 중 Moss 1998은 기관명을 "Flygtekniska Forsoksanstalten, Stockholm"까지 적었다.

### 5.3 Celik 외 (2008)
- **Celik, I. B., Ghia, U., Roache, P. J., Freitas, C. J., Coleman, H., Raad, P. E.**, "Procedure for Estimation and Reporting of Uncertainty Due to Discretization in CFD Applications," *J. Fluids Eng.* 130(7):078001, 2008. https://doi.org/10.1115/1.2960953
- 근거 **[2차 2건]**:
  1. Rumsey 외 2010, NTRS 20100025022, 참고문헌 24
  2. Wackers 외 2017, HAL hal-02565571, 참고문헌 19
- ASME 페이지는 접근하지 못했다.

### 5.4 Anderson, *Modern Compressible Flow*
- **4판**: Anderson, J. D. Jr., *Modern Compressible Flow: With Historical Perspective*, 4th ed., McGraw-Hill (McGraw-Hill Series in Aeronautical and Aerospace Engineering), ©2021, ISBN 978-1-260-47144-1.
  - 근거: McGraw-Hill 제품 페이지(https://www.mheducation.com/highered/product/modern-compressible-flow-with-historical-perspective-anderson.html)와 4판 변경 안내 PDF [검색 스니펫]. Google Books 서지 [검색 스니펫]은 778쪽이다.
  - **저자는 Anderson 단독이다**(변경 사항 #5).
- **3판**: 출판사 서지 **미확인**. 위키백과 저자 항목은 2002로 적는다 [검색 스니펫 1건].
- **보유 판본은 사용자가 알려줄 예정**이다. 식·그림 번호를 인용하기 전에 판을 정해야 한다.

---

## 6. E — 중국어권 선행연구 (선택 항목)

**이번 검색 범위에서는** "하나의 흡입구를 아음속~극초음속으로 연속 스윕하며 시동·불시동 경로와 벽 열유속을 함께 다룬" 연구를 **찾지 못했다.** 없다고 단정하지 않는다.

- 사용한 검색어: `高超声速进气道 起动 不起动 迟滞 热流 宽马赫数 连续 变马赫数 数值模拟` (웹 검색 1회). 그 밖에 OpenAlex 인용망(Trapier·Häberle·Waltrup–Billig 인용 OA 문헌)을 훑었다.
- 中国知网(CNKI)·万方 직접 검색은 하지 않았다.

인접 연구 (모두 [초록]):

| 제목 | 학술지·연도 | 링크 | 관련성 |
|---|---|---|---|
| 高超声速进气道低马赫数不起动和再起动试验 | 航空学报, 2017 | https://hkxb.buaa.edu.cn/CN/10.7527/S1000-6983.2017.121146 | 2D 흡입구. 받음각·하류 막힘으로 저마하 불시동·재시동을 모사. 분리포 흡입 지연(迟滞) 관측. 열유속 없음 |
| 大内收缩比进气道加速起动过程中喘振特性研究 | 推进技术, 2018(7) | http://tjjs.ijournals.cn/html/2018/7/20180706.htm | 내부 수축비 1.63 2D 흡입구의 **가속 시동 과정**(마하수 증가) 비정상 2D 계산. 진동 상태가 차례로 바뀜. 열유속 없음 |
| 迎角变化引起的高超声速进气道起动迟滞现象试验研究 | 实验流体力学, 2019(3) | https://html.rhhz.net/SYLTLX/html/2019-3-76.htm | M 5 Bump 흡입구, 받음각 변화에 따른 시동 히스테리시스(NUDT LF-220). 열유속 없음 |

---

## 7. 사용자 결정이 필요한 것

1. **Settles 24° 벽 조건(I4)**: §4.5의 (a) 등온 1.05·T₀ ≈ 275 K / (b) 단열 / (c) 등온 T₀ 중 선택.
2. **Emami 벽 조건(I7·I10)**: 단열 / 등온 상온 중 선택. 가정한 내용은 케이스 설정에 기록한다(규칙 1).
3. **Wagner·Trapier 벽 조건(I9·I10)**: 원문을 확보할 때까지 단열(Lee & Kang과 같음) / 등온 상온 중 선택.
4. **Waltrup–Billig 직사각 변형(I10)**: (a) Billig 1993 해석(Re_θ^¼, 작은 쪽 치수; Arakawa·Gillespie) / (b) S&M·Edelman 해석(Re_θ^⅕, 높이 H) / (c) 둘 다 그려 띠로 비교.
   - Emami 아이솔레이터는 높이 0.4 in < 폭 2.0 in이어서 (a)와 (b)의 길이 척도가 같다(H = 높이). 남는 차이는 지수뿐이다.
5. **브라우저로 직접 받을지** (모두 무료 공개, 자동 접근만 막힘): 받아서 `docs/papers/`에 넣으면 Science가 조건·치수·표를 추출한다.
   - Häberle 박사논문 (OPUS Stuttgart, http://elib.uni-stuttgart.de/handle/11682/3826) → C 전체, A(Häberle 벽 초기온도)
   - Smart, NATO RTO-EN-AVT-185 Lecture 10 "Scramjet Isolators" (링크 §2.1 #6) → B 확인 1건 추가
   - Wagner 박사논문 (UT Austin 저장소, 2009 전후) → A 보너스
   - Lyubimov 2016/2023 (Math-Net.Ru, 약관 동의 필요) → Trapier 조건 단서
6. **C 대체 후보 채택 여부**: NASA TN D-7150(P8 흡입구, M 7.4, T_w ≈ 303 K)을 I7 압력 검증 보조로 넣을지. 열유속 분포 검증(I11a)에는 약하다.
7. **MCF 보유 판본**(3판/4판) 알려주기.

## 8. 유료 접근이 있어야만 풀리는 것

| 문헌 | 필요한 이유 | 풀리면 쓰이는 단계 |
|---|---|---|
| Waltrup & Billig, "Structure of Shock Waves in Cylindrical Ducts," *AIAA J.* 11(10):1404–1408, 1973, https://doi.org/10.2514/3.50600 | 원전 식 번호(규칙 11), Re_θ 상태량 정의, s 시작점 정의, 압력비 적용 범위 | I10 |
| Billig, "Research on Supersonic Combustion," *JPP* 9(4):499–514, 1993, https://doi.org/10.2514/3.23652 | 직사각 변형의 Re_θ 지수(¼ vs ⅕)와 길이 척도 확정 | I10 |
| Sullins & McLafferty, "Experimental Results of Shock Trains in Rectangular Ducts," AIAA 92-5103, https://doi.org/10.2514/6.1992-5103 | Re_θ^⅕ 형태의 출처 확인 | I10 |
| Settles, Fitzpatrick & Bogdonoff, *AIAA J.* 17(6), 1979 및 Settles & Dodson NASA CR-177638(1994) | 벽온도 1.05·T₀의 원전 확인. 입구 경계층 측정 위치(−50.8 vs −63.5 mm) 확인 | I4 |
| Trapier, Duveau & Deck, *AIAA J.* 44(10), 2006 / Trapier, Deck & Duveau, *AIAA J.* 46(1), 2008 | 정체압·정체온도·Re·치수·벽 조건 (`validation_data.md` §6 빈칸) | I10 |
| Wagner 외, *AIAA J.* 47(6), 2009 (박사논문을 브라우저로 받을 수 있으면 불필요) | 벽 조건·원 시험 조건(현재 2차 인용) | I9·I10 |
| Häberle & Gülhan, *JPP* 24(3) 2008 / 23(5) 2007 / 24(5) 2008 (박사논문을 받으면 대부분 불필요) | p₀·T₀·Re 3가지, 목 높이, 수치 표 여부 | I7·I11a |

---

### 부록: 이번에 내려받은 공개 PDF
`docs/papers/i1b/`(`.gitignore`의 `docs/papers/`로 커밋 제외 확인됨):
- Edelman 외 NTRS 논문·세미나 자료
- Edelman 박사논문(UMich Deep Blue)
- Emami TP-3502
- Gillespie & Sandham 웹페이지 사본

`smart_rto_en_avt185.pdf`는 이름과 달리 PDF가 아니라 Cloudflare 확인 페이지(HTML)다. 사용자가 실제 PDF를 받으면 이 파일을 덮어쓰면 된다. 그 밖의 후보 문헌은 Science 작업공간에만 있다.
