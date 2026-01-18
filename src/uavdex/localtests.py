# -*- coding: utf-8 -*-
"""
Created on Sun Jan 18 16:27:11 2026

Testing locally, later learn how to test properly using the premade file structure

@author: NASSAS
"""

import common as ad

t = ad.PointDesign()
t.Motor('C-4130/20', 1)
t.Battery('Gaoneng_8S_3300', 0.85)
t.Prop('16x12E')
t.PointResult(Uinf = 28, h = 10, SOC = 1.0, dT = 0.8)
t.PointResult(Uinf = 28, h = 10, Voc = 3.7, dT = 0.8)

t.PointResult(Uinf = 40, h = 10, t = 100, dT = 0.8)
t.Motor('C-4130/20', 1)
t.PointResult(Uinf = 48, h = 10, t = 100, dT = 0.95)



import numpy as np

runtimes = np.linspace(10, 500)

etas = np.zeros(runtimes.size)
Ts = np.zeros(runtimes.size)
RPMs = np.zeros(runtimes.size)
for i, runtime in enumerate(runtimes):
    propQ = t.PointResult(Uinf = 15, h = 10, t = runtime, dT = 1.0, verbose = True)
    etas[i] = propQ[8]
    Ts[i] = propQ[0]
    RPMs[i] = propQ[2]
    
    
import matplotlib.pyplot as plt

plt.plot(runtimes, etas, '.')
plt.ylabel('Efficiency')
plt.yticks([0.25, 0.5, 0.75, 1.0])
plt.show()

plt.plot(runtimes, Ts)
plt.show()

plt.plot(runtimes, RPMs)
plt.show()