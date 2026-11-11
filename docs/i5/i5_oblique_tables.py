"""I5 보조 계산: 2단 외부 램프 + 카울의 비점성 사충격파 관계 (완전기체, gamma=1.4).

근거 식: NACA Report 1135 (Ames Research Staff, 1953)의 사충격파 theta-beta-M 관계(식 138),
정상충격파 관계(식 93-99), 등엔트로피 면적비(식 80). Kantrowitz & Donaldson (1945) 시동 한계
= 입구에서 정상충격파 후 아음속 등엔트로피 가속으로 목에서 M=1.
이 표는 형상을 추천하지 않는다. 비점성 값이며 경계층에 의한 유효 각 증가(Emami TP-3502: 11° 램프가
약 12° 유효 전향)를 포함하지 않는다.
"""
import numpy as np, csv, sys
from scipy.optimize import brentq

G = 1.4

def theta_from_beta(M, b):
    return np.arctan(2/np.tan(b)*(M**2*np.sin(b)**2-1)/(M**2*(G+np.cos(2*b))+2))

def theta_max(M):
    """부착 사충격파의 최대 전향각 [rad]과 그때의 beta."""
    mu = np.arcsin(1/M)
    bs = np.linspace(mu+1e-6, np.pi/2-1e-6, 20001)
    th = theta_from_beta(M, bs)
    i = np.argmax(th)
    return th[i], bs[i]

def weak_beta(M, th):
    tmax, bmax = theta_max(M)
    if th > tmax: return np.nan
    mu = np.arcsin(1/M)
    return brentq(lambda b: theta_from_beta(M, b)-th, mu+1e-9, bmax)

def shock(M, th):
    b = weak_beta(M, th)
    if np.isnan(b): return dict(beta=np.nan, M2=np.nan, p=np.nan, pt=np.nan, T=np.nan)
    Mn = M*np.sin(b)
    p = 1+2*G/(G+1)*(Mn**2-1)
    rho = (G+1)*Mn**2/((G-1)*Mn**2+2)
    Mn2 = np.sqrt((1+(G-1)/2*Mn**2)/(G*Mn**2-(G-1)/2))
    M2 = Mn2/np.sin(b-th)
    pt = (rho**(G/(G-1)))*((1/p)**(1/(G-1)))
    return dict(beta=b, M2=M2, p=p, pt=pt, T=p/rho)

def area_ratio(M):  # A/A*
    return (1/M)*((2/(G+1))*(1+(G-1)/2*M**2))**((G+1)/(2*(G-1)))

def kantrowitz_Ath_Ai(M):
    """자기 시동 한계 A_th/A_i (이보다 크면 시동). 입구 정상충격파 후 M_y에서 A*/A."""
    My = np.sqrt((1+(G-1)/2*M**2)/(G*M**2-(G-1)/2))
    pt_ratio = shock_normal_pt(M)
    # A_th/A_i = (A*/A)(My) ; 정상충격 후 아음속 등엔트로피
    return 1/area_ratio(My)

def shock_normal_pt(M):
    return (((G+1)*M**2/((G-1)*M**2+2))**(G/(G-1)))*(((G+1)/(2*G*M**2-(G-1)))**(1/(G-1)))

def min_mach_attached(th):
    """전향각 th[rad]에서 부착 사충격파가 가능한 최소 상류 마하수."""
    return brentq(lambda M: theta_max(M)[0]-th, 1.0001, 50)

def lip_point(d1, b1, b2abs, L1=1.0):
    """1단 램프 길이 L1(앞전 원점)일 때 두 램프 충격파 교점 = shock-on-lip 립 위치."""
    xc, yc = L1*np.cos(d1), L1*np.sin(d1)
    t1, t2 = np.tan(b1), np.tan(b2abs)
    x = (yc - xc*t2)/(t1 - t2)
    return x, x*t1

def selftest():
    s = shock(5.0, np.radians(10))
    assert abs(np.degrees(s['beta'])-19.38) < 0.02, np.degrees(s['beta'])
    assert abs(s['p']-3.045) < 0.01, s['p']
    assert abs(np.degrees(theta_max(5.0)[0])-41.12) < 0.02
    assert abs(kantrowitz_Ath_Ai(2.0)-0.822) < 0.003, kantrowitz_Ath_Ai(2.0)
    print('selftest OK: M5 θ10 → β=%.2f°, p2/p1=%.3f; θmax(M5)=%.2f°; Kantrowitz A_th/A_i(M2)=%.3f'
          % (np.degrees(s['beta']), s['p'], np.degrees(theta_max(5.0)[0]), kantrowitz_Ath_Ai(2.0)))

