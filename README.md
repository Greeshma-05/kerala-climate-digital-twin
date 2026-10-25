# Kerala Climate Observatory — Phase 1

A working Python prototype for **AI-Powered Digital Twin of India for Climate Change Adaptation**, starting with Kerala's 14 districts.

The prototype collects weather from Open-Meteo, validates and processes it with pandas, saves it in SQLite and CSV, and displays it in a Streamlit dashboard with Plotly charts and a PyDeck map. This phase builds the data foundation: it does not yet implement an AI model, climate simulation, or disaster prediction.

To publish the live dashboard from GitHub, follow [the deployment guide](docs/DEPLOYMENT.md). It includes the repository, Streamlit settings, sharing options and cloud-storage limitations.

For Render hosting, the repository also includes a free demo service configuration in `render.yaml`; follow [the Render deployment guide](docs/RENDER_DEPLOYMENT.md). This option retains the existing Streamlit app.

## 1. Set up and run

Use Python 3.11 or newer, a terminal, and an internet connection for installation and collection. SQLite comes with Python; no database server or API key is needed for the public Open-Meteo endpoint. The free endpoint is intended for non-commercial use; review the [current usage terms](https://open-meteo.com/en/terms) before deployment.

### macOS / Linux

Open a terminal in this project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python collect_weather.py
streamlit run app.py
```

If using the environment already installed in this workspace, start at `source .venv/bin/activate`.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe collect_weather.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Using the executable directly avoids PowerShell activation-policy issues.

Open **http://localhost:8501**. Stop the server with **Ctrl+C**. You can also start the dashboard before collecting anything: it displays an empty state with a **Collect weather** button.

### Dependencies

| Package | Purpose |
| --- | --- |
| `requests` | Send HTTP GET requests to Open-Meteo |
| `pandas` | Turn JSON arrays into rows, validate, filter, group, and export |
| `streamlit` | Build the interactive dashboard |
| `plotly` | Interactive weather charts |
| `pydeck` | Interactive geographic point map |
| Python standard library | `sqlite3`, `json`, `datetime`, `pathlib`, `unittest`, and others |

`requirements.txt` contains compatible version ranges. `requirements-lock.txt` records the exact environment used for verification; it is optional and may require a matching Python/platform combination.

## 2. What you should see

On a complete default collection, the terminal reports approximately:

```text
INFO: Thiruvananthapuram: ok (73 rows)
...
INFO: Kasaragod: ok (73 rows)
Complete districts: 14/14 | Valid rows: 1022
SQLite: .../data/weather.sqlite3
CSV: .../data/weather.csv
Report: .../data/collection_report.json
```

The default request covers yesterday, today and tomorrow: normally 72 hourly records and one current record per district. Counts decrease if records fail validation. Repeated runs can increase stored rows as new current timestamps and forecast hours arrive. Weather values vary with the API response; no example weather is inserted into the live database.

The dashboard contains:

- **Overview:** district coverage, average temperature/humidity across selected points, freshness, map, comparison chart, and current records with timestamps.
- **Weather trends:** three hourly charts, district filters, an IST date range, a daily summary, and a selected-data CSV download.
- **Data explorer:** saved records, current/hourly filtering, and CSV download.
- **How it works:** pipeline explanation, representative coordinates, data source, and phase boundaries.

Hover over a map point to see district, location, weather, accumulation interval and weather timestamp. Mint-to-amber colors represent the selected weather variable's minimum-to-maximum range, not a risk category. Date filtering applies to hourly trends; the overview always uses each selected district's latest saved current record.

The app flags records older than two hours and lists missing or failed districts. A recent successful fetch for one district does not imply all districts were updated: inspect the collection status and individual record timestamps.

## 3. Project files

```text
project/
├── app.py                    # Streamlit dashboard
├── collect_weather.py        # API requests and collection command
├── config.py                 # Paths, variables, API URL, timezone
├── districts.py              # All 14 representative locations
├── processing.py             # JSON extraction and pandas validation
├── storage.py                # SQLite schema, upsert, CSV export
├── requirements.txt          # Dependency ranges
├── requirements-lock.txt     # Exact verified environment
├── render.yaml               # Optional Render hosting configuration
├── .python-version           # Python version for Render
├── .streamlit/config.toml    # Dashboard theme
├── .gitignore               # Exclude environment and generated data
├── docs/
│   ├── API_GUIDE.md          # Endpoint, parameters, JSON, extraction
│   ├── WALKTHROUGH.md        # Step-by-step explanation of each module
│   ├── VERIFICATION.md       # Actual collection and test results
│   ├── DEPLOYMENT.md         # GitHub and Streamlit hosting instructions
│   └── RENDER_DEPLOYMENT.md  # Alternative Render hosting instructions
├── tests/
│   ├── __init__.py           # Makes tests importable as a package
│   ├── test_pipeline.py     # Validation, storage, failure tests
│   └── test_dashboard.py    # Dashboard rendering and filter tests
└── data/                    # Created when collection runs
    ├── weather.sqlite3      # Main database
    ├── weather.csv          # Export of all database rows
    ├── collection_report.json
    └── raw/                 # Original, timestamped API JSON files
```

Read [API_GUIDE.md](docs/API_GUIDE.md) to understand the request and response, then [WALKTHROUGH.md](docs/WALKTHROUGH.md) to follow the implementation file by file.

## 4. Locations and geographic meaning

These are approximate town points chosen for this prototype. They are not surveyed coordinates, district centroids, boundaries, or district-wide averages. No geocoder or API district-name lookup is required at runtime.

| District | Representative location | Latitude | Longitude |
| --- | --- | ---: | ---: |
| Thiruvananthapuram | Thiruvananthapuram | 8.5241 | 76.9366 |
| Kollam | Kollam | 8.8932 | 76.6141 |
| Pathanamthitta | Pathanamthitta | 9.2648 | 76.7870 |
| Alappuzha | Alappuzha | 9.4981 | 76.3388 |
| Kottayam | Kottayam | 9.5916 | 76.5222 |
| Idukki | Painavu | 9.8494 | 76.9730 |
| Ernakulam | Kakkanad | 10.0159 | 76.3419 |
| Thrissur | Thrissur | 10.5276 | 76.2144 |
| Palakkad | Palakkad | 10.7867 | 76.6548 |
| Malappuram | Malappuram | 11.0510 | 76.0711 |
| Kozhikode | Kozhikode | 11.2588 | 75.7804 |
| Wayanad | Kalpetta | 11.6103 | 76.0828 |
| Kannur | Kannur | 11.8745 | 75.3704 |
| Kasaragod | Kasaragod | 12.4996 | 74.9869 |

Open-Meteo may return a nearby weather-model grid coordinate. Both requested coordinates (`latitude`, `longitude`) and returned coordinates (`grid_latitude`, `grid_longitude`) are stored; the map uses the requested town points.

## 5. Refreshing and storing data

Collect once:

```bash
python collect_weather.py
```

Fetch a longer recent window:

```bash
python collect_weather.py --past-days 7 --forecast-days 3
```

`forecast_days` includes today. Request limits are checked before the network call. The dashboard's button always uses the default one past day and two forecast days.

Rebuild the CSV from SQLite without using the API:

```bash
python collect_weather.py --export-only
```

SQLite is the source of truth. Its primary key is `(district, timestamp_utc, data_kind)`. A newer fetch updates an existing key; an older fetch cannot overwrite it. A current record and an hourly record may share a timestamp and remain separate. Hourly forecast revisions replace earlier versions in the main table; this is not a forecast-version archive. Timestamped raw JSON files preserve the original responses.

CSV is replaced atomically after the database transaction commits. If export fails, the database can still contain the successfully saved data; fix the filesystem issue and run `--export-only`. Database and CSV writes are not one cross-file transaction.

Collection is **manual**. Leave the dashboard open and use its button, or run the collector in a terminal and click **Reload saved data**. Simply opening the dashboard does not send API requests. For a later unattended demo, schedule the collector with your operating system's scheduler at a modest interval, such as hourly; avoid overlapping jobs.

To keep a separate dataset, set `KERALA_DATA_DIR` before running either command. For example on macOS/Linux:

```bash
export KERALA_DATA_DIR=/absolute/path/to/another/data
python collect_weather.py
streamlit run app.py
```

## 6. Data quality and time

- Missing fields, unequal arrays, unexpected units, invalid coordinates/timestamps, impossible humidity, negative or non-finite rain, and out-of-range temperatures are rejected.
- Broad temperature sanity bounds are −90 to 60 °C. These are validation limits, not Kerala alert thresholds.
- A missing rain value is **not** filled with zero. Invalid hours are excluded and counted in the report; charts show gaps.
- `timestamp_utc` is the time the weather value refers to. `fetched_at_utc` is when this application received it; it is not the model's issue time.
- Storage and downloads use ISO UTC strings ending in `Z`. Dashboard labels use IST, which is UTC+05:30. JSON epoch seconds are interpreted as UTC exactly once.
- Current records retain the API's `interval_seconds`; hourly rain represents the preceding hour. Do not add current precipitation to hourly precipitation.
- Daily summaries group hourly records by their timestamp's IST date. Rain therefore uses interval-end dates, not exact midnight-to-midnight accumulation windows. `available_hours` shows missing/incomplete coverage; totals can include forecast hours.

The system never silently substitutes synthetic weather after an API failure. Previously stored data remains visible with its original time and freshness label. Check `data/collection_report.json` for district-level outcomes, rejected rows, and errors. The collector exits with status 1 for partial or failed collection, making problems visible to scheduled jobs.

## 7. Verify the project

```bash
python -m unittest discover -s tests -v
```

Tests use explicitly synthetic fixtures and temporary databases. They check parsing, UTC conversion, invalid/missing values, duplicate handling, newer-versus-older updates, SQLite/CSV agreement, partial/all-request failures, the dashboard's empty state, and district filters. They do not contact Open-Meteo or alter the live dataset. Browser map tiles require a separate visual/network check.

See [the verification record](docs/VERIFICATION.md) for the actual live collection, test results and browser verification limit.

You can inspect the database using Python:

```python
import sqlite3
import pandas as pd

with sqlite3.connect("data/weather.sqlite3") as connection:
    summary = pd.read_sql_query(
        "SELECT district, data_kind, COUNT(*) AS records "
        "FROM weather GROUP BY district, data_kind", connection
    )
print(summary)
```

## 8. Troubleshooting

| Problem | What to do |
| --- | --- |
| `ModuleNotFoundError` | Use the virtual environment's Python and install `requirements.txt`. |
| Timeout / connection error | Check internet access. The collector retries transient failures and lists affected districts; rerun later. |
| HTTP 429 | The service is rate limiting requests. Wait before retrying and reduce collection frequency. |
| Blank map background | Map tiles need internet and browser WebGL. Check connectivity/browser support; tables and charts remain available. |
| No data on first run | Click **Collect weather** or run the collector. There is no bundled fake dataset. |
| Stale records | Collect again; check which districts failed in the report. |
| CSV missing but SQLite exists | Run `python collect_weather.py --export-only`. |
| Port 8501 in use | Run `streamlit run app.py --server.port 8502`. |
| Wrong local dataset | Check `KERALA_DATA_DIR`; all default paths are relative to the code folder, not the terminal's current folder. |

## 9. How to present Phase 1

Demonstrate collection, a complete 14-district status report, a district filter, the map tooltip, the three weather charts, the timestamps, and a CSV download. Explain that the data pipeline is the foundation for the digital twin.

Future phases can add multiple grid points per district, district polygons, longer historical datasets, terrain/river/land-use information, validated prediction models and adaptation scenarios. Short-term weather charts alone do not establish climate-change trends. Any future AI model needs training data, a time-based evaluation split, baseline comparisons, and measured performance before making prediction claims.

## Sources and attribution

- [Open-Meteo forecast API documentation](https://open-meteo.com/en/docs): parameters, variables, time and model-data semantics.
- [Open-Meteo data licence](https://open-meteo.com/en/licence) and [terms](https://open-meteo.com/en/terms): data attribution and service use.
- [Streamlit documentation](https://docs.streamlit.io/): dashboard widgets and testing.
- [Plotly Python documentation](https://plotly.com/python/): charts.
- [PyDeck documentation](https://deckgl.readthedocs.io/en/latest/): point-map rendering.

Weather data is attributed to Open-Meteo under CC BY 4.0. This project validates, normalizes, filters and aggregates it. Basemap attribution belongs to CARTO and OpenStreetMap contributors.
