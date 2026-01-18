# -*- coding: utf-8 -*-
"""
Propulsions Model Restructuring (8/29/2025)
File structure:
    - Numerical methods for numba calculation (bisection, secant, brent, etc)
    - Preprocessing functions for propeller, motor, battery, ESC data
    - PointResult function
    - LinePlot functions (one for each input combo)
    - ContourPlot functions
    - CubicPlot functions
    - Pareto Front functions
    - Mission model compatible functions
    - GEKKO prop model functions for reference 

Primary inputs:
    Battery State Of Charge (SOC) as %
    Freestream Velocity (Vinf) as m/s
    Throttle Setting (dT) as %
    
LinePlot function:
    By fixing two of these inputs, a line plot of a propulsion quantity (propQ) can be plotted with respect to the third.

ContourPlot function:
    By fixing one of these inputs, a contour plot of a propQ is plotted wrt the two unfixed inputs.

CubicPlot function:
    Additionally a cubic plot of propQ variation with all three variables is available, but usually hard to use in reports.

for all of these functions, SOC can be provided as SOC (%), Voc (Volt), or t (s), which assumes constant current (i.e. good for aircraft in cruise)

Available propQs are:
    T (lbf)     (thrust for all motors)
    Q (N*m)     (torque for all motors)
    RPM         (for a single motor/propeler)

nondimensional:
    CT          (propeller (prop) torque constant)
    CP          (propeller power constant)
    eta_p       (propeller efficiency)
    eta_m       (motor efficiency)
    eta_c       (controller (ESC) efficiency)
    eta_drive   (drive efficiency)

all in Watts (W):
    Pout    (mechanical W for a single motor)
    Pin_m   (electric W input to a single motor (equivalent to Pout from a single ESC))
    Pin_c   (electric W input to all ESCs (equivalent to Pout from the battery))
    
all in Ampere (A):
    Im      (motor current for a single motor)
    Ic      (ESC current for a single ESC)
    Ib      (battery current)
    
all in Volts (V):
    Voc     (cell voltage)
    Vb      (battery voltage)
    Vm      (motor voltage)
    Vc      (ESC voltage)
    
    
Propeller coefficients (CT, CP) are primarily acquired by interpolation between the APC technical datasheets 
(see: https://www.apcprop.com/technical-information/performance-data/?v=7516fd43adaa)

These datasheets were generated using Blade Element Theory in conjunction with NASA TAIR and some databases for airfoil data. 
They are NOT fully accurate, especially for propeller stall, which mostly occurs when propellers low diam/pitch ratios travel at lower freestream velocities. 

Use the APCBEMTvsUIUCexpdata.py file to automatically compare APC electric propeller data from both sources!

While a wonderful amount of experimental data has been gathered by Michael Selig of UIUC's group (see: https://m-selig.ae.illinois.edu/props/propDB.html),
this data does not extend into the high performance ranges (say RPMs of 6k-12k for ~15-20 inch diameter propellers) that typically occur with 6-12S liPo batteries.

As of 8/29/2025, this experimental data is not implemented yet, but in the future it will be used in conjunction with the APC data for a mixed fidelity approach.



Model Formulation (primary based on Saemi 2023, secondary if available data based on Gong 2018):
    Simplified RPM (with constant ESC efficiency and constant I0)
    SAEMI 2023: https://www.mdpi.com/2226-4310/11/1/16
    GONG 2018:  https://www.researchgate.net/profile/Andrew-Gong-2/publication/326263042
    Jeong 2020: https://www.researchgate.net/publication/347270768_Improvement_of_Electric_Propulsion_System_Model_for_Performance_Analysis_of_Large-Size_Multicopter_UAVs
    
LiPo discharge curve (Voc(SOC)) from Chen 2006 (https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf):
    Voc = 3.685 - 1.031 * np.exp(-35 * SOC) + 0.2156 * SOC - 0.1178 * SOC**2 + 0.3201 * SOC**3
    
    Alternative from Jeong 2020
    Voc = 1.7*(SOC**3) - 2.1*(SOC**2) + 1.2*SOC + 3.4

In reality the discharge curve (and total capacity) is strongly influenced by cell temperature and battery health. 
Corrections on Voc for battery health are optionally defined by inputting Voc at maximum charge (determined experimentally) (NOT IMPLEMENTED AS OF 8/29/2025).
    
All of the following constants used in the propulsion model are aquired via the Motors, Batteries, and ESCs CSV sheets, which can all be adjusted by any user.
Motor constants:    KV (RPM/V), I0 (A), Rm (Ohm)
Battery constants:  CB (mAh), ns (number of cells in series), Rb (Ohm)

ESC constants (Saemi):      Rds (Ohm), fPWM (Hz), Tsd (s), Psb (W)   <---- currently defaults from Saemi 2023 are used
ESC constants (Gong):       a_m (the slope of constant a), a_0 (y intercept), b, c_m, c_0  <---- only available for a very limited selection of tested ESCs
ESC constnats (Jeong):       #TODO FILL IN JEONG CONSTANTS
    
KV = speed constant, I0 = no-load current, Rm = motor resistance
CB = battery capacity, ns = number of cells (in series), Rb = battery resistance

Simplifed RPM formulation (known Vsoc, Vinf, dT):
    
    RPM guess
    J = Vinf/((RPM/60)*d)
    CP = CPNumba(RPM, J, rpm_list, coef_numba_prop_data)
    Q = rho*((RPM/60)**2)*(d**5)*(CP/(2*np.pi))
    Im = Q*KV*(np.pi/30) + I0 # for one motor
    Ib = (nmot/eta_c)*Im
    Vb = ns*(Voc) - Ib*Rb
    Vm = dT*Vb
    RPMcalc = KV*(Vm - Im*Rm)
    res = RPMcalc - RPM

Simplified RPM formulation (known runtime (t), constant current):

    RPM guess
    J = Vinf/((RPM/60)*d)
    CP = CPNumba(RPM, J, rpm_list, coef_numba_prop_data)
    Q = rho*((RPM/60)**2)*(d**5)*(CP/(2*np.pi))
    Im = Q*KV*(np.pi/30) + I0 # for one motor
    Ib = (nmot/eta_c)*Im
    SOC = 1.0 - (Ib*t)/(CB*3.6)
    Voc = 3.685 - 1.031 * np.exp(-35 * SOC) + 0.2156 * SOC - 0.1178 * SOC**2 + 0.3201 * SOC**3
    Vb = ns*(Voc) - Ib*Rb
    Vm = dT*Vb
    RPMcalc = KV*(Vm - Im*Rm)
    res = RPMcalc - RPM
    
minimize res!

This formulation is advantageous for its computational efficiency. With only one variable, plots can be made extremely quickly.
Significant loss of accuracy due to the constant I0 assumption compared to the other models.

    
@author: NASSAS
"""

import pandas as pd
import numpy as np
from numpy.polynomial import Polynomial
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from tqdm import tqdm
import scipy.optimize as opt
import time
from gekko import GEKKO
import multiprocessing
from functools import partial
import itertools
import numba
from numba import njit, jit
from numba.typed import List
from numba.types import unicode_type
from uavdex.VSPcontribution.atmosphere import stdatm1976 as atm 

lbfN = 4.44822
ftm = 0.3048
MPH_TO_MPS = 0.44704  # Conversion factor: 1 mph to m/s

global propQnames
propQnames = ['Total Thrust (lbf)', 'Total Torque (Nm)', 'RPM', 'Drive Efficiency', 'Propeller Efficiency', 'Gearing Efficiency', 'Motor Efficiency', 'ESC Efficiency', 'Battery Efficiency', 'Mech. Power Out of 1 Motor (W)', 
                   'Elec. Power Into 1 Motor (W)', 'Elec. Power Into 1 ESC (W)', 'Current in 1 Motor (A)', 'Current in 1 ESC (A)', 'Current in Battery (A)',
                   'Voltage in 1 Motor (V)', 'Voltage in 1 ESC (V)', 'Battery Voltage (V)', 'Voltage Per Cell (V)', 'State of Charge']

