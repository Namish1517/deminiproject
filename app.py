
from pathlib import Path
import time

import pandas as pd
import plotly.express as px
import streamlit as st

from src.storage.postgres_store import PostgresStore
from src.storage.parquet_store import ParquetStore
from src.analytics.analyze_stream import SensorAnalytics


st.set_page_config(
    page_title="IoT Pulse | Operations",
    page_icon="📡",
    layout="wide",
)

st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetric"] {
        background: #111827;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #273449;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_services():
    return PostgresStore(), ParquetStore(), SensorAnalytics()


store, parquet, analytics = get_services()

st.sidebar.title("📡 IoT Pulse")
st.sidebar.caption("Industrial Sensor Intelligence")
page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Device Registry",
        "Live Monitoring",
        "Fault Alerts",
        "Historical Analytics",
        "Data Pipeline",
    ],
)

st.sidebar.divider()
auto_refresh = st.sidebar.toggle("Auto-refresh", value=False)
refresh_seconds = st.sidebar.slider(
    "Refresh interval (seconds)", 3, 30, 5
)
if st.sidebar.button("Refresh now"):
    st.rerun()

if auto_refresh:
    st.sidebar.caption(f"Refreshing every {refresh_seconds} seconds.")
    time.sleep(refresh_seconds)
    st.rerun()


def safe_stats():
    return store.get_stats()


def get_history():
    return parquet.load_history()

def render_table(df):
    if df.empty:
        st.info("No data available.")
        return

    display_df = df.copy()

    if "timestamp" in display_df.columns:
        display_df["timestamp"] = pd.to_datetime(
            display_df["timestamp"], errors="coerce"
        )
        display_df = display_df.sort_values(
            "timestamp", ascending=False
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )
stats = safe_stats()
latest = pd.DataFrame(store.get_latest_readings())
alerts = pd.DataFrame(store.get_alerts())
history = get_history()

