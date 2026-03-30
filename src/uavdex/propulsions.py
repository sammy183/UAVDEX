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
    T_N         (newtons, thrust for all motors)
    T_lbf       (pound-force, thrust for all motors)
    T_g         (gram-force, thrust for all motors)
    T_oz        (ounce-force, thrust for all motors)
    
    Q_Nm        (N*m, torque for all motors)
    Q_lbfft     (lbf*ft, torque for all motors)
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

import numpy as np
from numpy.polynomial import Polynomial
import matplotlib.pyplot as plt
from matplotlib import patheffects
import mplcursors # wonderful package
# from tqdm import tqdm
from numba import njit
import copy
from uavdex.VSPcontribution.atmosphere import stdatm1976 as atm 
from uavdex.VSPcontribution.units import n2lb, mph2ms, n2g, n2oz, nm2ftlb
from uavdex.utils import exactly_one_defined, reverse_input_conversion, get_array_idx, get_const_idx, find_intersections, get_const_vals
import warnings
warnings.filterwarnings("ignore", message="Pick support for QuadMesh")
warnings.filterwarnings("ignore", message="No artists with labels found to put in legend")


global propQnames, propQshort, propQunit, FullInputNames, FullInputNamesShort, FullInputUnits
propQnames = ['Total Thrust (N)',
              'Total Thrust (lbf)',
              'Total Thrust (g)',
              'Total Thrust (oz)',
              'Total Torque (N-m)',
              'Total Torque (lbf-ft)',
              'RPM', 
              'Drive Efficiency', 
              'Propeller Efficiency', 
              'Gearing Efficiency', 
              'Motor Efficiency', 
              'ESC Efficiency', 
              'Battery Efficiency', 
              'Mech. Power Out of 1 Motor (W)', 
              'Elec. Power Into 1 Motor (W)', 
              'Elec. Power Into 1 ESC (W)', 
              'Waste Power in 1 Motor (W)', 
              'Waste Power in 1 ESC (W)',
              'Waste Power in 1 Battery (W)',
              'Current in 1 Motor (A)', 
              'Current in 1 ESC (A)', 
              'Current in Battery (A)',
              'Voltage in 1 Motor (V)', 
              'Voltage in 1 ESC (V)', 
              'Battery Voltage (V)', 
              'Voltage Per Cell (V)', 
              'State of Charge']
propQshort = ['T_N', 'T_lbf', 'T_g', 'T_oz',
              'Q_Nm', 'Q_lbfft', 'RPM', 
              'eta_drive', 'eta_p', 'eta_g', 'eta_m', 'eta_c', 'eta_b', 
              'Pout', 'Pin_m', 'Pin_c', 'Pw_m', 'Pw_c', 'Pw_b', 
              'Im', 'Ic', 'Ib', 'Vm', 'Vc', 'Vb', 
              'Voc', 'SOC']
propQunit = ['N', 'lbf', 'g', 'oz',
             'N-m', 'lbf-ft', 'RPM',
             '%', '%', '%', '%', '%', '%',
             'W', 'W', 'W', 'W', 'W', 'W', 
             'A', 'A', 'A', 
             'V', 'V', 'V', 
             'V', '%']
FullInputNames = ['State of Charge (%)', 'Cell Voltage (V)', 'Runtime (s)', 
                  'Runtime (min)', 'Runtime (hr)',
                  'Velocity (mph)', 'Velocity (fps)', 'Velocity (m/s)', 
                  'Velocity (kmh)', 'Velocity (knots)',
                  'Throttle (%)', 
                  'Altitude (m)', 'Altitude (ft)', 'Air Density (kg/m\u00B3)', 
                  'Air Density (slug/ft\u00B3)', 'Air Density (lbm/ft\u00B3)',
                  ]
FullInputNamesShort = ['SOC', 'Voc', 't', 't', 't',
                       'Uinf', 'Uinf', 'Uinf', 'Uinf', 'Uinf',
                       'dT',
                       'h', 'h', 'rho', 'rho', 'rho']
FullInputUnits = ['%', 'V', 's', 'min', 'hr',
                  'mph', 'fps', 'm/s', 'kmh', 'kt',
                  '%',
                  'm', 'ft', 'kg/m\u00B3', 'slug/ft\u00B3', 'lbm/ft\u00B3']

from uavdex import _uavdex_root
path_to_data = _uavdex_root / 'Databases/'

### OLD LOCAL TESTING
# from VSPcontribution.atmosphere import stdatm1976 as atm
# from pathlib import Path
# _uavdex_root = Path(__file__).parent
# path_to_data = _uavdex_root / 'Databases/'

#%%################### Numerical Methods ###################
# 1D root finding 
@njit(fastmath = True)
def bisection(low, high, func, *args):
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
    Parses the provided PER3_16x10E.dat content to extract RPM, J (advance ratio), CT (coef. thrust), CP (coef torque)
    
    Stores in PROP_DATA as {rpm: {'J': np.array, 'CT': np.array, 'CP': np.array}}
    
    Stores same data in numba_prop_data in a 3D np.array of (i, j, k), 
        where i corresponds to rpm_values[i], 
        j corresponds to J, CT, CP, 
        k corresponds to the values
        
    # todo: improve docstring
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
    datasizes = []
    maxJ = 0.0
    for RPM in PROP_DATA['rpm_list']:
        specmaxJ = PROP_DATA[RPM]['J'].max()
        if specmaxJ > maxJ:
            maxJ = specmaxJ
        datasection = np.array([PROP_DATA[RPM]['J'], 
                                PROP_DATA[RPM]['CT'], 
                                PROP_DATA[RPM]['CP']])
        datasizes.append(datasection.shape[1])
        numba_prop_data.append(datasection)
    
    # to avoid a list of np arrays, add 0s to the end of all arrays to match the sizes
    # some props have (3, 30) for most datasection shapes, then (3, 29) for a few, 
    # which prevents combination into a single np array
    datasizes = np.array(datasizes)
    max_data_size = datasizes.max()
    zeroarr = np.zeros((3, 1))
    zeroarr[0, 0] = maxJ
    for i, data in enumerate(numba_prop_data):
        while data.shape[1] < max_data_size:
            data = np.concatenate((data,zeroarr), 1) # IMPORTANT, J cannot be zero or the plot gets messed up. J must be equivalent to J max!
            numba_prop_data[i] = data        
    numba_prop_data = np.stack(numba_prop_data) # now this is a 3D array!  
        
    return(PROP_DATA, numba_prop_data)

