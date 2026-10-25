"""Vercel loads this ASGI app; the dashboard itself stays in app.py.

Local equivalent: python -m uvicorn vercel_app:app --port 8502
The hosting platform starts the server, so do not call streamlit.run here.
"""

from pathlib import Path

import streamlit as st

app = st.App(Path(__file__).resolve().parent / "app.py")
