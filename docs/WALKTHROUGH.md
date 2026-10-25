# Follow the implementation, file by file

Read the files in the order below. The flow is:

```text
districts.py + config.py
          ↓
collect_weather.py → Open-Meteo → original JSON in data/raw/
          ↓
processing.py → validated pandas DataFrame
          ↓
storage.py → SQLite → CSV
          ↓
app.py → filters, charts, map and downloads
```

## 1. `config.py`: settings in one place

`ROOT` finds the directory containing the code. `DATA_DIR` defaults to its `data/` folder, so running the program from another terminal directory does not accidentally create a second database. An optional `KERALA_DATA_DIR` environment variable lets you use another location.

The file defines the API URL, three requested variables, output paths and timezone. Broad temperature bounds are shared by pandas validation. There are no weather API credentials to configure. On Vercel, `ON_VERCEL` selects a temporary writable data directory; an explicit `KERALA_DATA_DIR` overrides either default.

## 2. `districts.py`: the geographic input

`DISTRICTS` is a list of 14 Python dictionaries. Each dictionary contains a district name, representative town, latitude and longitude. A loop can therefore use exactly the same request logic for every district.

`DISTRICT_NAMES` extracts the names for dashboard filters and validation. To change a representative point, update its coordinates here and document the change. Because location is not part of the database's primary key, use a new data directory when changing points to avoid mixing old and new sampling locations in a time series.

## 3. `collect_weather.py`: acquire data

1. `build_params()` constructs the query parameters for one point.
2. `make_session()` creates a `requests.Session` with bounded retries and backoff. A session reuses connections across requests.
3. `collect_all()` loops through the district dictionaries. It requests JSON, records retrieval time, and writes a timestamped original response.
4. `parse_weather()` returns clean rows and rejection/duplicate counts. A district is `ok`, `partial`, or `failed`.
5. `pd.concat()` combines valid district frames. If any rows survive, `save_weather()` stores them.
6. `collection_report.json` records the results. The optional `progress` callback lets Streamlit update a progress bar without embedding UI code in the collector.
7. `main()` handles command-line options. The `if __name__ == "__main__"` guard means importing this file into the dashboard does not automatically start collection.

A failed district does not discard other districts. Filesystem/database errors are different: they can prevent storage and should be fixed before retrying. The app reports these errors rather than displaying a success message.

## 4. `processing.py`: turn JSON into tidy rows

`parse_weather()` checks the response's units, current object and hourly array lengths before pairing values. It builds one current row and one row per hourly timestamp, adding district metadata and both coordinate pairs.

Epoch seconds become timezone-aware UTC timestamps with `pd.to_datetime(..., unit="s", utc=True)`. `validate_rows()` then:

1. Checks required columns.
2. Converts numeric columns with `pd.to_numeric(errors="coerce")`, making unparseable values missing.
3. Builds a Boolean mask for valid names, coordinates, weather ranges, intervals, source and timestamps.
4. Counts and drops invalid rows. Current timestamps cannot be implausibly far in the future; hourly forecasts may be in the future.
5. Formats UTC times consistently and removes duplicate district/time/type keys, retaining the most recently fetched row.
6. Sorts the table for predictable output.

`latest_current()` filters `data_kind == "current"` before choosing each district's latest timestamp. This prevents tomorrow's forecast from being mistaken for current weather.

## 5. `storage.py`: make records persistent

`connect()` opens SQLite and creates the table/index if necessary. `SCHEMA` defines the columns, basic SQL constraints and composite primary key. Python's built-in `sqlite3` module handles the database.

`save_weather()` checks the input again and uses parameterized `?` placeholders to insert rows. SQLite's `ON CONFLICT ... DO UPDATE` updates existing keys only when the incoming retrieval timestamp is at least as new as the stored one. Database writes use a transaction: an error during insertion rolls back that insertion batch.

`load_weather()` reads SQLite into a DataFrame. A missing database returns an empty frame, which enables the dashboard's first-run message.

