#!/usr/bin/env python3
"""
Run both GUI and CLI interfaces for Input Collector.

This script starts the Input Collector with both GUI and CLI interfaces.
"""

import sys
import os

if __name__ == "__main__":
    # Add the same arguments to run.py but ensure CLI is enabled
    args = ["--cli"] + sys.argv[1:]
    
    # Execute run.py with the updated arguments
    run_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.py")
    sys.argv = [run_py_path] + args
    with open(run_py_path) as f:
        exec(f.read())
