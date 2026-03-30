# -*- coding: utf-8 -*-
"""
Unit table for conversions (eventually)

@author: Sammy N
"""
from uavdex.VSPcontribution.units import m2s, hr2m, mph2ms, ft2m, kmh2ms, kt2ms, ftm, slugcf2kgcm, lbmcf2kgcm

UNIT_TABLE = {
    0: ("spec", 0.01, "State of Charge (%)"),
    1: ("spec", 1, "Cell Voltage (V)"),
    2: ("spec", 1, "Runtime (s)"),
    3: ("spec", m2s, "Runtime (min)"),
    4: ("spec", hr2m, "Runtime (hr)"),

    5: ("Uinf", mph2ms, "Velocity (mph)"),
    6: ("Uinf", ft2m, "Velocity (fps)"),
    7: ("Uinf", 1, "Velocity (m/s)"),
    8: ("Uinf", kmh2ms, "Velocity (kmh)"),
    9: ("Uinf", kt2ms, "Velocity (knots)"),

    10: ("dT", 0.01, "Throttle (%)"),

    11: ("rhoh", 1, "Altitude (m)"),
    12: ("rhoh", ft2m, "Altitude (ft)"),
    13: ("rhoh", 1, "Air Density (kg/m³)"),
    14: ("rhoh", slugcf2kgcm, "Air Density (slug/ft³)"),
    15: ("rhoh", lbmcf2kgcm, "Air Density (lbm/ft³)")
}