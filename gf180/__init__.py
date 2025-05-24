"""GF180 PDK (Legacy, Deprecated)

This module is a legacy/deprecated alias for the gf180mcu library.
Please use gf180mcu directly in new code.
"""

import sys
import warnings
import os

# Show a deprecation warning when the module is imported
warnings.warn(
    "The gf180 package is deprecated and will be removed in a future version. "
    "Please use the gf180mcu package instead.",
    DeprecationWarning,
    stacklevel=2,
)

import gf180mcu

# Re-export everything from gf180mcu
from gf180mcu import *

# Re-export specific items to ensure compatibility
__version__ = gf180mcu.__version__
__all__ = gf180mcu.__all__
PDK = gf180mcu.PDK
cells = gf180mcu.cells
