"""Data sources, provenance specifications, and lineage transparency endpoints."""

from typing import Dict, Any, List
from fastapi import APIRouter

router = APIRouter(prefix="/api/sources", tags=["Sources & Provenance"])


@router.get("")
async def get_all_data_sources() -> Dict[str, Any]:
    """Return scientific data sources, resolutions, lineage definitions, and caveats."""
    return {
        "sources": [
            {
                "id": "nasa_power",
                "name": "NASA Prediction of Worldwide Energy Resources (POWER)",
                "organization": "NASA Langley Research Center",
                "portal_url": "https://power.larc.nasa.gov/",
                "resolution": "0.5° x 0.5° latitude/longitude",
                "temporal_coverage": "1981 - near present (climatological & daily)",
                "variables": [
                    {
                        "code": "T2M",
                        "name": "Temperature at 2 Meters",
                        "units": "°C",
                        "description": "Daily and monthly average ambient air temperature.",
                    },
                    {
                        "code": "RH2M",
                        "name": "Relative Humidity at 2 Meters",
                        "units": "%",
                        "description": "Ratio of actual water vapor pressure to saturation pressure.",
                    },
                    {
                        "code": "WS2M",
                        "name": "Wind Speed at 2 Meters",
                        "units": "m/s",
                        "description": "Average wind velocity for evapotranspiration estimation.",
                    },
                    {
                        "code": "ALLSKY_SFC_SW_DWN",
                        "name": "All Sky Surface Shortwave Downward Irradiance",
                        "units": "kWh/m²/day",
                        "description": "Solar radiation energy reaching crop canopy.",
                    },
                    {
                        "code": "PRECTOTCORR",
                        "name": "Precipitation Corrected",
                        "units": "mm",
                        "description": "Precipitation estimates derived from MERRA-2 assimilation.",
                    },
                ],
                "status": "Active REST API with local offline caching",
            },
            {
                "id": "soilgrids",
                "name": "ISRIC SoilGrids v2.0",
                "organization": "International Soil Reference and Information Centre (ISRIC - World Soil Information)",
                "portal_url": "https://www.isric.org/explore/soilgrids",
                "resolution": "250m spatial grid",
                "standard_depths": ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"],
                "variables": [
                    {"code": "phh2o", "name": "Soil pH in H2O", "units": "pH unitless"},
                    {"code": "soc", "name": "Soil Organic Carbon", "units": "g/kg"},
                    {"code": "clay", "name": "Clay fraction", "units": "% (< 0.002 mm)"},
                    {"code": "silt", "name": "Silt fraction", "units": "% (0.002 - 0.05 mm)"},
                    {"code": "sand", "name": "Sand fraction", "units": "% (0.05 - 2.0 mm)"},
                    {"code": "bdod", "name": "Bulk Density of Fine Earth", "units": "cg/cm³"},
                    {"code": "cec", "name": "Cation Exchange Capacity", "units": "cmol(+)/kg"},
                ],
                "critical_caveat": (
                    "SoilGrids does NOT measure or predict soil salinity (ECe). "
                    "Salinity must NEVER be assumed safe. It is tracked as explicitly UNKNOWN."
                ),
            },
            {
                "id": "egypt_agricultural_benchmarks",
                "name": "Egyptian Agricultural Research Center & Ministry of Agriculture",
                "organization": "Agricultural Research Center (ARC) / MALR Egypt",
                "bulletins": [
                    "Crop Water Requirements and Irrigation Scheduling in Egypt (SWERI)",
                    "Agricultural Economics & Statistical Yearbooks (2023-2025)",
                    "National Wheat and Maize Productivity Programs",
                ],
            },
        ],
        "lineage_categories": {
            "sourced": "Directly fetched from validated external APIs (NASA POWER, SoilGrids).",
            "farmer": "Reported directly by the Egyptian farmer via voice utterance or tap fallback.",
            "estimated": "Empirically calculated using standard agronomic models (e.g. FAO-56, depth-weighted soil averages).",
            "simulated": "Generated via scenario stress-testing parameters.",
            "fixture": "Calibrated offline fallback datasets for demonstration when network is unavailable.",
            "unknown": "Properties that cannot be measured by satellite or global models (e.g. salinity).",
        },
    }
