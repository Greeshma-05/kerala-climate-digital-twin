# Verification record

Verified on **25 October 2026**, using Python 3.14.6 on macOS. Exact installed packages are listed in `requirements-lock.txt`.

## Live collection

Command: `python collect_weather.py`

- Open-Meteo requests completed successfully for all **14 districts**.
- **1,022 valid rows**: 14 current records and 1,008 hourly records.
- **Zero rejected rows** in this collection.
- Collection finished at **09:04:33 IST** (`2026-10-25T03:34:33Z`). This is a retrieval timestamp, not the weather valid time.
- The SQLite table and CSV were compared with pandas and matched.
- Original JSON responses and the district-level report were retained in `data/`.

These results describe this particular run. Later collections may have different counts, values and coverage.

## Automated checks

Command: `python -m unittest discover -s tests -v`

All **12 tests passed**, covering parsing, timezone conversion, missing/invalid values, unequal arrays, incorrect units, duplicate keys, newer-fetch updates, CSV/SQLite agreement, partial/all-request failures, the dashboard's empty state and district filtering.

The dashboard was also run through Streamlit `AppTest` against the actual collected database. It reported no exceptions, coverage of 14/14 districts, four Plotly charts, and one PyDeck map component.

## Local server and visual limit

The Streamlit server started successfully on `http://127.0.0.1:8501`. Its `/_stcore/health` endpoint returned `ok`.

The browser automation runtime failed to start in this environment, so there was no browser screenshot or visual confirmation of the external basemap tiles. Component creation was verified by AppTest. Open the dashboard in a browser to verify map tiles, hover tooltips and visual layout on your machine.

## Vercel adapter checks — 25 October 2026

- All **15 automated tests passed**, including new checks that local data paths stay unchanged and Vercel uses writable temporary storage.
- `python -m tests.check_vercel_server` passed against the real ASGI entry point: frontend HTTP, health endpoint, WebSocket handshake, dashboard execution and 14/14 district coverage using temporary synthetic data.
- Vercel CLI **65.2.0** detected `vercel_app:app` as a Python application from the repository configuration.
- A controlled CLI development-server run passed repeated HTTP requests and two dashboard runs over its WebSocket connection.
- These are local compatibility checks. Vercel cloud deployment, live map tiles, download routing across instances and reconnect behavior still require verification after deployment.
