"""Offline tests use synthetic fixtures only; no sample data enters the live DB."""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests

from collect_weather import collect_all
from districts import DISTRICTS
from processing import latest_current, parse_weather, validate_rows
from storage import load_weather, save_weather


def fixture_payload():
    now = int(datetime.now(timezone.utc).timestamp())
    hour = now - now % 3600
    units = {"time": "unixtime", "temperature_2m": "°C", "relative_humidity_2m": "%", "precipitation": "mm"}
    return {
        "latitude": 8.5, "longitude": 76.9,
        "current_units": {**units, "interval": "seconds"}, "hourly_units": units,
        "current": {"time": now - now % 900, "interval": 900, "temperature_2m": 29.0,
                    "relative_humidity_2m": 80, "precipitation": 0.1},
        "hourly": {"time": [hour - 3600, hour, hour + 3600], "temperature_2m": [28.0, 29.0, 30.0],
                   "relative_humidity_2m": [85, 80, 75], "precipitation": [0.5, 0.0, 0.2]},
    }


def fixture_frame(point=None):
    return parse_weather(fixture_payload(), point or DISTRICTS[0], datetime.now(timezone.utc))[0]


class PipelineTests(unittest.TestCase):
    def test_fourteen_unique_districts(self):
        self.assertEqual(len({point["district"] for point in DISTRICTS}), 14)

    def test_parse_and_timezone(self):
        payload = fixture_payload()
        frame, quality = parse_weather(payload, DISTRICTS[0], datetime.now(timezone.utc))
        self.assertEqual(len(frame), 4)
        self.assertEqual(quality["rejected_rows"], 0)
        stamp = pd.Timestamp(frame.loc[frame.data_kind.eq("current"), "timestamp_utc"].iloc[0])
        self.assertEqual(int(stamp.timestamp()), payload["current"]["time"])
        self.assertEqual(stamp.tz_convert("Asia/Kolkata").utcoffset().total_seconds(), 19800)
        self.assertTrue(frame["latitude"].eq(DISTRICTS[0]["latitude"]).all())
        self.assertTrue(frame["grid_latitude"].eq(8.5).all())

    def test_reject_unequal_arrays(self):
        payload = fixture_payload()
        payload["hourly"]["precipitation"].pop()
        with self.assertRaisesRegex(ValueError, "unequal lengths"):
            parse_weather(payload, DISTRICTS[0], datetime.now(timezone.utc))

    def test_reject_wrong_units(self):
        payload = fixture_payload()
        payload["current_units"]["temperature_2m"] = "°F"
        with self.assertRaisesRegex(ValueError, "units"):
            parse_weather(payload, DISTRICTS[0], datetime.now(timezone.utc))

    def test_null_is_not_zero_rain(self):
        payload = fixture_payload()
        payload["hourly"]["precipitation"][0] = None
        frame, quality = parse_weather(payload, DISTRICTS[0], datetime.now(timezone.utc))
        self.assertEqual(len(frame), 3)
        self.assertEqual(quality["rejected_rows"], 1)
        self.assertFalse(frame["precipitation_mm"].isna().any())

    def test_reject_bad_ranges_and_dates(self):
        for column, value in [("humidity_pct", 101), ("temperature_c", 80),
                              ("precipitation_mm", -1), ("precipitation_mm", float("inf")),
                              ("latitude", 91), ("timestamp_utc", "bad-date"),
                              ("timestamp_utc", "1970-01-01T00:00:00Z")]:
            with self.subTest(column=column, value=value):
                frame = fixture_frame()
                frame.loc[0, column] = value
                clean, quality = validate_rows(frame)
                self.assertEqual(len(clean), 3)
                self.assertEqual(quality["rejected_rows"], 1)

    def test_duplicate_rows_and_future_not_current(self):
        frame = fixture_frame()
        clean, quality = validate_rows(pd.concat([frame, frame]))
        self.assertEqual(len(clean), 4)
        self.assertEqual(quality["duplicate_rows"], 4)
        current = latest_current(clean)
        self.assertEqual(len(current), 1)
        self.assertEqual(current.iloc[0]["temperature_c"], 29.0)

    def test_upsert_csv_and_older_fetch_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            db, csv = Path(directory) / "test.sqlite3", Path(directory) / "test.csv"
            frame = fixture_frame()
            self.assertEqual(save_weather(frame, db, csv), 4)
            self.assertEqual(save_weather(frame, db, csv), 4)
            updated = frame.copy()
            updated["temperature_c"] = 31.0
            updated["fetched_at_utc"] = (pd.to_datetime(updated["fetched_at_utc"], utc=True)
                                        + pd.Timedelta(minutes=1)).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            save_weather(updated, db, csv)
            save_weather(frame, db, csv)
            saved = load_weather(db)
            self.assertEqual(len(saved), 4)
            self.assertTrue(saved["temperature_c"].eq(31).all())
            pd.testing.assert_frame_equal(saved, pd.read_csv(csv), check_dtype=False)

    @patch("collect_weather.time.sleep")
    @patch("collect_weather.make_session")
    def test_partial_failure_still_saves_other_districts(self, make_session, _sleep):
        session = make_session.return_value.__enter__.return_value
        response = Mock()
        response.json.side_effect = lambda: deepcopy(fixture_payload())
        session.get.side_effect = [requests.Timeout("test timeout")] + [response] * 13
        with tempfile.TemporaryDirectory() as directory:
            frame, report = collect_all(data_dir=directory)
            self.assertEqual(report["successful_districts"], 13)
            self.assertTrue(report["stored"])
            self.assertEqual(frame["district"].nunique(), 13)
            self.assertEqual(report["districts"][0]["status"], "failed")

    @patch("collect_weather.time.sleep")
    @patch("collect_weather.make_session")
    def test_all_failures_preserve_previous_data(self, make_session, _sleep):
        make_session.return_value.__enter__.return_value.get.side_effect = requests.Timeout("offline test")
        with tempfile.TemporaryDirectory() as directory:
            db, csv = Path(directory) / "weather.sqlite3", Path(directory) / "weather.csv"
            save_weather(fixture_frame(), db, csv)
            before = csv.read_bytes()
            frame, report = collect_all(data_dir=directory)
            self.assertTrue(frame.empty)
            self.assertFalse(report["stored"])
            self.assertEqual(len(load_weather(db)), 4)
            self.assertEqual(csv.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