if page == "Overview":
    st.title("Operations Overview")
    st.caption("Real-time industrial sensor monitoring and data engineering.")

    latest_faults = (
        int((latest["status"] == "FAULT").sum())
        if not latest.empty else 0
    )
    active_devices = len(latest)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registered Devices", stats["devices"])
    c2.metric("Reporting Devices", active_devices)
    c3.metric("Stored Readings", f'{stats["readings"]:,}')
    c4.metric("Current Faults", latest_faults)

    st.subheader("Latest Device Readings")
    render_table(latest)

    left, right = st.columns(2)

    with left:
        st.subheader("Temperature by Device")
        if not latest.empty:
            fig = px.bar(
                latest.sort_values("temperature_c", ascending=False),
                x="device_id",
                y="temperature_c",
                color="status",
                title="Latest Temperature (°C)",
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Vibration by Device")
        if not latest.empty:
            fig = px.bar(
                latest.sort_values("vibration_mm_s", ascending=False),
                x="device_id",
                y="vibration_mm_s",
                color="status",
                title="Latest Vibration (mm/s)",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent Fault Alerts")
    if alerts.empty:
        st.success("No alerts recorded.")
    else:
        st.dataframe(alerts, use_container_width=True, hide_index=True)


elif page == "Device Registry":
    st.title("Device Registry")
    st.caption("Registered industrial devices and their assigned production zones.")

    with store.engine.connect() as connection:
        devices = pd.read_sql(
            "SELECT device_id, device_name, location, registered_at, is_active "
            "FROM devices ORDER BY device_id",
            connection,
        )

    render_table(devices)

    st.subheader("Register a Device")
    with st.form("register_device"):
        device_id = st.text_input("Device ID", placeholder="MACHINE_009")
        device_name = st.text_input("Device Name")
        location = st.text_input("Production Zone")
        submitted = st.form_submit_button("Register device")

        if submitted:
            if not all([device_id.strip(), device_name.strip(), location.strip()]):
                st.error("Complete all fields.")
            else:
                try:
                    from sqlalchemy import text

                    with store.engine.begin() as connection:
                        connection.execute(
                            text("""
                                INSERT INTO devices (
                                    device_id, device_name, location
                                )
                                VALUES (:id, :name, :location)
                            """),
                            {
                                "id": device_id.strip(),
                                "name": device_name.strip(),
                                "location": location.strip(),
                            },
                        )
                    st.success(f"Registered {device_id}.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not register device: {exc}")


elif page == "Live Monitoring":
    st.title("Live Sensor Monitoring")

    if latest.empty:
        st.warning("No readings available. Start the simulator.")
    else:
        selected_device = st.selectbox(
            "Select device", latest["device_id"].tolist()
        )
        reading = latest[latest["device_id"] == selected_device].iloc[0]

        a, b, c, d = st.columns(4)
        a.metric("Temperature", f'{reading["temperature_c"]:.2f} °C')
        b.metric("Humidity", f'{reading["humidity_pct"]:.2f} %')
        c.metric("Vibration", f'{reading["vibration_mm_s"]:.2f} mm/s')
        d.metric("Power", f'{reading["power_kw"]:.2f} kW')

        st.metric("Machine Status", reading["status"])

        st.subheader("All Device Readings")
        render_table(latest)


elif page == "Fault Alerts":
    st.title("Fault & Alert Center")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Alerts", stats["alerts"])
    c2.metric(
        "Critical Alerts",
        int((alerts["severity"] == "CRITICAL").sum())
        if not alerts.empty else 0,
    )
    c3.metric(
        "Unacknowledged Alerts",
        int((~alerts["acknowledged"].astype(bool)).sum())
        if not alerts.empty else 0,
    )

    if alerts.empty:
        st.success("No alerts recorded.")
    else:
        severity = st.multiselect(
            "Filter by severity",
            sorted(alerts["severity"].dropna().unique()),
            default=sorted(alerts["severity"].dropna().unique()),
        )
        filtered = alerts[alerts["severity"].isin(severity)]
        st.dataframe(filtered, use_container_width=True, hide_index=True)


elif page == "Historical Analytics":
    st.title("Historical Sensor Analytics")
    st.caption("DuckDB SQL analytics over Parquet historical records.")

    overview = analytics.get_overview()
    device_summary = analytics.get_device_summary()
    hourly = analytics.get_hourly_trends()

    a, b, c, d = st.columns(4)
    a.metric("Historical Readings", f'{overview["total_readings"]:,}')
    b.metric("Historical Faults", f'{overview["fault_readings"]:,}')
    c.metric("Average Temperature", f'{overview["avg_temperature"]} °C')
    d.metric("Average Vibration", f'{overview["avg_vibration"]} mm/s')

    st.subheader("Device Performance")
    if device_summary.empty:
        st.info("No Parquet data yet. Run the simulator.")
    else:
        st.dataframe(
            device_summary, use_container_width=True, hide_index=True
        )

        fig = px.bar(
            device_summary,
            x="device_id",
            y="faults",
            color="faults",
            title="Fault Readings per Device",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Hourly Sensor Trends")
    if not hourly.empty:
        fig = px.line(
            hourly,
            x="hour",
            y=["temperature", "vibration"],
            title="Average Temperature and Vibration",
        )
        st.plotly_chart(fig, use_container_width=True)

        fig = px.bar(
            hourly,
            x="hour",
            y="faults",
            title="Fault Readings Over Time",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Historical Data")
    render_table(history)


elif page == "Data Pipeline":
    st.title("Data Pipeline Health")
    st.caption("Ingestion, validation, operational storage and analytics.")

    a, b, c, d = st.columns(4)
    a.metric("PostgreSQL Readings", f'{stats["readings"]:,}')
    a.metric("Registered Devices", stats["devices"])
    b.metric("Recorded Alerts", stats["alerts"])
    c.metric("Quarantined Records", stats["quarantined"])
    d.metric(
        "Parquet Rows",
        f'{len(history):,}' if not history.empty else "0",
    )

    st.subheader("Pipeline Architecture")
    st.code(
        "Sensor Simulator → Python Queue → Validation → PostgreSQL\n"
        "                                           ├→ Quarantine\n"
        "                                           └→ Parquet → DuckDB → Dashboard",
        language="text",
    )

    st.subheader("Storage Status")
    st.write("PostgreSQL: Connected if metrics loaded successfully.")

    parquet_path = parquet.history_file
    st.write(f"Parquet file: `{parquet_path}`")
    st.write(f"Parquet exists: {parquet_path.exists()}")

    db_path = (
        Path(__file__).resolve().parent
        / "data"
        / "warehouse"
        / "analytics.duckdb"
    )
    st.write(f"DuckDB database: `{db_path}`")
    st.write(f"DuckDB file exists: {db_path.exists()}")

    st.subheader("Quarantined Records")
    with store.engine.connect() as connection:
        quarantined = pd.read_sql(
            "SELECT id, received_at, record, reason "
            "FROM quarantined_records ORDER BY received_at DESC LIMIT 100",
            connection,
        )
    render_table(quarantined)

st.sidebar.divider()
st.sidebar.caption("IoT Pulse · Data Engineering Demo")
st.sidebar.caption("PostgreSQL · Parquet · DuckDB · Streamlit")
