"""Expert Console — Page 1: Farm Overview."""

import json
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Farm Overview — FieldWise AI", page_icon="🌾", layout="wide")

st.title("🌾 Farm & Environmental Overview")
st.caption("Comprehensive physical, chemical, and climatological assessment for Egyptian agricultural plots.")

API_BASE = "http://localhost:8000"

# Select demo farm or enter custom GPS coordinates
st.sidebar.header("Plot Selection")
farm_choice = st.sidebar.selectbox(
    "Choose Representative Plot:",
    [
        "Kafr El-Sheikh (كفر الشيخ - دلتا النيل)",
        "Minya (المنيا - مصر الوسطى)",
        "New Valley (الوادي الجديد - واحة الخارجة)",
        "Custom Coordinates (إحداثيات مخصصة)",
    ],
)

presets = {
    "Kafr El-Sheikh (كفر الشيخ - دلتا النيل)": {
        "lat": 31.11, "lon": 30.94, "area_feddans": 3.0, "area_qirats": 0.0,
        "water_source": "Canal with Rotation Schedule (ترعة بالمناوبة)",
        "history": ["Wheat (قمح)", "Berseem (برسيم)", "Rice (أرز)"],
        "budget": 45000,
    },
    "Minya (المنيا - مصر الوسطى)": {
        "lat": 28.11, "lon": 30.75, "area_feddans": 5.0, "area_qirats": 12.0,
        "water_source": "Continuous Branch Canal (ترعة مستمرة)",
        "history": ["Maize (ذرة)", "Wheat (قمح)"],
        "budget": 75000,
    },
    "New Valley (الوادي الجديد - واحة الخارجة)": {
        "lat": 25.45, "lon": 30.55, "area_feddans": 10.0, "area_qirats": 0.0,
        "water_source": "Deep Groundwater Well (بئر ارتوازي)",
        "history": ["Fava Beans (فول بلدي)", "Dates / Alfalfa"],
        "budget": 120000,
    },
}

if farm_choice in presets:
    p = presets[farm_choice]
    lat = p["lat"]
    lon = p["lon"]
    area_feddans = p["area_feddans"]
    area_qirats = p["area_qirats"]
    water_source = p["water_source"]
    history = p["history"]
    budget = p["budget"]
else:
    lat = st.sidebar.number_input("Latitude (°N)", 22.0, 31.8, 30.04)
    lon = st.sidebar.number_input("Longitude (°E)", 24.7, 36.9, 31.23)
    area_feddans = st.sidebar.number_input("Area (Feddans)", 0.5, 500.0, 3.0)
    area_qirats = st.sidebar.number_input("Area (Qirats)", 0.0, 24.0, 0.0)
    water_source = st.sidebar.selectbox("Water Source", ["canal_rotation", "groundwater_well", "canal_continuous"])
    history = ["Wheat", "Maize"]
    budget = 50000

total_feddans = round(area_feddans + (area_qirats / 24.0), 2)

# Fetch environmental summary from API or fallback fixture
env_data = None
try:
    res = requests.get(f"{API_BASE}/api/environment/point?lat={lat}&lon={lon}", timeout=3.0)
    if res.status_code == 200:
        env_data = res.json()
except Exception:
    pass

if not env_data:
    # Load fallback fixture
    fixture_path = Path("data/demo/fixtures_egypt.json")
    if fixture_path.exists():
        with open(fixture_path, "r", encoding="utf-8") as f:
            fixtures = json.load(f)
        key = "kafr_el_sheikh" if "Kafr" in farm_choice else "minya" if "Minya" in farm_choice else "new_valley"
        env_data = fixtures.get(key, fixtures["kafr_el_sheikh"])

# 1. Farm Overview Metrics Bar
st.markdown("### 📍 Plot Identity & Baseline Resources")
mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
mcol1.metric("Location", farm_choice.split(" ")[0])
mcol2.metric("GPS Coordinates", f"{lat:.2f}°N, {lon:.2f}°E")
mcol3.metric("Total Area", f"{total_feddans} Feddans", help="1 Feddan = 4,200.83 m² = 24 Qirats")
mcol4.metric("Water System", water_source.split(" ")[0])
mcol5.metric("Available Budget", f"{budget:,.0f} EGP")

