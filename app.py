"""Run with: streamlit run app.py"""

from datetime import datetime, timezone
import json
import sqlite3

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

from collect_weather import collect_all
from config import DB_PATH, REPORT_PATH, TIMEZONE
from districts import DISTRICTS, DISTRICT_NAMES
from processing import latest_current
from storage import load_weather

st.set_page_config(page_title="Kerala Climate Observatory", page_icon="🌿", layout="wide")
st.markdown("""
<style>
  .block-container {max-width: 1500px; padding-top: 2.2rem; padding-bottom: 3rem;}
  h1 {font-weight: 650 !important; letter-spacing: -1.3px;}
  h2, h3 {letter-spacing: -.5px;}
  .eyebrow {font-size: .73rem; letter-spacing: .2em; color: #8FE3BC; margin-bottom: .6rem;}
  .intro {color: #A9BDB6; max-width: 760px; font-size: 1.05rem; margin-bottom: 1.6rem;}
  [data-testid="stMetric"] {background: #142223; border: 1px solid #2A403B; border-radius: 12px; padding: 18px;}
  [data-testid="stMetricLabel"] {color: #A9BDB6;}
  [data-testid="stMetricValue"] {font-size: 1.9rem;}
  [data-testid="stSidebar"] {border-right: 1px solid #2A403B;}
</style>
""", unsafe_allow_html=True)


def local_time(value):
    return pd.Timestamp(value).tz_convert(TIMEZONE).strftime("%d %b %Y, %H:%M IST")


def read_report():
    try:
        return json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def style_chart(figure, height=360):
    figure.update_layout(height=height, margin=dict(l=8, r=12, t=25, b=10),
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#D5E6DF"), legend_title_text="",
                         legend=dict(orientation="h", y=-0.25), hovermode="x unified")
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="#263A35", zeroline=False)
    return figure


st.sidebar.markdown("### 🌿 Kerala Twin")
st.sidebar.caption("CLIMATE OBSERVATORY · PHASE 01")
st.sidebar.divider()
st.sidebar.markdown("**Weather collection**")
st.sidebar.caption("Fetch current conditions plus yesterday, today and tomorrow's hourly data.")
if st.sidebar.button("↻ Collect weather", type="primary", width="stretch"):
    bar = st.sidebar.progress(0, text="Connecting to Open-Meteo…")
    try:
        _, collection = collect_all(progress=lambda fraction, status: bar.progress(
            fraction, text=f"{status['district']} · {status['status']}"))
        if collection["successful_districts"] == 14:
            st.sidebar.success("All 14 districts updated.")
        else:
            st.sidebar.warning(f"Complete: {collection['successful_districts']}/14. Check collection status below.")
    except (OSError, ValueError, sqlite3.Error) as error:
        st.sidebar.error(f"Could not finish collection: {error}")
    finally:
        bar.empty()
st.sidebar.button("Reload saved data", width="stretch",
                  help="Reread SQLite after running the collector in a terminal. No API request.")

st.markdown('<div class="eyebrow">INDIA DIGITAL TWIN / KERALA PILOT</div>', unsafe_allow_html=True)
st.title("A closer look at Kerala’s weather.")
st.markdown('<div class="intro">Explore weather across 14 districts. A first step toward a digital twin for climate adaptation.</div>',
            unsafe_allow_html=True)

try:
    weather = load_weather()
except (OSError, sqlite3.Error, pd.errors.DatabaseError) as error:
    st.error(f"Cannot read {DB_PATH}: {error}")
    st.stop()
report = read_report()
if report.get("districts"):
    incomplete = [item["district"] for item in report["districts"] if item["status"] != "ok"]
    if incomplete:
        st.warning("Last collection was incomplete for: " + ", ".join(incomplete)
                   + ". Previously stored data, if any, remains available.")
    if not report.get("stored"):
        st.warning("The last collection did not finish storage/export. Check the report and terminal output.")
    with st.expander("Last collection · status and data quality"):
        st.caption(f"Finished: {local_time(report['finished_at_utc'])}")
        st.dataframe(pd.DataFrame(report["districts"]), hide_index=True, width="stretch")

if weather.empty:
    st.info("Your observatory is ready. Choose ‘Collect weather’ in the sidebar to fetch all 14 districts.")
    st.code("python collect_weather.py\nstreamlit run app.py", language="bash")
    st.caption("Internet is required for collection and map tiles. Saved charts and tables work without new API calls.")
    st.dataframe(pd.DataFrame(DISTRICTS), hide_index=True, width="stretch")
    st.stop()

weather["time_ist"] = pd.to_datetime(weather["timestamp_utc"], utc=True).dt.tz_convert(TIMEZONE)
weather["fetched_ist"] = pd.to_datetime(weather["fetched_at_utc"], utc=True).dt.tz_convert(TIMEZONE)
now = pd.Timestamp(datetime.now(timezone.utc))
selected = st.sidebar.multiselect("Districts", DISTRICT_NAMES, default=DISTRICT_NAMES)
st.sidebar.caption("One representative town per district. Points are not district averages.")
if not selected:
    st.info("Select at least one district to explore weather.")
    st.stop()
