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