`export_csv()` queries the database, writes a temporary CSV, and atomically replaces the target CSV. A short SQLite write lock serializes exports/writes so an older export cannot overwrite a newer snapshot. Connections are explicitly closed after use.

SQL and CSV cannot commit atomically together. SQLite commits first; an export failure can be repaired without another API request using `--export-only`.

## 6. `app.py`: explore the data

Streamlit runs the Python script again whenever a widget changes. The sidebar collection button is the only dashboard action that calls the API. Other interactions reread saved data and render it.

The app converts stored UTC values to IST for display, applies a district selection, and finds the latest current record per district. It compares each weather timestamp with the current time to mark stale records. Overview statistics use selected points with equal weights; they are not a statewide area-weighted estimate.

The map builds a PyDeck `ScatterplotLayer`: each row supplies longitude, latitude, color and tooltip fields. All points use the same nominal radius. The color scale follows the selected variable's range. No district boundary file is necessary for this point map.

Plotly draws a district comparison bar chart and three hourly line charts. Before drawing hourly lines, the code reindexes each district to the hourly timeline, preserving missing data as gaps. A dotted vertical line marks the current time where it falls within the selected range.

The date selector uses IST dates. The daily table groups selected hourly rows by district and timestamp date. Means apply to temperature/humidity; precipitation is summed and available hours counted. The app explicitly describes precipitation's interval-end-date convention.

Download buttons produce CSV strings from the selected DataFrame. The main `data/weather.csv` remains an export of the entire database.

The **How it works** tab explains what Phase 1 does, its assumptions and the future AI work. Source attribution is included at the bottom of the dashboard.

## 7. Supporting files

- `requirements.txt` lists installable package ranges; `requirements-lock.txt` records the tested versions.
- `.streamlit/config.toml` sets the dark green theme and disables Streamlit usage statistics.
- `.gitignore` excludes the local Python environment, bytecode and generated datasets from version control. Share source code separately from collected data when appropriate.
- `README.md` gives setup, run commands, expected outputs, limitations and troubleshooting.
- `docs/API_GUIDE.md` teaches the HTTP request, JSON shape and extraction.
- `tests/__init__.py` makes the tests importable as a package.
- `tests/test_pipeline.py` contains synthetic fixtures and data-integrity/failure tests.
- `tests/test_dashboard.py` uses Streamlit's `AppTest` to exercise the empty state, populated dashboard and filters without a browser. It does not prove that external map tiles render correctly.
- `vercel_app.py` wraps `app.py` with Streamlit's ASGI interface so Vercel can serve HTTP and WebSocket requests. `pyproject.toml` selects that entry point and `vercel.json` sets its runtime limits and bundle exclusions.
- `.vercelignore` keeps local data and secrets out of Vercel uploads. `.python-version` chooses the hosting Python version. `render.yaml` is the alternative Render configuration.
- `tests/test_hosting.py` checks cloud/local data paths, and `tests/check_vercel_server.py` performs an optional real HTTP and WebSocket check using a temporary local server.
- `docs/VERCEL_DEPLOYMENT.md` and `docs/RENDER_DEPLOYMENT.md` explain their hosting setups and data/session limits.

## 8. A small learning exercise

After collection, start a Python interpreter in this folder:

```python
from storage import load_weather
from processing import latest_current

weather = load_weather()
print(weather.shape)
print(weather.head())
print(weather.groupby(["district", "data_kind"]).size())

snapshot = latest_current(weather)
print(snapshot[["district", "temperature_c", "timestamp_utc"]])

wayanad = weather[(weather["district"] == "Wayanad") & (weather["data_kind"] == "hourly")]
print(wayanad[["timestamp_utc", "humidity_pct", "precipitation_mm"]].head())
```

This shows how the same DataFrame supports both analysis and dashboard display. Add a new weather variable only after updating the request, extraction, validation, storage schema and display consistently.
