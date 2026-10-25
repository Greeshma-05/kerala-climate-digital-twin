"""Convert Open-Meteo JSON into a validated, tidy pandas DataFrame."""

import math
import pandas as pd

from config import TEMPERATURE_BOUNDS, VARIABLES
from districts import DISTRICT_NAMES

COLUMNS = [
    "district", "location", "latitude", "longitude", "grid_latitude", "grid_longitude",
    "timestamp_utc", "data_kind", "temperature_c", "humidity_pct", "precipitation_mm",
    "interval_seconds", "fetched_at_utc", "source",
]


def utc_string(value):
    """Use a single UTC format so SQLite can sort timestamps as text."""
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        raise ValueError("A timezone-aware timestamp is required")
    return stamp.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_rows(frame):
    """Reject invalid rows explicitly. Never replace missing rain with zero."""
    frame = frame.copy()
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    for column in ["latitude", "longitude", "grid_latitude", "grid_longitude",
                   "temperature_c", "humidity_pct", "precipitation_mm", "interval_seconds"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    stamps = pd.to_datetime(frame["timestamp_utc"], format="ISO8601", utc=True, errors="coerce")
    fetched = pd.to_datetime(frame["fetched_at_utc"], format="ISO8601", utc=True, errors="coerce")
    valid = (
        frame["district"].isin(DISTRICT_NAMES)
        & frame["location"].notna()
        & frame["latitude"].between(-90, 90)
        & frame["longitude"].between(-180, 180)
        & frame["grid_latitude"].between(-90, 90)
        & frame["grid_longitude"].between(-180, 180)
        & frame["temperature_c"].between(*TEMPERATURE_BOUNDS)
        & frame["humidity_pct"].between(0, 100)
        & frame["precipitation_mm"].ge(0)
        & frame["precipitation_mm"].map(lambda x: math.isfinite(x))
        & frame["data_kind"].isin(["current", "hourly"])
        & frame["interval_seconds"].between(1, 3600)
        & frame["interval_seconds"].mod(1).eq(0)
        & (frame["data_kind"].ne("hourly") | frame["interval_seconds"].eq(3600))
        & frame["source"].eq("Open-Meteo")
        & stamps.notna() & fetched.notna()
        & stamps.between(fetched - pd.Timedelta(days=93), fetched + pd.Timedelta(days=17))
        & (frame["data_kind"].ne("current") | stamps.le(fetched + pd.Timedelta(minutes=15)))
    )
    rejected = int((~valid).sum())
    clean = frame.loc[valid, COLUMNS].copy()
    clean["timestamp_utc"] = stamps.loc[valid].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    clean["fetched_at_utc"] = fetched.loc[valid].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    clean["interval_seconds"] = clean["interval_seconds"].astype(int)
    before = len(clean)
    clean = clean.sort_values("fetched_at_utc").drop_duplicates(
        ["district", "timestamp_utc", "data_kind"], keep="last"
    ).sort_values(["district", "data_kind", "timestamp_utc"]).reset_index(drop=True)
    return clean, {"rejected_rows": rejected, "duplicate_rows": before - len(clean)}


def parse_weather(payload, point, fetched_at):
    """Pair hourly arrays by index and add district metadata to every record."""
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError(f"API error or unexpected JSON: {payload}")
    for block in ["current", "hourly"]:
        units = payload.get(f"{block}_units", {})
        expected = {"time": "unixtime", "temperature_2m": "°C",
                    "relative_humidity_2m": "%", "precipitation": "mm"}
        if block == "current":
            expected["interval"] = "seconds"
        if any(units.get(key) != value for key, value in expected.items()):
            raise ValueError(f"Missing or unexpected units in {block}_units")
    hourly = payload.get("hourly", {})
    times = hourly.get("time")
    if not isinstance(times, list) or not times:
        raise ValueError("Missing or empty hourly time array")
    if any(not isinstance(hourly.get(name), list) or len(hourly[name]) != len(times)
           for name in VARIABLES):
        raise ValueError("Hourly arrays are missing or have unequal lengths")
    current = payload.get("current")
    if not isinstance(current, dict):
        raise ValueError("Missing current weather object")
    base = {**point, "grid_latitude": payload.get("latitude"),
            "grid_longitude": payload.get("longitude"),
            "fetched_at_utc": utc_string(fetched_at), "source": "Open-Meteo"}
    rows = [{**base, "timestamp_utc": current.get("time"), "data_kind": "current",
             "temperature_c": current.get("temperature_2m"),
             "humidity_pct": current.get("relative_humidity_2m"),
             "precipitation_mm": current.get("precipitation"),
             "interval_seconds": current.get("interval")}]
    for index, timestamp in enumerate(times):
        rows.append({**base, "timestamp_utc": timestamp, "data_kind": "hourly",
                     "temperature_c": hourly["temperature_2m"][index],
                     "humidity_pct": hourly["relative_humidity_2m"][index],
                     "precipitation_mm": hourly["precipitation"][index], "interval_seconds": 3600})
    frame = pd.DataFrame(rows)
    # Epoch seconds are UTC even when the API's requested timezone is Asia/Kolkata.
    frame["timestamp_utc"] = pd.to_datetime(
        pd.to_numeric(frame["timestamp_utc"], errors="coerce"), unit="s", utc=True, errors="coerce"
    )
    return validate_rows(frame)


def latest_current(frame):
    """Select actual current records; never substitute a future hourly forecast."""
    current = frame.loc[frame["data_kind"].eq("current")]
    return current.sort_values("timestamp_utc").drop_duplicates("district", keep="last").copy()
