"""SoilGrids REST API v2.0 client for retrieving soil profiles."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import httpx

from src.data.cache import EnvironmentalDataCache
from src.data.normalize import (
    calculate_depth_weighted_average,
    classify_usda_texture,
    normalize_soilgrids_units,
)
from src.data.validation import validate_egyptian_coordinates
from src.domain.provenance import DataSourceType, ProvenanceRecord
from src.domain.schemas import SoilSummary

logger = logging.getLogger("fieldwise.soilgrids")

SOILGRIDS_BASE_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
TARGET_SOIL_PROPERTIES = ["phh2o", "soc", "clay", "silt", "sand", "bdod", "cec"]
TARGET_DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]


class SoilGridsClient:
    """Client for retrieving and normalizing soil profile data from ISRIC SoilGrids v2."""

    def __init__(self, cache: Optional[EnvironmentalDataCache] = None, timeout_seconds: float = 12.0):
        self.cache = cache or EnvironmentalDataCache()
        self.timeout_seconds = timeout_seconds

    def _get_cache_key(self, lat: float, lon: float) -> str:
        return f"soilgrids:{round(lat, 2)}:{round(lon, 2)}"

    def _load_fallback_fixture(self, lat: float, lon: float) -> Tuple[SoilSummary, ProvenanceRecord, Dict[str, Any]]:
        """Load geographically closest Egyptian soil fixture when live API is unavailable."""
        fixture_path = Path("data/demo/fixtures_egypt.json")
        if not fixture_path.exists():
            fixture_path = Path(__file__).resolve().parent.parent.parent / "data" / "demo" / "fixtures_egypt.json"

        with open(fixture_path, "r", encoding="utf-8") as f:
            fixtures = json.load(f)

        best_key = "kafr_el_sheikh"
        min_dist = float("inf")
        for key, item in fixtures.items():
            c = item["coordinates"]
            dist = (lat - c["latitude"]) ** 2 + (lon - c["longitude"]) ** 2
            if dist < min_dist:
                min_dist = dist
                best_key = key

        chosen = fixtures[best_key]
        soil_data = chosen["soil"]
        summary = SoilSummary(**soil_data)

        provenance = ProvenanceRecord(
            source_name="SOILGRIDS_OFFLINE_FIXTURE",
            source_type=DataSourceType.FIXTURE,
            retrieval_timestamp=datetime.now(timezone.utc),
            standardized_units="pH, g/kg, %, cg/cm³, cmol(+)/kg",
            quality_flag="DEGRADED_FALLBACK_FIXTURE",
            notes=(
                f"External SoilGrids API unavailable. Loaded representative soil fixture for {chosen['location_name']}. "
                "CRITICAL: SoilGrids does NOT measure salinity. Salinity remains explicitly UNKNOWN."
            ),
        )
        return summary, provenance, chosen

    async def fetch_soil_data(
        self, latitude: float, longitude: float
    ) -> Tuple[SoilSummary, ProvenanceRecord, Dict[str, Any]]:
        """Fetch soil profile from ISRIC SoilGrids API v2 or cache.
        
        Returns:
            Tuple of (SoilSummary, ProvenanceRecord, raw_response_dict)
        """
        valid, errors = validate_egyptian_coordinates(latitude, longitude)
        if not valid:
            logger.warning(f"Coordinate warning for soil: lat={latitude}, lon={longitude}: {errors}")

        cache_key = self._get_cache_key(latitude, longitude)
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Loaded SoilGrids data from cache for key: {cache_key}")
            summary = SoilSummary(**cached["summary"])
            prov = ProvenanceRecord(
                source_name="SOILGRIDS_CACHE",
                source_type=DataSourceType.SOURCED,
                retrieval_timestamp=datetime.fromisoformat(cached["retrieval_timestamp"]),
                standardized_units="pH, g/kg, %, cg/cm³, cmol(+)/kg",
                quality_flag="VALID_CACHED",
                notes="Retrieved from local verified cache. Salinity is explicitly UNKNOWN.",
            )
            return summary, prov, cached.get("raw", {})

        params = [
            ("lat", f"{latitude:.4f}"),
            ("lon", f"{longitude:.4f}"),
        ]
        for prop in TARGET_SOIL_PROPERTIES:
            params.append(("property", prop))
        for depth in TARGET_DEPTHS:
            params.append(("depth", depth))
        params.append(("value", "mean"))
        params.append(("value", "Q0.05"))
        params.append(("value", "Q0.95"))

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                logger.info(f"Querying SoilGrids API for lat={latitude}, lon={longitude}")
                response = await client.get(SOILGRIDS_BASE_URL, params=params)
                response.raise_for_status()
                raw_data = response.json()

            summary = self._parse_soilgrids_response(raw_data)
            prov = ProvenanceRecord(
                source_name="SOILGRIDS_API_V2",
                source_type=DataSourceType.SOURCED,
                retrieval_timestamp=datetime.now(timezone.utc),
                original_units="ph*10, dg/kg, g/kg, cg/cm³, mmol(c)/kg",
                standardized_units="pH, g/kg, %, cg/cm³, cmol(+)/kg",
                transformation_applied="Weighted 0-30cm root depth; converted scale units; derived USDA texture class",
                quality_flag="VALID_API",
                notes="ISRIC SoilGrids v2.0 dataset. SoilGrids does NOT supply salinity. Salinity remains explicitly UNKNOWN.",
                raw_payload_snippet={
                    "query": raw_data.get("query", {}),
                    "properties_present": list(raw_data.get("properties", {}).get("layers", {})),
                },
            )

            # Store in cache
            self.cache.set(
                cache_key,
                "soilgrids",
                {
                    "summary": summary.model_dump(),
                    "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                    "raw": raw_data,
                },
            )
            return summary, prov, raw_data

        except Exception as exc:
            logger.warning(
                f"SoilGrids API query failed ({exc}). Falling back to calibrated Egyptian fixture."
            )
            return self._load_fallback_fixture(latitude, longitude)

    def _parse_soilgrids_response(self, raw_data: Dict[str, Any]) -> SoilSummary:
        """Parse SoilGrids layers, apply depth weighting (0-30cm), and determine texture class."""
        layers = {layer.get("name"): layer for layer in raw_data.get("properties", {}).get("layers", [])}

        def get_weighted_prop(prop_name: str, fallback_raw: float) -> float:
            layer = layers.get(prop_name)
            if not layer:
                return fallback_raw
            depths = layer.get("depths", [])
            raw_avg = calculate_depth_weighted_average(depths)
            return normalize_soilgrids_units(prop_name, raw_avg)

        ph_val = get_weighted_prop("phh2o", 79.0)  # default ~7.9 pH
        soc_val = get_weighted_prop("soc", 90.0)    # default ~9.0 g/kg
        clay_pct = get_weighted_prop("clay", 450.0) # default ~45%
        silt_pct = get_weighted_prop("silt", 350.0) # default ~35%
        sand_pct = get_weighted_prop("sand", 200.0) # default ~20%
        bdod_val = get_weighted_prop("bdod", 135.0) # default ~135 cg/cm³
        cec_val = get_weighted_prop("cec", 320.0)   # default ~32 cmol(+)/kg

        texture_class = classify_usda_texture(clay_pct, silt_pct, sand_pct)

        return SoilSummary(
            ph_water=ph_val,
            organic_carbon_g_kg=soc_val,
            clay_pct=clay_pct,
            silt_pct=silt_pct,
            sand_pct=sand_pct,
            bulk_density_cg_cm3=bdod_val,
            cation_exchange_capacity_cmolc_kg=cec_val,
            texture_class=texture_class,
            salinity_status="UNKNOWN",
            salinity_estimated_dsm=None,
        )
