"""Project gas constants — the single source (CLAUDE.md rule 4).

Calorically perfect air. Every case dictionary (thermophysicalProperties) and
every analysis script must take gamma, R, Cp from here.

Sutherland coefficients are NOT defined yet: they are a physical coefficient
(CLAUDE.md rule 1) and are added with user approval at I4 (first viscous case).
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
