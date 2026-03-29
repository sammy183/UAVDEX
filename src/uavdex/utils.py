# -*- coding: utf-8 -*-
"""
Created on Thu Mar 26 17:04:09 2026

Extra utility functions

@author: NASSAS
"""

import subprocess
import platform
import os
from pathlib import Path
from uavdex.VSPcontribution.atmosphere import stdatm1976, densAlt2GeomAlt 
from uavdex.VSPcontribution.units import *
import numpy as np

def open_csv(filename: str) -> None:
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return

    filepath = os.path.realpath(filename)

    # Determine OS and run appropriate command
    if platform.system() == 'Darwin':       # macOS
        subprocess.run(['open', filepath], check=True)
    elif platform.system() == 'Windows':    # Windows
        os.startfile(filepath) # or subprocess.run(['start', filepath], shell=True)
    else:                                   # Linux/Unix
        subprocess.run(['xdg-open', filepath], check=True)

def open_folder(path_to_folder):
    """
    Opens the specified folder using the default system file viewer
        if path_to_folder is str, make it a path object
        otherwise use directly

    Args:
        path_to_folder: The path to the directory (as a string or Path object)
    """
    # Ensure the path is a Path object for consistency and checks
    if isinstance(path_to_folder, str):
        path_to_folder = Path(path_to_folder)

    # Use a normalized absolute path
    abs_path = os.path.normpath(path_to_folder.resolve())

    if platform.system() == "Windows":
        # Use os.startfile() on Windows
        os.startfile(abs_path)
    elif platform.system() == "Darwin":
        # Use 'open' command on macOS
        subprocess.run(["open", abs_path], check=True)
    else:
        # Assume Linux or other POSIX-like, use 'xdg-open'
        try:
            subprocess.run(["xdg-open", abs_path], check=True)
        except FileNotFoundError:
            print("xdg-open not found. Please install xdg-utils package to open csv")
        except Exception as e:
            print(f"An error occurred on Linux: {e}")

def exactly_one_defined(*args) -> bool:
    return sum(x is not None for x in args) == 1
            
def input_conversion(Uinf_mps, Uinf_mph, Uinf_fps, Uinf_kmh, Uinf_kt,
                     dT,
                     h_m, h_ft, rho_kgm3, rho_lbft3, rho_slugft3,
                     t_s, t_m, t_hr, SOC):
    
    # convert speed units to m/s
    if Uinf_mps is not None:
        Uinf = Uinf_mps
    elif Uinf_mph is not None:
        Uinf = Uinf_mph*mph2ms # mph to m/s 
    elif Uinf_fps is not None:
        Uinf = Uinf_fps*ft2m   # ft/s to m/s
    elif Uinf_kmh is not  None:
        Uinf = Uinf_kmh*kmh2ms # kmh to m/s
    elif Uinf_kt is not None:
        Uinf = Uinf_kt*kt2ms
    
    # convert dT % to decimal
    if np.all(np.asarray(dT)) != None:
        dT /= 100
        
    # convert altitude or density to m or kg/m3
    if h_m is not None:
        h = h_m
        rho = None
    elif h_ft is not None:
        h = h_ft*ft2m
        rho = None
    elif rho_kgm3 is not None:
        rho = rho_kgm3
        h = None
    elif rho_lbft3 is not None:
        rho = rho_lbft3*lbmcf2kgcm
        h = None
    elif rho_slugft3 is not None:
        rho = rho_slugft3*slugcf2kgcm 
        h = None
        
    # convert time to s and SOC% to SOC decimal
    if t_s is not None:
        t = t_s
    elif t_m is not None:
        t = t_m*m2s
    elif t_hr is not None:
        t = t_hr*hr2m
    elif SOC is not None:
        SOC /= 100 
        t = None
    else:
        t = None
        
    return(Uinf, dT, rho, h, t, SOC)

def check(val, cond, name):
    '''for checking whether inputs are within range'''
    if val is None:
        return
    arr = np.asarray(val)
    if not np.all(cond(arr)):
        raise ValueError(f"{name} out of bounds: {val}")


# def convert_base_metric(input_unit):
#     '''Converts all input units to base metric (i.e. m/s instead of kmh)'''
#     conversions = {
#         "kmh":1/3.6,        # kmh to m/s
#         "fps":0.3048,       # fps to m/s
#         "mph":1/2.237,      # mph to m/s
#         "kt":1/1.944,
#         "":,
#         "":,
#         "":,
#         "":,
#         "":,
#         "":,
#         "":,
#         "":,
#         "":,
#         }
#     if input_unit == 'kmh':
#         return(1/3.6)
#     elif input_unit == ''
        
        
        
        
        
        
        
        
        
        
        