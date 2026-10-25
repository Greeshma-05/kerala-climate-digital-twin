"""Streamlit smoke tests: empty state, populated app, and district filters."""

from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from districts import DISTRICTS
from processing import COLUMNS
from tests.test_pipeline import fixture_frame

APP = str(Path(__file__).resolve().parents[1] / "app.py")


class DashboardTests(unittest.TestCase):
    def test_first_run_without_database(self):
        with patch("storage.load_weather", return_value=pd.DataFrame(columns=COLUMNS)):
            app = AppTest.from_file(APP, default_timeout=30).run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any("observatory is ready" in message.value for message in app.info))

    def test_populated_app_and_filters(self):
        frame = pd.concat([fixture_frame(point) for point in DISTRICTS], ignore_index=True)
        with patch("storage.load_weather", return_value=frame):
            app = AppTest.from_file(APP, default_timeout=30).run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.metric[0].value, "14 / 14")
            app.multiselect[0].set_value(["Wayanad"]).run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.metric[0].value, "1 / 1")
            app.selectbox[0].set_value("Humidity (%)").run()
            self.assertEqual(len(app.exception), 0)
            app.multiselect[0].set_value([]).run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any("Select at least one" in message.value for message in app.info))


if __name__ == "__main__":
    unittest.main()
