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
                     t_s, t_m, t_hr, SOC, Voc):
    '''
    Converts all units to base metric (i.e. m/s)
    and all percentages to decimal
    
    Also returns a list of idxs used to convert them back for titles
    '''
    # convert speed units to m/s
    unitconv_idx = []
    # convert time to s and SOC% to SOC decimal
    if SOC is not None:
        SOC /= 100
        t = None
        unitconv_idx.append(0)
    elif Voc is not None:
        t = None
        unitconv_idx.append(1)
    elif t_s is not None:
        t = t_s
        unitconv_idx.append(2)
    elif t_m is not None:
        t = t_m*m2s
        unitconv_idx.append(3)
    elif t_hr is not None:
        t = t_hr*hr2m
        unitconv_idx.append(4)
    else:
        t = None
    
    if Uinf_mph is not None:
        Uinf = Uinf_mph*mph2ms # mph to m/s 
        unitconv_idx.append(5)
    elif Uinf_fps is not None:
        Uinf = Uinf_fps*ft2m   # ft/s to m/s
        unitconv_idx.append(6)
    elif Uinf_mps is not None:
        Uinf = Uinf_mps
        unitconv_idx.append(7)
    elif Uinf_kmh is not  None:
        Uinf = Uinf_kmh*kmh2ms # kmh to m/s
        unitconv_idx.append(8)
    elif Uinf_kt is not None:
        Uinf = Uinf_kt*kt2ms   # knots to m/s
        unitconv_idx.append(9)
    
    # convert dT % to decimal
    if dT is not None:
         dT /= 100
         unitconv_idx.append(10)
        
    # convert altitude or density to m or kg/m3
    if h_m is not None:
        h = h_m
        rho = None
        unitconv_idx.append(11)
    elif h_ft is not None:
        h = h_ft*ft2m
        rho = None
        unitconv_idx.append(12)
    elif rho_kgm3 is not None:
        rho = rho_kgm3
        h = None
        unitconv_idx.append(13)
    elif rho_slugft3 is not None:
        rho = rho_slugft3*slugcf2kgcm 
        h = None
        unitconv_idx.append(14)
    elif rho_lbft3 is not None:
        rho = rho_lbft3*lbmcf2kgcm
        h = None
        unitconv_idx.append(15)
        
    return(Uinf, dT, rho, h, t, SOC, unitconv_idx)

def reverse_input_conversion(SOC, Voc, t, Uinf, dT, rho, h, unitconv_idx):
    '''
    Uinf_idx determines how to convert m/s 
    rho_idx determines how to convert h or rho
    t_idx determines how to convert t or SOC
    unitconv_idx:
        0 --> SOC
        1 --> Voc
        2 --> t s
        3 --> t m
        4 --> t hr
        
        5 --> Uinf mph
        6 --> Uinf fps
        7 --> Uinf m/s
        8 --> Uinf kmh
        9 --> Uinf kt
        
        10 --> dT
        
        11 --> h m
        12 --> h ft
        13 --> rho kg/m3
        14 --> rho slug/ft3
        15 --> rho lbm/ft3
    IMPORTANT: ordering chosen to match autoaxes for contourplot

    '''
    
    # conversion factors, matching unitconv_idx inputs
    convs = [0.01, 1, 1, m2s, hr2m, mph2ms, ft2m, 1, kmh2ms, kt2ms, 1, 1, ft2m, 1, slugcf2kgcm, lbmcf2kgcm]
    
    specidx = 0
    if SOC is not None:
        SOC *= 100
        specidx += 1
    elif Voc is not None:
        specidx += 1 
    elif t is not None:
        t /= convs[unitconv_idx[specidx]]
        specidx += 1
        
    if Uinf is not None:
        Uinf /= convs[unitconv_idx[specidx]] # 2nd idx in unitconv will always be Uinf
        specidx += 1
        
    if dT is not None:
        dT *= 100
        specidx += 1 # dT occupies 3rd idx of unitconv_idx
    
    if rho is not None:
        rho /= convs[unitconv_idx[specidx]] # third idx in unitconv will be rho or h
        specidx += 1
    else:  # h input
        h /= convs[unitconv_idx[specidx]]
        specidx += 1
    
    return(SOC, Voc, t, Uinf, dT, rho, h)

def get_array_idx(SOC, Voc, t, Uinf, dT, rho, h, unit_idxs):
    '''
    To recover unit idx for plot titles and tooltips
    This only functions when Voc/rho calculated via SOC/h aren't used
    '''
    spec = SOC if SOC is not None else (Voc if Voc is not None else t)
    rhoh = rho if rho is not None else h
    vars_ordered = [spec, Uinf, dT, rhoh]
    for i, v in enumerate(vars_ordered):
        if isinstance(v, np.ndarray):
            return unit_idxs[i]
    return None

def get_const_idx_vals(SOC, Voc, t, Uinf, dT, rho, h, unit_idxs):
    '''To recover unit idx for plot titles and tooltips'''
    spec = SOC if SOC is not None else (Voc if Voc is not None else t)
    rhoh = rho if rho is not None else h

    outs = []
    vals = []
    vars_ordered = [spec, Uinf, dT, rhoh]
    for i, v in enumerate(vars_ordered):
        if isinstance(v, float) or isinstance(v, int):
            outs.append(unit_idxs[i])
            vals.append(v)
    return outs, vals

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
        
        
        
        
        
        
        
        
        
        
        