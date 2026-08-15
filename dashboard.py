"""Streamlit interface for the Electricity Theft Detection API.

Start the API first:
    uvicorn src.api:app --reload --port 8000 --app-dir src

Then run:
    streamlit run dashboard.py
"""

import os
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="Electricity Theft & Anomaly Detection",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_API_URL = "http://127.0.0.1:8000"
API_BASE_URL = os.getenv("THEFT_API_URL", DEFAULT_API_URL).rstrip("/")


def run_scan_local_fallback(top_n: int, threshold: float = 0.5) -> dict:
    """Local fallback execution when backend API server is unreachable."""
    try:
        from src.models import TheftDetectionEnsemble
        from src.explain import ShapExplainer
        from src.features import build_feature_table
        from src.generate_data import generate
    except ImportError:
        raise RuntimeError("Local ML fallback dependencies missing.")

    data_path = Path("data/smart_meter_readings.csv")
    model_path = Path("models/theft_ensemble.joblib")
    feature_table_path = Path("models/feature_table.csv")

    if not model_path.exists() or not feature_table_path.exists():
        if not data_path.exists():
            os.makedirs("data", exist_ok=True)
            generate(out_path=str(data_path))
        df_readings = pd.read_csv(data_path, parse_dates=["date"], on_bad_lines="skip")
        feat_df = build_feature_table(df_readings)
        ensemble = TheftDetectionEnsemble()
        ensemble.fit(feat_df, feat_df["label"])
        os.makedirs("models", exist_ok=True)
        ensemble.save(str(model_path))
        feat_df.to_csv(feature_table_path, index=False)
    else:
        ensemble = TheftDetectionEnsemble.load(str(model_path))
        feat_df = pd.read_csv(feature_table_path, on_bad_lines="skip")

    explainer = ShapExplainer(ensemble)
    scored = ensemble.score(feat_df).sort_values("risk_score", ascending=False)
    top = scored.head(top_n)

    top_feats = feat_df.set_index("consumer_id").loc[top["consumer_id"]].reset_index()
    reasons = explainer.top_reasons(top_feats, k=3)

    results = []
    for (_, row), reason in zip(top.iterrows(), reasons):
        results.append({
            "consumer_id": row["consumer_id"],
            "transformer_id": row["transformer_id"],
            "risk_score": round(float(row["risk_score"]), 4),
            "supervised_prob": round(float(row["supervised_prob"]), 4),
            "anomaly_score": round(float(row["anomaly_score"]), 4),
            "reasons": reason,
        })

    return {
        "total_consumers": len(scored),
        "flagged_count": int((scored["risk_score"] >= threshold).sum()),
        "threshold": threshold,
        "results": results,
    }


def run_scan(top_n: int) -> dict:
    """Fetch ranked detection results from FastAPI or fallback to local ML engine."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/scan",
            params={"top_n": top_n},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return run_scan_local_fallback(top_n)


def as_percent(value: float) -> str:
    return f"{value:.1%}"


# Custom CSS for dark professional styling without decorative emojis
st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; }
        .stMetric { background-color: #1E293B; padding: 12px 18px; border-radius: 8px; border: 1px solid #334155; }
        .audit-card { background-color: #1E293B; border-left: 4px solid #06B6D4; padding: 12px 16px; margin-bottom: 10px; border-radius: 4px; }
        .reason-box { background-color: #0F172A; border: 1px solid #334155; padding: 10px 14px; margin-top: 6px; border-radius: 6px; color: #F8FAFC; }
    </style>
""", unsafe_allow_html=True)

st.title("Electricity Theft & Anomaly Detection System")
st.caption("Decision support platform for smart meter non-technical loss analytics and inspection triage.")

with st.sidebar:
    st.header("Scan Configuration")
    top_n = st.slider(
        "Top suspects to display",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
    )
    st.caption(f"Backend API: {API_BASE_URL}")
    scan_clicked = st.button("Run Threat Scan", type="primary", use_container_width=True)

# Run scan on button click or load state
if scan_clicked or "scan_data" not in st.session_state:
    try:
        with st.spinner("Analyzing consumption patterns..."):
            st.session_state.scan_data = run_scan(top_n)
            st.session_state.scan_top_n = top_n
    except Exception as exc:
        st.error(f"Scan failed: {exc}")

data = st.session_state.get("scan_data")
if not data:
    st.info("Adjust the scan size in the sidebar, then select Run Threat Scan.")
    st.stop()

results = data.get("results", [])
if not results:
    st.warning("The scan completed but returned no ranked suspect accounts.")
    st.stop()

# Key Metric Summaries
col1, col2, col3, col4 = st.columns(4)
col1.metric("Consumers Monitored", f"{data['total_consumers']:,}")
col2.metric("High-Risk Suspects Flagged", f"{data['flagged_count']:,}", delta="Requires Inspection", delta_color="inverse")
col3.metric("Current Population Displayed", f"{len(results):,}")
col4.metric("Risk Threshold", as_percent(data["threshold"]))

st.markdown("---")

df = pd.DataFrame(results)