from uavdex import _uavdex_root
path_to_data = _uavdex_root / 'Databases/'

#%%################### Numerical Methods ###################
# 1D root finding 
@njit(fastmath = True)
def bisection(low, high, func, *args):
    tol = 1e-3
    max_iter = 100
    for _ in range(max_iter):
        print(low, high)
        mid = (low + high) / 2
        res_mid = func(mid, *args)
        
        if res_mid**2 < tol**2 or res_mid == 0.0:
            return(mid)
        
        if res_mid*func(low, *args) < 0:
            high = mid
        else:
            low = mid
    else:
        # essentially error message
        return(-1.0)

@njit(fastmath = True)
def secant(low, high, func, *args):
    tol = 1e-3
    max_iter = 100 
    
    x0 = low 
    x1 = high
    for i in range(max_iter):
        x2 = x1 - func(x1, *args) * (x1 - x0) / (func(x1, *args) - func(x0, *args))
        x0, x1 = x1, x2
        if (x0 - x1)**2 < tol**2 or func(x1, *args)**2 < tol**2:
            return(x2)
    else:
        return(-1.0)

# non-numba version for faster single point analysis
def bisectionBase(low, high, func, *args):
    tol = 1e-3
    max_iter = 100
    for _ in range(max_iter):
        mid = (low + high) / 2
        res_mid = func(mid, *args)
        
        if res_mid**2 < tol**2 or res_mid == 0.0:
            return(mid)
        
        if res_mid*func(low, *args) < 0:
            high = mid
        else:
            low = mid
    else:
        # essentially error message
        return(-1.0)

#%% ################### Data Parsing ###################
def parse_coef_propeller_data(prop_name):
    """
    prop_name in the form: 16x10E, 18x12E, 12x12, etc (no PER3_ and no .dat to make it easier for new users)
    Parses the provided PER3_16x10E.dat content to extract RPM, V (m/s), Thrust (N), Torque (N-m).
    Stores in PROP_DATA as {rpm: {'V': np.array, 'Thrust': np.array, 'Torque': np.array}}
    """    
    PROP_DATA = {}

    with open(path_to_data / f'APCPropDatabase/PER3_{prop_name}.dat', 'r') as f:
        data_content = f.read()

    current_rpm = None
    in_table = False
    table_lines = []
    
    for line in data_content.splitlines():
        line = line.strip()
        if line.startswith("PROP RPM ="):
            # Extract RPM
            current_rpm = int(line.split("=")[-1].strip())
            in_table = False
            table_lines = []
        elif line.startswith("V") and "J" in line and current_rpm is not None:
            # Start of table headers
            in_table = True
        elif in_table and line and not line.startswith("(") and len(line.split()) >= 10:
            # Parse data rows (ensure it's a data line with enough columns)
            parts = line.split()
            try:
                J = float(parts[1])  # advance ratio J
                CT = float(parts[3])  # thrust coef
                CP = float(parts[4])  # power coef (can convert to CQ)
                # v_mps = v_mph * MPH_TO_MPS  # Convert to m/s
                table_lines.append((J, CT, CP))
            except (ValueError, IndexError):
                continue  # Skip malformed lines
        elif in_table and (line == "" or "PROP RPM" in line):
            # End of table for this RPM, store if data exists
            if current_rpm and table_lines:
                J_list, CT_list, CP_list = zip(*sorted(table_lines))  # Sort by V for interp1d
                PROP_DATA[current_rpm] = {
                    'J': np.array(J_list),
                    'CT': np.array(CT_list),
                    'CP': np.array(CP_list)
                }
            in_table = False
    
    # Sort RPM keys for efficient lookup
    PROP_DATA['rpm_list'] = sorted(PROP_DATA.keys())
    
    # array based datastructure where each index corresponds to rpm_values[i] (or i+1*1000 RPM)
    # and in each index there is [[V values], [Thrust values], [Torque values]] at the indices, 0, 1, 2
    numba_prop_data = []
    for RPM in PROP_DATA['rpm_list']:
        datasection = np.array([PROP_DATA[RPM]['J'], 
                                PROP_DATA[RPM]['CT'], 
                                PROP_DATA[RPM]['CP']])
        numba_prop_data.append(datasection)
        
    return(PROP_DATA, numba_prop_data)

def parse_propeller_data(prop_name):
    """
    prop_name in the form: 16x10E, 18x12E, 12x12, etc (no PER3_ and no .dat to make it easier for new users)
    Parses the provided PER3_16x10E.dat content to extract RPM, V (m/s), Thrust (N), Torque (N-m).
    Stores in PROP_DATA as {rpm: {'V': np.array, 'Thrust': np.array, 'Torque': np.array}}
    """    
    PROP_DATA = {}

    with open(path_to_data / f'APCPropDatabase/PER3_{prop_name}.dat', 'r') as f:
        data_content = f.read()

    current_rpm = None
    in_table = False
    table_lines = []
    
    for line in data_content.splitlines():
        line = line.strip()
        if line.startswith("PROP RPM ="):
            # Extract RPM
            current_rpm = int(line.split("=")[-1].strip())
            in_table = False
            table_lines = []
        elif line.startswith("V") and "J" in line and current_rpm is not None:
            # Start of table headers
            in_table = True
        elif in_table and line and not line.startswith("(") and len(line.split()) >= 10:
            # Parse data rows (ensure it's a data line with enough columns)
            parts = line.split()
            try:
                v_mph = float(parts[0])  # V in mph
                torque_nm = float(parts[9])  # Torque (N-m)
                thrust_n = float(parts[10])  # Thrust (N)
                v_mps = v_mph * MPH_TO_MPS  # Convert to m/s
                table_lines.append((v_mps, thrust_n, torque_nm))
            except (ValueError, IndexError):
                continue  # Skip malformed lines
        elif in_table and (line == "" or "PROP RPM" in line):
            # End of table for this RPM, store if data exists
            if current_rpm and table_lines:
                v_list, thrust_list, torque_list = zip(*sorted(table_lines))  # Sort by V for interp1d
                PROP_DATA[current_rpm] = {
                    'V': np.array(v_list),
                    'Thrust': np.array(thrust_list),
                    'Torque': np.array(torque_list)
                }
            in_table = False
    
    # Sort RPM keys for efficient lookup
    PROP_DATA['rpm_list'] = sorted(PROP_DATA.keys())
    
    # array based datastructure where each index corresponds to rpm_values[i] (or i+1*1000 RPM)
    # and in each index there is [[V values], [Thrust values], [Torque values]] at the indices, 0, 1, 2
    numba_prop_data = []
    for RPM in PROP_DATA['rpm_list']:
        datasection = np.array([PROP_DATA[RPM]['V'], 
                                PROP_DATA[RPM]['Thrust'], 
                                PROP_DATA[RPM]['Torque']])
        numba_prop_data.append(datasection)
        
    return(PROP_DATA, numba_prop_data)

def initialize_RPM_polynomials(PROP_DATA):
    """
    returns: rpm_values, thrust_polys, torque_polys, V_DOMAINS
    
    Creates polynomial approximations for thrust and torque that are compatible with GEKKO in the form of Thrust(V) for a fixed RPM
    Uses piecewise polynomials for different RPM ranges.
    """
    
    # Extract data for polynomial fitting
    rpm_values = sorted([rpm for rpm in PROP_DATA.keys() if isinstance(rpm, int)])
    
    # Create coefficient matrices for polynomial approximation
    # We'll use separate polynomials for different velocity ranges
    thrust_polys = {}
    torque_polys = {}
    
    V_DOMAINS = []
    for rpm in rpm_values:
        data = PROP_DATA[rpm]
        V_data = data['V']
        thrust_data = data['Thrust']
        torque_data = data['Torque']
                
        # Fit polynomials (degree 3-4 should be sufficient for most cases)
        thrust_poly = Polynomial.fit(V_data, thrust_data, deg=4)
        thrust_polys[rpm] = thrust_poly
        
        # Fit polynomial to torque data  
        torque_poly = Polynomial.fit(V_data, torque_data, deg=4)
        torque_polys[rpm] = torque_poly
    
        V_DOMAINS.append(torque_poly.domain[1])
    
    V_DOMAINS = np.array(V_DOMAINS)
    return rpm_values, thrust_polys, torque_polys, V_DOMAINS

