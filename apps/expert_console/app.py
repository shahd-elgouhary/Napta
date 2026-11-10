"""FieldWise AI (Napta) - Expert Console

Streamlit application for agronomists, agricultural engineers, advisers, and judges.
Connects directly to the FastAPI backend and provides deep agronomic oversight.
"""

import requests
import streamlit as st

st.set_page_config(
    page_title="FieldWise AI - Expert Console",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Expert Agronomic Theme
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1B5E20;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #455A64;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F1F8E9;
        border-right: 4px solid #2E7D32;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-online { background-color: #C8E6C9; color: #1B5E20; }
    .status-offline { background-color: #FFCDD2; color: #B71C1C; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Backend Health Check
API_URL = "http://localhost:8000"
backend_healthy = False
backend_version = "Unknown"

try:
    res = requests.get(f"{API_URL}/health", timeout=2.0)
    if res.status_code == 200:
        backend_healthy = True
        backend_version = res.json().get("version", "1.0.0")
except Exception:
    backend_healthy = False

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/sprout.png", width=64)
    st.title("FieldWise AI — Egypt")
    st.caption("NASA Space Apps Challenge 2026")
    st.markdown("---")

    if backend_healthy:
        st.markdown(
            f'<div class="metric-card"><span class="status-badge status-online">● Backend API Connected</span><br><small>FastAPI v{backend_version}</small></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="metric-card"><span class="status-badge status-offline">○ Offline / Local Fixtures Mode</span><br><small>Running with calibrated offline data</small></div>',
            unsafe_allow_html=True,
        )

    st.markdown("### Navigation")
    st.info("Select a page from the sidebar above:\n- **1. Farm Overview**\n- **2. Sources**\n- **3. Voice Review**")
    st.markdown("---")
    st.caption("Track B: The Body (Backend, Data Engineering, Voice AI, Console)")

# Landing Page Hero
st.markdown('<div class="main-header">🌾 FieldWise AI — Expert Console</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Scientific Decision Engine & Environmental Intelligence Platform for Egyptian Agriculture</div>',
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌾 1. Farm Overview")
    st.write(
        "Inspect plot attributes, coordinates, soil chemical/physical composition (pH, texture, CEC, bulk density), "
        "and NASA POWER seasonal agroclimatology with data quality and missing-data indicators."
    )

with col2:
    st.markdown("### 🔬 2. Data Sources & Provenance")
    st.write(
        "Trace scientific lineage across NASA POWER and ISRIC SoilGrids. Review retrieval timestamps, "
        "uncertainty intervals (Q0.05 vs Q0.95), and the explicit absence of salinity data."
    )

with col3:
    st.markdown("### 🎙️ 3. Voice Review & Lexicon")
    st.write(
        "Audit Egyptian farmer spoken dialogue sessions. Review raw ASR transcripts vs. parsed structured slots, "
        "inspect confidence scores, and curate the versioned Fellahi agricultural dialect lexicon."
    )

st.markdown("---")
st.subheader("System Architecture: One Engine, Two Presentations")
st.markdown(
    """
```
                    ┌─────────────────────────────────────────────────────┐
                    │               FieldWise Decision Engine             │
                    │         (Deterministic Egyptian Agronomy)           │
                    └──────────┬───────────────────────────────┬──────────┘
                               │                               │
                               ▼                               ▼
               ┌──────────────────────────────┐ ┌──────────────────────────────┐
               │  Farmer Voice Assistant PWA  │ │  Expert Agronomist Console   │
               │   • Egyptian Arabic Dialect  │ │   • Multi-layer Soil Physics │
               │   • Voice-first & Tap Fallback│ │   • NASA POWER Climatology   │
               │   • 3 Plain Archetypes       │ │   • Data Provenance & Lineage│
               └──────────────────────────────┘ └──────────────────────────────┘
```
"""
)
