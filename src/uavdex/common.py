# -*- coding: utf-8 -*-
"""

Primary Classes:
    
    PointDesign <-- higher fidelity analyses of detailed designs
    DesignStudy <-- lowest fidelity MDAO using GEKKO
    ClassicSizing <-- Raymer methods with added electric propulsion


With motor, battery, propeller selected:
    Primary Inputs: 
        throttle setting (dT) in %
        freestream velocity (Vinf) in m/s
        
        1 of:
            air density (rho) in kg/m^3
            altitude (h) in m --> rho via stdatm1976 
        
        1 of:
            cell voltage (Voc) in Volts
            battery State of Charge (SOC) in % --> Voc from LiPo discharge curve
            runtime (t) in seconds --> SOC from constant current approximation --> Voc
        
    Output any propulsion quantity.

@author: NASSAS
"""

import numpy as np
import pandas as pd
import os
import subprocess
from uavdex import _uavdex_root
from uavdex.performance import *
from uavdex.propulsions import *
from uavdex.VSPcontribution.atmosphere import stdatm1976 as atm 
from uavdex.utils import *

### OLD LOCAL TESTING
# from performance import *
# from propulsions import *
# from VSPcontribution.atmosphere import stdatm1976 as atm

# from pathlib import Path
# _uavdex_root = Path(__file__).parent

path_to_data = _uavdex_root / 'Databases/'

lbfN = 4.44822
ftm = 0.3048

