# -*- coding: utf-8 -*-
"""
Created on Sun Jan 18 16:27:11 2026

Testing locally, later learn how to test properly using the premade file structure

@author: NASSAS
"""

import common as ad

t = ad.PointDesign()
t.Motor('A-5025-310', 2)
t.Battery('Gaoneng_8S_3300', 0.85)
t.Prop('16x10E')
t.PointResult(Uinf = 30, h = 10, SOC = 1.0, dT = 0.8)

