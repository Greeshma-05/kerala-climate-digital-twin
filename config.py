"""Shared paths and settings. Paths work even if launched from another folder."""

import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent
ON_VERCEL = os.environ.get("VERCEL") == "1"
# Vercel's application files are read-only. Its temporary directory is writable,
# but is neither permanent nor shared between separate function instances.
DEFAULT_DATA_DIR = Path(tempfile.gettempdir()) / "kerala-climate-twin" if ON_VERCEL else ROOT / "data"
DATA_DIR = Path(os.environ.get("KERALA_DATA_DIR", str(DEFAULT_DATA_DIR)))
DB_PATH = DATA_DIR / "weather.sqlite3"
CSV_PATH = DATA_DIR / "weather.csv"
REPORT_PATH = DATA_DIR / "collection_report.json"
API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Asia/Kolkata"
VARIABLES = ["temperature_2m", "relative_humidity_2m", "precipitation"]

# Broad sanity bounds, not local warning thresholds or climate classifications.
TEMPERATURE_BOUNDS = (-90, 60)