#%% Numba Interpolation Functions for J, CT, CP data
@njit(fastmath = True)
def CPNumba(RPM, J, rpm_list, numba_prop_data):
    '''
    J: advance ratio

    numba_prop_data is packaged so each index corresponds to (i+1)*1000 RPM 
    with the structure [[Jvalues], [CTvalues], [CPvalues]] for each index
    data[0] = J values, data[1] = CT, data[2] = CP
    '''
    if RPM < rpm_list[0] or RPM > rpm_list[-1] or J < 0:
        return 0.0
    
    idx = np.searchsorted(rpm_list, RPM)
    if idx == 0:
        closest_rpms = [rpm_list[0]]
    elif idx == len(rpm_list):
        closest_rpms = [rpm_list[-1]]
    else:
        closest_rpms = [rpm_list[idx - 1], rpm_list[idx]]
        
    CPs = []
    for rpm in closest_rpms:
        data = numba_prop_data[int(rpm/1000 -1)]
        # NEW CODE WAS NEEDED TO BRING IT TO 0 WHEN J WAS OUTSIDE BOUNDS!!
        if J > data[0].max():
            CPs.append(0.0)
            continue
        CPs.append(np.interp(J, data[0], data[2]))
        
    CPs = np.array(CPs)
    
    if len(closest_rpms) == 1:
        return CPs[0]
    else:
        weight = (RPM - closest_rpms[0]) / (closest_rpms[1] - closest_rpms[0])
        return (1 - weight) * CPs[0] + weight * CPs[1]

@njit(fastmath = True)
def CTNumba(RPM, J, rpm_list, numba_prop_data):
    '''
    J: advance ratio
    
    numba_prop_data is packaged so each index corresponds to (i+1)*1000 RPM 
    with the structure [[Jvalues], [CTvalues], [CPvalues]] for each index
    data[0] = J values, data[1] = CT, data[2] = CP
    '''
    if RPM < rpm_list[0] or RPM > rpm_list[-1] or J < 0:
        return 0.0
    
    idx = np.searchsorted(rpm_list, RPM)
    if idx == 0:
        closest_rpms = [rpm_list[0]]
    elif idx == len(rpm_list):
        closest_rpms = [rpm_list[-1]]
    else:
        closest_rpms = [rpm_list[idx - 1], rpm_list[idx]]
        
    CTs = []
    for rpm in closest_rpms:
        data = numba_prop_data[int(rpm/1000 -1)]
        if J > data[0].max():
            CTs.append(0.0)
            continue
        CTs.append(np.interp(J, data[0], data[1]))
        
    CTs = np.array(CTs)
    
    if len(closest_rpms) == 1:
        return CTs[0]
    else:
        weight = (RPM - closest_rpms[0]) / (closest_rpms[1] - closest_rpms[0])
        return (1 - weight) * CTs[0] + weight * CTs[1]
    

def CPBase(RPM, J, rpm_list, numba_prop_data):
    '''
    J: advance ratio

    numba_prop_data is packaged so each index corresponds to (i+1)*1000 RPM 
    with the structure [[Jvalues], [CTvalues], [CPvalues]] for each index
    data[0] = J values, data[1] = CT, data[2] = CP
    '''
    if RPM < rpm_list[0] or RPM > rpm_list[-1] or J < 0:
        return 0.0
    
    idx = np.searchsorted(rpm_list, RPM)
    if idx == 0:
        closest_rpms = [rpm_list[0]]
    elif idx == len(rpm_list):
        closest_rpms = [rpm_list[-1]]
    else:
        closest_rpms = [rpm_list[idx - 1], rpm_list[idx]]
        
    CPs = []
    for rpm in closest_rpms:
        data = numba_prop_data[int(rpm/1000 -1)]
        # NEW CODE WAS NEEDED TO BRING IT TO 0 WHEN J WAS OUTSIDE BOUNDS!!
        if J > data[0].max():
            CPs.append(0.0)
            continue
        CPs.append(np.interp(J, data[0], data[2]))
        
    CPs = np.array(CPs)
    
    if len(closest_rpms) == 1:
        return CPs[0]
    else:
        weight = (RPM - closest_rpms[0]) / (closest_rpms[1] - closest_rpms[0])
        return (1 - weight) * CPs[0] + weight * CPs[1]

def CTBase(RPM, J, rpm_list, numba_prop_data):
    '''
    J: advance ratio
    
    numba_prop_data is packaged so each index corresponds to (i+1)*1000 RPM 
    with the structure [[Jvalues], [CTvalues], [CPvalues]] for each index
    data[0] = J values, data[1] = CT, data[2] = CP
    
    '''
    if RPM < rpm_list[0] or RPM > rpm_list[-1] or J < 0:
        return 0.0
    
    idx = np.searchsorted(rpm_list, RPM)
    if idx == 0:
        closest_rpms = [rpm_list[0]]
    elif idx == len(rpm_list):
        closest_rpms = [rpm_list[-1]]
    else:
        closest_rpms = [rpm_list[idx - 1], rpm_list[idx]]
    
    CTs = []
    for rpm in closest_rpms:
        data = numba_prop_data[int(rpm/1000 - 1)]
        
        # NEW CODE WAS NEEDED TO BRING IT TO 0 WHEN J WAS OUTSIDE BOUNDS!!
        if J > data[0].max():
            CTs.append(0.0)
            continue
        
        CTs.append(np.interp(J, data[0], data[1]))
    CTs = np.array(CTs)
    
    if len(closest_rpms) == 1:
        return CTs[0]
    else:
        weight = (RPM - closest_rpms[0]) / (closest_rpms[1] - closest_rpms[0])
        return (1 - weight) * CTs[0] + weight * CTs[1]


#%% ####################### PROPULSION MODELS #######################
@njit(fasthmath = True)
def VocFunc(SOC, BattType):
    '''
    Determines the battery Voltage (Voc) as a function of State of Charge (SOC) given from 0-1 for a specified battery chemistry
    
    LiPo
    Main equation from Chen 2006
    https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf
    
    Alternative from Jeong 2020
    Voc = 1.7*(SOC**3) - 2.1*(SOC**2) + 1.2*SOC + 3.4
    https://www.researchgate.net/publication/347270768_Improvement_of_Electric_Propulsion_System_Model_for_Performance_Analysis_of_Large-Size_Multicopter_UAVs
    
    NOTE:
    Jeong 2020 also presents resistance as a function of cell energy:
    Rbatt.cell = 21.0*(ebatt.cell)**-0.8056
    
    
    Liion
    https://www.researchgate.net/publication/346515863_Comparison_of_Lithium-Ion_Battery_Pack_Models_Based_on_Test_Data_from_Idaho_and_Argonne_National_Laboratories
    Using the i3 battery pack as an intermediate value
    
    TODO: implment battery voltage equation adjustments based on predicted health (measured via Vsoc at full charge!)
    '''
    if BattType == 'LiPo':
        return(3.685 - 1.031 * np.exp(-35 * SOC) + 0.2156 * SOC - 0.1178 * SOC**2 + 0.3201 * SOC**3)
    elif BattType == 'Liion':
        return(-4.48*((1-SOC)**5) + 9.09*((1-SOC)**4) - 7.08*((1-SOC)**3) + 2.32*((1-SOC)**2) - 0.76*(1-SOC) + 4.10)
    else:
        raise ValueError('Battery Type not recognized')

