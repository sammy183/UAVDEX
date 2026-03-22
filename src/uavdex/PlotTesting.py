# -*- coding: utf-8 -*-
"""
OLD FILE; IGNORE

Created on Tue Mar 17 14:49:22 2026

Test for hicken

@author: sammy
"""

import common as ud
import matplotlib.pyplot as plt
import numpy as np
import scipy.optimize as sop

design = ud.PointDesign()
# design.OpenMotorData()
design.Motor('V8110-170', 1)
design.Battery('Gaoneng_8S_3300', 0.85)
design.Prop('22x12E')

design.Motor('C-4130/20', 1)
design.Battery('Gaoneng_8S_3300', 0.85)
design.Prop('22x12E')
# design.PointResult(Uinf = 28, h = 10, SOC = 1.0, dT = 0.8, verbose = True)


Uinf = np.linspace(0, 30, 50)
propQs, arr = design.LinePlot(Uinf = Uinf, h = 10, SOC = 0.6, dT = 0.4, verbose = False)

Tcoefs = np.polyfit(arr, propQs[:, 0], 4)
Tfit = np.poly1d(Tcoefs)
rho = 1.224 
CdSw = 0.12*0.87
def T_func(V):
    return(Tfit(V) - 0.5*rho*(V**2)*CdSw)

Vmatch = sop.root(T_func, (Uinf[-1]-Uinf[0])/2)['x'][0]

# T, D plot
fig, ax = plt.subplots(figsize = (6, 4), dpi = 500)
                
propQnames = ['Total Thrust (N)', 
              'Total Torque (Nm)', 
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
ax.plot(arr, propQs[:, 0], label = 'Thrust output')
ax.plot(arr, Tfit(arr), '--', label = 'Thrust fit')
ax.plot(arr, 0.5*rho*(arr**2)*CdSw, label = 'Drag')
ax.minorticks_on()
plt.ylabel(f'{propQnames[0]}') # need to add a way to get units in correctly
plt.title('Velocity sweep for 300m altitude, 70% SOC, 100% throttle')
plt.xlabel('Velocity (m/s)')
plt.legend()
plt.show()

#%% Checking drive efficiency
fig, ax = plt.subplots(figsize = (6, 4), dpi = 500)
                
Pb = propQs[:, 11] # Pin to 1 ESC
# 14 current, 17 voltage
Pb_alt = propQs[:, 17]*propQs[:, 20]

# check that Pb = Pb_alt
# print(Pb[5], Pb_alt[5])
# True!

# then check (T*Uinf)/(Pb+Plostinm) = eta_drive
# print(propQs[:, 0]*Uinf/Pb) # without P_wastebat
# print(propQs[:, 3])
# they're nearly identical as expected (differing in the 4th or 5th decimal place)

# ax.plot(arr, propQs[:, 0], label = 'Thrust output')
# ax.plot(arr, Tfit(arr), '--', label = 'Thrust fit')
# ax.plot(arr, 0.5*rho*(arr**2)*CdSw, label = 'Drag')
# ax.minorticks_on()
# plt.ylabel(f'{propQnames[0]}') # need to add a way to get units in correctly
# plt.title('Velocity sweep for 300m altitude, 70% SOC, 100% throttle')
# plt.xlabel('Velocity (m/s)')
# plt.legend()
# plt.show()


#%% Other quantities with velocity match plotted 
Vs = arr 
for interestindex in [0, 2, 3, 4, 6, 12, 13, 14]:
    fig, ax = plt.subplots(figsize = (6, 4), dpi = 500)
    ax.plot(arr, propQs[:, interestindex])
    ax.axvline(Vmatch, linestyle = '--', color = 'k', label = 'T = D')
    ax.grid()
    ax.minorticks_on()
    plt.ylabel(f'{propQnames[interestindex]}') # need to add a way to get units in correctly
    plt.title('Velocity sweep for 300m altitude, 70% SOC, 100% throttle')
    plt.xlabel('Velocity (m/s)')

