#!/usr/bin/env python3
"""
Simple wrapper script to run comprehensive video analysis
"""

import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Import and run the analysis runner
from analysis_runner import main

if __name__ == "__main__":
    main()
