---
title: Electricity Theft & Anomaly Detection System
sdk: streamlit
app_file: dashboard.py
pinned: false
---

# Electricity Theft & Anomaly Detection System

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40-FF4B4B.svg)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ED.svg)](https://www.docker.com/)

An end-to-end decision support platform for power utility managers to flag suspicious smart-meter accounts, catch non-technical losses (NTL), and provide plain-English SHAP audit justifications for field inspection crews.

## Live Web Application

* **GitHub Pages Live Site:** [https://bshubhayu07.github.io/electricity_theft_nyx/](https://bshubhayu07.github.io/electricity_theft_nyx/)



## Why This Approach?

Standard tutorials train one classifier on confirmed theft labels and stop there. That fails in the real world for two reasons:
1. **Historical Theft Labels are Sparse & Biased:** Standard supervised models only learn what inspectors caught in the past, making them completely blind to novel ("zero-day") meter bypass tricks.
2. **Utilities Need Reasons, Not Black-Box Scores:** Field inspection crews are expensive to dispatch. Unexplained risk scores erode inspector trust and lead to wasted operational budgets.

### Dual-Signal Engine & XAI Architecture

| Signal | Engine / Model | What It Catches |
| **Supervised** | XGBoost (Class-Weighted) | Patterns matching past confirmed theft cases |
| **Unsupervised** | Isolation Forest | Novel ("zero-day") statistical anomalies with no past labels |
| **Explainability** | SHAP (TreeExplainer) | Human-readable audit reasons per flagged account |
| **Peer Comparison** | Transformer Z-Score & Correlation | Usage divergence from immediate neighbors on the same feeder (filters out cold weather) |

$$\text{Composite Risk Score} = 0.65 \times P_{\text{supervised}} + 0.35 \times \text{Score}_{\text{anomaly}}$$

Both risk components are reported separately so that an account with a high anomaly score but low supervised probability is triaged as *"Needs Human Review"* rather than making a false theft accusation.

---

## Running with Docker (Recommended)

The easiest way to launch the full-stack system (FastAPI Backend + Streamlit Dashboard) is using Docker Compose:

```bash
# 1. Clone the repository
git clone https://github.com/bshubhayu07/electricity_theft_nyx.git
cd electricity_theft_nyx

# 2. Build and start containers
docker-compose up --build
```

### Access Ports:
* **Interactive Dashboard (UI):** [http://localhost:8501](http://localhost:8501)
* **FastAPI Backend (Swagger API Docs):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

*(To stop the containers, press `Ctrl + C` or run `docker-compose down`)*

---

## Running Locally (Without Docker)

### 1. Prerequisites & Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2. Train Model Engine
Generates synthetic data (if missing in `data/`), engineers 15 domain features, trains the dual-signal ensemble, and saves artifacts to `models/`:
```bash
python -m src.train
```

### 3. Start Backend API
```bash
python -m uvicorn src.api:app --reload --port 8000
```

### 4. Start Operator Dashboard (In a New Terminal)
```bash
streamlit run dashboard.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Dashboard Visual Analytics (3 Navigation Tabs)

The Streamlit interface provides an interactive, professional visual analytics environment:

1. **Tab 1: Threat Queue & Transformer Feeder Breakdown:**
   * Interactive high-risk suspect dataframe.
   * Transformer feeder suspect count bar chart.
2. **Tab 2: Dual-Signal Risk Analytics & Scatter:**
   * **Supervised vs. Anomaly Scatter Quadrant Plot:** Compares XGBoost probability vs. Isolation Forest anomaly score with threshold quadrant lines.
   * **Population Risk Histogram:** Visual distribution of composite risk scores across the grid.
3. **Tab 3: Account Audit Inspector:**
   * **Individual Risk Component Bar Chart:** Side-by-side comparison of Supervised Prob, Anomaly Score, and Risk Score for any selected account.
   * **Automated SHAP Audit Reasons:** Highlights top drivers (e.g., *"14-day zero streak [+0.38]"*, *"Transformer z-score divergence +2.8 [+0.25]"*).

---

## API Endpoints

### `POST /scan`
Scans and ranks the grid population by risk score.
```bash
curl -X POST "http://127.0.0.1:8000/scan?top_n=10"
```

### `POST /score`
Ad-hoc scoring of raw consumption daily series.
```bash
curl -X POST http://127.0.0.1:8000/score -H "Content-Type: application/json" -d '{
  "consumer_id": "C_ADHOC_1",
  "dates": ["2024-01-01", "2024-01-02", "...at least 14 days..."],
  "consumption_kwh": [10.2, 9.8, "..."]
}'
```

---

## Project Structure

```
electricity_theft_nyx/
├── src/
│   ├── api.py               # FastAPI backend application & routes
│   ├── explain.py           # SHAP TreeExplainer & audit reason rules
│   ├── features.py          # 15 domain-engineered time-series features
│   ├── generate_data.py     # Synthetic smart-meter data generator
│   ├── models.py            # TheftDetectionEnsemble (XGBoost + Isolation Forest)
│   ├── schemas.py           # Pydantic request/response schemas
│   └── train.py             # End-to-end training & evaluation pipeline
├── dashboard.py             # Streamlit visual analytics frontend
├── Dockerfile               # Multi-stage Python 3.11 container setup
├── docker-compose.yml       # Orchestration for Backend (8000) & Frontend (8501)
├── generate_final_submission_deck.py # 12-slide PowerPoint presentation generator
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

---

## Public Benchmark Datasets

* **SGCC (State Grid Corporation of China):** Standard IEEE TII benchmark containing 42,372 consumers (3,615 theft cases). Reshape using `pandas.melt` and feed directly into `build_feature_table`.
* **PRECON:** Pakistan Residential Electricity Consumption dataset.
* **Irish CER:** High-frequency 30-minute interval smart-meter dataset.

---

## Real-World Operational Caveats

* **Synthetic vs. Real Noise:** Bundled synthetic data is cleanly separable; real grid data contains significantly more noise and yields lower ROC-AUC.
* **Feeder Topology Reliance:** Peer comparison assumes accurate transformer mapping. Corrupted topology data affects z-scores.
* **Decision Support:** Statistical anomalies can be vacant properties—the tool is designed for human-in-the-loop inspection triage, not automatic legal billing penalties.

---

## Presentation Decks Included

This repository includes automated script generators and generated presentation decks for hackathon pitches and final project submissions:
* [`Electricity_Theft_Detection_Final_Submission.pptx`](file:///c:/Users/User/Documents/electricity_theft/Electricity_Theft_Detection_Final_Submission.pptx) (12 Widescreen Slides)
* [`Electricity_Theft_Detection_Deck.pptx`](file:///c:/Users/User/Documents/electricity_theft/Electricity_Theft_Detection_Deck.pptx) (10 Widescreen Pitch Slides)
