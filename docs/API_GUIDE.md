# Understanding the Open-Meteo request and response

## 1. Which endpoint does this project use?

An endpoint is the URL a program contacts for a service. This project sends HTTP **GET** requests to:

```text
https://api.open-meteo.com/v1/forecast
```

The same endpoint supplies the requested current conditions and hourly values, including a recent past window. This prototype does not call a separate endpoint for each variable. It makes one request per district, which makes district-specific failure reporting easy to understand.

Other endpoints you may encounter later are the historical weather endpoint, `https://archive-api.open-meteo.com/v1/archive`, and the optional place-search endpoint, `https://geocoding-api.open-meteo.com/v1/search`. Neither is used here. Consult their own [historical](https://open-meteo.com/en/docs/historical-weather-api) and [geocoding](https://open-meteo.com/en/docs/geocoding-api) documentation before extending the project.

## 2. Request parameters

Parameters are key/value pairs appended after the URL's `?`. `requests` handles encoding them safely through its `params` argument.

| Parameter | This project's value | Meaning |
| --- | --- | --- |
| `latitude` | For example, `8.5241` | Representative point north/south position |
| `longitude` | For example, `76.9366` | Representative point east/west position |
| `current` | `temperature_2m,relative_humidity_2m,precipitation` | Values for current conditions |
| `hourly` | The same three variables | Arrays of values at hourly timestamps |
| `temperature_unit` | `celsius` | Request temperature in °C |
| `precipitation_unit` | `mm` | Request precipitation in millimetres |
| `timezone` | `Asia/Kolkata` | Use Kerala's timezone for requested day boundaries |
| `timeformat` | `unixtime` | Return timestamps as Unix seconds |
| `past_days` | `1` by default | Include yesterday |
| `forecast_days` | `2` by default | Include today and tomorrow |

The implemented CLI accepts 0–92 past days and 1–16 forecast days. These are request limits, not a guarantee of local forecast accuracy. See the [official parameter definitions](https://open-meteo.com/en/docs).

For a readable browser request, paste this URL as one line:

```text
https://api.open-meteo.com/v1/forecast?latitude=8.5241&longitude=76.9366&current=temperature_2m,relative_humidity_2m,precipitation&hourly=temperature_2m,relative_humidity_2m,precipitation&temperature_unit=celsius&precipitation_unit=mm&timezone=Asia%2FKolkata&timeformat=unixtime&past_days=1&forecast_days=2
```

## 3. Minimal Python request

Run this from the project folder after installing dependencies:

```python
import requests
from collect_weather import build_params
from config import API_URL
from districts import DISTRICTS

point = DISTRICTS[0]
response = requests.get(API_URL, params=build_params(point), timeout=(10, 30))
response.raise_for_status()       # Raise an error for unsuccessful HTTP status.
payload = response.json()         # Decode JSON into Python dictionaries/lists.
print(response.url)
print(payload["current"])
```

The full collector additionally uses a reusable `Session`, retries transient server/rate-limit failures, keeps raw JSON, and continues after individual district failures.

## 4. What does the JSON look like?

This is an **illustrative, shortened response**, not an actual measurement or bundled dataset. Real requests return many more hourly entries and additional metadata.

```json
{
  "latitude": 8.5,
  "longitude": 76.9,
  "timezone": "Asia/Kolkata",
  "utc_offset_seconds": 19800,
  "current_units": {
    "time": "unixtime",
    "interval": "seconds",
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "precipitation": "mm"
  },
  "current": {
    "time": 1767225600,
    "interval": 900,
    "temperature_2m": 29.4,
    "relative_humidity_2m": 78,
    "precipitation": 0.0
  },
  "hourly_units": {
    "time": "unixtime",
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "precipitation": "mm"
  },
  "hourly": {
    "time": [1767225600, 1767229200],
    "temperature_2m": [29.4, 30.1],
    "relative_humidity_2m": [78, 75],
    "precipitation": [0.0, 0.2]
  }
}
```

`current` contains single values. `hourly` contains parallel arrays: the first time, first temperature, first humidity and first precipitation belong together. The arrays must have equal lengths before combining them.

`temperature_2m` and `relative_humidity_2m` refer to conditions at two metres above ground. Precipitation includes rain, showers and snow; it is not a probability. Hourly precipitation is accumulated over the preceding hour. Current conditions use model data; retain the returned current interval rather than assuming it equals an hour. See [Open-Meteo's variable definitions](https://open-meteo.com/en/docs).

The JSON has no Kerala district field. We add `point["district"]` and `point["location"]` from `districts.py`.

## 5. Extract variables with pandas

The simplest extraction, once the response structure is checked, is:

```python
import pandas as pd

hourly = payload["hourly"]
frame = pd.DataFrame({
    "timestamp_utc": pd.to_datetime(hourly["time"], unit="s", utc=True),
    "temperature_c": hourly["temperature_2m"],
    "humidity_pct": hourly["relative_humidity_2m"],
    "precipitation_mm": hourly["precipitation"],
})
frame["district"] = point["district"]
frame["latitude"] = point["latitude"]
frame["longitude"] = point["longitude"]
frame["time_ist"] = frame["timestamp_utc"].dt.tz_convert("Asia/Kolkata")
print(frame.head())
```

Do **not** add `utc_offset_seconds` to epoch timestamps and then convert them to IST again: that would apply the offset twice. Unix seconds represent UTC regardless of the requested timezone.

In the complete project, use `parse_weather(payload, point, fetched_at)` from `processing.py`. It also checks units and array lengths, builds the current record separately, validates ranges, rejects invalid rows, and returns a data-quality summary.

## 6. Stored columns

| Column | Meaning |
| --- | --- |
| `district`, `location` | Local project metadata |
| `latitude`, `longitude` | Requested town point, decimal degrees |
| `grid_latitude`, `grid_longitude` | Weather-model coordinates returned by the API |
| `timestamp_utc` | Weather valid time, ISO UTC text |
| `data_kind` | `current` or `hourly` |
| `temperature_c` | Temperature in °C |
| `humidity_pct` | Relative humidity, 0–100% |
| `precipitation_mm` | Accumulation over the row's interval |
| `interval_seconds` | API current interval, or 3600 for hourly rows |
| `fetched_at_utc` | Application retrieval time, ISO UTC text |
| `source` | `Open-Meteo` |

The valid time can be later than retrieval time for a forecast. A past valid time does not turn a model estimate into a weather-station observation. After later collections, the SQLite table contains the newest retrieved version of each key, potentially from different fetch times.

## 7. API and data failures

`raise_for_status()` detects HTTP failures; `.json()` can fail if a server returns malformed JSON. The parser also checks API-level errors and response structure. Valid JSON can still contain missing or invalid weather, so row validation is a separate step.

The collector retries HTTP 429, 500, 502, 503 and 504 and eligible connection failures up to three times, with backoff. A `Retry-After` response can extend the wait. Requests use separate 10-second connection and 30-second read timeouts; these are per-attempt timeouts, not a bound on the whole 14-district run.

For a partial failure, successful districts are saved, the report names the affected districts, and the command exits with a nonzero status. Missing data is neither interpolated nor silently replaced with example values.