def main(Minf=5.0, out='oblique_M5_two_ramp.csv'):
    selftest()
    rows = []
    for d1 in [6, 8, 10, 12]:
        # 등강도(두 램프 충격파 정압비 같음) δ2
        s1 = shock(Minf, np.radians(d1))
        d2eq = brentq(lambda d: shock(s1['M2'], np.radians(d))['p']-s1['p'], 0.1, np.degrees(theta_max(s1['M2'])[0])-0.01)
        for dt in [16, 18, 20, 22, 24, 26, 28, 30]:
            d2 = dt-d1
            if d2 <= 0: continue
            s2 = shock(s1['M2'], np.radians(d2))
            b2abs = np.radians(d1)+s2['beta']
            xl, yl = lip_point(np.radians(d1), s1['beta'], b2abs)
            tmax2 = np.degrees(theta_max(s2['M2'])[0]) if not np.isnan(s2['M2']) else np.nan
            s3 = shock(s2['M2'], np.radians(dt)) if (not np.isnan(tmax2) and dt < tmax2) else None
            rows.append(dict(
                Minf=Minf, d1=d1, d2=d2, dtot=dt, d2_equal_strength=round(d2eq, 2),
                beta1=round(np.degrees(s1['beta']), 2), M1=round(s1['M2'], 3), p1_pinf=round(s1['p'], 3),
                beta2_rel=round(np.degrees(s2['beta']), 2), beta2_abs=round(np.degrees(b2abs), 2),
                M2=round(s2['M2'], 3), p2_p1=round(s2['p'], 3), p2_pinf=round(s1['p']*s2['p'], 3),
                pt2_ptinf=round(s1['pt']*s2['pt'], 4),
                margin1_deg=round(np.degrees(theta_max(Minf)[0])-d1, 2),
                margin2_deg=round(np.degrees(theta_max(s1['M2'])[0])-d2, 2),
                xlip_L1=round(xl, 4), ylip_L1=round(yl, 4),
                cowl_flat_margin_deg=round(tmax2-dt, 2),
                M3_flat_cowl=(round(s3['M2'], 3) if s3 else 'detached'),
                p3_pinf_flat_cowl=(round(s1['p']*s2['p']*s3['p'], 2) if s3 else 'detached'),
                kantrowitz_Ath_Ai_at_M2=round(kantrowitz_Ath_Ai(s2['M2']), 4),
                isentropic_Ath_Ai_at_M2=round(1/area_ratio(s2['M2']), 4),
                Mmin_ramp1=round(min_mach_attached(np.radians(d1)), 3),
            ))
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return rows

if __name__ == '__main__':
    rows = main()
    print(len(rows), 'rows')


def _first_root(f, a, b, n=400):
    """[a,b]를 훑어 f가 처음 양(부착)으로 바뀌는 구간에서 근을 찾는다. NaN(아음속 후류)은 음으로 취급."""
    g = lambda M: (lambda v: -1.0 if (v is None or np.isnan(v)) else v)(f(M))
    xs = np.linspace(a, b, n)
    prev = xs[0]
    for x in xs[1:]:
        if g(x) > 0 and g(prev) <= 0:
            return brentq(g, prev, x)
        prev = x
    return np.nan


def detach_boundaries(pairs=((6,10),(8,10),(8,12),(10,10),(10,12),(10,14),(12,12)), out='detach_mach_two_ramp.csv'):
    """각 (δ1, δ2)에 대해: 램프1 부착 최소 M∞, 램프2 부착 최소 M∞, 수평 카울(δ1+δ2 되돌림) 부착 최소 M∞.
    모두 비점성, 설계점 외 마하에서 기하 고정 가정."""
    def M1(Minf, d1): return shock(Minf, np.radians(d1))['M2']
    def f2(Minf, d1, d2):
        m1 = M1(Minf, d1)
        return np.nan if np.isnan(m1) else theta_max(m1)[0]-np.radians(d2)
    def f3(Minf, d1, d2):
        m1 = M1(Minf, d1)
        if np.isnan(m1): return -1
        s2 = shock(m1, np.radians(d2))
        if np.isnan(s2['M2']): return -1
        return theta_max(s2['M2'])[0]-np.radians(d1+d2)
    rows = []
    for d1, d2 in pairs:
        m1min = min_mach_attached(np.radians(d1))
        m2min = _first_root(lambda M: f2(M, d1, d2), m1min+1e-3, 20)
        m3min = _first_root(lambda M: f3(M, d1, d2), m2min+1e-3, 30)
        rows.append(dict(d1=d1, d2=d2, dtot=d1+d2, Mmin_ramp1=round(m1min, 3),
                         Mmin_ramp2=round(m2min, 3), Mmin_flat_cowl=round(m3min, 3)))
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return rows

if __name__ == '__main__':
    for r in detach_boundaries(): print(r)