#%% Numba SimpleRPM functions (one for precalculated Voc one for t)
@njit(fastmath = True)
def SimpleRPMeqs_Voc(RPM, *args):
    '''
    rho, Voc precalculated from h and SOC (or given directly)
    TODO: full docstring
    '''
    Voc, Uinf, dT, rho, eta_c, eta_g, GR, rpm_list, coef_numba_prop_data, d, ns, np, CB, Rb, BattType, KV, Rm, I0, nmot = args
    J = Uinf/((RPM/60)*d)
    CP = CPNumba(RPM, J, rpm_list, coef_numba_prop_data)
    Qm = (rho*((RPM/60)**2)*(d**5)*CP)/(2*np.pi*GR*eta_g)
    Im = Qm*KV*(np.pi/30) + I0
    Ib = (Im*nmot)/eta_c
    Vb = ns*Voc - Ib*Rb
    Vm = dT*Vb
    RPMcalc = KV*(Vm - Im*Rm)/GR
    return(RPMcalc, J, CP, Qm, Im, Ib, Vb, Vm)

@njit(fastmath = True)
def SimpleRPMeqs_t(RPM, *args):
    '''
    rho precalculated from h and t given to calculate SOC, Voc
    TODO: full docstring
    '''
    t, Uinf, dT, rho, eta_c, eta_g, GR, rpm_list, coef_numba_prop_data, d, ns, np, CB, Rb, BattType, KV, Rm, I0, nmot = args
    J = Uinf/((RPM/60)*d)
    CP = CPNumba(RPM, J, rpm_list, coef_numba_prop_data)
    Qm = (rho*((RPM/60)**2)*(d**5)*CP)/(2*np.pi*GR*eta_g)
    Im = Qm*KV*(np.pi/30) + I0
    Ib = (Im*nmot)/eta_c
    SOC = 1.0 - (Ib*t)/(3.6*CB*np)
    Vb = ns*VocFunc(SOC, BattType) - Ib*Rb
    Vm = dT*Vb
    RPMcalc = KV*(Vm - Im*Rm)/GR
    return(RPMcalc, J, CP, Qm, Im, Ib, Vb, Vm)

# I need some method of setting whether we're inputting h or rho/t or SOC or Voc for the same function
@njit(fastmath = True)
def SimplifiedRPM_Voc(Uinf, dT, rho, Voc, SOC, *args):
    '''
    rho given directly or precalculated from h
    Voc given directly or precalculated from SOC
    TODO: full docstring
    0  1   2       3        4      5      6      7       8    9      10     11   12  13  14  15  16  17  18    19
    T, Q, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
    '''
    ##### Assume ESC efficiency = 0.93 (93%) ##### 
    # note: max ESC efficiency occurs at dT = 1.0
    eta_c = 0.93
    
    # in the future could optimize parameters passed for memory, for now, it aids readability to pass everything
    GR, rpm_list, coef_numba_prop_data, d, ns, np, CB, Rb, BattType, KV, Rm, I0, nmot = args
    
    # Gearing efficiency
    if GR != 1.0:
        eta_g = 0.94 # 94% gear efficiency assumed
    else:
        eta_g = 1.0

    def residualfunc(RPM, *args):
        RPMcalc = SimpleRPMeqs_Voc(RPM, *args)[0]
        res = RPMcalc - RPM
        return(res)
    
    # Vbattinit = throttle*3.6*ns
    high = rpm_list[-1]
    low = rpm_list[0]
    RPM = bisection(low, high, residualfunc, Voc, Uinf, dT, rho, eta_c, eta_g *args)
    
    _, J, CP, Q, Im, Ib, Vb, Vm = SimpleRPMeqs_Voc(RPM, Voc, Uinf, dT, rho, eta_c, eta_g *args)
    CT = CTNumba(RPM, J, rpm_list, coef_numba_prop_data) 
    Ic = Ib/nmot 
    Vc = Vb 
    
    Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
    Pin_m = Vm*Im                           # electric power into one motor
    Pin_c = Vc*Ic                           # electric power into one controller
    
    eta_p = (CT*J)/CP
    eta_m = Pout/Pin_m 
    eta_c = Pin_m/Pin_c 
    eta_b = 1.0 - (Ib**2)*Rb/(nmot*Pin_c + ((Ib**2)*Rb))
    eta_drive = (eta_p*eta_g*eta_m*eta_c)*eta_b
    
    T = nmot*rho*((RPM/60)**2)*(d**4)*CT
    Q *= nmot
    return([T, Q, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC])


# I need some method of setting whether we're inputting h or rho/t or SOC or Voc for the same function
@njit(fastmath = True)
def SimplifiedRPM_t(Uinf, dT, rho, t, *args):
    '''
    rho given directly or precalculated from h
    t given directly
    TODO: full docstring
    '''
    ##### Assume ESC efficiency = 0.93 (93%) ##### 
    # note: max ESC efficiency occurs at dT = 1.0
    eta_c = 0.93
    
    # in the future could optimize parameters passed for memory, for now, it aids readability to pass everything
    GR, rpm_list, coef_numba_prop_data, d, ns, np, CB, Rb, BattType, KV, Rm, I0, nmot = args
    
    # Gearing efficiency
    if GR != 1.0:
        eta_g = 0.94 # 94% gear efficiency assumed
    else:
        eta_g = 1.0

    def residualfunc(RPM, *args):
        RPMcalc = SimpleRPMeqs_t(RPM, *args)[0]
        res = RPMcalc - RPM
        return(res)
    
    # Vbattinit = throttle*3.6*ns
    high = rpm_list[-1]
    low = rpm_list[0]
    RPM = bisection(low, high, residualfunc, t, Uinf, dT, rho, eta_c, eta_g *args)
    
    _, J, CP, Q, Im, Ib, Vb, Vm = SimpleRPMeqs_t(RPM, t, Uinf, dT, rho, eta_c, eta_g *args)
    CT = CTNumba(RPM, J, rpm_list, coef_numba_prop_data) 
    Ic = Ib/nmot 
    Vc = Vb 
    
    Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
    Pin_m = Vm*Im                           # electric power into one motor
    Pin_c = Vc*Ic                           # electric power into one controller
    
    eta_p = (CT*J)/CP
    eta_m = Pout/Pin_m 
    eta_c = Pin_m/Pin_c 
    eta_b = 1.0 - (Ib**2)*Rb/(nmot*Pin_c + ((Ib**2)*Rb))
    eta_drive = (eta_p*eta_g*eta_m*eta_c)*eta_b
    
    SOC = 1.0 - (Ib*t)/(3.6*CB*np)
    Voc = VocFunc(SOC, BattType)
    
    T = nmot*rho*((RPM/60)**2)*(d**4)*CT
    Q *= nmot
    return([T, Q, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC])


#%% Non-Numba SimpleRPM functions (one for precalculated Voc one for t)
def VocFuncBase(SOC, BattType):
    '''
    Determines the battery Voltage (Voc) as a function of State of Charge (SOC) given from 0-1 for a specified battery chemistry
    
    LiPo
    Main equation from Chen 2006
    https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf
    
    Alternative from Jeong 2020
    Voc = 1.7*(SOC**3) - 2.1*(SOC**2) + 1.2*SOC + 3.4
    https://www.researchgate.net/publication/347270768_Improvement_of_Electric_Propulsion_System_Model_for_Performance_Analysis_of_Large-Size_Multicopter_UAVs
    
    NOTE:
    Jeong 2020 also presents resistance as a function of cell energy:
    Rbatt.cell = 21.0*(ebatt.cell)**-0.8056
    
    
    Liion
    https://www.researchgate.net/publication/346515863_Comparison_of_Lithium-Ion_Battery_Pack_Models_Based_on_Test_Data_from_Idaho_and_Argonne_National_Laboratories
    Using the i3 battery pack as an intermediate value
    
    TODO: implment battery voltage equation adjustments based on predicted health (measured via Vsoc at full charge!)
    '''
    if BattType == 'LiPo':
        return(3.685 - 1.031 * np.exp(-35 * SOC) + 0.2156 * SOC - 0.1178 * SOC**2 + 0.3201 * SOC**3)
    elif BattType == 'Liion':
        return(-4.48*((1-SOC)**5) + 9.09*((1-SOC)**4) - 7.08*((1-SOC)**3) + 2.32*((1-SOC)**2) - 0.76*(1-SOC) + 4.10)
    else:
        raise ValueError('Battery Type not recognized')

