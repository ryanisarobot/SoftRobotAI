"""Compatibility entry point for the existing Streamlit Cloud deployment.

The application lives in website/app.py after the repository reorganization.
"""
from pathlib import Path
import runpy
import sys

website = Path(__file__).resolve().parent.parent / "website"
sys.path.insert(0, str(website))
runpy.run_path(str(website / "app.py"), run_name="__main__")