def parse_propeller_data(prop_name):
    """
    prop_name in the form: 16x10E, 18x12E, 12x12, etc (no PER3_ and no .dat to make it easier for new users)
    Parses the provided PER3_16x10E.dat content to extract RPM, V (m/s), Thrust (N), Torque (N-m).
    Stores in PROP_DATA as {rpm: {'V': np.array, 'Thrust': np.array, 'Torque': np.array}}
    
    NOTE: this is an older function, remnant of before I used the propeller coefficients effectively
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
                v_mph = float(parts[0])         # V in mph
                torque_nm = float(parts[9])     # Torque (N-m)
                thrust_n = float(parts[10])     # Thrust (N)
                v_mps = v_mph * mph2ms      # Convert to m/s
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
    
    # array based datastructure where each index corresponds to rpm_values[i] (or (i+1)*1000 RPM)
    # and in each index there is [[V values], [Thrust values], [Torque values]] at the indices, 0, 1, 2
    numba_prop_data = []
    datasizes = []
    for RPM in PROP_DATA['rpm_list']:
        datasection = np.array([PROP_DATA[RPM]['V'], 
                                PROP_DATA[RPM]['Thrust'], 
                                PROP_DATA[RPM]['Torque']])
        datasizes.append(datasection.shape[1])
        numba_prop_data.append(datasection)
    
    # to avoid a list of np arrays, add 0s to the end of all arrays to match the sizes
    # some props have (3, 30) for most datasection shapes, then (3, 29) for a few, 
    # which prevents combination into a single np array
    datasizes = np.array(datasizes)
    max_data_size = datasizes.max()
    zeroarr = np.zeros((3, 1)) 
    for i, data in enumerate(numba_prop_data):
        while data.shape[1] < max_data_size:
            data = np.concatenate((data,zeroarr), 1)
            numba_prop_data[i] = data        
    numba_prop_data = np.stack(numba_prop_data) # now this is a 3D array!  
    
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
    
#%% Non-numba interpolation functions
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
@njit(fastmath = True)
def VocFunc(SOC, BattType):
    '''
    Determines the battery Voltage (Voc) as a function of State of Charge (SOC) given from 0-1 for a specified battery chemistry
    
    LiPo
    Main equation from Jeong 2020
    Voc = 1.7*(SOC**3) - 2.1*(SOC**2) + 1.2*SOC + 3.4
    https://www.researchgate.net/publication/347270768_Improvement_of_Electric_Propulsion_System_Model_for_Performance_Analysis_of_Large-Size_Multicopter_UAVs
    
    alternative equation from Chen 2006
    https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf
        
    NOTE:
    Jeong 2020 also presents resistance as a function of cell energy:
    Rbatt.cell = 21.0*(ebatt.cell)**-0.8056
    
    
    Liion
    https://www.researchgate.net/publication/346515863_Comparison_of_Lithium-Ion_Battery_Pack_Models_Based_on_Test_Data_from_Idaho_and_Argonne_National_Laboratories
    Using the i3 battery pack as an intermediate value
    
    TODO: implment battery voltage equation adjustments based on predicted health (measured via Vsoc at full charge!)
    '''
    if BattType == 'LiPo':
        return(1.7*SOC**3 - 2.1*SOC**2 + 1.2*SOC + 3.4)
        # return(3.685 - 1.031 * np.exp(-35 * SOC) + 0.2156 * SOC - 0.1178 * SOC**2 + 0.3201 * SOC**3)
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
    Voc, Uinf, dT, rho, eta_c, eta_g, GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot, ds = args
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
    t, Uinf, dT, rho, eta_c, eta_g, GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot, ds = args
    J = Uinf/((RPM/60)*d)
    CP = CPNumba(RPM, J, rpm_list, coef_numba_prop_data)
    Qm = (rho*((RPM/60)**2)*(d**5)*CP)/(2*np.pi*GR*eta_g)
    Im = Qm*KV*(np.pi/30) + I0
    Ib = (Im*nmot)/eta_c
    SOC = 1.0 - (Ib*t)/(3.6*CB*np_batt)
    Vb = ns*VocFunc(SOC, BattType) - Ib*Rb
    Vm = dT*Vb
    RPMcalc = KV*(Vm - Im*Rm)/GR
    return(RPMcalc, J, CP, Qm, Im, Ib, Vb, Vm)

# I need some method of setting whether we're inputting h or rho/t or SOC or Voc for the same function
@njit(fastmath = True)
def SimplifiedRPM_Voc(Uinf, dT, rho, Voc, *args):
    '''
    rho given directly or precalculated from h
    Voc given directly or precalculated from SOC
    TODO: full docstring
    
    Output indexes:
    0       1    2     3     4      5      6      7         8      9      10     11     12 
    T_N, T_lbf, T_g, T_oz, Q_Nm, Q_lbfft, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
    
     13      14     15    16     17    18  19  20  21  22  23  24   25   26
    Pout, Pin_m, Pin_c, Pw_m   Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
    '''
    ##### Assume ESC efficiency = 0.93 (93%) ##### 
    # note: max ESC efficiency occurs at dT = 1.0
    eta_c = 0.93
    
    # in the future could optimize parameters passed for memory, for now, it aids readability to pass everything
    GR, rpm_list, coef_numba_prop_data, d, ns, np, CB, Rb, BattType, KV, Rm, I0, nmot, ds = args
    
    # Gearing efficiency
    if GR != 1.0:
        eta_g = 0.94 # 94% gear efficiency assumed
    else:
        eta_g = 1.0
    
    # checking initial feasibility with propeller Jmax
    Jmax = coef_numba_prop_data[:, 0, :].max()
    RPMlowerlimit = (Uinf*60)/(Jmax*d)
    if RPMlowerlimit != 0 and RPMlowerlimit > SimpleRPMeqs_Voc(RPMlowerlimit, Voc, Uinf, dT, rho, eta_c, eta_g, *args)[0]:
        # print('Propeller data predicts no thrust at specified condition (high advance ratio!)\nReduce Uinf, t or increase dT')
        return([0.0]*27) ## TODO: make a way for the len of propQ to change automatically

    def residualfunc(RPM, *args):
        RPMcalc = SimpleRPMeqs_Voc(RPM, *args)[0]
        res = RPMcalc - RPM
        return(res)
    
    # Vbattinit = throttle*3.6*ns
    high = rpm_list[-1]
    low = rpm_list[0]
    RPM = bisection(low, high, residualfunc, Voc, Uinf, dT, rho, eta_c, eta_g, *args)
    
    _, J, CP, Q, Im, Ib, Vb, Vm = SimpleRPMeqs_Voc(RPM, Voc, Uinf, dT, rho, eta_c, eta_g, *args)
    if CP == 0.0: 
        return([0.0]*27) ## TODO: make a way for the len of propQ to change automatically
    CT = CTNumba(RPM, J, rpm_list, coef_numba_prop_data) 
    Ic = Ib/nmot 
    Vc = Vb 
    
    Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
    Pin_m = Vm*Im                           # electric power into one motor
    Pin_c = Vc*Ic                           # electric power into one controller
    
    # Waste power calculations (via power loss); useful for heat estimation
    Pw_m = Pin_m - Pout
    Pw_c = Pin_c - Pin_m
    Pw_b = Rb*(Ib**2)
    
    eta_p = (CT*J)/CP
    eta_m = Pout/Pin_m 
    eta_c = Pin_m/Pin_c 
    eta_b = 1.0 - (Ib**2)*Rb/(nmot*Pin_c + ((Ib**2)*Rb))
    eta_drive = (eta_p*eta_g*eta_m*eta_c)*eta_b
    
    T = nmot*rho*((RPM/60)**2)*(d**4)*CT
    Q *= nmot
    
    # Calculate SOC via bisection between 0, 1
    # @njit(fastmath = True)
    def VocResidual(SOC, *args):
        Voc, BattType = args
        return(VocFunc(SOC, BattType) - Voc)
    SOC = bisection(0, 1, VocResidual, Voc, BattType)
    if SOC <= 1-ds:
        return([0.0]*27) ## TODO: make a way for the len of propQ to change automatically
    
    T_lbf = T*n2lb
    T_g = T*n2g
    T_oz = T*n2oz 
    Q_lbfft = Q*nm2ftlb
    
    # convert efficiencies from decimal to %
    eta_drive *= 100
    eta_p *= 100
    eta_g *= 100
    eta_m *= 100
    eta_c *= 100
    eta_b *= 100
    SOC *= 100
    
    return([T, T_lbf, T_g, T_oz, Q, Q_lbfft, RPM, 
            eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
            Pout, Pin_m, Pin_c, Pw_m, Pw_c, Pw_b,
            Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC])


# I need some method of setting whether we're inputting h or rho/t or SOC or Voc for the same function
@njit(fastmath = True)
def SimplifiedRPM_t(Uinf, dT, rho, t, *args):
    '''
    rho given directly or precalculated from h
    t given directly
    
    Output indexes:
    0       1    2     3     4      5      6      7         8      9      10     11     12 
    T_N, T_lbf, T_g, T_oz, Q_Nm, Q_lbfft, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
    
     13      14     15    16     17    18  19  20  21  22  23  24   25   26
    Pout, Pin_m, Pin_c, Pw_m   Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
    '''
    ##### Assume ESC efficiency = 0.93 (93%) ##### 
    # note: max ESC efficiency occurs at dT = 1.0
    eta_c = 0.93
    
    # in the future could optimize parameters passed for memory, for now, it aids readability to pass everything
    GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot, ds = args
    
    # Gearing efficiency
    if GR != 1.0:
        eta_g = 0.94 # 94% gear efficiency assumed
    else:
        eta_g = 1.0
        
    # checking initial feasibility with propeller Jmax
    Jmax = coef_numba_prop_data[:, 0, :].max()
    RPMlowerlimit = (Uinf*60)/(Jmax*d)
    if RPMlowerlimit != 0 and RPMlowerlimit > SimpleRPMeqs_t(RPMlowerlimit, t, Uinf, dT, rho, eta_c, eta_g, *args)[0]:
        # print('Propeller data predicts no thrust at specified condition (high advance ratio!)\nReduce Uinf, t or increase dT')
        return([0.0]*27) ## TODO: make a way for the len of propQ to change automatically

    def residualfunc(RPM, *args):
        RPMcalc = SimpleRPMeqs_t(RPM, *args)[0]
        res = RPMcalc - RPM
        return(res)
    
    # Vbattinit = throttle*3.6*ns
    high = rpm_list[-1]
    low = rpm_list[0]
    RPM = bisection(low, high, residualfunc, t, Uinf, dT, rho, eta_c, eta_g, *args)
    
    _, J, CP, Q, Im, Ib, Vb, Vm = SimpleRPMeqs_t(RPM, t, Uinf, dT, rho, eta_c, eta_g, *args)
    if CP == 0.0:
        return([0.0]*27) ## TODO: make a way for the len of propQ to change automatically
    CT = CTNumba(RPM, J, rpm_list, coef_numba_prop_data) 
    Ic = Ib/nmot 
    Vc = Vb 
    
    Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
    Pin_m = Vm*Im                           # electric power into one motor
    Pin_c = Vc*Ic                           # electric power into one controller
    
    # Waste power calculations (via power loss); useful for heat estimation
    Pw_m = Pin_m - Pout
    Pw_c = Pin_c - Pin_m
    Pw_b = Rb*(Ib**2)
    
    eta_p = (CT*J)/CP
    eta_m = Pout/Pin_m 
    eta_c = Pin_m/Pin_c 
    eta_b = 1.0 - (Ib**2)*Rb/(nmot*Pin_c + ((Ib**2)*Rb))
    eta_drive = (eta_p*eta_g*eta_m*eta_c)*eta_b
    
    SOC = 1.0 - (Ib*t)/(3.6*CB*np_batt)
    if SOC <= 1-ds:
        return([0.0]*27) ## TODO: make a way for the len of propQ to change automatically

    Voc = VocFunc(SOC, BattType)
    
    T = nmot*rho*((RPM/60)**2)*(d**4)*CT
    Q *= nmot
    
    T_lbf = T*n2lb
    T_g = T*n2g
    T_oz = T*n2oz 
    Q_lbfft = Q*nm2ftlb
    
    # convert efficiencies from decimal to %
    eta_drive *= 100
    eta_p *= 100
    eta_g *= 100
    eta_m *= 100
    eta_c *= 100
    eta_b *= 100
    SOC *= 100
    
    return([T, T_lbf, T_g, T_oz, Q, Q_lbfft, RPM, 
            eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
            Pout, Pin_m, Pin_c, Pw_m, Pw_c, Pw_b,
            Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC])


#%% Non-Numba SimpleRPM functions (one for precalculated Voc one for t)
def VocFuncBase(SOC, BattType):
    '''
    Determines the battery Voltage (Voc) as a function of State of Charge (SOC) given from 0-1 for a specified battery chemistry
    
    LiPo
    Main equation from Jeong 2020
    Voc = 1.7*(SOC**3) - 2.1*(SOC**2) + 1.2*SOC + 3.4
    https://www.researchgate.net/publication/347270768_Improvement_of_Electric_Propulsion_System_Model_for_Performance_Analysis_of_Large-Size_Multicopter_UAVs
    
    alternative equation from Chen 2006
    https://rincon-mora.gatech.edu/publicat/jrnls/tec05_batt_mdl.pdf
        
    NOTE:
    Jeong 2020 also presents resistance as a function of cell energy:
    Rbatt.cell = 21.0*(ebatt.cell)**-0.8056
    
    
    Liion
    https://www.researchgate.net/publication/346515863_Comparison_of_Lithium-Ion_Battery_Pack_Models_Based_on_Test_Data_from_Idaho_and_Argonne_National_Laboratories
    Using the i3 battery pack as an intermediate value
    
    Consider: https://mcdonaldaerospace.com/projects/batteries_not_fuel/ alternative in more depth
    
    
    TODO: implment battery voltage equation adjustments based on predicted health (measured via Vsoc at full charge!)
    '''
    # if np.array([SOC]).any() < 0.0: # effective error message
    #     return(-1)
    
    if BattType == 'LiPo':
        return(1.7*SOC**3 - 2.1*SOC**2 + 1.2*SOC + 3.4)
        # return(3.685 - 1.031 * np.exp(-35 * SOC) + 0.2156 * SOC - 0.1178 * SOC**2 + 0.3201 * SOC**3)
    elif BattType == 'Liion':
        return(-4.48*((1-SOC)**5) + 9.09*((1-SOC)**4) - 7.08*((1-SOC)**3) + 2.32*((1-SOC)**2) - 0.76*(1-SOC) + 4.10)
    else:
        raise ValueError('Battery Type not recognized')

def SimpleRPMeqsBase_Voc(RPM, *args):
    '''
    rho, Voc precalculated from h and SOC (or given directly)
    TODO: full docstring
    '''
    Voc, Uinf, dT, rho, eta_c, eta_g, GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot, ds = args
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
    
    Output indexes:
    0       1    2     3     4      5      6      7         8      9      10     11     12 
    T_N, T_lbf, T_g, T_oz, Q_Nm, Q_lbfft, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
    
     13      14     15    16     17    18  19  20  21  22  23  24   25   26
    Pout, Pin_m, Pin_c, Pw_m   Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
    '''
    t, Uinf, dT, rho, eta_c, eta_g, GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot, ds = args
    J = Uinf/((RPM/60)*d)
    CP = CPBase(RPM, J, rpm_list, coef_numba_prop_data)
    Qm = (rho*((RPM/60)**2)*(d**5)*CP)/(2*np.pi*GR*eta_g)
    Im = Qm*KV*(np.pi/30) + I0
    Ib = (Im*nmot)/eta_c
    SOC = 1.0 - (Ib*t)/(3.6*CB*np_batt)
    Vb = ns*VocFuncBase(SOC, BattType) - Ib*Rb
    Vm = dT*Vb
    RPMcalc = KV*(Vm - Im*Rm)/GR
    return([RPMcalc, J, CP, Qm, Im, Ib, Vb, Vm])

# I need some method of setting whether we're inputting h or rho/t or SOC or Voc for the same function
def SimplifiedRPMBase_Voc(Uinf, dT, rho, Voc, *args):
    '''
    rho given directly or precalculated from h
    Voc given directly or precalculated from SOC
    
    Output indexes:
    0       1    2     3     4      5      6      7         8      9      10     11     12 
    T_N, T_lbf, T_g, T_oz, Q_Nm, Q_lbfft, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
    
     13      14     15    16     17    18  19  20  21  22  23  24   25   26
    Pout, Pin_m, Pin_c, Pw_m   Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
    '''
    ##### Assume ESC efficiency = 0.93 (93%) ##### 
    # note: max ESC efficiency occurs at dT = 1.0
    eta_c = 0.93
    
    # in the future could optimize parameters passed for memory, for now, it aids readability to pass everything
    GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot, ds = args
    
    # Gearing efficiency
    if GR != 1.0:
        eta_g = 0.94 # 94% gear efficiency assumed
    else:
        eta_g = 1.0
        
    # checking initial feasibility with propeller Jmax
    Jmax = coef_numba_prop_data[:, 0, :].max()
    RPMlowerlimit = np.max([(Uinf*60)/(Jmax*d), rpm_list[0]])
    if RPMlowerlimit > SimpleRPMeqsBase_Voc(RPMlowerlimit, Voc, Uinf, dT, rho, eta_c, eta_g, *args)[0]:
        # print('Propeller data predicts no thrust at specified condition (high advance ratio!)\nReduce Uinf or increase dT, Voc')
        return([0.0]*len(propQshort))

    def residualfunc(RPM, *args):
        RPMcalc = SimpleRPMeqsBase_Voc(RPM, *args)[0]
        res = RPMcalc - RPM
        return(res)
    
    high = rpm_list[-1]
    low = rpm_list[0]
    RPM = bisectionBase(low, high, residualfunc, Voc, Uinf, dT, rho, eta_c, eta_g, *args)
    if RPM == -1:
        # print('SOC < 0, cannot solve')
        return([0.0]*len(propQshort))
    
    _, J, CP, Q, Im, Ib, Vb, Vm = SimpleRPMeqsBase_Voc(RPM, Voc, Uinf, dT, rho, eta_c, eta_g, *args)
    # if CP == 0.0:
    #     return([0.0]*len(propQshort))
    CT = CTBase(RPM, J, rpm_list, coef_numba_prop_data) 
    Ic = Ib/nmot 
    Vc = Vb 
    
    Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
    Pin_m = Vm*Im                           # electric power into one motor
    Pin_c = Vc*Ic                           # electric power into one controller
    
    # Waste power calculations (via power loss); useful for heat estimation
    Pw_m = Pin_m - Pout
    Pw_c = Pin_c - Pin_m
    Pw_b = Rb*(Ib**2)
    
    eta_p = (CT*J)/CP
    eta_m = Pout/Pin_m 
    eta_c = Pin_m/Pin_c 
    eta_b = 1.0 - ((Ib**2)*Rb)/(nmot*Pin_c + ((Ib**2)*Rb))
    eta_drive = eta_p*eta_g*eta_m*eta_c*eta_b # took out divided by nmot, REVIEW later
    
    T = nmot*rho*((RPM/60)**2)*(d**4)*CT
    Q *= nmot
    
    # Calculate SOC via bisection between 0, 1
    def VocResidual(SOC):
        return(VocFuncBase(SOC, BattType) - Voc)
    SOC = bisectionBase(0, 1, VocResidual)
    if SOC <= 1-ds:
        # print('SOC < specified discharge')
        return([0.0]*len(propQshort))
    
    T_lbf = T*n2lb
    T_g = T*n2g
    T_oz = T*n2oz 
    Q_lbfft = Q*nm2ftlb
    
    # convert efficiencies from decimal to %
    eta_drive *= 100
    eta_p *= 100
    eta_g *= 100
    eta_m *= 100
    eta_c *= 100
    eta_b *= 100
    SOC *= 100
    
    return([T, T_lbf, T_g, T_oz, Q, Q_lbfft, RPM, 
            eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
            Pout, Pin_m, Pin_c, Pw_m, Pw_c, Pw_b,
            Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC])


# I need some method of setting whether we're inputting h or rho/t or SOC or Voc for the same function
def SimplifiedRPMBase_t(Uinf, dT, rho, t, *args):
    '''
    rho given directly or precalculated from h
    t given directly
    
    Output indexes:
    0       1    2     3     4      5      6      7         8      9      10     11     12 
    T_N, T_lbf, T_g, T_oz, Q_Nm, Q_lbfft, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
    
     13      14     15    16     17    18  19  20  21  22  23  24   25   26
    Pout, Pin_m, Pin_c, Pw_m   Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
    '''
    ##### Assume ESC efficiency = 0.93 (93%) ##### 
    # note: max ESC efficiency occurs at dT = 1.0
    eta_c = 0.93
    
    # in the future could optimize parameters passed for memory, for now, it aids readability to pass everything
    GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot, ds = args
    
    # Gearing efficiency
    if GR != 1.0:
        eta_g = 0.94 # 94% gear efficiency assumed
    else:
        eta_g = 1.0
        
    # checking initial feasibility with propeller Jmax
    Jmax = coef_numba_prop_data[:, 0, :].max()
    RPMlowerlimit = np.max([(Uinf*60)/(Jmax*d), rpm_list[0]])
    if RPMlowerlimit > SimpleRPMeqsBase_t(RPMlowerlimit, t, Uinf, dT, rho, eta_c, eta_g, *args)[0]:
        # print('Propeller data predicts no thrust at specified condition (high advance ratio!)\nReduce Uinf, t or increase dT')
        return([0.0]*len(propQshort))

    def residualfunc(RPM, *args):
        RPMcalc = SimpleRPMeqsBase_t(RPM, *args)[0]
        res = RPMcalc - RPM
        return(res)
    
    # Vbattinit = throttle*3.6*ns
    high = rpm_list[-1]
    low = rpm_list[0]
    RPM = bisectionBase(low, high, residualfunc, t, Uinf, dT, rho, eta_c, eta_g, *args)
    
    # # check if convergence failed
    if RPM == -1:
        # print('cannot solve')

    #     # why could this fail?
    #     # 1. J outside propeller map 
    #     # 2. SOC < 1-ds, meaning Voc falls outside physical range
        return([0.0]*len(propQshort))
    
    _, J, CP, Q, Im, Ib, Vb, Vm = SimpleRPMeqsBase_t(RPM, t, Uinf, dT, rho, eta_c, eta_g, *args)
    if CP == 0.0:
        # print('CP = 0')
        return([0.0]*len(propQshort))
        
    CT = CTBase(RPM, J, rpm_list, coef_numba_prop_data)
    Ic = Ib/nmot 
    Vc = Vb 
    
    Pout =  rho*((RPM/60)**3)*(d**5)*CP     # mechanical power out of ONE motor
    Pin_m = Vm*Im                           # electric power into one motor
    Pin_c = Vc*Ic                           # electric power into one controller
    
    # Waste power calculations (via power loss); useful for heat estimation
    Pw_m = Pin_m - Pout
    Pw_c = Pin_c - Pin_m
    Pw_b = Rb*(Ib**2)

    eta_p = (CT*J)/CP
    eta_m = Pout/Pin_m 
    eta_c = Pin_m/Pin_c 
    eta_b = 1.0 - ((Ib**2)*Rb)/(nmot*Pin_c + ((Ib**2)*Rb)) 
    # TODO: FIX THE BATTERY EFFICIENCY BY ACCOUNTING FOR RB VARYING WITH SOC (CRITICAL)
    # Check battery efficiency varies with runtime: 
    # https://ntrs.nasa.gov/api/citations/20205004497/downloads/Battery_Evaluation_EATS_07_15_20.pdf
    eta_drive = eta_p*eta_g*eta_m*eta_c*eta_b # took out divided by nmot, REVIEW later
    
    T = nmot*rho*((RPM/60)**2)*(d**4)*CT
    Q *= nmot
    
    SOC = 1.0 - (Ib*t)/(3.6*CB*np_batt)
    if SOC <= 1-ds:
        # print('SOC < Specified Discharge')
        return([0.0]*len(propQshort))

    Voc = VocFuncBase(SOC, BattType)
    
    T_lbf = T*n2lb
    T_g = T*n2g
    T_oz = T*n2oz 
    Q_lbfft = Q*nm2ftlb
    
    # convert efficiencies from decimal to %
    eta_drive *= 100
    eta_p *= 100
    eta_g *= 100
    eta_m *= 100
    eta_c *= 100
    eta_b *= 100
    SOC *= 100
    
    return([T, T_lbf, T_g, T_oz, Q, Q_lbfft, RPM, 
            eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
            Pout, Pin_m, Pin_c, Pw_m, Pw_c, Pw_b,
            Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC])


#%%################## PLOTTING FUNCTIONS ##################

################################# PointResult #################################
def PointResultFunc(self, Uinf = None, dT = None, 
                    rho = None, h = None, 
                    SOC = None, Voc = None, t = None, 
                    verbose = True):
    ''' 
    PointResult for fixed Uinf, dT, t/SOC/Voc, h/rho
        
    Outputs
    --------------------------------
    array of:
    0       1    2     3     4      5      6      7         8      9      10     11     12 
    T_N, T_lbf, T_g, T_oz, Q_Nm, Q_lbfft, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
    
     13      14     15    16     17    18  19  20  21  22  23  24   25   26
    Pout, Pin_m, Pin_c, Pw_m   Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
    
    '''
    args = (self.GR, self.rpm_list, self.COEF_NUMBA_PROP_DATA, self.propdiam, 
            self.ns_batt, self.np_batt, self.CB, self.Rb, self.BattType, 
            self.KV, self.Rm, self.I0, self.nmot, self.ds/100)
    if not exactly_one_defined(t, SOC, Voc):
        raise ValueError("Exactly one of t, SOC, or Voc must be provided")
        
    if not exactly_one_defined(rho, h):
        raise ValueError("Exactly one of h or rho must be provided")
    
    if h is not None:
        rho = atm().rho(h)
                
    if t is not None: 
        # quick check for propeller viability
        Jmax = self.COEF_NUMBA_PROP_DATA[:, 0, :].max()
        RPMlowerlimit = (Uinf*60)/(Jmax*self.propdiam)
        eta_c = 0.93
        if self.GR != 1.0:
            eta_g = 0.94 # 94% gear efficiency assumed
        else:
            eta_g = 1.0
        if RPMlowerlimit > SimpleRPMeqsBase_t(RPMlowerlimit, t, Uinf, dT, rho, eta_c, eta_g, *args)[0]:
            print('ERROR: Propeller data predicts zero thrust (high advance ratio). Reduce Uinf, t or increase dT')
            return(np.zeros(len(propQshort)))
            
        propQs = SimplifiedRPMBase_t(Uinf, dT, rho, t, *args)
        if propQs[0] == 0.0:
            print(f'ERROR: Input t corresponds to SOC less than {100-self.ds:.0f}% from .Battery()')
            return(np.zeros(len(propQshort)))
    else:
        # Voc or SOC input
        if SOC is not None:
            if SOC < 1 - self.ds/100:
                print(f'ERROR: SOC input less than {100-self.ds:.0f}% from .Battery()')
                return(np.zeros(len(propQshort)))
            Voc = VocFuncBase(SOC, self.BattType)
        else:
            # voc input, check that it maps to SOC between 0-1
            if Voc < VocFuncBase(1-self.ds/100, self.BattType):
                print(f'ERROR: Input Voc for {self.BattType} corresponds to SOC < {100-self.ds:.0f}%')
                return(np.zeros(len(propQshort)))
            elif Voc > VocFuncBase(1, self.BattType):
                print(f'ERROR: Input Voc for {self.BattType} corresponds to SOC > 100%')
                return(np.zeros(len(propQshort)))
            
        # quick check for propeller viability
        Jmax = self.COEF_NUMBA_PROP_DATA[:, 0, :].max()
        RPMlowerlimit = (Uinf*60)/(Jmax*self.propdiam)
        eta_c = 0.93
        if self.GR != 1.0:
            eta_g = 0.94 # 94% gear efficiency assumed
        else:
            eta_g = 1.0
        if RPMlowerlimit > SimpleRPMeqsBase_Voc(RPMlowerlimit, Voc, Uinf, dT, rho, eta_c, eta_g, *args)[0]:
            print('ERROR: Propeller data predicts zero thrust (high advance ratio). Reduce Uinf, t or increase dT')
            return(np.zeros(len(propQshort)))
        
        propQs = SimplifiedRPMBase_Voc(Uinf, dT, rho, Voc, *args)
        if propQs[0] == 0.0:
            print('ERROR: Infeasible input combination, try reducing runtime')
            return(np.zeros(len(propQshort)))
        
    if verbose:
        # TODO: automate this, so it matches units and names with self.unit_idxs!
        # TODO
        # TODO
        # TODO
        # TODO
        if t is not None:
            print(f'\nAt Uinf = {Uinf:.2f} m/s, Throttle = {dT*100:.0f}%, Density = {rho:.3f} kg/m\u00B3, Runtime = {t:.1f} s')
        elif SOC is not None and SOC > 0.0:
            print(f'\nAt Uinf = {Uinf:.2f} m/s, Throttle = {dT*100:.0f}%, Density = {rho:.3f} kg/m\u00B3, SOC = {SOC:.0f}%')
        elif Voc is not None:
            print(f'\nAt Uinf = {Uinf:.2f} m/s, Throttle = {dT*100:.0f}%, Density = {rho:.3f} kg/m\u00B3, Voc = {Voc:.2f} V')

        for i, name in enumerate(propQnames):
            print(f'{name:30} = {propQs[i]:.3f}')
    return(np.array(propQs))

#%%################################ LinePlot #################################
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

# supplemental function for the cursor values
def make_cursor_lineplot(artist, xname_idx, propQidx):
    
    c = mplcursors.cursor(artist)
    @c.connect("add")
    def _(sel):
        sel.annotation.get_bbox_patch().set(fc="white")
        x, y =  sel.target
        # idx =   sel.index
        sel.annotation.set_text(
            f"{FullInputNamesShort[xname_idx]} = {x:.4g} {FullInputUnits[xname_idx]}\n"
            f"{propQshort[propQidx]} = {y:.4g} {propQunit[propQidx]}"
        )
    return c

def LinePlotFunc(self, propQ = 'T',
                 Uinf = None, dT = None, 
                 rho = None, h = None, 
                 SOC = None, Voc = None, t = None, 
                 verbose = True, plot = False):
    '''
    Input
    ----------------------------------------------------------------------------------------------------------
        a propulsion quantity (propQ) of interest (options given by the output array)
        
        constant values for three of: Uinf, dT, rho/h, SOC/Voc/t
        a range of the final value 
        
    IMPORTANT: 
        bounds on ranges: dT in (0, 1), rho >= 0, h >= 0, SOC in (0, 1), Voc in (2.0, 4.2), t >= 0

    Output
    ----------------------------------------------------------------------------------------------------------
        2D np array with columns corresponding to 
        
        0       1    2     3     4      5      6      7         8      9      10     11     12 
        T_N, T_lbf, T_g, T_oz, Q_Nm, Q_lbfft, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
        
         13      14     15    16     17    18  19  20  21  22  23  24   25   26
        Pout, Pin_m, Pin_c, Pw_m   Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
        
        and rows corresponding to a range of the nonconstant value
    '''
    
    args = (self.GR, self.rpm_list, self.COEF_NUMBA_PROP_DATA, self.propdiam, 
            self.ns_batt, self.np_batt, self.CB, self.Rb, self.BattType, 
            self.KV, self.Rm, self.I0, self.nmot, self.ds/100)
    
    if not exactly_one_defined(t, SOC, Voc):
        raise ValueError("Exactly one of t, SOC, or Voc must be provided")
        
    if not exactly_one_defined(rho, h):
        raise ValueError("Exactly one of h or rho must be provided")
    
    # Find the np array and the constants to use
    full_inputs = [Uinf, dT, rho, h, SOC, Voc, t]
    # xname idx corresponds to FullInputNames global (used for plot titles)
    xname_idx = get_array_idx(SOC, Voc, t, Uinf, dT, rho, h, self.unit_idxs)
    # get the idxs for FullInputName (do it here before rho, SOC redefined)
    const_idxs = get_const_idx(SOC, Voc, t, Uinf, dT, rho, h, self.unit_idxs)
    arrs = 0
    idxarr = 0
    for i, specinput in enumerate(full_inputs):
        if isinstance(specinput, np.ndarray):
            arrs += 1
            idxarr = i
            inputarr = specinput
    if arrs != 1:
        raise KeyError("Exactly one array of inputs must be provided")
    
    # convert h to rho
    if h is not None:
        rho1 = atm().rho(h)
    else:
        if isinstance(rho, np.ndarray):
            rho1 = rho.copy()
        else:
            rho1 = rho
        
    # convert SOC to Voc
    if SOC is not None:
        Voc1 = VocFuncBase(SOC, self.BattType)
    elif Voc is not None:
        if isinstance(rho, np.ndarray):
            Voc1 = Voc.copy()
        else:
            Voc1 = Voc
    
    # collapsing indexes
    if idxarr == 3:
        idxarr = 2
    elif idxarr == 4 or idxarr == 5 or idxarr == 6:
        idxarr = 3 

    if t is None:
        clean_inputs = [Uinf, dT, rho1, Voc1] # if Voc is arr, SOC is arr and vice versa
        PropQs = np.zeros((clean_inputs[idxarr].size, len(propQshort)))
        for i, value in enumerate(clean_inputs[idxarr]):
            inner_input = copy.deepcopy(clean_inputs)
            inner_input[idxarr] = value
            PropQs[i, :] = SimplifiedRPMBase_Voc(inner_input[0], inner_input[1], inner_input[2], inner_input[3], *args)
            # TODO add speedup based on when the data starts and ends 
            # (assume it has no discontinuities in between!)

            # if PropQs[i, 0] <= 0: # indicates that the solution is infeasible
            #     endidx = i 
            #     break 
        endidx = clean_inputs[idxarr].size
    else:
        clean_inputs = [Uinf, dT, rho1, t]
        PropQs = np.zeros((clean_inputs[idxarr].size, len(propQshort)))
        inner_input = copy.deepcopy(clean_inputs)
        for i, value in enumerate(clean_inputs[idxarr]):
            inner_input[idxarr] = value
            PropQs[i, :] = SimplifiedRPMBase_t(inner_input[0], inner_input[1], inner_input[2], inner_input[3], *args)
            # todo, add speedup based on when the data starts and ends 
            # (assume it has no discontinuities in between!)
            # if PropQs[i, 0] <= 0: # indicates that the solution is infeasible
            #     endidx = i 
            #     break
            if PropQs[i, -1] <= 100-self.ds: # minimum SOC = 10% for batteries
                endidx = i
                PropQs[i, :] = np.array([0.0]*len(propQshort))
        endidx = clean_inputs[idxarr].size
    
    # todo: convert units back to original input
    inputarr = inputarr[:endidx]
    PropQs = PropQs[:endidx, :]

    # convert units back and get arrays
    [SOC, Voc, t, Uinf, dT, rho, h] = reverse_input_conversion(SOC, Voc, t, Uinf, dT, rho, h, self.unit_idxs)
    inputs_reverted = [SOC, Voc, t, Uinf, dT, rho, h]
    for item in inputs_reverted:
        if isinstance(item, np.ndarray):
            inputarr = item
        
    # can do this no problem now bc rho and Voc weren't impacted by the conversions (so they stayed as None)
    const_vals = get_const_vals(SOC, Voc, t, Uinf, dT, rho, h, self.unit_idxs)
    
    if plot:
        # primary goal: plot the inputarray on the x-axis versus a selected propQ on the yaxis
        # secondary goal: if some aircraft characteristics (Cd, Sw) have been provided, plot the T = D over the selected propQ
        # anything else? Do I want to have an option of plotting a contour where propQ is yaxis, and another var (such as dT corresponds to different contour lines?)
        # I say no for now

        # IMPORTANT: figure out what to do with the values that don't converge
        # do I plot them directly and let people alter their inputs?
        # would prefer to get the code to determine the bounds automatically and raise errors
        #   if the range is extremely limited
        
        # TODO: add in T = D
        # TODO: limit plot (or data gathering range automatically 
        # so ppl don't have to input values 
        # they just specify which variable they want to be the array (simple)
        if isinstance(propQ, list):
            pass
        else:
            propQ = [propQ]
            
        #Iblimit, Imlimit
        for propQspec in propQ:
            propqidx = propQshort.index(propQspec)
    
            fig, ax = plt.subplots()#figsize = (7, 4), dpi = 300)
            lines = ax.plot(inputarr, PropQs[:, propqidx], color = 'k', label= '_nolegend')
            plt.xlabel(FullInputNames[xname_idx])
            plt.ylabel(propQnames[propqidx])
            
            # TODO: add tick marks to the limit lines!
            # Ib limit line
            if self.Iblimit is None:
                continue
            else:
                Ib = PropQs[:, 21]
                xcrosses, xcross_idxs = find_intersections(inputarr, Ib, self.Iblimit)
                if Ib.min() > self.Iblimit: # entire plot is invalid!
                    ax.axvline(inputarr[0], color = 'orange', path_effects = [patheffects.withTickedStroke(spacing = 12, angle = -135, length = 0.5)], 
                               label = f'Ib max = {self.Iblimit:.4g} W')
                    ax.axvline(inputarr[-1], color = 'orange', path_effects = [patheffects.withTickedStroke(spacing = 12, angle = 135, length = 0.5)])

                if len(xcrosses) == 0:
                    pass
                elif len(xcrosses) == 1:
                    # determine which way to orient the ticks
                    if Ib[xcross_idxs[0] - 1] > self.Iblimit: # if left is higher than limit, ticks face left (default)
                        ax.axvline(xcrosses[0], color = 'orange', path_effects = [patheffects.withTickedStroke(spacing = 12, angle = 135, length = 0.5)], 
                                   label = f'Ib max = {self.Iblimit:.4g} A')
                    else:
                        ax.axvline(xcrosses[0], color = 'orange', path_effects = [patheffects.withTickedStroke(spacing = 12, angle = -135, length = 0.5)], 
                                   label = f'Ib max = {self.Iblimit:.4g} A')
                        
                elif len(xcrosses) == 2:
                    # left ticks -->  |\   (angle = 135 deg)
                    # right ticks --> /|  (angle = 135 deg)
                    ax.axvline(xcrosses[0], color = 'orange', path_effects = [patheffects.withTickedStroke(spacing = 12, angle = -135, length = 0.5)], 
                               label = f'Ib max = {self.Iblimit:.4g} A')
                    ax.axvline(xcrosses[1], color = 'orange', path_effects = [patheffects.withTickedStroke(spacing = 12, angle = 135, length = 0.5)])
                    
            # Pm limit line
            if self.Pmlimit is None:
                continue
            else:
                Pin_m = PropQs[:, 14]
                xcrosses, xcross_idxs = find_intersections(inputarr, Pin_m, self.Pmlimit)
                if Pin_m.min() > self.Pmlimit: # entire plot is invalid!
                    ax.axvline(inputarr[0], color = '#cc0000', path_effects = [patheffects.withTickedStroke(spacing = 10, angle = -135, length = 0.5)], 
                               label = f'Pin_m max = {self.Pmlimit:.4g} W')
                    ax.axvline(inputarr[-1], color = '#cc0000', path_effects = [patheffects.withTickedStroke(spacing = 10, angle = 135, length = 0.5)])
                    
                if len(xcrosses) == 0:
                    pass
                elif len(xcrosses) == 1:
                    if Pin_m[xcross_idxs[0] - 1] > self.Pmlimit: # if left is higher than limit, ticks face left (default)
                        ax.axvline(xcrosses[0], color = '#cc0000', path_effects = [patheffects.withTickedStroke(spacing = 10, angle = 135, length = 0.5)], 
                                   label = f'Pin_m max = {self.Pmlimit:.4g} W')
                    else:
                        ax.axvline(xcrosses[0], color = '#cc0000', path_effects = [patheffects.withTickedStroke(spacing = 10, angle = -135, length = 0.5)], 
                                   label = f'Pin_m max = {self.Pmlimit:.4g} W')
                elif len(xcrosses) == 2:
                    ax.axvline(xcrosses[0], color = '#cc0000', path_effects = [patheffects.withTickedStroke(spacing = 10, angle = -135, length = 0.5)], 
                               label = f'Pin_m max = {self.Pmlimit:.4g} W')
                    ax.axvline(xcrosses[1], color = '#cc0000', path_effects = [patheffects.withTickedStroke(spacing = 10, angle = 135, length = 0.5)])

            # TODO: get the Mtip line to work
            # if h is None:
            #     # TODO: get alt from rho in stdatm1976 (or specified atmosphere), then get temp from alt
            #     print('Currently, cannot plot tip mach limit for rho input, please input h')
            #     continue
            # else:
            #     RPM = PropQs[:, 6]
            #     gamma = 1.4
            #     R = 286.9   # J/(kg*K)
            #     a = np.sqrt(gamma*R*atm().T(h)) #TODO allow Mtip conversion for when h is arr
            #     Mtip = (RPM*self.propdiam*np.pi/60)/a
            #     if Mtip.any() >= 0.8:
            #         ax.axvline(inputarr[np.argmin(np.abs(Mtip-0.8))], color = 'xkcd:sky blue', label = '0.8 Mtip')
            
            # cursor for datatips
            make_cursor_lineplot(lines, xname_idx, propqidx)
            
            parts = []
            validx = 0
            for idx in const_idxs:
                parts.append(f"{FullInputNamesShort[idx]} = {const_vals[validx]:.4g} {FullInputUnits[idx]}")
                validx += 1
            title_str = ", ".join(parts)
            if self.nmot > 1: # crude but works
                extra = 's'
            else:
                extra = ''
            plt.title(f'{FullInputNames[xname_idx]} sweep; {title_str}' + f'\n{self.nmot} {self.motor_name} motor{extra}, {self.prop_name} propeller{extra}, {self.batt_name} battery')
            plt.legend()
            plt.grid()
            plt.minorticks_on()
        plt.show()
        
    return(PropQs, inputarr)

#%% ContourPlot
@njit(fastmath=True)
def process_contour_loop(Uinf_grid, dT_grid, rho_grid, batt_grid, mode, args):
    '''
    mode 0: Voc or SOC (batt_grid contains Voc values)
    mode 1: t (batt_grid contains t values)
    '''
    print('Code complied, running...')
    rows, cols = Uinf_grid.shape
    output_array = np.zeros((rows, cols, 27)) # TODO: pass the 27 as some variable for the len of propQ
    for i in range(rows):
        for j in range(cols):
            Uinf = Uinf_grid[i, j]
            dT = dT_grid[i, j]
            rho = rho_grid[i, j]
            b_val = batt_grid[i, j]
            
            if mode == 0:
                # b_val is Voc
                output_array[i, j, :] = SimplifiedRPM_Voc(Uinf, dT, rho, b_val, *args)
            else:
                # b_val is t
                output_array[i, j, :] = SimplifiedRPM_t(Uinf, dT, rho, b_val, *args)
    return output_array

# supplemental function for the cursor values
def make_cursor_contourplot(artist, xname_idx, yname_idx, propQidx):
    
    c = mplcursors.cursor(artist)
    @c.connect("add")
    def _(sel):
        sel.annotation.get_bbox_patch().set(fc="white")
        x, y =  sel.target
        idx =   sel.index
        vals =  sel.artist.get_array()[idx]
        sel.annotation.set_text(
            f"{FullInputNamesShort[xname_idx]} = {x:.4g} {FullInputUnits[xname_idx]}\n"
            f"{FullInputNamesShort[yname_idx]} = {y:.4g} {FullInputUnits[yname_idx]}\n"
            f"{propQshort[propQidx]} = {vals:.4g} {propQunit[propQidx]}"
        )
    return c

# can plot any two of Uinf, dT, h/rho, t/Voc/SOC
def ContourPlotFunc(self, propQ = 'T_lbf',
                    Uinf = None, dT = None, 
                    rho = None, h = None, 
                    SOC = None, Voc = None, t = None, 
                    verbose = True, plot = False,
                    colormap = 'viridis', 
                    grade = 15):
    '''
    Input
    ----------------------------------------------------------------------------------------------------------
        a propulsion quantity (propQ) of interest (options given by the output array)
        
        constant values for two of: 
            SOC/Voc/t, Uinf, dT, rho/h
        np.array for the other two values!
        
    IMPORTANT: 
        bounds on ranges: dT in (0, 1), rho >= 0, h >= 0, SOC in (0, 1), Voc in (2.0, 4.2), t >= 0
        input arrays MUST have the same size (square input)

    Output
    ----------------------------------------------------------------------------------------------------------
        3D np array (0, 0, :) corresponding to 
        
        0       1    2     3     4      5      6      7         8      9      10     11     12 
        T_N, T_lbf, T_g, T_oz, Q_Nm, Q_lbfft, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
        
         13      14     15    16     17    18  19  20  21  22  23  24   25   26
        Pout, Pin_m, Pin_c, Pw_m   Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
        
        (0, :, 0) corresponding to the x axis input
        (:, 0, 0) corresponding to the y axis input
        
        
    Little note:
        Might be confusing why input_names is in a different order compared to LinePlot. That's to provide
        better xaxis, yaxis selection by default (time on horizontal axis, altitude on vertical, etc)
    '''
    if verbose:
        print('Compiling code (please wait ~15s)...')
    
    args = (self.GR, self.rpm_list, self.COEF_NUMBA_PROP_DATA, self.propdiam, 
            self.ns_batt, self.np_batt, self.CB, self.Rb, self.BattType, 
            self.KV, self.Rm, self.I0, self.nmot, self.ds/100)
    
    if not exactly_one_defined(t, SOC, Voc):
        raise ValueError("Exactly one of t, SOC, or Voc must be provided")
        
    if not exactly_one_defined(rho, h):
        raise ValueError("Exactly one of h or rho must be provided")
    
    full_inputs = [SOC, Voc, t, Uinf, dT, rho, h]
    # print(dT[-1])
    input_names = ['SOC', 'Voc', 't', 'Uinf', 'dT', 'rho', 'h']
    
    # out = reverse_input_conversion(SOC, Voc, t, Uinf, dT, rho, h, self.unit_idxs)
    const_idxs = get_const_idx(SOC, Voc, t, Uinf, dT, rho, h, self.unit_idxs)
    # print(dT[-1])
    # dictionary formulation
    provided_inputs = {name: val for name, val in zip(input_names, full_inputs) if val is not None}
    arrays = {}
    constants = {}
    
    for name, val in provided_inputs.items():
        if isinstance(val, (np.ndarray, list, tuple)):
            arrays[name] = np.asarray(val)
        else:
            constants[name] = val

    if len(arrays) != 2:
        raise ValueError(f"Expected exactly 2 array inputs, but found {len(arrays)}: {list(arrays.keys())}")

    xaxis, yaxis = list(arrays)
    x_array = arrays[xaxis]
    y_array = arrays[yaxis]
    
    if x_array.shape != y_array.shape:
        raise ValueError(f"Input arrays must have the same size. Got {x_array.shape} and {y_array.shape}.")

    # possible combinations
    X_grid, Y_grid = np.meshgrid(x_array, y_array)
    grid_shape = X_grid.shape 

    # map names to either a 2D varying grid or a constant 2D array
    def get_grid(name, const_dict):
        if xaxis == name: return X_grid
        if yaxis == name: return Y_grid
        return np.full(grid_shape, const_dict.get(name, 0.0), dtype=np.float64)

    # 2D input grids
    Uinf_grid = get_grid('Uinf', constants)
    dT_grid = get_grid('dT', constants)

    # Air density (rho or h input)
    if 'rho' in provided_inputs:
        rho_grid = get_grid('rho', constants)
    else:
        h_grid = get_grid('h', constants)
        rho_grid = np.vectorize(atm().rho)(h_grid) #atm().rho(h_grid) 

    # Battery state (Voc or SOC or t)
    if 'Voc' in provided_inputs:
        batt_grid = get_grid('Voc', constants)
        mode = 0
    elif 'SOC' in provided_inputs:
        soc_grid = get_grid('SOC', constants)
        batt_grid = VocFuncBase(soc_grid, self.BattType) 
        mode = 0
    else:
        batt_grid = get_grid('t', constants)
        mode = 1
        
    # Numba loop
    output_array = process_contour_loop(Uinf_grid, dT_grid, rho_grid, batt_grid, mode, args)
    SOC, Voc, t, Uinf, dT, rho, h = reverse_input_conversion(SOC, Voc, t, Uinf, dT, rho, h, self.unit_idxs)
    # recall to get correctly scaled values
    full_inputs = [SOC, Voc, t, Uinf, dT, rho, h]
    input_names = ['SOC', 'Voc', 't', 'Uinf', 'dT', 'rho', 'h']    
    
    # repopulate arrays and constants with unconverted values
    provided_inputs = {name: val for name, val in zip(input_names, full_inputs) if val is not None}
    arrays = {}
    constants = {}
    fullname_idxs = []
    specidx = 0 # used to determine which two indixes from self.unit_idxs to use for axes
    for name, val in provided_inputs.items():
        if isinstance(val, (np.ndarray, list, tuple)):
            arrays[name] = np.asarray(val)
            fullname_idxs.append(self.unit_idxs[specidx])
            specidx += 1
        else:
            constants[name] = val
            specidx += 1
    xaxis, yaxis = list(arrays)
    x_array = arrays[xaxis]
    y_array = arrays[yaxis]
    
    xname_idx = fullname_idxs[0]
    yname_idx = fullname_idxs[1]
    
    const_vals = get_const_vals(SOC, Voc, t, Uinf, dT, rho, h, self.unit_idxs) # TODO: automate so it gets the input const vals (ignore rho, Voc if they get precalculated)
    if plot:
        # TODO: add in T = D
        # TODO: limit plot (or data gathering range automatically 
        # so ppl don't have to input values, they just specify which variable they want to be the array (simple)
        if isinstance(propQ, list):
            pass
        else:
            propQ = [propQ]
        
        X, Y = np.meshgrid(x_array, y_array)
        
        # Mandatory: 
            # Ilimit from battery/motor spec sheet  (Orange)
            # Plimit from motor spec sheet          (Red)
            # M = 0.8 tip speed for propellers (?)  (Sky blue)
        # optional:
            # any propQ value
        
        # Ib, Im, Ic used for limits
        # Iblimit from batteries.csv (use continuous)
        # Imlimit from motors.csv
        # Ic from generic, maybe user input?
        # Do I want to have specific esc input in the setup? Could use Jeong model then
        # could use generic ESC by default
        
        # diam from propeller data
        # then tip speed from RPM
        
        # NOTE: rn no Imlimit in motors.csv
        # yeah that needs to change
        # voltage limit on motors based on compatable cells
        # print(self.Iblimit)
        
        # key:
        # 0       1    2     3     4      5      6      7         8      9      10     11     12 
        # T_N, T_lbf, T_g, T_oz, Q_Nm, Q_lbfft, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
        
        #  13      14     15    16     17    18  19  20  21  22  23  24   25   26
        # Pout, Pin_m, Pin_c, Pw_m   Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
        for propQspec in propQ:
            fig, ax = plt.subplots()

            propqidx = propQshort.index(propQspec)
            propQ_spec = output_array[:, :, propqidx]
            
            # plot propQ contourplot
            propQ_spec_alt = propQ_spec[propQ_spec > 0]    # very good for removing all the violation keys, and finding the max, but flattens the array
            lower = propQ_spec_alt.min()                    # finds the minimum Score discounting violation trips
            upper = propQ_spec.max()
            img = ax.contourf(X, Y, propQ_spec, cmap = colormap, levels = np.linspace(lower, upper, grade))
            fig.colorbar(img, ticks = np.linspace(lower, upper, 11), pad = 0.025, shrink = 1.0, spacing = 'uniform', label=f'{propQnames[propqidx]}')
        
            # TODO: add tick marks to the limit lines!
            inlinelabel = True
            # Ib limit line
            if self.Iblimit is None:
                continue
            else:
                Ib = output_array[:, :, 21]

                if self.Iblimit < Ib.max():
                    Iblimitline = ax.contour(X, Y, Ib, colors = 'orange', levels = np.array([self.Iblimit]))
                    ax.clabel(Iblimitline, inline = inlinelabel, fmt=lambda v: f'{v:.1f}A')
                    
            # Pm limit line
            if self.Pmlimit is None:
                continue
            else:
                Pin_m = output_array[:, :, 14]
                if self.Pmlimit < Pin_m.max():
                    Pmlimitline = ax.contour(X, Y, Pin_m, colors = '#cc0000', levels = np.array([self.Pmlimit]))
                    ax.clabel(Pmlimitline, inline = inlinelabel, fmt=lambda v: f'{v:.1f}W')

            # Tip Mach (Mtip) limit line
            if h is None:
                # TODO: get alt from rho in stdatm1976 (or specified atmosphere), then get temp from alt
                print('Currently, cannot plot tip mach limit for rho input, please input h')
                continue
            else:
                RPM = output_array[:, :, 6]
                
                gamma = 1.4
                R = 286.9   # J/(kg*K)
                a = np.sqrt(gamma*R*atm().T(h)) #TODO allow Mtip conversion for when h is arr
                Mtip = (RPM*self.propdiam*np.pi/60)/a
                if Mtip.any() >= 0.8:
                    Mtiplimitline = ax.contour(X, Y, Mtip, colors = 'xkcd:sky blue', levels = np.array([0.8]))
                    ax.clabel(Mtiplimitline, inline = inlinelabel, fmt=lambda v: f'{v:.2f}')

            # properly need to get xname, yname indices corresponding to FullInputNames!
            plt.xlabel(FullInputNames[xname_idx])
            plt.ylabel(FullInputNames[yname_idx])
            
            # make a grid of hidden points to use with the interactive datatips
            dots = ax.scatter(X.flatten(), Y.flatten(), c = propQ_spec.flatten(), alpha = 0)
            make_cursor_contourplot(dots, xname_idx, yname_idx, propqidx)
            
            # get short names of inputs along with title string
            # parts = []
            # for name, val in zip(input_names, full_inputs):
            #     if val is None:
            #         continue
            #     if isinstance(val, np.ndarray):
            #         continue  # skip arrays
            #     parts.append(f"{name} = {val}")
            # title_str = ", ".join(parts)
            
            # add constants to title string with proper units!
            parts = []
            validx = 0
            for idx in const_idxs:
                parts.append(f"{FullInputNamesShort[idx]} = {const_vals[validx]:.4g} {FullInputUnits[idx]}")
                validx += 1
            title_str = ", ".join(parts)
            if self.nmot > 1:
                extra = 's'
            else:
                extra = ''
            plt.title(f'{FullInputNames[xname_idx]}, {FullInputNames[yname_idx]} sweeps; {title_str}' + f'\n{self.nmot} {self.motor_name} motor{extra}, {self.prop_name} propeller{extra}, {self.batt_name} battery')
            plt.minorticks_on()
        plt.show()
        
    
    # output array = (n, n, len(propQshort)) where (:, 0, 0) corresponds to y and (0, :, :) corresponds to x
    # return xarr, yarr, output
    return(x_array, y_array, output_array)