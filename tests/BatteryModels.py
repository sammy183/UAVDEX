# -*- coding: utf-8 -*-
"""
Created on Tue Mar 31 12:28:01 2026

@author: NASSAS
"""

from uavdex.propulsions import VocFuncBase
import matplotlib.pyplot as plt
import numpy as np

n = 500
SOC = np.linspace(0, 1, n)

def VocChen(SOC):
    return(3.685 - 1.031 * np.exp(-35 * SOC) + 0.2156 * SOC - 0.1178 * SOC**2 + 0.3201 * SOC**3)
def VocJeong(SOC):
    return(1.7*SOC**3 - 2.1*SOC**2 + 1.2*SOC + 3.4)

Voc_c = VocChen(SOC)
Voc_j = VocJeong(SOC)

fig, ax = plt.subplots()
ax.invert_xaxis()
ax.plot(SOC*100, Voc_c, label= 'Chen 2006')
ax.plot(SOC*100, Voc_j, label = 'Jeong 2020')
plt.xlabel('SOC (%)')
plt.ylabel('Voc (V)')
plt.legend()
plt.show()