st.markdown("---")

# 2. Missing Data & Salinity Warning
st.markdown("### ⚠️ Data Quality & Scientific Caveats")
warnings = env_data.get("missing_data_warnings", [])
for w in warnings:
    st.warning(f"⚠️ {w}")

st.info(
    "**Salinity Policy:** SoilGrids does NOT measure or predict electrical conductivity (ECe). "
    "FieldWise marks salinity strictly as **UNKNOWN**. Farmers in North Delta and reclaimed desert "
    "are advised to perform electrical conductivity soil tests before planting sensitive crops."
)

st.markdown("---")

# 3. Two-Column Environmental Diagnostic
col_soil, col_climate = st.columns(2)

with col_soil:
    st.subheader("🧪 Soil Physical & Chemical Profile")
    soil = env_data.get("soil", {})

    scol1, scol2, scol3 = st.columns(3)
    scol1.metric("Soil pH (H2O)", f"{soil.get('ph_water', 7.9):.2f}")
    scol2.metric("Organic Carbon", f"{soil.get('organic_carbon_g_kg', 10.0):.1f} g/kg")
    scol3.metric("Bulk Density", f"{soil.get('bulk_density_cg_cm3', 135):.0f} cg/cm³")

    st.markdown(f"**USDA Texture Classification:** `{soil.get('texture_class', 'Clay')}`")
    st.markdown(f"**Salinity Status:** `{soil.get('salinity_status', 'UNKNOWN')}`")

    # Soil Texture Donut Chart
    clay = soil.get("clay_pct", 45.0)
    silt = soil.get("silt_pct", 35.0)
    sand = soil.get("sand_pct", 20.0)

    fig_texture = px.pie(
        values=[clay, silt, sand],
        names=["Clay (طين)", "Silt (غرين)", "Sand (رمل)"],
        title="Soil Texture Fractions (0-30cm Depth-Weighted)",
        hole=0.45,
        color_discrete_sequence=["#2E7D32", "#81C784", "#FFF59D"],
    )
    fig_texture.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_texture, use_container_width=True)

with col_climate:
    st.subheader("☀️ NASA POWER Climatology (Agroclimatology)")
    climate = env_data.get("climate", {})

    ccol1, ccol2, ccol3 = st.columns(3)
    ccol1.metric("Annual Mean Temp", f"{climate.get('annual_mean_temp_c', 21.0)} °C")
    ccol2.metric("Summer Mean", f"{climate.get('summer_mean_temp_c', 28.5)} °C")
    ccol3.metric("Winter Mean", f"{climate.get('winter_mean_temp_c', 13.5)} °C")

    ccol4, ccol5, ccol6 = st.columns(3)
    ccol4.metric("Relative Humidity", f"{climate.get('relative_humidity_pct', 65.0):.1f}%")
    ccol5.metric("Solar Radiation", f"{climate.get('solar_radiation_kwh_m2_day', 5.5):.1f} kWh/m²/d")
    ccol6.metric("Annual Rainfall", f"{climate.get('annual_precipitation_mm', 45.0):.0f} mm")

    # Temperature and Solar Bar Chart
    fig_climate = go.Figure(data=[
        go.Bar(
            name="Mean Temp (°C)",
            x=["Winter Mean", "Annual Mean", "Summer Mean"],
            y=[
                climate.get("winter_mean_temp_c", 13.5),
                climate.get("annual_mean_temp_c", 21.0),
                climate.get("summer_mean_temp_c", 28.5),
            ],
            marker_color="#FF9800",
        ),
    ])
    fig_climate.update_layout(
        title="Thermal Profile Across Egyptian Seasons",
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig_climate, use_container_width=True)

st.markdown("---")

# 4. Crop History & Previous Sequences
st.subheader("🌱 Plot Rotation History & Preceding Crops")
st.write(f"**Previous crops cultivated on this plot:** {', '.join(history)}")
st.caption("Preceding crops are evaluated by the decision engine to prevent pest buildup and preserve soil nitrogen balance.")