def SimpleRPMeqsBase_Voc(RPM, *args):
    '''
    rho, Voc precalculated from h and SOC (or given directly)
    TODO: full docstring
    '''
    Voc, Uinf, dT, rho, eta_c, eta_g, GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot = args
    J = Uinf/((RPM/60)*d)
    CP = CPBase(RPM, J, rpm_list, coef_numba_prop_data)
    Qm = (rho*((RPM/60)**2)*(d**5)*CP)/(2*np.pi*GR*eta_g)
    Im = Qm*KV*(np.pi/30) + I0
    Ib = (Im*nmot)/eta_c
    Vb = ns*Voc - Ib*Rb
    Vm = dT*Vb
    RPMcalc = KV*(Vm - Im*Rm)/GR
    return(RPMcalc, J, CP, Qm, Im, Ib, Vb, Vm)

def SimpleRPMeqsBase_t(RPM, *args):
    '''
    rho precalculated from h and t given to calculate SOC, Voc
    TODO: full docstring
    '''
    t, Uinf, dT, rho, eta_c, eta_g, GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot = args
    J = Uinf/((RPM/60)*d)
    CP = CPBase(RPM, J, rpm_list, coef_numba_prop_data)
    Qm = (rho*((RPM/60)**2)*(d**5)*CP)/(2*np.pi*GR*eta_g)
    Im = Qm*KV*(np.pi/30) + I0
    Ib = (Im*nmot)/eta_c
    SOC = 1.0 - (Ib*t)/(3.6*CB*np_batt)
    Vb = ns*VocFuncBase(SOC, BattType) - Ib*Rb
    Vm = dT*Vb
    RPMcalc = KV*(Vm - Im*Rm)/GR
    return(RPMcalc, J, CP, Qm, Im, Ib, Vb, Vm)

# I need some method of setting whether we're inputting h or rho/t or SOC or Voc for the same function
def SimplifiedRPMBase_Voc(Uinf, dT, rho, Voc, SOC, *args):
    '''
    rho given directly or precalculated from h
    Voc given directly or precalculated from SOC
    TODO: full docstring
    '''
    ##### Assume ESC efficiency = 0.93 (93%) ##### 
    # note: max ESC efficiency occurs at dT = 1.0
    eta_c = 0.93
    
    # in the future could optimize parameters passed for memory, for now, it aids readability to pass everything
    GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot = args
    
    # Gearing efficiency
    if GR != 1.0:
        eta_g = 0.94 # 94% gear efficiency assumed
    else:
        eta_g = 1.0

    def residualfunc(RPM, *args):
        RPMcalc = SimpleRPMeqsBase_Voc(RPM, *args)[0]
        res = RPMcalc - RPM
        return(res)
    
    high = rpm_list[-1]
    low = rpm_list[0]
    RPM = bisectionBase(low, high, residualfunc, Voc, Uinf, dT, rho, eta_c, eta_g, *args)
    
    _, J, CP, Q, Im, Ib, Vb, Vm = SimpleRPMeqsBase_Voc(RPM, Voc, Uinf, dT, rho, eta_c, eta_g, *args)
    CT = CTBase(RPM, J, rpm_list, coef_numba_prop_data) 
    Ic = Ib/nmot 
    Vc = Vb 
    
    Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
    Pin_m = Vm*Im                           # electric power into one motor
    Pin_c = Vc*Ic                           # electric power into one controller
    
    eta_p = (CT*J)/CP
    eta_m = Pout/Pin_m 
    eta_c = Pin_m/Pin_c 
    eta_b = 1.0 - ((Ib**2)*Rb)/(nmot*Pin_c + ((Ib**2)*Rb))
    eta_drive = eta_p*eta_g*eta_m*eta_c*eta_b # took out divided by nmot, REVIEW later
    
    T = nmot*rho*((RPM/60)**2)*(d**4)*CT
    
    # eta_drive_pt2 = (T*Uinf)/(nmot*Pin_c + (Ib**2)*Rb)
    # print(eta_drive_pt2)
    Q *= nmot
    
    # print(Pout)
    # CP = CPBase(RPM, J, rpm_list, coef_numba_prop_data)
    # Qm = (rho*((RPM/60)**2)*(d**5)*CP)/(2*np.pi*GR*eta_g)
    # print(Qm*RPM*np.pi / 30)
    # print((T/nmot)*Uinf)
    # print((T*Uinf) / (nmot*Pin_c))
    return([T, Q, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC])


# I need some method of setting whether we're inputting h or rho/t or SOC or Voc for the same function
def SimplifiedRPMBase_t(Uinf, dT, rho, t, *args):
    '''
    rho given directly or precalculated from h
    t given directly
    TODO: full docstring
    '''
    ##### Assume ESC efficiency = 0.93 (93%) ##### 
    # note: max ESC efficiency occurs at dT = 1.0
    eta_c = 0.93
    
    # in the future could optimize parameters passed for memory, for now, it aids readability to pass everything
    GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot = args
    
    # Gearing efficiency
    if GR != 1.0:
        eta_g = 0.94 # 94% gear efficiency assumed
    else:
        eta_g = 1.0

    def residualfunc(RPM, *args):
        RPMcalc = SimpleRPMeqsBase_t(RPM, *args)[0]
        res = RPMcalc - RPM
        return(res)
    
    # Vbattinit = throttle*3.6*ns
    high = rpm_list[-1]
    low = rpm_list[0]
    RPM = bisectionBase(low, high, residualfunc, t, Uinf, dT, rho, eta_c, eta_g, *args)
    
    _, J, CP, Q, Im, Ib, Vb, Vm = SimpleRPMeqsBase_t(RPM, t, Uinf, dT, rho, eta_c, eta_g, *args)
    if RPM < 0.0:
        raise ValueError('Infeasible input combination')
        
    CT = CTBase(RPM, J, rpm_list, coef_numba_prop_data) 
    Ic = Ib/nmot 
    Vc = Vb 
    
    Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
    Pin_m = Vm*Im                           # electric power into one motor
    Pin_c = Vc*Ic                           # electric power into one controller

    eta_p = (CT*J)/CP
    eta_m = Pout/Pin_m 
    eta_c = Pin_m/Pin_c 
    eta_b = 1.0 - ((Ib**2)*Rb)/(nmot*Pin_c + ((Ib**2)*Rb)) # TODO ensure battery efficiency varies with runtime: https://ntrs.nasa.gov/api/citations/20205004497/downloads/Battery_Evaluation_EATS_07_15_20.pdf
    eta_drive = eta_p*eta_g*eta_m*eta_c*eta_b # took out divided by nmot, REVIEW later
    
    T = nmot*rho*((RPM/60)**2)*(d**4)*CT
    
    # eta_drive_pt2 = (T*Uinf)/(nmot*Pin_c + (Ib**2)*Rb)
    # print(eta_drive_pt2)
    Q *= nmot
    
    # print(Pout)
    # CP = CPBase(RPM, J, rpm_list, coef_numba_prop_data)
    # Qm = (rho*((RPM/60)**2)*(d**5)*CP)/(2*np.pi*GR*eta_g)
    # print(Qm*RPM*np.pi / 30)
    # print((T/nmot)*Uinf)
    # print((T*Uinf) / (nmot*Pin_c))
    
    SOC = 1.0 - (Ib*t)/(3.6*CB*np_batt)
    Voc = VocFuncBase(SOC, BattType)
    
    return([T, Q, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC])


