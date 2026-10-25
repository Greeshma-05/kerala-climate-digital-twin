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
- These checks established local compatibility before the cloud deployment below.

## Vercel production deployment — 25 October 2026

- Public URL: https://kerala-climate-digital-twin.vercel.app
- Production deployment `dpl_5s31MxxCWBmR2G3UQwYy8QsbSxAD` reached **Ready** in the `greeshma-05s-projects` Hobby workspace.
- The final configuration uses a Python service in `vercel.json`, a public catch-all rewrite, and `requirements.txt` for dependency installation. The earlier entry-point-only `pyproject.toml` was removed because it took precedence over `requirements.txt` in cloud builds.
- Requests without Vercel authentication returned **200** for the frontend and **200 / ok** for `/_stcore/health`.
- A TLS-verified, same-origin WebSocket executed the actual Streamlit dashboard without exceptions. Triggering **Collect weather** completed Open-Meteo collection for **14/14 districts**, and the dashboard reported **14/14 fresh records**.
- The dashboard emitted one PyDeck map and four Plotly chart elements. Both CSV downloads returned **200**, with 134,281 and 136,143 bytes in this check.
- `vercel deploy --dry --json` confirmed that local credentials, the virtual environment, SQLite/CSV data and raw responses were excluded from the upload.
- Browser screenshots, external basemap tile rendering, concurrent users across different instances, and reconnection after the 300-second limit were not verified. Successful CSV downloads in this session do not guarantee shared state across instances. Cloud data remains temporary.
