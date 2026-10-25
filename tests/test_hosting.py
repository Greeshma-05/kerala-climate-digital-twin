"""Check that hosting never attempts to write data inside read-only app files."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HostingPathTests(unittest.TestCase):
    def data_path(self, vercel, override=None):
        environment = os.environ.copy()
        environment.pop("KERALA_DATA_DIR", None)
        environment["VERCEL"] = vercel
        if override:
            environment["KERALA_DATA_DIR"] = override
        return Path(subprocess.check_output(
            [sys.executable, "-c", "from config import DATA_DIR; print(DATA_DIR)"],
            cwd=ROOT, env=environment, text=True,
        ).strip())

    def test_local_storage_keeps_existing_location(self):
        self.assertEqual(self.data_path("0"), ROOT / "data")

    def test_vercel_uses_temporary_storage(self):
        self.assertEqual(self.data_path("1"), Path(tempfile.gettempdir()) / "kerala-climate-twin")

    def test_explicit_data_directory_wins(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.data_path("1", directory), Path(directory))
