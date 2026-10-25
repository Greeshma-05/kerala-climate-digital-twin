"""Fetch all 14 districts: python collect_weather.py"""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
import time

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import API_URL, CSV_PATH, DATA_DIR, DB_PATH, REPORT_PATH, TIMEZONE, VARIABLES
from districts import DISTRICTS
from processing import COLUMNS, parse_weather, utc_string
from storage import export_csv, save_weather

LOGGER = logging.getLogger(__name__)


def build_params(point, past_days=1, forecast_days=2):
    return {"latitude": point["latitude"], "longitude": point["longitude"],
            "current": ",".join(VARIABLES), "hourly": ",".join(VARIABLES),
            "temperature_unit": "celsius", "precipitation_unit": "mm",
            "timezone": TIMEZONE, "timeformat": "unixtime",
            "past_days": past_days, "forecast_days": forecast_days}


def make_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET"], respect_retry_after_header=True)
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers["User-Agent"] = "KeralaClimateTwin-Phase1/1.0"
    return session


def collect_all(past_days=1, forecast_days=2, progress=None, data_dir=DATA_DIR):
    """Continue on a failed district and report partial coverage explicitly."""
    if not 0 <= past_days <= 92 or not 1 <= forecast_days <= 16:
        raise ValueError("past_days must be 0–92; forecast_days must be 1–16")
    data_dir = Path(data_dir)
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    report = {"started_at_utc": utc_string(datetime.now(timezone.utc)), "districts": [],
              "past_days": past_days, "forecast_days": forecast_days}
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    with make_session() as session:
        for index, point in enumerate(DISTRICTS):
            status = {"district": point["district"], "status": "failed", "valid_rows": 0}
            try:
                response = session.get(API_URL, params=build_params(point, past_days, forecast_days),
                                       timeout=(10, 30))
                response.raise_for_status()
                payload = response.json()
                fetched_at = datetime.now(timezone.utc)
                # Preserve the original response for your project report and debugging.
                raw_path = raw_dir / f"{run_id}_{point['district']}.json"
                raw_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
                frame, quality = parse_weather(payload, point, fetched_at)
                if frame.empty:
                    raise ValueError("No rows passed validation")
                frames.append(frame)
                has_current = bool(frame["data_kind"].eq("current").any())
                has_hourly = bool(frame["data_kind"].eq("hourly").any())
                status.update({**quality, "status": "ok" if not quality["rejected_rows"]
                               and has_current and has_hourly else "partial",
                               "valid_rows": len(frame), "has_current": has_current,
                               "has_hourly": has_hourly})
            except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                status["error"] = str(error)
                LOGGER.warning("%s: %s", point["district"], error)
            report["districts"].append(status)
            LOGGER.info("%s: %s (%s rows)", point["district"], status["status"], status["valid_rows"])
            if progress:
                progress((index + 1) / len(DISTRICTS), status)
            time.sleep(0.15)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    report["finished_at_utc"] = utc_string(datetime.now(timezone.utc))
    report["valid_rows"] = len(combined)
    report["successful_districts"] = sum(item["status"] == "ok" for item in report["districts"])
    report["stored"] = False
    try:
        if not combined.empty:
            report["database_rows"] = save_weather(combined, data_dir / DB_PATH.name, data_dir / CSV_PATH.name)
            report["stored"] = True
    except (OSError, ValueError, sqlite3.Error) as error:
        report["storage_error"] = str(error)
        raise
    finally:
        (data_dir / REPORT_PATH.name).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return combined, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--past-days", type=int, default=1, help="Past days, 0–92 (default: 1)")
    parser.add_argument("--forecast-days", type=int, default=2, help="Days including today, 1–16 (default: 2)")
    parser.add_argument("--export-only", action="store_true", help="Rebuild CSV from SQLite without network access")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.export_only:
        if not DB_PATH.exists():
            parser.error("No database exists yet. Run the collector first.")
        print(f"Exported {export_csv()} rows to {CSV_PATH}")
        return 0
    if not 0 <= args.past_days <= 92 or not 1 <= args.forecast_days <= 16:
        parser.error("--past-days must be 0–92 and --forecast-days must be 1–16")
    _, report = collect_all(args.past_days, args.forecast_days)
    print(f"Complete districts: {report['successful_districts']}/14 | Valid rows: {report['valid_rows']}")
    print(f"SQLite: {DB_PATH}\nCSV: {CSV_PATH}\nReport: {REPORT_PATH}")
    # Nonzero status makes failures visible to scheduled jobs, even after partial success.
    return 0 if report["successful_districts"] == 14 and report["stored"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