class PointDesign:
    def __init__(self):
        print('Point Design Initiated!')#\nPlease define a battery, motor, prop, and aerodynamic parameters')
        self.rho = 1.225 #kg/m3
        self.density_specified = False
        
    def MotorOptions(self):
        df = pd.read_csv(path_to_data / 'Motors.csv')
        print('\nMotor Options:')
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        print(df[['Manufacturer', 'Name', 'KV', 'Pmax (W)', 'Gear Ratio']])
        pd.reset_option('display.max_rows')
        pd.reset_option('display.max_columns')
        
    def BatteryOptions(self):
        df = pd.read_csv(path_to_data / 'Batteries.csv')
        print('\nBattery Options:')
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        print(df.assign(
            Config=df['Series Cell Count'].astype(str) + 'S' +
                   df['Parallel Cell Count'].astype(str) + 'P'
        )
        .rename(columns={'Max Continuous Discharge (A)': 'Max Current (A)'})
        [['Name', 'Config', 'Max Current (A)', 'Capacity (mAh)']])
        pd.reset_option('display.max_rows')
        pd.reset_option('display.max_columns')
    
    def PropellerOptions(self):
        with open(path_to_data / 'APCPropDatabase/proplist.txt', 'r') as f:
            data_content = f.read()
        propellers = data_content.replace('PER3_', '')
        propellers = propellers.replace('.dat', '').split('\n')
        print('\nAPC Propeller Options:')
        for a,b,c,d, e, f in zip(propellers[::6],propellers[1::6],propellers[2::6], propellers[3::6], propellers[4::6], propellers[5::6]):
            print(f'{a:14} {b:14} {c:14} {d:14} {e:14} {f:14}')

    def ViewSetup(self):
        print(f'Battery Specs: {self.batt_name}, {self.ns_batt}S{self.np_batt}P, {self.CB} mAh, {self.Rb} Ohm\n'
              f'Motor Specs:   {self.nmot:.0f} {self.motor_name}, {self.KV} KV, I0 = {self.I0} A, {self.Rm} Ohm, Max Power = {self.Pmlimit} W\n')
    
    def OpenMotorData(self):
        '''
        Opens the Motor CSV for editing/review
        '''
        filename = path_to_data / 'Motors.csv'
        open_csv(filename)
    
    def OpenBatteryData(self):
        '''
        Opens the Batteries CSV for editing/review
        '''
        
        filename = path_to_data / 'Batteries.csv'
        open_csv(filename)
    
    def OpenPropellerData(self):
        '''
        Opens the Propeller data folder for editing/review
        '''
        folder_path = path_to_data /'APCPropDatabase'
        open_folder(folder_path)
            
    ########################################################
    ########################################################
    ############### COMPONENT INITIALIZATION ###############
    ########################################################
    ########################################################
    def Battery(self, batt_name, discharge = 0.85):
        '''
        batt_name will be "manufacturer_#cellS_capacity"
        i.e. "Gaoneng_8S_3300, MaxAmps_12S_2000"
        '''
        self.batt_name = batt_name
        self.ds = discharge
        df = pd.read_csv(path_to_data / 'Batteries.csv')
        try:
            batt_data = df.loc[df['Name'] == self.batt_name]
        except:
            raise ValueError('Battery name not recognized; please call .BatteryOptions() or .OpenBatteryData()')
        self.ns_batt = batt_data['Series Cell Count'].values[0]
        self.np_batt = batt_data['Parallel Cell Count'].values[0]
        self.CB = batt_data['Capacity (mAh)'].values[0]
        self.Rb = batt_data['Resistance (Ohm)'].values[0]
        self.BattType = batt_data['Battery Type'].values[0] # string, either LiPo or Liion
        self.Iblimit = batt_data['Max Continuous Discharge (A)'].values[0]
        self.battery = True
        # soon add weight, max continuous current, etc
        
    def Motor(self, motor_name, nmot = 1):
        '''
        Motor name will be the designation without the manufacturer name
        i.e. C-4120/30 for the Cobra C-4120/30 motors
        Follow the nomenclature from eCalc for consistency 
        (AND IMPLEMENT A SEARCH THAT MAKES THE NAME CASE INSENSITIVE)
        
        NOTE: make sure to save the csv as a UTF-8 deliminated file (and perhaps change to excel workbook soon)
        '''
        self.motor_name = motor_name
        self.nmot = nmot
        df = pd.read_csv(path_to_data / 'Motors.csv')
        try:
            motor_data = df.loc[df['Name'] == motor_name]
            self.motor_manufacturer = motor_data['Manufacturer'].values[0]
            self.KV = motor_data['KV'].values[0]
            self.I0 = motor_data['I0 (A)'].values[0]
            self.V_I0 = motor_data['V_I0 (V)'].values[0]
            self.Rm = motor_data['Rm (Ohm)'].values[0]
            self.Pmlimit = motor_data['Pmax (W)'].values[0]
            self.GR = motor_data['Gear Ratio'].values[0]
            self.motor = True
        except:
            # if self.suppress == False:
            raise KeyError('Motor name not recognized, please call .MotorOptions()')
        # soon add V_I0
    
    def Prop(self, prop_name):
        '''
        prop_name is a string with the form 16x10E, 12x12 (no PER3_ or .dat for useability'''
        self.prop_name = prop_name
        self.COEF_PROP_DATA, self.COEF_NUMBA_PROP_DATA = parse_coef_propeller_data(prop_name)
        self.rpm_list = np.array(self.COEF_PROP_DATA['rpm_list'])
        self.propdiam = float(prop_name.split('x')[0])*0.0254 # convert inches to m
        self.prop = True
        
        # self.PROP_DATA, self.NUMBA_PROP_DATA = parse_propeller_data(prop_name)
        # rpm_vals, self.THRUST_POLYS, self.TORQUE_POLYS, self.V_DOMAINS  = initialize_RPM_polynomials(self.PROP_DATA)

        
    ########################################################
    ########################################################
    ############### PROPULSION FUNCTIONS ###################
    ########################################################
    ########################################################
    def PointResult(self, Uinf = None, dT = None, 
                    rho = None, h = None, 
                    SOC = None, Voc = None, t = None, 
                    verbose = True):
        '''
        Input
        ----------------------------------------------------------------------------------------------------------
            Uinf        (freestream velocity, m/s)
            dT          (throttle, 0-1)
            rho         (density, kg/m3) 
                or h    (altitude, m)
            SOC         (state of charge, 0-1) 
                or Voc  (cell voltage, 3.3-4.2) 
                or t    (runtime, s)
            
        Output
        ----------------------------------------------------------------------------------------------------------
        np.array of propulsion quantities (propQs) with corresponding indexes
            0  1   2       3        4      5      6      7       8    
            T, Q, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
            
             9      10     11    12    13    14   15  16  17  18  19  20   21   22
            Pout, Pin_m, Pin_c, Pw_m  Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
        '''
        def check(val, cond, name):
            if val is None:
                return
            if not cond(val):
                raise ValueError(f"{name} out of bounds: {val}")
        check(dT,  lambda x: (x >= 0.0) & (x <= 1), "dT")
        check(rho, lambda x: x >= 0.0, "rho")
        check(h,   lambda x: x >= 0.0, "h")
        check(SOC, lambda x: (x >= 0.0) & (x <= 1), "SOC")
        check(Voc, lambda x: (x >= 2.0) & (x <= 4.2), "Voc")
        check(t,   lambda x: x >= 0.0, "t") 
            
        return(PointResultFunc(self, Uinf = Uinf, dT = dT, rho = rho, h = h, 
                               SOC = SOC, Voc = Voc, t = t, 
                               verbose = verbose))
    
    def LinePlot(self, propQ = 'T', 
                 Uinf = None, dT = None, 
                 rho = None, h = None, 
                 SOC = None, Voc = None, t = None, 
                 verbose = False, plot = True):
        '''
        Input
        ----------------------------------------------------------------------------------------------------------
            fix three of 
                dT, Vinf, rho/h, t/SOC/Voc
            for the remaining one, input a np.array of values
            
            OPTIONAL FOR PLOTTING: 
                propulsion quantity (propQ) of interest to plot:
                    T, Q, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
                    Pout, Pin_m, Pin_c, Pw_m, Pw_c, Pw_b, Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
        
        Output
        ----------------------------------------------------------------------------------------------------------
            PropQs, input array
            
        PropQs: a 2D np array with columns corresponding to
            0  1   2       3        4      5      6      7       8    
            T, Q, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
            
             9      10     11    12    13    14   15  16  17  18  19  20   21   22
            Pout, Pin_m, Pin_c, Pw_m  Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC

        and the rows corresponding to the value of the variable input
        
        then also the input 1D np array
        '''
        # todo add bounds on ranges
        # bounds on ranges: dT in (0, 1), rho >= 0, h >= 0, SOC in (0, 1), Voc in (2.0, 4.2), t >= 0
        def check(val, cond, name):
            if val is None:
                return
            arr = np.asarray(val)
            if not np.all(cond(arr)):
                raise ValueError(f"{name} out of bounds (see func docstring)")
        check(dT,  lambda x: (x >= 0.0) & (x <= 1), "dT")
        check(rho, lambda x: x >= 0.0, "rho")
        check(h,   lambda x: x >= 0.0, "h")
        check(SOC, lambda x: (x >= 0.0) & (x <= 1), "SOC")
        check(Voc, lambda x: (x >= 2.0) & (x <= 4.2), "Voc")
        check(t,   lambda x: x >= 0.0, "t") 
                
        return(LinePlotFunc(self, propQ = propQ, Uinf = Uinf, dT = dT, 
                            rho = rho, h = h, SOC = SOC, Voc = Voc, t = t, 
                            verbose = verbose, plot = plot))
        
    def ContourPlot(self, propQ = 'T',
                    xaxis = None,
                    yaxis = None,
                    Uinf = None, dT = None, 
                    rho = None, h = None, 
                    SOC = None, Voc = None, t = None, 
                    verbose = True, plot = True):
        '''
        Input
        ----------------------------------------------------------------------------------------------------------
            a propulsion quantity (propQ) of interest (options given by the output array)
            
            constant values for two of: 
                Uinf, dT, rho/h, SOC/Voc/t
            equal size np.arrays for the other two values
            
            Optional: 
                xaxis, yaxis for plot specified from the names:
                    ['Uinf', 'dT', 'rho', 'h', 'SOC', 'Voc', 't']

            
        IMPORTANT: 
            bounds on ranges: dT in (0.2, 1), rho >= 0, h >= 0, SOC in (0, 1), Voc in (2.0, 4.2), t >= 0
            input arrays MUST have the same size (square input)

        Output
        ----------------------------------------------------------------------------------------------------------
            3D np array where (0, 0, :) corresponds to 
            
            0  1   2       3        4      5      6      7       8    
            T, Q, RPM, eta_drive, eta_p, eta_g, eta_m, eta_c, eta_b, 
            
             9      10     11    12    13    14   15  16  17  18  19  20   21   22
            Pout, Pin_m, Pin_c, Pw_m  Pw_c  Pw_b  Im, Ic, Ib, Vm, Vc, Vb, Voc, SOC
            
            (0, :, 0) corresponding to the x axis input
            (:, 0, 0) corresponding to the y axis input
        
        
        '''
        def check(val, cond, name):
            if val is None:
                return
            arr = np.asarray(val)
            if not np.all(cond(arr)):
                raise ValueError(f"{name} out of bounds: {val}")
        check(dT,  lambda x: (x > 0) & (x <= 1), "dT")
        check(rho, lambda x: x >= 0, "rho")
        check(h,   lambda x: x >= 0, "h")
        check(SOC, lambda x: (x >= 0) & (x <= 1), "SOC")
        check(Voc, lambda x: (x >= 2.0) & (x <= 4.2), "Voc")
        check(t,   lambda x: x >= 0, "t") 
        
        return(ContourPlotFunc(self, propQ = propQ, xaxis = xaxis, yaxis=yaxis, 
                               Uinf = Uinf, dT = dT, 
                               rho = rho, h = h, SOC = SOC, Voc = Voc, t = t, 
                               verbose = verbose, plot = plot))
        
    # #############################################################################
    # #############################################################################
    # #############################################################################
    # ################## OLD CODE TO BE REPLACED AND REFORMATTED ##################
    # #############################################################################
    # #############################################################################
    # #############################################################################
    # def PropulsionSlices(self, slicevalues, throttles, sliceinput = 'SOC', quantity = 'thrust', n = 300, plot = True, verbose = True):
    #     '''
    #     Here slicevalues and throttles are lists (**ADD IN ARRAY COMPATIBILITY SOON**) which will all be plotted on the same graph
        
    #     NOTE: time for each iteration is insignificant compared to numba compile time (n = 50 ~= n = 300)1
    #     '''
    #     if self.CheckVariables():
    #         self.qofinterest = quantity
    #         if sliceinput == 'SOC':
    #             self.sliceinput = 'SOC'
    #             self.slicevalue = slicevalues
    #         elif sliceinput == 'Voc':
    #             self.sliceinput = 'Voc'
    #             self.slicevalue = slicevalues
    #         elif sliceinput == 'velocity':
    #             self.sliceinput = 'velocity'
    #             self.slicevalue = slicevalues
    #         else:
    #             print('SOCinput not recognized.\nPlease provide State Of Charge (SOC) as a fraction or Voltage per cell in series (Voc) in Volts or Velocity in m/s')
    #             return()
            
    #         if len(slicevalues) != len(throttles):
    #             raise KeyError(f'{sliceinput} and throttle values do not have the same length')
    #             return()
            
    #         propulsions.DynamicPropulsionPlot(self, n, throttle = throttles, plot = plot, verbose = verbose)

        
    # def Runtimes(self, n, verbose = False, showthrust = True):
    #     '''
    #     TO BE OPTIMIZED LATER WITH SCIPY CONFIG OR MULTIPROCESSING
        
    #     n is number of velocities considered (essentially more --> greater accuracy, less --> faster execution)
    #     '''
    #     if self.CheckVariables():
    #         propulsions.PlotRuntimes(self, n, verbose = False, showthrust = showthrust)       
    
    # def PointDesignData(self, n, Ilimit = np.inf, grade = 15):
    #     '''
    #     inputs n (iter), Ilimit for current limits, grade (contours), 
    #     plots Thrust, RPM, Power per motor, and Current as functions of cruise velocity and battery runtime

    #     n is number of indices, Ilimit is the current limit in A
        
    #     Multiprocessing is significantly slower than the normal version 
    #     (for n = 300, it takes 689s instead of 149s (but I kept it in the propulsions module bc I'm proud of the work)
    #     '''
    #     if self.CheckVariables():
    #         propulsions.GetPointDesignData(self, n)
    #         propulsions.plotMosaic(self, Ilimit = Ilimit, grade = grade)
            
    # def PointDesignDataV2(self, n, Varr = False, tarr = False, Ilimit = np.inf, throttle = None, grade = 15):
    #     '''
    #     inputs n (iter), Ilimit for current limits, grade (contours), 
    #     plots Thrust, RPM, Power per motor, and Current as functions of cruise velocity and battery runtime

    #     n is number of indices, Ilimit is the current limit in A
        
    #     Multiprocessing is significantly slower than the normal version 
    #     (for n = 300, it takes 689s instead of 149s (but I kept it in the propulsions module bc I'm proud of the work)
    #     '''
    #     if self.CheckVariables():    
    #         if type(Varr) != bool and type(tarr) != bool:
    #             self.Vtemp = Varr
    #             self.ttemp = tarr
    #             self.setbounds = True
    #         else:
    #             self.setbounds = False
    #         propulsions.GetPointDesignDataV2(self, n, throttle = throttle)
    #         propulsions.plotMosaic(self, Ilimit = Ilimit, grade = grade, throttle = throttle)
            
    # def PointDesignDataV4(self, n, Ilimit = np.inf, throttle = None, grade = 15):
    #     '''
    #     inputs n (iter), Ilimit for current limits, grade (contours), 
    #     plots Thrust, RPM, Power per motor, and Current as functions of cruise velocity and battery runtime
    
    #     n is number of indices, Ilimit is the current limit in A
        
    #     Multiprocessing is significantly slower than the normal version 
    #     (for n = 300, it takes 689s instead of 149s (but I kept it in the propulsions module bc I'm proud of the work)
    #     '''
    #     if self.CheckVariables():                
    #         propulsions.GetPointDesignDataV3(self, n, throttle = throttle)
    #         propulsions.plotMosaic(self, Ilimit = Ilimit, grade = grade, throttle = throttle)

    # def ThrustCruisePareto(self, proplist=None, lb=0.0, ub=1000.0, 
    #                     Ilimit = 100, verbose=False, AnnotateAll = False):
    #     '''
    #     Plots the pareto front of static thrust vs cruise speed
    #     for all (or selected) propellers 
        
    #     multiprocessing
    #     '''
    #     if self.CheckVariables(proptest=False):
    #         self.Ilimit = Ilimit
    #         self.lb = lb
    #         self.ub = ub
    #         self.AnnotateAll = AnnotateAll
    #         self.proplist = proplist
    #         propulsions.PlotTCPareto_mp(self, verbose = verbose)
        
    # def TakeoffCruisePareto(self, proplist = None, lb = 0.0, ub = 1000.0,
    #                         Ilimit = 100, xloflimit = 150,
    #                         verbose = False, AnnotateAll = False):
    #     '''
    #     xloflimit in ft, Ilimit in A, mufric as takeoff friction coef
        
    #     no multiprocessing (yet)
    #     '''
    #     if self.CheckVariables(proptest = False):
    #         self.Ilimit = Ilimit
    #         self.lb = lb
    #         self.ub = ub
    #         self.AnnotateAll = AnnotateAll
    #         self.proplist = proplist
    #         self.xloflimit = xloflimit
    #         propulsions.plotTakeoffParetoFrontNumba(self, verbose = verbose)
        
    # def MGTOWCruisePareto(self, motorlist = None, nmots = None, proplist = None, 
    #                       lb = 0.0, ub = 1000.0, Ilimit = 100, xloflimit = 150, 
    #                       AnnotateAll = False, SkipInvalid = False, 
    #                       AllPareto = False):
    #     '''
    #     xloflimit in ft, Ilimit in A, mufric as takeoff friction coef
        
    #     can pass a list of motors and the corresponding number of them to test, or pass none
    #     to test all with 1 motor
        
    #     FUTURE: replace mufric with 'wet grass' or 'concrete', etc
    #     '''
    #     if self.CheckVariables(proptest=False, motortest=False):
    #         self.Ilimit = Ilimit
    #         self.lb = lb 
    #         self.ub = ub
    #         self.xloflimit = xloflimit
    #         self.AnnotateAll = AnnotateAll
    #         self.SkipInvalid = SkipInvalid
            
    #         # if motorlist is undefined and a motor is given, 
    #         #       run the preset motor and nmot
    #         # if motorlist is undefined and no motors are given:
    #         #       run all motors as singles
    #         # if motorlist is defined but number of motors is not:
    #         #       run all motors as singles and note
    #         # if motorlist is defined and nmot is defined:
    #         #       run as given
    #         if motorlist == None and self.CheckVariables(proptest = False):
    #             self.motorlist = [self.motor_name]
    #             self.nmots = [self.nmot]
    #         elif motorlist == None or motorlist == 'All' or motorlist == 'all':
    #             self.motorlist = 'all'
    #             self.nmots = nmots
    #         elif motorlist != None and nmots == None:
    #             self.motorlist = motorlist 
    #             self.nmots = np.ones(len(self.motorlist))
    #             print('\nNumber of motors undefined; running all motors as single')
    #         else:
    #             self.motorlist = motorlist
    #             self.nmots = nmots
            
    #         self.proplist = proplist
    #         propulsions.plotMultiMotorMGTOWPareto(self, verbose = False, AllPareto = AllPareto)
        
    # def MGTOWCruiseParetoFAST(self, motorlist = None, nmots = None, proplist = None, 
    #                       lb = 0.0, ub = 1000.0, Ilimit = 100, xloflimit = 150, runtimelimit = None,
    #                       AnnotateAll = False):
    #     if self.CheckVariables(proptest=False, motortest=False):
    #         self.Ilimit = Ilimit
    #         self.lb = lb 
    #         self.ub = ub
    #         self.xloflimit = xloflimit
    #         self.runtimelimit = runtimelimit
    #         self.AnnotateAll = AnnotateAll
            
    #         # if motorlist is undefined and a motor is given, 
    #         #       run the preset motor and nmot
    #         # if motorlist is undefined and no motors are given:
    #         #       run all motors as singles
    #         # if motorlist is defined but number of motors is not:
    #         #       run all motors as singles and note
    #         # if motorlist is defined and nmot is defined:
    #         #       run as given
    #         if motorlist == None and self.CheckVariables(proptest = False):
    #             self.motorlist = [self.motor_name]
    #             self.nmots = [self.nmot]
    #         elif motorlist == None or motorlist == 'All' or motorlist == 'all':
    #             self.motorlist = 'all'
    #             self.nmots = nmots
    #         elif motorlist != None and nmots == None:
    #             self.motorlist = motorlist 
    #             self.nmots = np.ones(len(self.motorlist))
    #             print('\nNumber of motors undefined; running all motors as single')
    #         else:
    #             self.motorlist = motorlist
    #             self.nmots = nmots
            
    #         self.proplist = proplist
    #         propulsions.plotmultiparetoFullNumba(self, verbose = False)
            
    # def MGTOWEffParetoFAST(self, motorlist = None, nmots = None, proplist = None, 
    #                       lb = 0.0, ub = 1000.0, Ilimit = 100, xloflimit = 150, runtimelimit = None,
    #                       AnnotateAll = False):
    #     if self.CheckVariables(proptest=False, motortest=False):
    #         self.Ilimit = Ilimit
    #         self.lb = lb 
    #         self.ub = ub
    #         self.xloflimit = xloflimit
    #         self.runtimelimit = runtimelimit
    #         self.AnnotateAll = AnnotateAll
            
    #         # if motorlist is undefined and a motor is given, 
    #         #       run the preset motor and nmot
    #         # if motorlist is undefined and no motors are given:
    #         #       run all motors as singles
    #         # if motorlist is defined but number of motors is not:
    #         #       run all motors as singles and note
    #         # if motorlist is defined and nmot is defined:
    #         #       run as given
    #         if motorlist == None and self.CheckVariables(proptest = False):
    #             self.motorlist = [self.motor_name]
    #             self.nmots = [self.nmot]
    #         elif motorlist == None or motorlist == 'All' or motorlist == 'all':
    #             self.motorlist = 'all'
    #             self.nmots = nmots
    #         elif motorlist != None and nmots == None:
    #             self.motorlist = motorlist 
    #             self.nmots = np.ones(len(self.motorlist))
    #             print('\nNumber of motors undefined; running all motors as single')
    #         else:
    #             self.motorlist = motorlist
    #             self.nmots = nmots
            
    #         self.proplist = proplist
    #         propulsions.plotmultiparetoEFFICIENCYFullNumba(self, verbose = False)
            
    # def CruiseEffPareto(self, motorlist = None, nmots = None, proplist = None, 
    #                       lb = 0.0, ub = 1000.0, Ilimit = 100, xloflimit = 150, runtimelimit = None,
    #                       AnnotateAll = False):
    #     if self.CheckVariables(proptest=False, motortest=False):
    #         self.Ilimit = Ilimit
    #         self.lb = lb 
    #         self.ub = ub
    #         self.xloflimit = xloflimit
    #         self.runtimelimit = runtimelimit
    #         self.AnnotateAll = AnnotateAll
            
    #         # if motorlist is undefined and a motor is given, 
    #         #       run the preset motor and nmot
    #         # if motorlist is undefined and no motors are given:
    #         #       run all motors as singles
    #         # if motorlist is defined but number of motors is not:
    #         #       run all motors as singles and note
    #         # if motorlist is defined and nmot is defined:
    #         #       run as given
    #         if motorlist == None and self.CheckVariables(proptest = False):
    #             self.motorlist = [self.motor_name]
    #             self.nmots = [self.nmot]
    #         elif motorlist == None or motorlist == 'All' or motorlist == 'all':
    #             self.motorlist = 'all'
    #             self.nmots = nmots
    #         elif motorlist != None and nmots == None:
    #             self.motorlist = motorlist 
    #             self.nmots = np.ones(len(self.motorlist))
    #             print('\nNumber of motors undefined; running all motors as single')
    #         else:
    #             self.motorlist = motorlist
    #             self.nmots = nmots
            
    #         self.proplist = proplist
    #         propulsions.plotmultiparetoCruiseEff(self, verbose = False)

                
    # def testVmax(self):
    #     print(propulsions.VmaxLean(self, 0.0, t_in = 0.0, Tlimit = True))
        
    # def testMGTOW(self):
    #     self.xloflimit = 60
    #     self.Ilimit = 105
    #     print(propulsions.MGTOWinnerfunc_fast(self, 30.0))
    
    
    # ########################################################
    # ########################################################
    # ########################################################
    # ############## PERFORMANCE FUNCTIONS ###################  
    # ########################################################
    # ########################################################
    # ########################################################
    # def PrepMissionSim(self, CDtoPreR, CDtoPostR, CLtoPreR, CLtoPostR, CDturn, CLturn, 
    #                    takeoffdT, climbdT, cruisedT, turndT):
    #     print('\nMission Simulation Initialized!')
        
    #     self.cruisedT = cruisedT
    #     self.turndT = turndT 
    #     self.takeoffdT = takeoffdT 
    #     self.climbdT = climbdT
        
    #     # acceleration, velocity, position, altitude, time
    #     self.a_track = []
    #     self.V_track = []
    #     self.x_track = []
    #     self.h_track = []
    #     self.t_track = []
        
    #     # forces
    #     self.T_track = []
    #     self.D_track = []
    #     self.n_track = []
        
    #     # propulsion data
    #     self.SOC_track = []
    #     self.Itot_track = []
    #     self.RPM_track = []
    #     self.Q_track = []
    #     self.P_track = []
    #     self.eta_track = []
        
    #     self.datatrack = [self.a_track, 
    #                     self.V_track,
    #                     self.x_track,
    #                     self.h_track,
    #                     self.t_track,
    #                     self.T_track,
    #                     self.D_track,
    #                     self.n_track,       #load factor
    #                     self.SOC_track,
    #                     self.Itot_track,
    #                     self.RPM_track,
    #                     self.P_track,
    #                     self.Q_track,
    #                     self.eta_track]
        
    #     self.mass = self.MGTOW/9.81 
        
    #     self.CDtoPreR = CDtoPreR # drag coef for takeoff pre-rotation (so 0 aoa with high lift devices)
    #     self.CDtoPostR = CDtoPostR # drag coef for takeoff post-rotation (so ~10 deg aoa with high lift devices)
    #     self.CLtoPreR = CLtoPreR
    #     self.CLtoPostR = CLtoPostR
        
    #     self.CLturn = CLturn
    #     self.CDturn = CDturn
    #     self.Vstall = np.sqrt((2*self.MGTOW)/(self.rho*self.Sw*self.CLmax)) # later modify so flaps can be specified in turn segments
    #     self.Vlof = 1.15 * self.Vstall
        
    #     self.segment_index = 0
    #     self.labels = []
        
    #     self.CheckVariables()
    #     #velocity for stall and lof are already implemented!
    #     self.PreppedMissionSim = True
        
    # def CheckMissionInit(self):
    #     if self.PreppedMissionSim:
    #         return True
    #     else:
    #         raise ValueError('\nMission simulation not initialized; please use PrepMissionSim()')
    #         return False
    
    # def DetailedTakeoff(self, aoa_rotation, t_expect = 50, plot = True):
    #     '''
    #     b is wingspan in m
    #     h0 is height from fuselage centerline to ground (before takeoff)
    #     taper is the taper ratio'''
    #     if self.CheckVariables() and self.CheckMissionInit():
    #         performance.SimulateTakeoff(self, aoa_rotation = aoa_rotation,
    #                                     texpect = t_expect, 
    #                                     plot = plot, results = True)

    # def resetdata(self):
    #     # acceleration, velocity, position, altitude, time
    #     self.a_track = []
    #     self.V_track = []
    #     self.x_track = []
    #     self.h_track = []
    #     self.t_track = []
        
    #     # forces
    #     self.T_track = []
    #     self.D_track = []
    #     self.n_track = []
        
    #     # propulsion data
    #     self.SOC_track = []
    #     self.Itot_track = []
    #     self.RPM_track = []
    #     self.Q_track = []
    #     self.P_track = []
    #     self.eta_track = []
        
    #     self.datatrack = [self.a_track, 
    #                     self.V_track,
    #                     self.x_track,
    #                     self.h_track,
    #                     self.t_track,
    #                     self.T_track,
    #                     self.D_track,
    #                     self.n_track,       #load factor
    #                     self.SOC_track,
    #                     self.Itot_track,
    #                     self.RPM_track,
    #                     self.P_track,
    #                     self.Q_track, 
    #                     self.eta_track]
    #     self.segment_index = 0 
    #     self.labels = []
    #     self.lap_ends = []
        
    # def updatedata(self, newdata):
    #     '''
    #     All data from the takeoff, cruise, climb, turn functions is in the format:
    #         avalues, Vvalues, xvalues, tvalues, Tvalues, Dvalues, SOCvalues, Itotvalues, RPMvalues,
    #         Qvalues, Pvalues (note: P is per motor!)'''
    #     for i in range(len(self.datatrack)):
    #         self.datatrack[i].append(newdata[i])
            
    # def DBF_Lap(self, verbose = False):
    #     '''
        
    #     Typical DBF lap: 
    #     500 ft straight, 180 deg turn, 500 ft straight (or less or more!), 360 deg turn, 500 ft straight, 180 deg turn, 500 ft straight 
    #     (and you're back over the start line!)
         
    #     First lap is slightly different bc you don't have the initial 500 ft straight, you go straight from the climb to the turn typically
        
    #     '''
                
    #     # 500 ft cruise
    #     texpect = 300
    #     m = 5000
    #     segment_distance = 500*ftm # 200 ft converted to m
    #     self.segment_index += 1
    #     if verbose:
    #         print(f'Simulating {segment_distance/ftm:.1f} ft cruise')
    #     data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns_batt, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('500 ft cruise')
        
    #     # 180 turn (IMPLEMENT)
    #     segment_degrees = 180
    #     self.segment_index += 1
    #     if verbose:
    #         print(f'Simulating {segment_degrees} deg turn')
    #     data = performance.Turn(segment_degrees, self.nmax,  self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CLturn, self.CDturn, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns_batt, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.turndT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('180 deg turn')
        
    #     # 500 ft cruise
    #     segment_distance = 500*ftm # 200 ft converted to m
    #     self.segment_index += 1
    #     if verbose:
    #         print(f'Simulating {segment_distance/ftm:.1f} ft cruise')
    #     data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('500 ft cruise')
        
    #     # 360 turn
    #     segment_degrees = 360
    #     self.segment_index += 1
    #     if verbose:
    #         print(f'Simulating {segment_degrees} deg turn')
    #     data = performance.Turn(segment_degrees, self.nmax, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CLturn, self.CDturn, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.turndT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('360 deg turn')
        
    #     # 500 ft cruise
    #     segment_distance = 500*ftm # 200 ft converted to m
    #     self.segment_index += 1
    #     if verbose:
    #         print(f'Simulating {segment_distance/ftm:.1f} ft cruise')
    #     data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('500 ft cruise')

    #     # 180 turn
    #     segment_degrees = 180
    #     self.segment_index += 1
    #     if verbose:
    #         print(f'Simulating {segment_degrees} deg turn')
    #     data = performance.Turn(segment_degrees, self.nmax, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CLturn, self.CDturn, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.turndT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('180 deg turn')
        
    #     # 500 ft cruise
    #     segment_distance = 500*ftm # 200 ft converted to m
    #     self.segment_index += 1
    #     if verbose:
    #         print(f'Simulating {segment_distance/ftm:.1f} ft cruise')
    #     data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('500 ft cruise')
    #     #endlap
    
    # def DBF_ThreeLaps(self, aoa_rotation = 10, climb_altitude = 100*ftm, climb_angle = 10, plot = False):
    #     #### NOTE: FIND A BETTER WAY TO ANTICIPATE THE END OF THE SEGMENT (so it'll work beyond dbf!!!)
    #     self.CheckMissionInit()
    #     self.resetdata()
    #     texpect = 150
    #     m = 5000

    #     ############# TAKEOFF AND CLIMB TO FIRST TURN #############
    #     print(f'\nTakeoff with {aoa_rotation} deg of rotation') # print statements here bc f-strings haven't been implemented in numba yet!
    #     data = performance.Takeoff(aoa_rotation, texpect, self.h0, self.taper, self.AR, self.b, self.MGTOW, self.rho, self.Sw, 
    #                    self.CDtoPreR, self.CLtoPreR, self.CDtoPostR, self.CLtoPostR, self.CLmax,  
    #                    self.mass, self.mufric, self.Vlof, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, 
    #                    self.Rb, self.KV, self.Rm, self.nmot, self.I0, self.ds, self.takeoffdT, self.GR, m = m, plot = False, results = False)
    #     self.updatedata(data)
    #     self.labels.append('Takeoff')
        
    #     print(f'Climb to {climb_altitude/ftm} ft') 
    #     max_segment_distance = 500*ftm # total distance allowable (climb may be cut short)
    #     self.segment_index += 1
    #     data = performance.Climb(climb_altitude, climb_angle, max_segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.climbdT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('Climb')
        
    #     # remaining horizontal distance if end of lap isn't reached
    #     if self.x_track[-1][-1] < 500*ftm:
    #         segment_distance = 500*ftm - self.x_track[-1][-1] # total distance allowable (climb may be cut short)
    #         print(f'Cruise to Turn 1, {segment_distance/ftm:.1f} ft')
    #         self.segment_index += 1
    #         data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                                   self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                                   self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #         self.updatedata(data)
    #         self.labels.append('Cruise to first turn')
        
        
    #     ############# LAP 1 START #############
    #     print('Running Lap 1')
    #     # 180 deg turn
    #     segment_degrees = 180
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_degrees} deg turn')
    #     data = performance.Turn(segment_degrees, self.nmax, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CLturn, self.CDturn, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.turndT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('180 deg turn')
        
    #     # 500 ft cruise 
    #     segment_distance = 500*ftm # 500 ft converted to m
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_distance/ftm:.1f} ft cruise')
    #     data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('500 ft cruise')
        
    #     # 360 deg turn
    #     segment_degrees = 360
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_degrees} deg turn')
    #     data = performance.Turn(segment_degrees, self.nmax, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CLturn, self.CDturn, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.turndT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('360 deg turn')
        
    #     # 500 ft straight
    #     segment_distance = 500*ftm # 200 ft converted to m
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_distance/ftm:.1f} ft cruise')
    #     data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('500 ft cruise')
        
    #     # 180 deg turn
    #     segment_degrees = 180
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_degrees} deg turn')
    #     data = performance.Turn(segment_degrees, self.nmax, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CLturn, self.CDturn, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.turndT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)        
    #     self.labels.append('180 deg turn')
        
    #     # 500 ft cruise then we start Lap 2
    #     segment_distance = 500*ftm # 200 ft converted to m
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_distance/ftm:.1f} ft linear')
    #     data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('500 ft cruise')
        
    #     self.tlap1end = self.t_track[-1][-1]
        
    #     # ############# LAP 2 ##############
    #     print('Running Lap 2')
    #     self.DBF_Lap()
    #     self.tlap2end = self.t_track[-1][-1]
        
    #     # ############# LAP 3 ##############
    #     print('Running Lap 3')
    #     self.DBF_Lap()
    #     self.tlap3end = self.t_track[-1][-1]
        
    #     if self.SOC_track[-1][-1]-0.005 <= (1 - self.ds):
    #         self.mission_success = False
    #         print('Battery Runtime Exceeded! Mission failed.')
    #     else:
    #         self.mission_success = True
    #         print(f'Mission completed in {self.tlap3end:.2f}s')
        
    #     # all velocities (to easily get max)
    #     Vs = np.concatenate(self.V_track)
    #     self.maxV = Vs.max()/ftm 
        
    #     self.lap_ends = [self.tlap1end, self.tlap2end, self.tlap3end]
        
    #     self.turnindexes = []
    #     self.cruiseindexes = []
    #     self.climbindexes = [1]
    #     for i, label in enumerate(self.labels):
    #         if "turn" in label:
    #             self.turnindexes.append(i)
    #         elif "cruise" in label:
    #             self.cruiseindexes.append(i)
        
    #     if plot:
    #         lw = 1.3
    #         fig, ax = plt.subplots(figsize=(6,2), dpi = 1000)
    #         #plotting the one gridline around 100 fps for reference
    #         # ax.axhline(100, color='#D3D3D3', linewidth=0.8)
    #         # ax.axhline(80, color='#D3D3D3', linewidth=0.8)
    #         #plotting the laptime lines
    #         ax.plot([self.tlap1end, self.tlap1end], [0, self.maxV+5], '--', color='orange', linewidth=1)
    #         ax.plot([self.tlap2end, self.tlap2end], [0, self.maxV+5], '--', color='orange', linewidth=1)
    #         ax.plot([self.tlap3end, self.tlap3end], [0, self.maxV+5], '--', color='orange', linewidth=1)
    #         ax.plot(self.t_track[0], self.V_track[0]/ftm, color='black', label='Takeoff', linewidth = lw)
    #         ax.plot(self.t_track[1], self.V_track[1]/ftm, color='#0343DF', label='Climb', linewidth = lw)
    #         #plotting all the turn and cruise segments
    #         for i, segment in enumerate(self.t_track):
    #             if i in self.cruiseindexes:
    #                 ax.plot(self.t_track[i], self.V_track[i]/ftm, color = '#cc0000', linewidth = lw)
    #             elif i in self.turnindexes:
    #                 ax.plot(self.t_track[i], self.V_track[i]/ftm, color = '#666666', linewidth = lw)
    #         # ax.plot(M2_t, M2_V/ftm, color='black')
    #         #for the legend
    #         ax.plot([], [], color='#cc0000', label='Cruise')
    #         ax.plot([], [], color='#666666', label='Turn')
            
    #         #laptime labels
    #         ax.text(self.tlap1end-2.5, 40, f'Lap 1: {self.tlap1end:.1f}s', rotation=90, ha='center', va='center', fontsize = 8)
    #         ax.text(self.tlap2end-2.5, 40, f'Lap 2: {self.tlap2end:.1f}s', rotation=90, ha='center', va='center', fontsize = 8)
    #         ax.text(self.tlap3end-2.5, 40, f'Lap 3: {self.tlap3end:.1f}s', rotation=90, ha='center', va='center', fontsize = 8)
    #         # ax.set_ylim(bottom=0, top = self.maxV + 5)
    #         # ax.set_xlim(left=0, right = self.tlap3end + 2)
    #         plt.yticks([0, 20, 40, 60, 80, 100, 120, 140, 160])
    #         plt.xlabel('Time (s)')
    #         plt.ylabel('Velocity (fps)')
    #         plt.title('Three Lap Velocity Profile')
    #         plt.grid()
    #         plt.legend(loc='lower center', prop={'size': 9}, framealpha=1.0, fancybox = False, edgecolor='black', ncol=4, bbox_to_anchor = (0.5, -0.65))
    #         # fig.savefig('M2VelocityProfile_4_7_V13', dpi=800, bbox_inches="tight", pad_inches=0.05)
    #         plt.show()
            
    
    # def DBF_MaxLaps(self, aoa_rotation = 10, climb_altitude = 100*ftm, climb_angle = 10, time_limit = 300):
    #     ''' 
    #     Determines the maximum number of laps provided max discharge and a set time limit
        
    #     Intended for DBF #lap based simulations
        
    #     NOTE: MGTOW IMPACTS RUNTIME SIGNIFICANTLY!!! (Unsure why!)
    #     '''
    #     self.resetdata()
    #     self.CheckMissionInit()
    #     texpect = 150
    #     m = 5000

    #     ############# TAKEOFF AND CLIMB TO FIRST TURN #############
    #     print(f'\nSimulating Takeoff with {aoa_rotation} deg of rotation') # print statements here bc f-strings haven't been implemented in numba yet!
    #     data = performance.Takeoff(aoa_rotation, texpect, self.h0, self.taper, self.AR, self.b, self.MGTOW, self.rho, self.Sw, 
    #                    self.CDtoPreR, self.CLtoPreR, self.CDtoPostR, self.CLtoPostR, self.CLmax,  
    #                    self.mass, self.mufric, self.Vlof, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, 
    #                    self.Rb, self.KV, self.Rm, self.nmot, self.I0, self.ds, self.takeoffdT, self.GR, m = m, plot = False, results = False)
    #     self.updatedata(data)
    #     self.labels.append('Takeoff')
        
    #     print(f'Simulating Climb to {climb_altitude/ftm} ft') 
    #     max_segment_distance = 500*ftm # total distance allowable (climb may be cut short)
    #     self.segment_index += 1
    #     data = performance.Climb(climb_altitude, climb_angle, max_segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.climbdT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('Climb')
        
    #     # remaining horizontal distance if end of lap isn't reached
    #     if self.x_track[-1][-1] < 500*ftm:
    #         segment_distance = 500*ftm - self.x_track[-1][-1] # total distance allowable (climb may be cut short)
    #         print(f'Cruise to Turn 1, {segment_distance/ftm:.1f} ft')
    #         self.segment_index += 1
    #         data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                                   self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1],  self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                                   self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #         self.updatedata(data)
    #         self.labels.append('Cruise to first turn')
        
        
    #     ############# LAP 1 START #############
    #     print('Running Lap 1')
    #     # 180 deg turn
    #     segment_degrees = 180
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_degrees} deg turn')
    #     data = performance.Turn(segment_degrees, self.nmax, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1],  self.CLturn, self.CDturn, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.turndT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('180 deg turn')
        
    #     # 500 ft cruise 
    #     segment_distance = 500*ftm # 500 ft converted to m
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_distance/ftm:.1f} ft cruise')
    #     data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1],  self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('500 ft cruise')
        
    #     # 360 deg turn
    #     segment_degrees = 360
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_degrees} deg turn')
    #     data = performance.Turn(segment_degrees, self.nmax, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CLturn, self.CDturn, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.turndT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('360 deg turn')
        
    #     # 500 ft straight
    #     segment_distance = 500*ftm # 200 ft converted to m
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_distance/ftm:.1f} ft cruise')
    #     data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('500 ft cruise')
        
    #     # 180 deg turn
    #     segment_degrees = 180
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_degrees} deg turn')
    #     data = performance.Turn(segment_degrees, self.nmax, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1],  self.CLturn, self.CDturn, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.turndT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)        
    #     self.labels.append('180 deg turn')
        
    #     # 500 ft cruise then we start Lap 2
    #     segment_distance = 500*ftm # 200 ft converted to m
    #     self.segment_index += 1
    #     # print(f'Simulating {segment_distance/ftm:.1f} ft linear')
    #     data = performance.Cruise(segment_distance, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                               self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1],  self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                               self.KV, self.Rm, self.nmot, self.I0, self.cruisedT, self.GR, tend = texpect, m = m)
    #     self.updatedata(data)
    #     self.labels.append('500 ft cruise')
        
    #     self.lap_ends.append(self.t_track[-1][-1]) # lap one recording
    #     time_remaining = time_limit - self.lap_ends[0]
        
    #     i = 2
    #     while time_remaining > 0:    
    #         print(f'Running Lap {i}')
    #         self.DBF_Lap()

    #         if self.SOC_track[-1][-1]-0.005 <= (1 - self.ds):
    #             print('Battery Runtime Exceeded!')
    #             break
            
    #         self.lap_ends.append(self.t_track[-1][-1])
    #         time_remaining = time_limit - self.lap_ends[-1]
            
    #         if time_remaining < self.lap_ends[-1]-self.lap_ends[-2]:
    #             print('Mission time limit reached')
    #             break

    #         i += 1
            
    #     if time_remaining < 0:
    #         self.lap_ends = self.lap_ends[:-1] # cut the last lap bc it goes over the time limit!
    #         self.labels = self.labels[:-1]
    #         for i, track in enumerate(self.datatrack): # trimming the last lap (7 segments in a DBF lap)
    #             self.datatrack[i] = track[:-7]
                
    #         self.mission_success = True
        
    #     print(f'\n{"Total number of laps:":25} {len(self.lap_ends):.0f}\n'
    #           f'{"End Mission Time:":25} {self.lap_ends[-1]:.2f}s\n'
    #           f'{"Final Laptime:":25} {self.lap_ends[-1]-self.lap_ends[-2]:.2f}s\n'
    #           f'{"Final Battery %:":25} {self.SOC_track[-1][-1]*100:.2f}%')
            
    #     self.turnindexes = []
    #     self.cruiseindexes = []
    #     self.climbindexes = [1]
    #     for i, label in enumerate(self.labels):
    #         if "turn" in label:
    #             self.turnindexes.append(i)
    #         elif "cruise" in label:
    #             self.cruiseindexes.append(i)
        
    
    # def PlotMission(self, char, title = None):
    #     '''
    #     generalized plot that will plot any characteristic from:
    #         -  acceleration (m/s^2 by default)
    #         - Velocity (m/s) by default 
    #         - Position (m) 
    #         - Altitude (m)
    #         - Thrust (N)
    #         - Drag (N) (should make a plot with this and thrust!)
    #         - n (load factor)
    #         - SOC
    #         - Itot (current) (A)
    #         - RPM 
    #         - Torque (Q) N*m
    #         - Electric Power for one motor!
            
    #     Add in an all option that plots all at once (maybe make it a mosaic too!)
    #     '''
    #     units = ''
    #     conversion = 1.0
    #     special = False
    #     if char == 'Acceleration':
    #         var = self.a_track
    #         units = 'ft/s^2'
    #         conversion = 1/ftm
    #     elif char == 'Velocity':
    #         var = self.V_track
    #         units = 'ft/s'
    #         conversion = 1/ftm
    #     elif char == 'Position':
    #         var = self.x_track
    #         units = 'ft'
    #         conversion = 1/ftm
    #     elif char == 'Altitude':
    #         var = self.h_track
    #         units = 'ft'
    #         conversion = 1/ftm
    #     elif char == 'Thrust' or char == 'Drag':
    #         special = True
    #         var1 = self.T_track
    #         var2 = self.D_track
    #         units = 'lbf'
    #         conversion = 1/lbfN
    #         # var2 = self.D_track
    #     elif char == 'Load Factor':
    #         var = self.n_track 
    #     elif char == 'SOC':
    #         var = self.SOC_track 
    #         conversion = 100.0
    #         units = '%'
    #     elif char == 'Current':
    #         var = self.Itot_track 
    #         units = 'A'
    #     elif char == 'RPM':
    #         var = self.RPM_track 
    #         units = 'RPM'
    #     elif char == 'Torque':
    #         var = self.Q_track 
    #         units = 'N*m'
    #         conversion = 1.0
    #     elif char == 'Power':
    #         var = self.P_track
    #         units = 'W'
    #         conversion = 1.0
    #     elif char == 'eta':
    #         var = self.eta_track 
    #         units = ''
    #         conversion = 1.0
    #     # elif self.mission_success == False:
    #     #     print('Mission Failed; Plots Aborted')
    #     else:
    #         print('\nCharacteristic not recognized\nOptions are:\n\tVelocity, Current, SOC, Position,\n\tAltitude, Thrust, Drag, Acceleration,\n\tLoad Factor, RPM, Torque, and Power')
        
    #     if special:
    #         varuse = var1 + var2
    #         concatvar = np.concatenate(varuse)
    #     else:
    #         concatvar = np.concatenate(var)
            
    #     maxVar = concatvar.max()
        
    #     lw = 1.3
    #     fig, ax = plt.subplots(figsize=(6,4), dpi = 1000)
        
    #     if len(self.lap_ends) != 0:
    #         for i, lapend in enumerate(self.lap_ends):
    #             ax.plot([lapend, lapend], [0, maxVar*conversion*(6/5)], '--', color='orange', linewidth=1)
    #             ax.text(lapend-2.5, (maxVar*conversion)/4, f'Lap {i+1}: {lapend:.1f}s', rotation=90, ha='center', va='center', fontsize = 8)

    #     #plotting all the turn and cruise segments
    #     if special: # special is for the thrust - drag or any other multiplot!
    #         ax.plot(self.t_track[0], var1[0]*conversion, color='black', label='Takeoff Thrust', linewidth = lw)
    #         ax.plot(self.t_track[1], var1[1]*conversion, color='#0343DF', label='Climb Thrust', linewidth = lw)
    #         ax.plot(self.t_track[0], var2[0]*conversion, color='green', label='Takeoff Drag', linewidth = lw)
    #         ax.plot(self.t_track[1], var2[1]*conversion, color='purple', label='Climb Drag', linewidth = lw)

    #         for i, segment in enumerate(self.t_track):
    #             if i in self.cruiseindexes:
    #                 ax.plot(self.t_track[i], var1[i]*conversion, color = '#cc0000', linewidth = lw)
    #                 ax.plot(self.t_track[i], var2[i]*conversion, color = 'cyan', linewidth = lw)
    #             elif i in self.turnindexes:
    #                 ax.plot(self.t_track[i], var1[i]*conversion, color = '#666666', linewidth = lw)
    #                 ax.plot(self.t_track[i], var2[i]*conversion, color = 'pink', linewidth = lw)
    #             elif i in self.climbindexes:
    #                 ax.plot(self.t_track[i], var1[i]*conversion, color = 'purple', linewidth = lw)
    #                 ax.plot(self.t_track[i], var2[i]*conversion, color = 'green', linewidth = lw)
                    
    #         #for the legend
    #         ax.plot([], [], color='#cc0000', label='Cruise Thrust')
    #         ax.plot([], [], color='#666666', label='Turn Thrust')
    #         ax.plot([], [], color='cyan', label='Cruise Drag')
    #         ax.plot([], [], color='pink', label='Turn Drag')

    #     else:
    #         ax.plot(self.t_track[0], var[0]*conversion, color='black', label='Takeoff', linewidth = lw)
    #         # ax.plot(self.t_track[1], var[1]*conversion, color='#0343DF', label='Climb', linewidth = lw)

    #         for i, segment in enumerate(self.t_track):
    #             if i in self.cruiseindexes:
    #                 ax.plot(self.t_track[i], var[i]*conversion, color = '#cc0000', linewidth = lw)
    #             elif i in self.turnindexes:
    #                 ax.plot(self.t_track[i], var[i]*conversion, color = '#666666', linewidth = lw)
    #             elif i in self.climbindexes:
    #                 ax.plot(self.t_track[i], var[i]*conversion, color = '#0343DF', linewidth = lw)
             
    #         ax.plot([], [], color='#0343DF', label='Climb')
    #         ax.plot([], [], color='#cc0000', label='Cruise')
    #         ax.plot([], [], color='#666666', label='Turn')
            
    #     #laptime labels
    #     if self.lap_ends == 0:
    #         ax.set_ylim(bottom=0, top = maxVar*conversion*(6/5))
    #         ax.set_xlim(left=0, right = self.lap_ends[-1] + 2)
    #     else:
    #         ax.set_ylim(bottom=0, top = maxVar*conversion*(6/5))
            
    #     # plt.yticks([0, 20, 40, 60, 80, 100, 120, 140, 160])
    #     plt.xlabel('Time (s)')
    #     if special:
    #         plt.ylabel('Forces (lbf)')
    #         if title == None:
    #             plt.title('Force Profile')
    #         else:
    #             plt.title(title)
    #     else:
    #         plt.ylabel(f'{char} ({units})')
    #         if title == None:
    #             plt.title(f'{char} Profile')
    #         else:
    #             plt.title(title)
    #     plt.grid()
    #     plt.legend(loc='lower center', prop={'size': 9}, framealpha=1.0, fancybox = False, edgecolor='black', ncol=4, bbox_to_anchor = (0.5, -0.3))
    #     # fig.savefig('M2VelocityProfile_4_7_V13', dpi=800, bbox_inches="tight", pad_inches=0.05)
    #     plt.show()
        
        
    # # custom mission segments!
    # def MissionProfile(self, segment_data, m = 5000):
    #     self.CheckMissionInit()
    #     self.resetdata()
        
    #     for i, segment in enumerate(segment_data):
    #         if segment[0] == 'Takeoff':
    #             print(f'{segment[0]} segment')
    #             # assuming no takeoff will take longer than 100s!!
    #             texpect = 100
    #             data = performance.Takeoff(segment[1], texpect, self.h0, self.taper, self.AR, self.b, self.MGTOW, self.rho, self.Sw, 
    #                            self.CDtoPreR, self.CLtoPreR, self.CDtoPostR, self.CLtoPostR, self.CLmax,  
    #                            self.mass, self.mufric, self.Vlof, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, 
    #                            self.Rb, self.KV, self.Rm, self.nmot, self.I0, self.ds, m = m, plot = False, results = False)
    #             # issue arrising bc initial climb isn't modeled so even though we lift off at Vstall for CLturn, 
    #             self.updatedata(data)
    #             self.labels.append('Takeoff')
    #             self.segment_index += 1
    #         elif segment[0] == 'Climb':
    #             if segment[2] < 0:
    #                 print(f'{i}: Descend by {segment[1]/ftm:.1f} ft')
    #             elif segment[2] == 0:
    #                 raise ValueError('Climb angle = 0 deg')
    #             else:
    #                 print(f'{i}: Climb by {segment[1]/ftm:.1f} ft')
    #             texpect = 5000 ##### ALTER THIS SOON TO SCALE WITH SOME GUESS #####
    #             data = performance.Climb(segment[1], segment[2], segment[3], self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                                       self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1],  self.CL, self.CD, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                                       self.KV, self.Rm, self.nmot, self.I0, tend = texpect, m = m)
    #             self.updatedata(data)
    #             self.labels.append('Climb')
    #             self.segment_index += 1
    #         elif segment[0] == 'Cruise':
    #             print(f'{i}: Cruise {segment[1]/ftm:.1f} ft')
    #             texpect = 5000 ##### ALTER THIS SOON TO SCALE WITH SOME GUESS #####
    #             data = performance.Cruise(segment[1], self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                                       self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CL, self.CD, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                                       self.KV, self.Rm, self.nmot, self.I0, tend = texpect, m = m)
    #             self.updatedata(data)
    #             self.labels.append('Cruise')
    #             self.segment_index += 1
    #         elif segment[0] == 'Turn':
    #             print(f'{i}: Turn {segment[1]:.1f} deg')
    #             texpect = 1000 ##### ALTER THIS SOON TO SCALE WITH SOME GUESS #####
    #             data = performance.Turn(segment[1], self.nmax, self.V_track[self.segment_index-1][-1], self.t_track[self.segment_index-1][-1], self.SOC_track[self.segment_index-1][-1], 
    #                                       self.x_track[self.segment_index-1][-1], self.h_track[self.segment_index-1][-1], self.eta_track[self.segment_index - 1][-1], self.CLturn, self.CDturn, self.Vstall, self.Sw, self.rho, self.MGTOW, self.mass, self.ds, self.rpm_list, self.NUMBA_PROP_DATA, self.CB, self.ns, self.Rb, 
    #                                       self.KV, self.Rm, self.nmot, self.I0, tend = texpect, m = m)
                
    #             self.updatedata(data)
    #             self.labels.append('Turn')
    #             self.segment_index += 1
                
    #         if self.SOC_track[-1][-1]-0.005 <= (1 - self.ds):
    #             print(f'Battery depleted during segment {i}')
    #             break
            
    #     self.turnindexes = []
    #     self.cruiseindexes = []
    #     self.climbindexes = []
    #     for i, label in enumerate(self.labels):
    #         if "Turn" in label:
    #             self.turnindexes.append(i)
    #         elif "Cruise" in label:
    #             self.cruiseindexes.append(i)
    #         elif "Climb" in label:
    #             self.climbindexes.append(i)

    
    # # integrating the EM plots from EMfunc
    # def EnergyManeuverability(self):
    #     pass
        
        
        
        
        
        