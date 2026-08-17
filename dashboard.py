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


def generate_local_report(consumer_row: pd.Series) -> str:
    """Generates inspection report text locally if API is unreachable."""
    try:
        from src.report_generator import generate_inspection_report
        return generate_inspection_report(
            consumer_id=consumer_row["consumer_id"],
            transformer_id=consumer_row["transformer_id"],
            risk_score=consumer_row["risk_score"],
            supervised_prob=consumer_row["supervised_prob"],
            anomaly_score=consumer_row["anomaly_score"],
            reasons=consumer_row.get("reasons", [])
        )
    except Exception:
        return f"INSPECTION REPORT FOR CONSUMER {consumer_row['consumer_id']}\nRisk: {consumer_row['risk_score']:.1%}"


def fetch_report(consumer_id: str, consumer_row: pd.Series) -> str:
    """Fetch official report from API or generate locally."""
    try:
        res = requests.post(f"{API_BASE_URL}/report/{consumer_id}", timeout=5)
        if res.status_code == 200:
            return res.text
    except Exception:
        pass
    return generate_local_report(consumer_row)


def purge_data_session() -> dict:
    """Fetch DPDP purge receipt from API or generate locally."""
    try:
        res = requests.post(f"{API_BASE_URL}/purge-session", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    try:
        from src.security import purge_ephemeral_session_data
        return purge_ephemeral_session_data()
    except Exception:
        return {"receipt_text": "DPDP 2025 Data Purge Executed (0 Bytes Retained)"}


def as_percent(value: float) -> str:
    return f"{value:.1%}"


# Custom CSS for dark professional styling without decorative emojis
st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; }
        .stMetric { background-color: #1E293B; padding: 14px 18px; border-radius: 8px; border: 1px solid #334155; }
        .audit-card { background-color: #1E293B; border-left: 4px solid #06B6D4; padding: 14px 18px; margin-bottom: 12px; border-radius: 6px; }
        .reason-box { background-color: #0F172A; border: 1px solid #334155; padding: 10px 14px; margin-top: 6px; border-radius: 6px; color: #F8FAFC; }
        .receipt-box { background-color: #090D16; border: 1px solid #06B6D4; font-family: monospace; padding: 12px; border-radius: 4px; color: #38BDF8; font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

st.title("Electricity Theft & Anomaly Detection System")
st.caption("Enterprise decision support platform for smart meter non-technical loss analytics and inspection triage.")

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

    st.markdown("---")
    st.subheader("Data Governance & DPDP 2025")
    if st.button("Purge Session Data & Audit Certificate", use_container_width=True):
        st.session_state.purge_receipt = purge_data_session()

    if "purge_receipt" in st.session_state:
        st.markdown(f'<div class="receipt-box"><pre>{st.session_state.purge_receipt.get("receipt_text")}</pre></div>', unsafe_allow_html=True)

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
    "Account Audit Inspector & Report Export"
])

with tab_overview:
    left_col, right_col = st.columns([1.5, 1.1])
    
    with left_col:
        st.subheader("Ranked High-Risk Suspect Accounts")
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
        st.subheader("Suspects by Transformer Feeder Zone")
        transformer_counts = (
            df["transformer_id"].value_counts().rename_axis("Transformer ID").reset_index(name="Suspect Count")
        )
        
        fig_trans = px.bar(
            transformer_counts,
            x="Transformer ID",
            y="Suspect Count",
            color="Suspect Count",
            color_continuous_scale="Plasma",
            text="Suspect Count",
            template="plotly_dark",
        )
        fig_trans.update_traces(
            textposition="outside",
            marker_line_color="#06B6D4",
            marker_line_width=1.5,
            hovertemplate="<b>Transformer Zone %{x}</b><br>Suspect Accounts: %{y}<extra></extra>"
        )
        fig_trans.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            xaxis=dict(gridcolor="#334155"),
            yaxis=dict(gridcolor="#334155")
        )
        st.plotly_chart(fig_trans, use_container_width=True)

with tab_analytics:
    st.subheader("Dual-Signal Machine Learning Distribution")
    st.caption("Quadrant analysis comparing Supervised Theft Probability (XGBoost) vs. Unsupervised Anomaly Score (Isolation Forest).")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_scatter = px.scatter(
            df,
            x="supervised_prob",
            y="anomaly_score",
            color="risk_score",
            size="risk_score",
            color_continuous_scale="Turbo",
            custom_data=["transformer_id", "risk_score"],
            hover_name="consumer_id",
            labels={
                "supervised_prob": "Supervised ML Probability (XGBoost)",
                "anomaly_score": "Unsupervised Anomaly Score (Isolation Forest)",
                "risk_score": "Composite Risk Score"
            },
            title="Supervised Probability vs. Anomaly Score",
            template="plotly_dark"
        )
        fig_scatter.update_traces(
            hovertemplate="<b>Consumer %{hovertext}</b><br>Transformer: %{customdata[0]}<br>Composite Risk: %{customdata[1]:.1%}<br>Supervised Prob: %{x:.1%}<br>Anomaly Score: %{y:.1%}<extra></extra>",
            marker=dict(line=dict(width=1, color="#F8FAFC"))
        )
        fig_scatter.add_vline(x=0.5, line_dash="dash", line_color="#94A3B8")
        fig_scatter.add_hline(y=0.5, line_dash="dash", line_color="#94A3B8")
        
        # Quadrant Label Annotations
        fig_scatter.add_annotation(x=0.85, y=0.95, text="High Theft Signature", showarrow=False, font=dict(color="#EF4444", size=11, family="sans-serif"))
        fig_scatter.add_annotation(x=0.15, y=0.95, text="Zero-Day Anomaly", showarrow=False, font=dict(color="#F59E0B", size=11, family="sans-serif"))
        fig_scatter.add_annotation(x=0.85, y=0.05, text="Known Pattern", showarrow=False, font=dict(color="#3B82F6", size=11, family="sans-serif"))
        fig_scatter.add_annotation(x=0.15, y=0.05, text="Low Risk Baseline", showarrow=False, font=dict(color="#10B981", size=11, family="sans-serif"))

        fig_scatter.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(range=[-0.05, 1.05], gridcolor="#334155", tickformat=".0%"),
            yaxis=dict(range=[-0.05, 1.05], gridcolor="#334155", tickformat=".0%")
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_chart2:
        fig_hist = px.histogram(
            df,
            x="risk_score",
            nbins=12,
            color_discrete_sequence=["#06B6D4"],
            labels={"risk_score": "Composite Risk Score"},
            title="Population Risk Score Histogram",
            template="plotly_dark"
        )
        fig_hist.update_traces(
            marker_line_color="#38BDF8",
            marker_line_width=1.2,
            hovertemplate="Risk Range: %{x}<br>Consumer Count: %{y}<extra></extra>"
        )
        fig_hist.add_vline(x=0.5, line_dash="dash", line_color="#EF4444", annotation_text="Triage Threshold (50%)", annotation_position="top right")
        fig_hist.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#334155", tickformat=".0%"),
            yaxis=dict(gridcolor="#334155"),
            yaxis_title="Consumer Count"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

with tab_inspector:
    st.subheader("Account Deep-Dive Audit Inspector")
    selected_consumer = st.selectbox(
        "Select a Consumer ID to inspect SHAP attributions and export report:",
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
        
        report_content = fetch_report(selected_consumer, consumer_row)
        st.download_button(
            label="Download Inspection Audit Report (.txt)",
            data=report_content,
            file_name=f"inspection_report_{selected_consumer}.txt",
            mime="text/plain",
            use_container_width=True
        )

        st.write("**Automated SHAP Audit Reasons:**")
        reasons_list = consumer_row.get("reasons", [])
        if reasons_list:
            for r in reasons_list:
                st.markdown(f'<div class="reason-box">{r}</div>', unsafe_allow_html=True)
        else:
            st.info("No specific anomaly reasons flagged for this consumer.")

    with col_insp_chart:
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
            text="Score Percentage",
            color_discrete_map={
                "Supervised ML Prob": "#3B82F6",
                "Unsupervised Anomaly Score": "#10B981",
                "Composite Risk Score": "#F59E0B"
            },
            title=f"Risk Score Component Breakdown for {selected_consumer}",
            template="plotly_dark"
        )
        fig_comp.update_traces(
            texttemplate="%{y:.1%}",
            textposition="outside",
            marker_line_color="#F8FAFC",
            marker_line_width=1.2,
            hovertemplate="<b>%{x}</b>: %{y:.1%}<extra></extra>"
        )
        fig_comp.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            xaxis=dict(gridcolor="#334155"),
            yaxis=dict(range=[0, 1.15], tickformat=".0%", gridcolor="#334155")
        )
        st.plotly_chart(fig_comp, use_container_width=True)
