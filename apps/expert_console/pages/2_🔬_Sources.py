"""Expert Console — Page 2: Scientific Data Sources & Provenance."""

import requests
import streamlit as st

st.set_page_config(page_title="Sources & Lineage — FieldWise AI", page_icon="🔬", layout="wide")

st.title("🔬 Scientific Data Sources & Lineage Transparency")
st.caption("Traceability, data transformations, uncertainty quantification, and provenance audit for NASA and SoilGrids.")

API_BASE = "http://localhost:8000"

# Fetch data sources from API
sources_data = {}
try:
    res = requests.get(f"{API_BASE}/api/sources", timeout=3.0)
    if res.status_code == 200:
        sources_data = res.json()
except Exception:
    pass

st.markdown("### 🏷️ Lineage Classification Standard")
st.markdown(
    """
Every variable and calculation within FieldWise AI carries an explicit provenance tag to distinguish 
empirically measured data from farmer declarations and model simulations:
"""
)

lcol1, lcol2, lcol3, lcol4, lcol5, lcol6 = st.columns(6)
lcol1.info("**SOURCED**\n\nFetched from NASA POWER or SoilGrids API.")
lcol2.success("**FARMER**\n\nProvided directly by the farmer via voice/tap.")
lcol3.warning("**ESTIMATED**\n\nDerived via FAO-56 or depth weighting.")
lcol4.error("**UNKNOWN**\n\nUnmeasured variables (e.g. salinity).")
lcol5.info("**SIMULATED**\n\nScenario stress-testing recalculations.")
lcol6.secondary = lcol6.markdown("**FIXTURE**\n\nOffline calibrated regional dataset.")

st.markdown("---")

# 1. NASA POWER Documentation
st.subheader("🛰️ 1. NASA Prediction of Worldwide Energy Resources (POWER)")
st.markdown(
    """
- **Source Agency:** NASA Langley Research Center (LaRC)
- **Dataset:** Daily and Climatological Agroclimatology (AG) Point API
- **Spatial Resolution:** 0.5° x 0.5° latitude/longitude (~50 km)
- **Meteorological Base Model:** MERRA-2 assimilation model
- **API Endpoint:** `https://power.larc.nasa.gov/api/temporal/climatology/point`
"""
)

st.markdown("#### Parameter Specifications & Transformations")
nasa_table = [
    {"Variable": "T2M", "Name": "Air Temperature at 2m", "NASA Unit": "°C", "FieldWise Unit": "°C", "Transformation": "Extracted annual & seasonal averages"},
    {"Variable": "RH2M", "Name": "Relative Humidity at 2m", "NASA Unit": "%", "FieldWise Unit": "%", "Transformation": "Direct climatological mean"},
    {"Variable": "WS2M", "Name": "Wind Speed at 2m", "NASA Unit": "m/s", "FieldWise Unit": "m/s", "Transformation": "Direct climatological mean for ETo calculation"},
    {"Variable": "ALLSKY_SFC_SW_DWN", "Name": "Shortwave Solar Radiation", "NASA Unit": "MJ/m²/day", "FieldWise Unit": "kWh/m²/day", "Transformation": "Converted 1 MJ = 0.2778 kWh"},
    {"Variable": "PRECTOTCORR", "Name": "Precipitation Corrected", "NASA Unit": "mm/day", "FieldWise Unit": "mm/year", "Transformation": "Annualized sum (MERRA-2 corrected)"},
]
st.dataframe(nasa_table, use_container_width=True)

st.markdown("---")

# 2. SoilGrids ISRIC Documentation
st.subheader("🌱 2. ISRIC SoilGrids v2.0 Global Soil Information")
st.markdown(
    """
- **Source Agency:** International Soil Reference and Information Centre (ISRIC - World Soil Information, Wageningen)
- **Spatial Resolution:** 250m global spatial grid
- **Standard Depth Intervals:** 0-5cm, 5-15cm, 15-30cm, 30-60cm, 60-100cm, 100-200cm
- **API Endpoint:** `https://rest.isric.org/soilgrids/v2.0/properties/query`
"""
)

st.markdown("#### Parameter Specifications & Depth Weighting (0-30cm)")
soil_table = [
    {"Property": "phh2o", "Description": "Soil pH in H2O", "SoilGrids Raw": "pH * 10", "FieldWise Standard": "pH unitless", "Scale Factor": "/ 10.0"},
    {"Property": "soc", "Description": "Soil Organic Carbon", "SoilGrids Raw": "dg/kg (decigrams)", "FieldWise Standard": "g/kg", "Scale Factor": "/ 10.0"},
    {"Property": "clay", "Description": "Clay Fraction (< 0.002 mm)", "SoilGrids Raw": "g/kg", "FieldWise Standard": "%", "Scale Factor": "/ 10.0"},
    {"Property": "silt", "Description": "Silt Fraction (0.002-0.05 mm)", "SoilGrids Raw": "g/kg", "FieldWise Standard": "%", "Scale Factor": "/ 10.0"},
    {"Property": "sand", "Description": "Sand Fraction (0.05-2.0 mm)", "SoilGrids Raw": "g/kg", "FieldWise Standard": "%", "Scale Factor": "/ 10.0"},
    {"Property": "bdod", "Description": "Bulk Density of Fine Earth", "SoilGrids Raw": "cg/cm³", "FieldWise Standard": "cg/cm³", "Scale Factor": "Direct"},
    {"Property": "cec", "Description": "Cation Exchange Capacity", "SoilGrids Raw": "mmol(c)/kg", "FieldWise Standard": "cmol(+)/kg", "Scale Factor": "/ 10.0"},
]
st.dataframe(soil_table, use_container_width=True)

# 3. Explicit Salinity Absence Notice
st.error(
    "### 🚫 Scientific Integrity: The Salinity Constraint\n\n"
    "**Crucial Finding:** ISRIC SoilGrids does NOT measure or predict electrical conductivity (ECe) or soil salinity. "
    "Under no circumstances does FieldWise AI invent or assume soil salinity to be safe. "
    "In all schemas, database records, and UI displays, salinity is marked strictly as **UNKNOWN**, "
    "with actionable recommendations for farmers in high-salinity zones (e.g. North Delta lagoons, Siwa Oasis, and reclaimed desert soils) "
    "to obtain an empirical local laboratory or portable EC meter reading."
)

st.markdown("---")

# 4. Egyptian National Benchmark Sources
st.subheader("🏛️ 3. Egyptian Agronomic Research Benchmarks")
st.markdown(
    """
Field economic and water consumption coefficients are calibrated strictly using:
1. **Egyptian Ministry of Agriculture and Land Reclamation (MALR):** Annual Agricultural Statistics and Cost Bulletins (2023-2025).
2. **Agricultural Research Center (ARC) — Soils, Water and Environment Research Institute (SWERI):** National Irrigation and Evapotranspiration Guide for Egyptian Crops.
3. **General Authority for Supply Commodities (GASC):** Official guaranteed procurement prices for Egyptian wheat and strategic crops.
"""
)
