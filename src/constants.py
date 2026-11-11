"""Project gas constants — the single source (CLAUDE.md rule 4).

Calorically perfect air. Every case dictionary (thermophysicalProperties) and
every analysis script must take gamma, R, Cp from here.

Sutherland coefficients, the laminar conductivity model and the turbulent
Prandtl number were approved by the user at I4 (decisions.md D-013).
"""

# Ratio of specific heats, calorically perfect air.
GAMMA_AIR = 1.4

# Mean molar mass of dry air [kg/kmol] — U.S. Standard Atmosphere 1976 (M0 = 28.9644).
MOLWEIGHT_AIR = 28.9644

# OpenFOAM v2512 universal gas constant [J/(kmol K)]:
# RR = 1e3 * NA * k with NA = 6.0221417930e23 and k = 1.38065e-23
# (src/OpenFOAM/global/constants/thermodynamic/thermodynamicConstants.C,
#  etc/controlDict DimensionedConstants). Using OpenFOAM's own value makes the
# solver's R = RR/molWeight identical to R_AIR below.
RR_OPENFOAM = 1e3 * 6.0221417930e23 * 1.38065e-23

# Specific gas constant [J/(kg K)] (≈ 287.05).
R_AIR = RR_OPENFOAM / MOLWEIGHT_AIR

# Constant-pressure specific heat [J/(kg K)] giving exactly GAMMA_AIR with R_AIR.
CP_AIR = GAMMA_AIR / (GAMMA_AIR - 1.0) * R_AIR

# --- Viscous properties (approved 2026-11-11, decisions.md D-013) -----------------
# Sutherland's law  mu = MU_REF (T/T_REF)^1.5 (T_REF + S)/(T + S)
# Commonly used air values; the same set is used by docs/validation_data.md, and
# S = 110.4 K reproduces TMR's cf_vandriestII.dat to 1e-6 (tests/test_boundary_layer.py).
# Primary source of the three numbers not checked (decisions.md D-013 A).
SUTHERLAND_MU_REF = 1.716e-5   # [Pa s]
SUTHERLAND_T_REF = 273.15      # [K]
SUTHERLAND_S = 110.4           # [K]
# OpenFOAM form  mu = As sqrt(T) / (1 + Ts/T)
SUTHERLAND_AS = SUTHERLAND_MU_REF * (SUTHERLAND_T_REF + SUTHERLAND_S) / SUTHERLAND_T_REF**1.5
SUTHERLAND_TS = SUTHERLAND_S

# Laminar conductivity: OpenFOAM `sutherland` transport uses the modified Eucken
# relation kappa = mu Cv (1.32 + 1.77 R/Cv) (sutherlandTransportI.H, v2512).
# For gamma = 1.4 this gives a constant laminar Prandtl number of about 0.690
# (reference data use 0.71-0.72; the difference is reported, not corrected — D-013 C).
CV_AIR = CP_AIR - R_AIR
PRANDTL_LAMINAR = CP_AIR / (CV_AIR * (1.32 + 1.77 * R_AIR / CV_AIR))

# Turbulent Prandtl number (RAS coefficient `Prt`; OpenFOAM default is 1.0).
PRANDTL_TURBULENT = 0.9
