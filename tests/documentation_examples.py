# -*- coding: utf-8 -*-
"""
Created on Mon Mar 30 11:50:40 2026

Test Outputs for documentation

@author: NASSAS
"""

import uavdex as ud
import numpy as np

# Component Initialization
design = ud.PointDesign() 				# initialize PointDesign object
design.Motor('C-4130/20', nmot = 2)		# add a motor, and specify the # of motors
design.Battery('Gaoneng_8S_3300') 		# add a battery 
design.Prop('16x10E') 					# add a propeller

#%% PointResult
# Uinf_mps:	velocity in m/s   (alternatively use Uinf_fps, Uinf_mph, Uinf_kmh, Uinf_kt)
# dT: 	throttle (0-100%)
# h_m: 	altitude in m         (alternatively use h_ft, rho_kgm3, rho_slugft3, rho_lbft3)
# t_s: 	runtime in s          (alternatively use t_m, t_hr, SOC, Voc)
propQs = design.PointResult(Uinf_mps = 15, dT = 70, h_m = 50, t_s = 30, 
                            verbose = True) # this returns propQs as an array and also prints to console. To stop printing, set verbose = False.

#%% LinePlot usage
# design.LinePlot(propQ = ['T_lbf','eta_drive','Ib'], 
#                 Uinf_mph = np.linspace(0, 100), 
#                 dT = 100, h_m = 100, t_s = 30)

#%% ContourPlot
import uavdex as ud
import numpy as np

# Component Initialization
design = ud.PointDesign() 				# initialize PointDesign object
design.Motor('C-4130/20', nmot = 2)		# add a motor, and specify the # of motors
design.Battery('Gaoneng_8S_3300') 		# add a battery 
design.Prop('16x10E') 					# add a propeller

# to control the number of points used in linspace (n = 50 --> ~5s runtime, n = 200 --> ~15s runtime)
n = 120  

# ContourPlot (sweeps of velocity and runtime)
# design.ContourPlot(propQ = ['T_lbf', 'eta_drive', 'Ib'],
#                    Uinf_mps = np.linspace(0, 45, n), 
#                    t_s = np.linspace(0, 300, n),
#                    dT = 100, 
#                    h_m = 100)

#%% Additional contourplot
design.ContourPlot(propQ = 'eta_drive',
                  Uinf_mph = np.linspace(0, 120, 300), 
                  dT = np.linspace(20, 100, 300), 
                  h_m = 50, 
                  t_s = 20)

# design.ContourPlot(propQ = 'eta_drive',
#                   Uinf_mps = np.linspace(0, 45, 200), 
#                   dT = 100,
#                   h_m = 50, 
#                   Voc = np.linspace(3.5, 4.2, 200))

# design.ContourPlot(propQ = 'eta_drive',
#                   Uinf_mps = 30.0,
#                   dT = np.linspace(20, 100, 200),
#                   h_m = 50, 
#                   Voc = np.linspace(3.5, 4.2, 200))

#%% Altitude Efficiency Examination
n = 300
design.ContourPlot(propQ = ['eta_drive', 'eta_p', 'eta_m', 'RPM', 'Q_Nm'],
                   Uinf_kt = np.linspace(0, 90, n),
                   dT = 80,
                   h_ft = np.linspace(0, 80000, n),
                   t_s = 30)
#%% All 6 styles for t input
# n = 300 # overview of all 6 types of contourplot
# plot = True
# t_arr = np.linspace(0, 500, n)
# t_const = 30
# Uinf_arr = np.linspace(0, 60, n)
# Uinf_const = 25
# dT_arr = np.linspace(20, 100, n)
# dT_const = 80
# h_arr = np.linspace(0, 80000, n)
# h_const = 100
# cases = [{"propQ":"eta_drive",
#          "t_s":t_arr,
#          "Uinf_mps":Uinf_arr, 
#          "dT":dT_const,
#          "h_ft":h_const,
#          "plot":plot},
         
#          {"propQ":"eta_drive",
#         "t_s":t_arr,
#         "Uinf_mps":Uinf_const, 
#         "dT":dT_arr,
#         "h_ft":h_const,
#         "plot":plot},
         
#          {"propQ":"eta_drive",
#         "t_s":t_arr,
#         "Uinf_mps":Uinf_const, 
#         "dT":dT_const,
#         "h_ft":h_arr,
#         "plot":plot},
         
#          {"propQ":"eta_drive",
#         "t_s":t_const,
#         "Uinf_mps":Uinf_arr, 
#         "dT":dT_arr,
#         "h_ft":h_const,
#         "plot":plot},
         
#          {"propQ":"eta_drive",
#         "t_s":t_const,
#         "Uinf_mps":Uinf_arr, 
#         "dT":dT_const,
#         "h_ft":h_arr,
#         "plot":plot},
         
#          {"propQ":"eta_drive",
#         "t_s":t_const,
#         "Uinf_mps":Uinf_const, 
#         "dT":dT_arr,
#         "h_ft":h_arr,
#         "plot":plot}
#     ]
# for i, case in enumerate(cases):
#         _, _, _ = design.ContourPlot(**case)
