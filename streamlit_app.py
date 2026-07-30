"""ASTRA Streamlit Cloud Entry Point"""

import sys
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dashboard import app
importlib.reload(app)
from dashboard.app import *

if __name__ == "__main__":
    pass