#%%################## PLOTTING FUNCTIONS ##################

################################# PointResult #################################
def exactly_one_defined(*args) -> bool:
    return sum(x is not None for x in args) == 1

def PointResultFunc(self, Uinf = None, dT = None, rho = None, h = None, SOC = None, Voc = None, t = None, verbose = True):
    ''' 
    PointResult for fixed Uinf, dT, t/SOC/Voc, h/rho
        
    Outputs
    --------------------------------
    array of:
        
    0  1   2       3        4      5      6      7       8    9      10     11   12  13  14  15  16  17  18    19
    T, Q, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
    
    '''
    args = (self.GR, self.rpm_list, self.COEF_NUMBA_PROP_DATA, self.propdiam, 
            self.ns, self.np, self.CB, self.Rb, self.BattType, 
            self.KV, self.Rm, self.I0, self.nmot)
    if not exactly_one_defined(t, SOC, Voc):
        raise ValueError("Exactly one of t, SOC, or Voc must be provided")
        
    if not exactly_one_defined(rho, h):
        raise ValueError("Exactly one of h or rho must be provided")
    
    if h is not None:
        rho = atm().rho(h)
                
    if t is not None:
        try:
            propQs = SimplifiedRPMBase_t(Uinf, dT, rho, t, *args)
        except:
            print('ERROR: Infeasible input combination, try reducing runtime')
            return(np.zeros(20))
        if propQs[19] < 0.0:
            print('ERROR: SOC < 0% for that runtime')
            return(np.zeros(20))
    else:
        if SOC is not None:
            Voc = VocFuncBase(SOC, self.BattType)
        else:
            SOC = -0.5
        # find SOC from Voc? (too costly imo...)
        try:
            propQs = SimplifiedRPMBase_Voc(Uinf, dT, rho, Voc, SOC, *args)
        except:
            print('ERROR: Infeasible input combination, try reducing runtime')
            return(np.zeros(20))
        
    if verbose:
        if t is not None:
            print(f'\nAt Uinf = {Uinf/ftm:.2f} ft/s, Throttle = {dT*100:.0f}%, Density = {rho:.3f} kg/m3, Runtime = {t:.1f} s')
        elif SOC is not None and SOC > 0.0:
            print(f'\nAt Uinf = {Uinf/ftm:.2f} ft/s, Throttle = {dT*100:.0f}%, Density = {rho:.3f} kg/m3, SOC = {SOC*100:.0f}%')
        elif Voc is not None:
            print(f'\nAt Uinf = {Uinf/ftm:.2f} ft/s, Throttle = {dT*100:.0f}%, Density = {rho:.3f} kg/m3, Voc = {Voc:.2f} V')

        for i, name in enumerate(propQnames):
            if name == 'Total Thrust (lbf)':
                print(f'{name:30} = {propQs[i]/lbfN:.3f}')
            elif 'Efficiency' in name:
                print(f'{name:30} = {propQs[i]*100:.2f}%')
            elif 'State of Charge' in name:
                print(f'{name:30} = {propQs[i]*100:.2f}%')
            else:
                print(f'{name:30} = {propQs[i]:.3f}')
    return(np.array(propQs))

# #%% OLD WORK

# # TODO: Gather validation data on models and add some notes about assumption accuracy to the documentation
# # TODO: add in switch between SOC/t/Vsoc inputs!
# @njit(fastmath = True)
# def SimplifiedRPM(Vinf, dT, SOC_Voc, *args):
#     '''
#     SimplifiedRPM applies a fixed ESC efficiency. This assumption allows for 
#     computation simplifications. # TODO: ADD VALIDATION DATA ABOUT DROP IN ACCURACY!
    
#     Inputs:
#     ------------------------------------------------------------------------------------------------------------------
#     Vinf:       freestream velocity in m/s
#     dT:         throttle setting (0-1) corresponding to the duty ratio of the ESC
#     SOC/Voc:    battery State Of Charge (0-1) OR cell voltage (2.6-4.2 for LiPo)
    
#     *args has a list of propulsion characteristics and constants:
#         rpm_list is the list of provided RPMs with the corresponding coef_numba_prop_data
#         CB:     battery capacity (mAh)
#         ns:     number of cells in series
#         Rb:     battery resistance (Ohm)
#         KV:     motor constant (RPM/Volts)
#         Rm:     motor resistance (Ohm)
#         nmot:   number of motors
        
#         I0: motor no load current (A) 
#         ^^^^^^^^^^^^ Treatment of I0 is the largest simplification in the model; 
#                      in practice I0 is not constant but varies linearly with Vm (Gong 2018)
        
#         ds:     max discharge (as a fraction between 0.0-1.0) 
#         rho:    air density (kg/m3)
#         d:      prop diameter (m)
        
    
#     Outputs:
#     ------------------------------------------------------------------------------------------------------------------

#     a list of the following values with corresponding indicies,
    
#         0, 1,   2,     3,       4,     5,     6,     7,     8,     9,  10, 11, 12, 13, 14, 15, 16,    17
#         T, Q, RPM, eta_drive, eta_p, eta_m, eta_c, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC_Voc
    
#     where:
        
#         T           thrust (lbf) (combined for all motors)
#         Q           torque (N*m) (combined for all motors)
#         RPM
        
#         eta_drive   combined efficiency
#         eta_p       prop efficiency
#         eta_m       motor efficiency
#         eta_c       controller (ESC) efficiency
        
#         Pout        for one motor mechanical W (Q*kt = Q*KV*(pi/30))
#         Pin_m       for one motor electric W
#         Pin_c       for one ESC electric W
        
#         Im          motor current
#         Ic          controller current
#         Ib          battery current
        
#         Vm          motor voltage
#         Vc          controller voltage
#         Vb          battery voltage
#         Voc         cell voltage (open circuit)
    
#     While selection of whether to use the combined variable or the variable for one motor might seem arbitrary,
#     it was chosen based off constraint requirements. Constraining by the motor Pmax requires knowing the electrical
#     power in one motor. Calculating cruise velocity requires knowing the total thrust. 
#     '''
#     ##### Assume ESC efficiency = 0.93 (93%) ##### 
#     # note: max ESC efficiency occurs at dT = 1.0
#     eta_c = 0.93

#     # in the future could optimize parameters passed for memory, for now, it aids readability to pass everything
#     rpm_list, coef_numba_prop_data, CB, ns, Rb, KV, Rm, nmot, I0, ds, rho, d = args

#     # when inputing SOC, Voc is constant. When inputting t and using the constant Ib approximation, it has to be included inside the residual function (so make a new function for that!)
    
#     # stopgap solution, works because SOC will always be between 0-1 and Voc (for LiPo batteries) will always be > 2.5
#     # could pose problems if you're trying to integrate NiCaD batteries later
#     if SOC_Voc > 1.0:
#         Voc = SOC_Voc
#     else:
#         Voc = VocFunc(SOC_Voc)
        
#     def residualfunc(RPM, *args):
#         RPMcalc = SimpleRPMeqs(RPM, *args)[0]
#         res = RPMcalc - RPM
#         return(res)

#     # Vbattinit = throttle*3.6*ns
#     high = rpm_list[-1]
#     low = rpm_list[0]
#     RPM = bisection(low, high, residualfunc, Vinf, Voc, dT, eta_c, *args)
    
#     _, J, CP, Q, Im, Ib, Vb, Vm = SimpleRPMeqs(RPM, Vinf, Voc, dT, eta_c, *args)
#     CT = CTNumba(RPM, J, rpm_list, coef_numba_prop_data) 
#     Ic = Ib/nmot 
#     Vc = Vb 
    
