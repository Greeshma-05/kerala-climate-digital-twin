"""Optional local HTTP + WebSocket check of the actual Vercel ASGI entry point.

Run: python -m tests.check_vercel_server
Uses temporary synthetic data. Does not contact Open-Meteo or touch live data.
"""

import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import pandas as pd
import requests
from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
from websockets.sync.client import connect

from districts import DISTRICTS
from storage import save_weather
from tests.test_pipeline import fixture_frame


def main():
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="kerala-vercel-check-") as directory:
        data_dir = Path(directory) / "data"
        frame = pd.concat([fixture_frame(point) for point in DISTRICTS], ignore_index=True)
        save_weather(frame, data_dir / "weather.sqlite3", data_dir / "weather.csv")
        environment = {**os.environ, "VERCEL": "1", "KERALA_DATA_DIR": str(data_dir)}
        base = f"http://127.0.0.1:{port}"
        with open(Path(directory) / "server.log", "w+") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "vercel_app:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                with requests.Session() as client:
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            raise RuntimeError("ASGI server exited during startup")
                        try:
                            health = client.get(base + "/_stcore/health", timeout=1)
                            if health.status_code == 200 and health.text.strip() == "ok":
                                break
                        except requests.RequestException:
                            pass
                        time.sleep(0.25)
                    else:
                        raise RuntimeError("ASGI health check timed out")
                    page = client.get(base + "/", timeout=5)
                    assert page.status_code == 200 and "<html" in page.text.lower(), "Frontend did not load"
                    # Match a browser's same-origin handshake; keep XSRF protection enabled.
                    xsrf = client.cookies.get("_streamlit_xsrf")
                    protocols = ["streamlit"] + ([xsrf] if xsrf else [])
                    cookie = "; ".join(f"{key}={value}" for key, value in client.cookies.items())
                    with connect(f"ws://127.0.0.1:{port}/_stcore/stream", origin=base,
                                 subprotocols=protocols, additional_headers={"Cookie": cookie},
                                 open_timeout=10) as websocket:
                        back = BackMsg()
                        back.rerun_script.query_string = ""
                        websocket.send(back.SerializeToString())
                        coverage = False
                        for _ in range(500):
                            message = ForwardMsg()
                            message.ParseFromString(websocket.recv(timeout=15))
                            if message.HasField("delta") and message.delta.HasField("new_element"):
                                element = message.delta.new_element
                                if element.HasField("exception"):
                                    raise RuntimeError(element.exception.message)
                                if element.HasField("metric") and element.metric.body == "14 / 14":
                                    coverage = True
                            if message.HasField("script_finished"):
                                break
                        else:
                            raise RuntimeError("Dashboard did not finish rendering")
                        assert coverage, "Dashboard did not display 14/14 district coverage"
                    print("ASGI checks passed: HTTP frontend, health, WebSocket, dashboard execution, 14/14 coverage")
            except Exception:
                log.seek(0)
                print(log.read()[-6000:])
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