filtered = weather.loc[weather["district"].isin(selected)].copy()
current = latest_current(filtered)
current["stale"] = pd.to_datetime(current["timestamp_utc"], utc=True).lt(now - pd.Timedelta(hours=2))
st.caption(f"LATEST SUCCESSFUL FETCH · {local_time(weather['fetched_at_utc'].max())}  |  All displayed times: IST (UTC+05:30)")
missing = sorted(set(selected) - set(current["district"]))
if missing:
    st.warning("No current record for: " + ", ".join(missing))
if current["stale"].any():
    st.warning(f"{int(current['stale'].sum())} selected district(s) have current records older than 2 hours. Collect weather to refresh them.")

overview, trends, records, method = st.tabs(["Overview", "Weather trends", "Data explorer", "How it works"])
with overview:
    st.subheader("Latest district snapshot")
    st.caption("Latest saved current record per selected district, including any marked stale. Record times may differ.")
    first, second, third, fourth = st.columns(4)
    first.metric("District coverage", f"{len(current)} / {len(selected)}")
    second.metric("Mean temperature", f"{current['temperature_c'].mean():.1f} °C" if len(current) else "—")
    third.metric("Mean humidity", f"{current['humidity_pct'].mean():.0f} %" if len(current) else "—")
    fourth.metric("Fresh records · ≤ 2h", f"{int((~current['stale']).sum())} / {len(selected)}")
    st.caption("Means give each representative point equal weight; they are not area-weighted Kerala statistics.")
    map_column, comparison_column = st.columns([1.35, 1], gap="large")
    metrics = {"Temperature (°C)": "temperature_c", "Humidity (%)": "humidity_pct",
               "Precipitation (mm / current interval)": "precipitation_mm"}
    with map_column:
        st.markdown("### District weather map")
        label = st.selectbox("Map variable", list(metrics))
        metric = metrics[label]
        if not current.empty:
            points = current.copy()
            low, high = float(points[metric].min()), float(points[metric].max())
            scale = (points[metric] - low) / (high - low) if high > low else pd.Series(0.5, index=points.index)
            points["color"] = [[int(70 + 175 * value), int(200 - 45 * value), int(170 - 80 * value), 235]
                               for value in scale]
            points["weather_time"] = points["timestamp_utc"].map(local_time)
            points["freshness"] = points["stale"].map({True: "Stale (>2 hours)", False: "Fresh (≤2 hours)"})
            points["interval_minutes"] = points["interval_seconds"] / 60
            points = points.drop(columns=["time_ist", "fetched_ist"])
            layer = pdk.Layer("ScatterplotLayer", data=points, get_position="[longitude, latitude]",
                              get_fill_color="color", get_radius=6000, radius_min_pixels=7,
                              radius_max_pixels=22, pickable=True, stroked=True,
                              get_line_color=[235, 243, 239], line_width_min_pixels=1)
            deck = pdk.Deck(layers=[layer], map_provider="carto",
                            map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
                            initial_view_state=pdk.ViewState(latitude=10.5, longitude=76.2, zoom=6.5),
                            tooltip={"text": "{district} · {location}\n{temperature_c} °C | {humidity_pct}% RH\n"
                                     "Precipitation: {precipitation_mm} mm / {interval_minutes} min\n"
                                     "{weather_time}\n{freshness}"})
            st.pydeck_chart(deck, width="stretch", height=470)
            st.caption(f"Mint → amber: {low:.1f} → {high:.1f} · {label}. Hover over a point for its timestamp. Map: CARTO / OpenStreetMap.")
        else:
            st.info("Collect current records to display the map.")
    with comparison_column:
        st.markdown("### Across the districts")
        st.caption(label)
        if not current.empty:
            comparison = px.bar(current.sort_values(metric), x=metric, y="district", orientation="h",
                                color_discrete_sequence=["#8FE3BC"],
                                labels={metric: label, "district": ""})
            st.plotly_chart(style_chart(comparison, 510), width="stretch")
    st.markdown("### Current records")
    snapshot = current[["district", "location", "temperature_c", "humidity_pct", "precipitation_mm",
                        "interval_seconds", "timestamp_utc", "fetched_at_utc", "stale"]].copy()
    for column in ["timestamp_utc", "fetched_at_utc"]:
        snapshot[column.replace("_utc", "_ist")] = snapshot.pop(column).map(local_time)
    st.dataframe(snapshot, hide_index=True, width="stretch")
    st.caption("Current precipitation covers the API's interval_seconds. Hourly precipitation covers the preceding hour; these intervals are kept separate.")

