"""Streamlit interface for the Electricity Theft Detection API.

Start the API first:
    uvicorn src.api:app --reload --port 8000 --app-dir src

Then run:
    streamlit run dashboard.py
"""

import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


st.set_page_config(
    page_title="Electricity Theft Detection",
    page_icon="⚡",
    layout="wide",
)

DEFAULT_API_URL = "http://127.0.0.1:8000"
API_BASE_URL = os.getenv("THEFT_API_URL", DEFAULT_API_URL).rstrip("/")


def run_scan(top_n: int) -> dict:
    """Fetch the latest ranked detection results from the FastAPI service."""
    response = requests.post(
        f"{API_BASE_URL}/scan",
        params={"top_n": top_n},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def as_percent(value: float) -> str:
    return f"{value:.1%}"


st.title("⚡ Electricity Theft & Anomaly Detection")
st.caption("Decision support for prioritizing meter inspections. A risk flag is not proof of theft.")

with st.sidebar:
    st.header("Scan configuration")
    top_n = st.slider(
        "Top suspects to display",
        min_value=5,
        max_value=100,
        value=10,
        step=5,
    )
    st.caption(f"API: {API_BASE_URL}")
    scan_clicked = st.button("Run threat scan", type="primary", use_container_width=True)

if scan_clicked:
    try:
        with st.spinner("Analyzing consumption patterns…"):
            st.session_state.scan_data = run_scan(top_n)
            st.session_state.scan_top_n = top_n
    except requests.exceptions.ConnectionError:
        st.error(
            "Could not reach the API. Start Uvicorn on http://127.0.0.1:8000, "
            "or set THEFT_API_URL to its base URL."
        )
    except requests.exceptions.Timeout:
        st.error("The scan timed out after 30 seconds. Check that the API is responsive.")
    except requests.exceptions.HTTPError as exc:
        detail = exc.response.text
        try:
            detail = exc.response.json().get("detail", detail)
        except ValueError:
            pass
        st.error(f"The API returned {exc.response.status_code}: {detail}")
    except requests.exceptions.RequestException as exc:
        st.error(f"The scan request failed: {exc}")

data = st.session_state.get("scan_data")
if not data:
    st.info("Adjust the scan size in the sidebar, then select **Run threat scan**.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Consumers monitored", f"{data['total_consumers']:,}")
col2.metric("High-risk cases", f"{data['flagged_count']:,}", delta="Review required", delta_color="inverse")
col3.metric("Risk threshold", as_percent(data["threshold"]))

results = data.get("results", [])
if not results:
    st.warning("The API completed the scan but returned no ranked results.")
    st.stop()

df = pd.DataFrame(results)
df_display = df[
    ["consumer_id", "transformer_id", "risk_score", "supervised_prob", "anomaly_score"]
].copy()
df_display.columns = [
    "Consumer ID",
    "Transformer ID",
    "Overall risk score",
    "ML probability",
    "Anomaly score",
]

for column in ["Overall risk score", "ML probability", "Anomaly score"]:
    df_display[column] = df_display[column].map(as_percent)

left_col, right_col = st.columns([2, 1])
with left_col:
    displayed_count = st.session_state.get("scan_top_n", len(df))
    st.subheader(f"Top {displayed_count} ranked suspects")
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Overall risk score": st.column_config.TextColumn("Overall risk score"),
            "ML probability": st.column_config.TextColumn("ML probability"),
            "Anomaly score": st.column_config.TextColumn("Anomaly score"),
        },
    )

with right_col:
    st.subheader("Suspects by transformer")
    transformer_counts = (
        df["transformer_id"].value_counts().rename_axis("Transformer ID").reset_index(name="Suspect count")
    )
    fig = px.bar(
        transformer_counts,
        x="Transformer ID",
        y="Suspect count",
        color="Suspect count",
        color_continuous_scale="Reds",
    )
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("🔍 Automated audit reasons")
selected_consumer = st.selectbox(
    "Select a consumer ID to view audit logs",
    options=df["consumer_id"].tolist(),
)
consumer_data = df.loc[df["consumer_id"] == selected_consumer].iloc[0]
st.info(
    f"**Transformer zone:** {consumer_data['transformer_id']}\n\n"
    f"**Calculated risk:** {as_percent(consumer_data['risk_score'])}"
)
st.write("**Flagged anomalies**")
for reason in consumer_data.get("reasons", []):
    st.write(f"🛑 {reason}")