#     Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
#     Pin_m = Vm*Im                           # electric power into one motor
#     Pin_c = Vc*Ic                           # electric power into one controller
    
#     eta_p = (CT*J)/CP
#     eta_m = Pout/Pin_m 
#     eta_c = Pin_m/Pin_c 
#     eta_drive = eta_p*eta_m*eta_c
    
#     T = nmot*rho*((RPM/60)**2)*(d**4)*CT
#     Q *= nmot
#     return([T, Q, RPM, eta_drive, eta_p, eta_m, eta_c, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC_Voc])

# @njit(fastmath = True)
# def SimpleRPMeqs_t(RPM, *args):
#     Vinf, t, dT, eta_c, rpm_list, coef_numba_prop_data, CB, ns, Rb, KV, Rm, nmot, I0, ds, rho, d = args
#     J = Vinf/((RPM/60)*d) # advance ratio J = velocity/nD where n is rev/s and D is propeller diameter in m (velocity in m/s ofc)
#     CP = CPNumba(RPM, J, rpm_list, coef_numba_prop_data)
#     Q = rho*((RPM/60)**2)*(d**5)*(CP/(2*np.pi))
#     Im = Q*KV*(np.pi/30) + I0 # for one motor
#     Ib = (Im*nmot)/eta_c
#     SOC = 1.0 - (Ib*t)/(CB*3.6)
#     Vb = ns*(VocFunc(SOC)) - Ib*Rb
#     Vm = dT*Vb
#     RPMcalc = KV*(Vm - Im*Rm)
#     return(RPMcalc, J, CP, Q, SOC, Im, Ib, Vb, Vm)

# @njit(fastmath = True)
# def SimplifiedRPM_t(Vinf, dT, t, *args):
#     '''Same as SimplifiedRPM but assumes a constant current across a specified runtime
    
#     Returns zero for all values when SOC < the designated max, discharge'''
#     eta_c = 0.93
#     rpm_list, coef_numba_prop_data, CB, ns, Rb, KV, Rm, nmot, I0, ds, rho, d = args
    
#     def residualfunc(RPM, *args):
#         RPMcalc = SimpleRPMeqs_t(RPM, *args)[0]
#         res = RPMcalc - RPM
#         return(res)

#     # Vbattinit = throttle*3.6*ns
#     high = rpm_list[-1]
#     low = rpm_list[0]
#     RPM = bisection(low, high, residualfunc, Vinf, t, dT, eta_c, *args)
    
#     _, J, CP, Q, SOC, Im, Ib, Vb, Vm = SimpleRPMeqs_t(RPM, Vinf, t, dT, eta_c, *args)
    
#     if SOC < 1 - ds:
#         return([0.0]*20)
    
#     CT = CTNumba(RPM, J, rpm_list, coef_numba_prop_data) 
#     Ic = Ib/nmot 
#     Vc = Vb 
#     Voc = VocFunc(SOC)
    
#     Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
#     Pin_m = Vm*Im                           # electric power into one motor
#     Pin_c = Vc*Ic                           # electric power into one controller
    
#     eta_p = (CT*J)/CP
#     eta_m = Pout/Pin_m 
#     eta_c = Pin_m/Pin_c 
#     eta_drive = eta_p*eta_m*eta_c
    
#     T = nmot*rho*((RPM/60)**2)*(d**4)*CT
#     Q *= nmot
#     return([T, Q, RPM, eta_drive, eta_p, eta_m, eta_c, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC*100])
    

# ############## Non-numbified functions for faster PointResults ##############
# def VocFuncBase_LiPo(SOC):
#     return(3.685 - 1.031 * np.exp(-35 * SOC) + 0.2156 * SOC - 0.1178 * SOC**2 + 0.3201 * SOC**3)

# def VocFuncBase_Liion(SOC):
#     '''
#     Li-ion!!
#     https://www.researchgate.net/publication/346515863_Comparison_of_Lithium-Ion_Battery_Pack_Models_Based_on_Test_Data_from_Idaho_and_Argonne_National_Laboratories
    
#     Using the i3 battery pack bc it seems most representative (keep in mind that it is older than most)
#     '''
#     # i3_coeffs = [-4.48, 9.09, -7.08, 2.32, -0.76, 4.10]
#     return(-4.48*((1-SOC)**5) + 9.09*((1-SOC)**4) - 7.08*((1-SOC)**3) + 2.32*((1-SOC)**2) - 0.76*(1-SOC) + 4.10)

# def SimpleRPMeqsBase(RPM, *args):
#     Vinf, Voc, dT, eta_c, rpm_list, coef_numba_prop_data, CB, ns, Rb, KV, Rm, nmot, I0, ds, rho, d = args
#     J = Vinf/((RPM/60)*d) # advance ratio J = velocity/nD where n is rev/s and D is propeller diameter in m (velocity in m/s ofc)
#     CP = CPBase(RPM, J, rpm_list, coef_numba_prop_data)
#     Q = rho*((RPM/60)**2)*(d**5)*(CP/(2*np.pi))
#     Im = Q*KV*(np.pi/30) + I0 # for one motor
#     Ib = (Im*nmot)/eta_c
#     Vb = ns*(Voc) - Ib*Rb
#     Vm = dT*Vb
#     RPMcalc = KV*(Vm - Im*Rm)
#     return(RPMcalc, J, CP, Q, Im, Ib, Vb, Vm)

# def SimplifiedRPMBase(Vinf, dT, SOC_Voc, *args):
#     eta_c = 0.93
#     rpm_list, coef_numba_prop_data, CB, ns, Rb, KV, Rm, nmot, I0, ds, rho, d = args
#     if SOC_Voc > 1.0: # WON'T WORK IF Voc EVER DIPS BELOW 1.0 FOR A GIVEN BATTERY CHEMISTRY!
#         Voc = SOC_Voc
#     else:
#         Voc = VocFunc(SOC_Voc)
#         # SOC_Voc *= 100
    
#     def residualfunc(RPM, *args):
#         RPMcalc = SimpleRPMeqsBase(RPM, *args)[0]
#         res = RPMcalc - RPM
#         return(res)
    
#     high = rpm_list[-1]
#     low = rpm_list[0]
#     RPM = bisectionBase(low, high, residualfunc, Vinf, Voc, dT, eta_c, *args)
#     if RPM < 0.0:
#         return(np.zeros(18))
#     _, J, CP, Q, Im, Ib, Vb, Vm = SimpleRPMeqsBase(RPM, Vinf, Voc, dT, eta_c, *args)
#     CT = CTBase(RPM, J, rpm_list, coef_numba_prop_data) 
#     Ic = Ib/nmot 
#     Vc = Vb 
#     Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
#     Pin_m = Vm*Im                           # electric power into one motor
#     Pin_c = Vc*Ic                           # electric power into one controller
#     eta_p = (CT*J)/CP
#     eta_m = Pout/Pin_m 
#     eta_c = Pin_m/Pin_c 
#     eta_drive = eta_p*eta_m*eta_c
#     T = nmot*rho*((RPM/60)**2)*(d**4)*CT
#     Q *= nmot
    
    
#     return([T, Q, RPM, eta_drive, eta_p, eta_m, eta_c, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC_Voc])

# #%%################## PLOTTING FUNCTIONS ##################

# ################################# PointResult #################################
# def PointResult(self, Vinf, SOC_Voc, dT, verbose = True):
#     ''' 
#     PointResult for fixed Vinf, SOC, dT
    
#     Does not accept runtime t yet, only SOC and Voc
    
#     Outputs
#     --------------------------------
#     array of: [T, Q, RPM, eta_drive, eta_p, eta_m, eta_c, eta_b, Pout, Pin_m, Pin_c, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC_Voc]
    
#     TODO: allow PointResult to take in a runtime'''

