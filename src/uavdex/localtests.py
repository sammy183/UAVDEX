# -*- coding: utf-8 -*-
"""
OLD FILE; IGNORE

Created on Sun Jan 18 16:27:11 2026

Testing locally, later learn how to test properly using the premade file structure

@author: NASSAS
"""

import common as ad
import matplotlib.pyplot as plt
import numpy as np

t = ad.PointDesign()
t.Motor('C-4130/20', 1)
t.Battery('Gaoneng_8S_3300', 0.85)
t.Prop('16x12E')
t.PointResult(Uinf = 28, h = 10, SOC = 1.0, dT = 0.8, verbose = False)
t.PointResult(Uinf = 28, h = 10, Voc = 3.7, dT = 0.8, verbose = False)

t.PointResult(Uinf = 40, h = 10, t = 100, dT = 0.8, verbose = False)
t.Motor('C-4130/20', 1)
t.PointResult(Uinf = 48, h = 10, t = 100, dT = 0.95, verbose = False)


runtimes = np.linspace(10, 500)

SOCend = 0.2 # 15% end SOC
etas = np.zeros(runtimes.size)
Ts = np.zeros(runtimes.size)
RPMs = np.zeros(runtimes.size)
breaki = 0
for i, runtime in enumerate(runtimes):
    propQ = t.PointResult(Uinf = 15, h = 10, t = runtime, dT = 1.0, verbose = False)
    if propQ[19] > SOCend:
        etas[i] = propQ[3]
        Ts[i] = propQ[0]
        RPMs[i] = propQ[2]
        breaki = i
    else:
        break

runtimes = runtimes[:breaki]
etas = etas[:breaki]
Ts = Ts[:breaki]
RPMs = RPMs[:breaki]
plt.plot(runtimes, etas, '.')
plt.ylabel('Efficiency')
plt.yticks([0.25, 0.5, 0.75, 1.0])
# plt.ylim([etas[etas > 0].min(), etas.max()])
plt.show()

# plt.plot(runtimes, Ts)
# plt.show()

plt.plot(runtimes, RPMs)
plt.show()

#%% testing lineplot
ftm = 0.3048

t.Prop('22x12E')
t.Motor('V8110-170', 1) # dual motor
arrin = np.linspace(0, 500)
propQs, arr = t.LinePlot(Uinf = 15, dT = 1.0, t = arrin, h = 5)

Vs = arr 

for interestindex in [0, 2, 3, 4, 6]:
    fig, ax = plt.subplots(figsize = (6, 4), dpi = 400)
                    
    propQnames = ['Total Thrust (N)', 'Total Torque (Nm)', 'RPM', 'Drive Efficiency', 'Propeller Efficiency', 'Gearing Efficiency', 'Motor Efficiency', 'ESC Efficiency', 'Battery Efficiency', 'Mech. Power Out of 1 Motor (W)', 
                       'Elec. Power Into 1 Motor (W)', 'Elec. Power Into 1 ESC (W)', 'Current in 1 Motor (A)', 'Current in 1 ESC (A)', 'Current in Battery (A)',
                       'Voltage in 1 Motor (V)', 'Voltage in 1 ESC (V)', 'Battery Voltage (V)', 'Voltage Per Cell (V)', 'State of Charge']
    ax.plot(arrin, propQs[:, interestindex])
    # ax.plot([cruise_V/ftm, cruise_V/ftm], ax.get_ylim(), '--', color = 'red', label = 'Cruise Velocity')
    ax.grid()
    ax.minorticks_on()
    # plt.legend()
    plt.ylabel(f'{propQnames[interestindex]}') # need to add a way to get units in correctly
    plt.xlabel('Input Quantity')


# t.OpenMotorData()
# t.OpenBatteryData()
# t.OpenPropellerData()

# TODO: find a better way to say motor(s) depending on nmot
# if self.nmot > 1:
#     s = 's'
# else:
#     s = ''

# if self.SOCinput:
#     plt.title(f'{self.nmot:.0f} {self.motor_manufacturer} {self.motor_name} motor{s}; {self.ns:.0f}S {self.CB:.0f} mAh battery; {self.nmot:.0f} APC {self.prop_name} propeller{s}\n{propQnames[interestindex]} at {SOC_Voc_t*100:.0f}% SOC and {dT*100:.0f}% throttle')
# elif self.Vocinput:
#     plt.title(f'{self.nmot:.0f} {self.motor_manufacturer} {self.motor_name} motor{s}; {self.ns:.0f}S {self.CB:.0f} mAh battery; {self.nmot:.0f} APC {self.prop_name} propeller{s}\n{propQnames[interestindex]} at {SOC_Voc_t:.4f} V Voc and {dT*100:.0f}% throttle')
# else:
#     plt.title(f'{self.nmot:.0f} {self.motor_manufacturer} {self.motor_name} motor{s}; {self.ns:.0f}S {self.CB:.0f} mAh battery; {self.nmot:.0f} APC {self.prop_name} propeller{s}\n{propQnames[interestindex]} at {SOC_Voc_t:.1f} s runtime and {dT*100:.0f}% throttle')
plt.show()
    