# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 14:15:00 2026

@author: NASSAS
"""

from propulsions import VocFunc
import matplotlib.pyplot as plt
import numpy as np

BattType = 'LiPo'
# BattType = 'Liion'

SOC = np.linspace(0.0, 1)
Voc = VocFunc(SOC, BattType)

def BoteroFunc(x):
    return(-1.031*np.exp(-35*x) + 3.685 + 0.2156*x - 0.1178*x**2 + 0.3201*x**3)

def JeongFunc(SoC):
    return(1.7*SoC**3 - 2.1*SoC**2 + 1.2*SoC + 3.4)

chenV = VocFunc(SOC, 'LiPo')
ionV = VocFunc(SOC, 'Liion')
# boteroV = BoteroFunc(SOC)
jeongV = JeongFunc(SOC)
plt.plot(SOC, chenV, label = 'LiPo chen')
# plt.plot(SOC, ionV, label = 'Liion')
# plt.plot(SOC, boteroV, label = 'LiPo Botero')
plt.plot(SOC, jeongV, label = 'LiPo Jeong')
plt.legend()
plt.show()


print(f'chen median: {np.median(chenV)}, mean: {np.mean(chenV)}')
# print(f'liion median: {np.median(ionV)}, mean: {np.mean(ionV)}')
# print(f'botero median: {np.median(boteroV)}, mean: {np.mean(boteroV)}')
print(f'jeong median: {np.median(jeongV)}, mean: {np.mean(jeongV)}')

Ecell = np.linspace(0, 100/8)
Rb = 21.0*(Ecell)**-0.8056

plt.plot(SOC, Rb*1e-4)
plt.ylabel('Resistance (Ohm)')
plt.xlabel('Energy (Wh)')
plt.show()