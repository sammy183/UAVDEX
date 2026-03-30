# -*- coding: utf-8 -*-
"""
Created on Mon Mar 30 11:50:40 2026

Test Outputs for documentation

@author: NASSAS
"""

import uavdex as ud

design = ud.PointDesign() 			                    # initialize PointDesign object
design.Motor('C-4130/20', nmot = 2)                     # add a motor, and specify the # of motors (nmot = 1 by default)
design.Battery('Gaoneng_8S_3300', discharge = 85)       # add a battery, and specify the maximum discharge (default is 0.8, aka 80%)
design.Prop('16x10E')                                   # add a propeller

design.OpenMotorData()
design.OpenBatteryData()
design.OpenPropellerData()


design.MotorOptions()
design.BatteryOptions()
design.PropellerOptions()