# Create Navigation Tabs
tab_overview, tab_analytics, tab_inspector = st.tabs([
    "Threat Queue & Transformer Feeder Breakdown",
    "Dual-Signal Risk Analytics & Scatter",
    "Account Audit Inspector"
])

with tab_overview:
    left_col, right_col = st.columns([1.6, 1.0])
    
    with left_col:
        st.subheader("Ranked High-Risk Accounts")
        df_display = df[
            ["consumer_id", "transformer_id", "risk_score", "supervised_prob", "anomaly_score"]
        ].copy()
        df_display.columns = [
            "Consumer ID",
            "Transformer Zone",
            "Overall Risk Score",
            "Supervised Prob",
            "Anomaly Score",
        ]
        
        for col in ["Overall Risk Score", "Supervised Prob", "Anomaly Score"]:
            df_display[col] = df_display[col].map(as_percent)
            
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
        )

    with right_col:
        st.subheader("Suspects by Transformer Feeder")
        transformer_counts = (
            df["transformer_id"].value_counts().rename_axis("Transformer ID").reset_index(name="Suspect Count")
        )
        fig_trans = px.bar(
            transformer_counts,
            x="Transformer ID",
            y="Suspect Count",
            color="Suspect Count",
            color_continuous_scale="Reds",
            template="plotly_dark",
        )
        fig_trans.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_trans, use_container_width=True)

with tab_analytics:
    st.subheader("Dual-Signal Machine Learning Distribution")
    st.caption("Quadrant analysis comparing Supervised Theft Probability (XGBoost) vs. Unsupervised Anomaly Score (Isolation Forest).")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Scatter Plot: Supervised Prob vs Anomaly Score
        fig_scatter = px.scatter(
            df,
            x="supervised_prob",
            y="anomaly_score",
            color="risk_score",
            size="risk_score",
            hover_name="consumer_id",
            hover_data=["transformer_id", "risk_score"],
            color_continuous_scale="Viridis",
            labels={
                "supervised_prob": "Supervised ML Probability (XGBoost)",
                "anomaly_score": "Unsupervised Anomaly Score (Isolation Forest)",
                "risk_score": "Composite Risk Score"
            },
            title="Supervised Probability vs. Anomaly Score",
            template="plotly_dark"
        )
        fig_scatter.add_vline(x=0.5, line_dash="dash", line_color="#94A3B8")
        fig_scatter.add_hline(y=0.5, line_dash="dash", line_color="#94A3B8")
        fig_scatter.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_chart2:
        # Distribution Histogram of Overall Risk Scores
        fig_hist = px.histogram(
            df,
            x="risk_score",
            nbins=15,
            color_discrete_sequence=["#06B6D4"],
            labels={"risk_score": "Composite Risk Score"},
            title="Population Risk Score Histogram",
            template="plotly_dark"
        )
        fig_hist.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis_title="Consumer Count"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

with tab_inspector:
    st.subheader("Account Deep-Dive Audit Inspector")
    selected_consumer = st.selectbox(
        "Select a Consumer ID to inspect SHAP attributions and score components:",
        options=df["consumer_id"].tolist(),
    )
    
    consumer_row = df.loc[df["consumer_id"] == selected_consumer].iloc[0]
    
    col_insp_info, col_insp_chart = st.columns([1.2, 1.8])
    
    with col_insp_info:
        st.markdown(f"""
            <div class="audit-card">
                <h4 style="margin:0; color:#06B6D4;">Consumer ID: {consumer_row['consumer_id']}</h4>
                <p style="margin:4px 0; color:#94A3B8;">Transformer Feeder Zone: <b>{consumer_row['transformer_id']}</b></p>
                <p style="margin:4px 0; color:#F8FAFC;">Composite Risk Score: <b>{as_percent(consumer_row['risk_score'])}</b></p>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("**Automated SHAP Audit Reasons:**")
        reasons_list = consumer_row.get("reasons", [])
        if reasons_list:
            for r in reasons_list:
                st.markdown(f'<div class="reason-box">{r}</div>', unsafe_allow_html=True)
        else:
            st.info("No specific anomaly reasons flagged for this consumer.")

    with col_insp_chart:
        # Component comparison bar chart for selected consumer
        comp_df = pd.DataFrame({
            "Signal Metric": ["Supervised ML Prob", "Unsupervised Anomaly Score", "Composite Risk Score"],
            "Score Percentage": [
                consumer_row["supervised_prob"],
                consumer_row["anomaly_score"],
                consumer_row["risk_score"]
            ]
        })
        
        fig_comp = px.bar(
            comp_df,
            x="Signal Metric",
            y="Score Percentage",
            color="Signal Metric",
            color_discrete_map={
                "Supervised ML Prob": "#3B82F6",
                "Unsupervised Anomaly Score": "#10B981",
                "Composite Risk Score": "#F59E0B"
            },
            title=f"Risk Score Component Breakdown for {selected_consumer}",
            template="plotly_dark"
        )
        fig_comp.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            yaxis=dict(range=[0, 1.05], tickformat=".0%")
        )
        st.plotly_chart(fig_comp, use_container_width=True)
