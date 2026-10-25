"""SQLite is the source of truth; CSV is a readable export of the same rows."""

import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

import pandas as pd

from config import CSV_PATH, DB_PATH
from processing import COLUMNS, validate_rows

SCHEMA = """
CREATE TABLE IF NOT EXISTS weather (
    district TEXT NOT NULL,
    location TEXT NOT NULL,
    latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90),
    longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
    grid_latitude REAL NOT NULL CHECK(grid_latitude BETWEEN -90 AND 90),
    grid_longitude REAL NOT NULL CHECK(grid_longitude BETWEEN -180 AND 180),
    timestamp_utc TEXT NOT NULL,
    data_kind TEXT NOT NULL CHECK(data_kind IN ('current', 'hourly')),
    temperature_c REAL NOT NULL CHECK(temperature_c BETWEEN -90 AND 60),
    humidity_pct REAL NOT NULL CHECK(humidity_pct BETWEEN 0 AND 100),
    precipitation_mm REAL NOT NULL CHECK(precipitation_mm >= 0),
    interval_seconds INTEGER NOT NULL CHECK(interval_seconds BETWEEN 1 AND 3600),
    fetched_at_utc TEXT NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (district, timestamp_utc, data_kind)
);
CREATE INDEX IF NOT EXISTS idx_weather_time ON weather(timestamp_utc);
"""


def connect(db_path=DB_PATH):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=30)
    connection.executescript(SCHEMA)
    return connection


def load_weather(db_path=DB_PATH):
    if not Path(db_path).exists():
        return pd.DataFrame(columns=COLUMNS)
    with closing(connect(db_path)) as connection:
        return pd.read_sql_query("SELECT * FROM weather ORDER BY timestamp_utc, district", connection)


def _write_csv(connection, csv_path):
    """Replace the export atomically so readers never see a half-written CSV."""
    target = Path(csv_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.read_sql_query("SELECT * FROM weather ORDER BY timestamp_utc, district", connection)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", dir=target.parent,
                                     encoding="utf-8", newline="", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            frame.to_csv(handle, index=False)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return len(frame)


def export_csv(db_path=DB_PATH, csv_path=CSV_PATH):
    with closing(connect(db_path)) as connection:
        # Serialize exporters and writers so an older snapshot cannot win a race.
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            return _write_csv(connection, csv_path)


def save_weather(frame, db_path=DB_PATH, csv_path=CSV_PATH):
    clean, report = validate_rows(frame)
    if report["rejected_rows"] or clean.empty:
        raise ValueError("Storage requires a nonempty, validated DataFrame")
    placeholders = ", ".join("?" for _ in COLUMNS)
    keys = {"district", "timestamp_utc", "data_kind"}
    updates = ", ".join(f"{column}=excluded.{column}" for column in COLUMNS if column not in keys)
    sql = f"""INSERT INTO weather ({', '.join(COLUMNS)}) VALUES ({placeholders})
        ON CONFLICT(district, timestamp_utc, data_kind) DO UPDATE SET {updates}
        WHERE excluded.fetched_at_utc >= weather.fetched_at_utc"""
    with closing(connect(db_path)) as connection:
        with connection:
            connection.executemany(sql, clean[COLUMNS].itertuples(index=False, name=None))
    # Commit the database first. If CSV fails, the database remains usable and
    # `python collect_weather.py --export-only` repairs the export without API calls.
    return export_csv(db_path, csv_path)
