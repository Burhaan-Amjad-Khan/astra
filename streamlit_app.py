"""ASTRA Streamlit Cloud Entry Point"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dashboard.app import *

if __name__ == "__main__":
    pass