hourly = filtered.loc[filtered["data_kind"].eq("hourly")].copy()
with trends:
    st.subheader("Follow the weather over time")
    st.caption("Hourly model data. The date filter applies to this tab and its hourly download; the current snapshot is independent.")
    if hourly.empty:
        st.info("No hourly records for the selected districts.")
        period = hourly
    else:
        earliest, latest = hourly["time_ist"].dt.date.min(), hourly["time_ist"].dt.date.max()
        dates = st.date_input("Date range · IST", value=(earliest, latest), min_value=earliest, max_value=latest)
        if len(dates) != 2:
            st.info("Choose both a start date and an end date.")
            period = hourly.iloc[0:0]
        else:
            period = hourly.loc[hourly["time_ist"].dt.date.between(*dates)].copy()
        if period.empty:
            st.info("No hourly data in the selected date range.")
        else:
            # Reindex each district so dropped invalid hours appear as visible gaps.
            chart_parts = []
            for name, group in period.groupby("district"):
                indexed = group.set_index("time_ist").reindex(pd.date_range(
                    period["time_ist"].min(), period["time_ist"].max(), freq="h"))
                indexed.index.name = "time_ist"
                indexed["district"] = name
                chart_parts.append(indexed.reset_index())
            chart_data = pd.concat(chart_parts, ignore_index=True)
            # Plotly's browser formatting can otherwise depend on the viewer's zone.
            chart_data["time_ist"] = chart_data["time_ist"].dt.tz_localize(None)
            palette = px.colors.qualitative.Safe + px.colors.qualitative.Set2
            for variable, title in [("temperature_c", "Temperature (°C)"),
                                    ("humidity_pct", "Relative humidity (%)"),
                                    ("precipitation_mm", "Precipitation (mm / preceding hour)")]:
                figure = px.line(chart_data, x="time_ist", y=variable, color="district",
                                 color_discrete_sequence=palette,
                                 labels={"time_ist": "Time (IST)", variable: title})
                figure.update_traces(connectgaps=False)
                local_now = now.tz_convert(TIMEZONE).tz_localize(None)
                if chart_data["time_ist"].min() <= local_now <= chart_data["time_ist"].max():
                    figure.add_vline(x=local_now.to_pydatetime(), line_dash="dot", line_color="#DDE8BA")
                st.markdown(f"#### {title}")
                st.plotly_chart(style_chart(figure), width="stretch")
            st.caption("Dotted line = now. Future timestamps are forecasts; earlier timestamps are past model estimates. Missing hours appear as gaps.")
            daily = period.assign(date_ist=period["time_ist"].dt.strftime("%Y-%m-%d")).groupby(
                ["district", "date_ist"], as_index=False).agg(
                    mean_temperature_c=("temperature_c", "mean"), mean_humidity_pct=("humidity_pct", "mean"),
                    precipitation_mm=("precipitation_mm", "sum"), available_hours=("timestamp_utc", "count"))
            st.markdown("#### Daily summary of available hourly records")
            st.caption("Rain is summed by its interval-end date in IST; midnight's preceding hour belongs to the previous calendar day. Fewer than 24 hours means an incomplete total. Future hours may be included.")
            st.dataframe(daily.round(2), hide_index=True, width="stretch")
            st.download_button("Download selected hourly data", period.drop(columns=["time_ist", "fetched_ist"]).to_csv(index=False),
                               file_name="kerala_hourly_selection.csv", mime="text/csv")

with records:
    st.subheader("Explore the stored records")
    st.caption(f"{len(filtered):,} rows for selected districts · {len(weather):,} rows in SQLite · UTC timestamps in storage and exports")
    record_kind = st.radio("Record type", ["All", "current", "hourly"], horizontal=True)
    table = filtered if record_kind == "All" else filtered.loc[filtered["data_kind"].eq(record_kind)]
    table = table.drop(columns=["time_ist", "fetched_ist"]).sort_values(["timestamp_utc", "district"], ascending=[False, True])
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button("Download displayed records", table.to_csv(index=False), file_name="kerala_weather_selection.csv", mime="text/csv")

with method:
    st.subheader("From coordinates to an observatory")
    st.markdown("""
1. **Collect:** Python `requests` calls Open-Meteo for one representative point in each of Kerala's 14 districts.
2. **Validate:** Check JSON structure, array lengths, units, timestamps, coordinates and weather ranges. Reject invalid rows without inventing replacements.
3. **Process:** `pandas` converts hourly arrays into rows, normalizes UTC timestamps and removes duplicate keys.
4. **Store:** SQLite saves the latest version for each district, timestamp and record type. CSV exports the stored table; raw JSON preserves API responses.
5. **Explore:** Streamlit filters the data, Plotly draws charts, and PyDeck places weather points on a map.

**Phase 1 scope:** A weather monitoring and data foundation for your proposed AI-powered digital twin. This prototype does not train an AI model, simulate climate change or predict flood/landslide risk.

Open-Meteo values are weather-model estimates. A town point does not represent a whole district, especially where terrain varies. Historical forecast revisions are overwritten in the main table; original API responses remain in `data/raw/`.

Collection is manual through the button or command line. The app reads saved data on rerun; it does not poll the API in the background. The two-hour freshness label is a project display rule, not an official weather warning.
""")
    st.dataframe(pd.DataFrame(DISTRICTS), hide_index=True, width="stretch")

st.divider()
st.caption("Weather data: Open-Meteo · CC BY 4.0. Changes: validation, UTC normalization, filtering and aggregation. Kerala Climate Observatory · Final-year project / Phase 1")
st.markdown("[Open-Meteo documentation](https://open-meteo.com/en/docs) · [Data licence](https://open-meteo.com/en/licence)")