#     args = (self.rpm_list, self.COEF_NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
#             self.KV, self.Rm, self.nmot, self.I0, self.ds, self.rho, self.propdiam)
#     propQs = SimplifiedRPMBase(Vinf, dT, SOC_Voc, *args)
#     if verbose:
#         if SOC_Voc > 1.0:
#             print(f'\nAt Vinf = {Vinf/ftm:.4f} ft/s, Voc = {SOC_Voc:.4f} V, Throttle = {dT*100:.0f}%')
#         else:
#             print(f'\nAt Vinf = {Vinf/ftm:.4f} ft/s, SOC = {SOC_Voc*100:.0f}%, Throttle = {dT*100:.0f}%')
#         for i, name in enumerate(propQnames):
#             if name == 'Total Thrust (lbf)':
#                 print(f'{name:30} = {propQs[i]/lbfN:.4f}')
#             elif 'Efficiency' in name:
#                 print(f'{name:30} = {propQs[i]*100:.4f}%')
#             else:
#                 print(f'{name:30} = {propQs[i]:.4f}')
#     return(np.array(propQs))













# ################################# LinePlots ####################################
# # SOC, dT fixed with propQ vs Vinf
# # SOC, velocity fixed with propQ vs dT
# # dT, velocity fixed with propQ vs SOC
# # TODO: replace Rint everywhere with Rb, same with Ibat to Ib, etc
# @njit(fastmath = True)
# def process_LinePlot_Vinf_SOC(Vs, SOC_Voc, dT, propQindx, *args):
#     ''' To allow for numbification without needing to recompile every iteration '''
#     outputs = []
#     thrusts = []
#     for Vinf in Vs:
#         propQ = SimplifiedRPM(Vinf, dT, SOC_Voc, *args)
#         outputs.append(propQ[propQindx])
#         thrusts.append(propQ[0])
#     return(outputs, thrusts)

# @njit(fastmath = True)
# def process_LinePlot_Vinf_t(Vs, t, dT, propQindx, *args):
#     ''' Identical to above function but uses the constant current t approximation '''
#     outputs = []
#     thrusts = []
#     for Vinf in Vs:
#         propQ = SimplifiedRPM_t(Vinf, dT, t, *args)
#         outputs.append(propQ[propQindx])
#         thrusts.append(propQ[0])
#     return(outputs, thrusts)
        
# def LinePlot_Vinf(self, SOC_Voc_t, dT, plot = True, n = 200, sigfigs = 4):
#     '''
#     Line plot of propQ vs Vinf at fixed SOC/Voc/t, dT
    
#     Needs to accomidate SOC, Voc, t inputs
    
#     (propQ = propulsion quantity, see SimplifiedRPM documentation for options) 
#     '''
    
#     # checking that requested propQ exists
#     propQs = ['thrust', 'torque', 'RPM', 'eta_drive', 'eta_p', 'eta_m', 'eta_c',  
#               'Pout', 'Pin_m', 'Pin_c', 'Im', 'Ic', 'Ib', 'Vm', 'Vc', 'Vb', 'Voc', 'SOC']
    
#     try:
#         interestindex = propQs.index(self.propQ)
#         if self.SOCinput:
#             print(f'\nPlotting {self.propQ} for SOC = {SOC_Voc_t*100:.0f}%, throttle = {dT*100:.0f}%')
#         elif self.Vocinput:
#             print(f'\nPlotting {self.propQ} for Voc = {SOC_Voc_t:.4f} V, throttle = {dT*100:.0f}%')
#         elif self.tinput:
#             print(f'\nPlotting {self.propQ} for t = {SOC_Voc_t:.1f} s, throttle = {dT*100:.0f}%')
#     except:
#         print('Quantity not available, please choose one of:\nthrust, torque, RPM, eta_p, eta_m, eta_c, eta_drive, Pout, Pin_m, Pin_c, Im, Ic, Ib, Voc, Vbat, Vm, Vc, SOC')
#         return()
    
#     rpm_list = np.array(self.RPM_VALUES)

#     #################################################################
#     #### NEED A FUNCTION THAT GETS THE MAXIMUM VELOCITY FIRST #######
#     Vs = np.linspace(0, 50, n)        # FOR NOW APPROXIMATE AS 50 M/S
#     #################################################################
    
#     args = (rpm_list, self.COEF_NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
#             self.KV, self.Rm, self.nmot, self.I0, self.ds, self.rho, self.propdiam)
    
#     if self.tinput:
#         outs, Ts = process_LinePlot_Vinf_t(Vs, SOC_Voc_t, dT, interestindex, *args)
#         # if outs.count(0.0) > 3:
#         #     raise ValueError('Warning: input runtime too long')
#         # TODO: find a way to properly illustrate to ignorant users that where the plot goes to 0 is when SOC is less than max discharge
#     else:
#         outs, Ts = process_LinePlot_Vinf_SOC(Vs, SOC_Voc_t, dT, interestindex, *args)        

#     propQs = np.array(outs)
#     T = np.array(Ts)
    
#     if self.propQ == 'thrust': # convert to lbf if thrust is used 
#         propQs /= lbfN

#     # finding cruise velocity at the given SOC, dT
#     D = 0.5*self.rho*self.CD*self.Sw*(Vs**2) # metric here
#     cruise_idx = np.argmin(np.abs(T-D))
#     cruise_D = D[cruise_idx]
#     cruise_V = np.sqrt(cruise_D/(0.5*self.rho*self.CD*self.Sw)) # in m/s
    
#     # TODO: add max/min and cruise values to the plot
#     print(f'Max {self.propQ} = {propQs.max():.{sigfigs}f} at Vinf = {Vs[np.argmax(propQs)]/ftm:.{sigfigs}f} ft/s')
#     print(f'Min {self.propQ} = {propQs.min():.{sigfigs}f} at Vinf = {Vs[np.argmin(propQs)]/ftm:.{sigfigs}f} ft/s')
#     print(f'at cruise Vinf = {cruise_V/ftm:.{sigfigs}f} ft/s, {self.propQ} = {propQs[cruise_idx]:.{sigfigs}f}')
    
#     if plot:
#         fig, ax = plt.subplots(figsize = (6, 4), dpi = 1000)
                
#         ax.plot(Vs/ftm, propQs) 
#         ax.plot([cruise_V/ftm, cruise_V/ftm], ax.get_ylim(), '--', color = 'red', label = 'Cruise Velocity')
#         ax.grid()
#         ax.minorticks_on()
#         plt.legend()
#         plt.ylabel(f'{propQnames[interestindex]}') # need to add a way to get units in correctly
#         plt.xlabel('Velocity (ft/s)')
        
#         # TODO: find a better way to say motor(s) depending on nmot
#         if self.nmot > 1:
#             s = 's'
#         else:
#             s = ''
            
#         if self.SOCinput:
#             plt.title(f'{self.nmot:.0f} {self.motor_manufacturer} {self.motor_name} motor{s}; {self.ns:.0f}S {self.CB:.0f} mAh battery; {self.nmot:.0f} APC {self.prop_name} propeller{s}\n{propQnames[interestindex]} at {SOC_Voc_t*100:.0f}% SOC and {dT*100:.0f}% throttle')
#         elif self.Vocinput:
#             plt.title(f'{self.nmot:.0f} {self.motor_manufacturer} {self.motor_name} motor{s}; {self.ns:.0f}S {self.CB:.0f} mAh battery; {self.nmot:.0f} APC {self.prop_name} propeller{s}\n{propQnames[interestindex]} at {SOC_Voc_t:.4f} V Voc and {dT*100:.0f}% throttle')
#         else:
#             plt.title(f'{self.nmot:.0f} {self.motor_manufacturer} {self.motor_name} motor{s}; {self.ns:.0f}S {self.CB:.0f} mAh battery; {self.nmot:.0f} APC {self.prop_name} propeller{s}\n{propQnames[interestindex]} at {SOC_Voc_t:.1f} s runtime and {dT*100:.0f}% throttle')
#         plt.show()
    
#     return(outs, cruise_V)

