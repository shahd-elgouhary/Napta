"""NASA POWER API client for fetching climatological and meteorological data."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import httpx

from src.data.cache import EnvironmentalDataCache
from src.data.validation import validate_egyptian_coordinates
from src.domain.provenance import DataSourceType, ProvenanceRecord
from src.domain.schemas import ClimateSummary

logger = logging.getLogger("fieldwise.nasa_power")

# NASA POWER Climatology point endpoint
NASA_POWER_CLIMATOLOGY_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
TARGET_PARAMETERS = ["T2M", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]


class NasaPowerClient:
    """Client for retrieving and normalizing climate data from NASA POWER."""

    def __init__(self, cache: Optional[EnvironmentalDataCache] = None, timeout_seconds: float = 12.0):
        self.cache = cache or EnvironmentalDataCache()
        self.timeout_seconds = timeout_seconds

    def _get_cache_key(self, lat: float, lon: float) -> str:
        """Round coordinates to 2 decimal places (~1.1 km) for caching."""
        return f"nasa_power:{round(lat, 2)}:{round(lon, 2)}"

    def _load_fallback_fixture(self, lat: float, lon: float) -> Tuple[ClimateSummary, ProvenanceRecord, Dict[str, Any]]:
        """Load geographically closest Egyptian fixture when live API is unavailable."""
        fixture_path = Path("data/demo/fixtures_egypt.json")
        if not fixture_path.exists():
            fixture_path = Path(__file__).resolve().parent.parent.parent / "data" / "demo" / "fixtures_egypt.json"

        with open(fixture_path, "r", encoding="utf-8") as f:
            fixtures = json.load(f)

        # Find closest fixture by euclidean distance
        best_key = "kafr_el_sheikh"
        min_dist = float("inf")
        for key, item in fixtures.items():
            c = item["coordinates"]
            dist = (lat - c["latitude"]) ** 2 + (lon - c["longitude"]) ** 2
            if dist < min_dist:
                min_dist = dist
                best_key = key

        chosen = fixtures[best_key]
        climate_data = chosen["climate"]
        summary = ClimateSummary(**climate_data)

        provenance = ProvenanceRecord(
            source_name="NASA_POWER_OFFLINE_FIXTURE",
            source_type=DataSourceType.FIXTURE,
            retrieval_timestamp=datetime.now(timezone.utc),
            standardized_units="°C, %, m/s, kWh/m²/day, mm",
            quality_flag="DEGRADED_FALLBACK_FIXTURE",
            notes=f"External NASA POWER API unavailable. Loaded representative fixture for {chosen['location_name']}.",
        )
        return summary, provenance, chosen

    async def fetch_climate_data(
        self, latitude: float, longitude: float
    ) -> Tuple[ClimateSummary, ProvenanceRecord, Dict[str, Any]]:
        """Fetch climatology from NASA POWER API or cached response.
        
        Returns:
            Tuple of (ClimateSummary, ProvenanceRecord, raw_response_dict)
        """
        valid, errors = validate_egyptian_coordinates(latitude, longitude)
        if not valid:
            logger.warning(f"Coordinate warning for lat={latitude}, lon={longitude}: {errors}")

        cache_key = self._get_cache_key(latitude, longitude)
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Loaded NASA POWER data from cache for key: {cache_key}")
            summary = ClimateSummary(**cached["summary"])
            prov = ProvenanceRecord(
                source_name="NASA_POWER_CACHE",
                source_type=DataSourceType.SOURCED,
                retrieval_timestamp=datetime.fromisoformat(cached["retrieval_timestamp"]),
                standardized_units="°C, %, m/s, kWh/m²/day, mm",
                quality_flag="VALID_CACHED",
                notes="Retrieved from local verified cache",
            )
            return summary, prov, cached.get("raw", {})

        params = {
            "parameters": ",".join(TARGET_PARAMETERS),
            "community": "AG",
            "longitude": f"{longitude:.4f}",
            "latitude": f"{latitude:.4f}",
            "format": "JSON",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                logger.info(f"Querying NASA POWER API for lat={latitude}, lon={longitude}")
                response = await client.get(NASA_POWER_CLIMATOLOGY_URL, params=params)
                response.raise_for_status()
                raw_data = response.json()

            summary = self._parse_nasa_response(raw_data)
            prov = ProvenanceRecord(
                source_name="NASA_POWER_API",
                source_type=DataSourceType.SOURCED,
                retrieval_timestamp=datetime.now(timezone.utc),
                original_units="°C, %, m/s, MJ/m²/day or kWh/m²/day, mm/day",
                standardized_units="°C, %, m/s, kWh/m²/day, mm",
                transformation_applied="Extracted monthly & annual climatological means; converted units where necessary",
                quality_flag="VALID_API",
                notes="NASA POWER agroclimatology climatology dataset",
                raw_payload_snippet={
                    "header": raw_data.get("header", {}),
                    "parameter_keys": list(raw_data.get("properties", {}).get("parameter", {}).keys()),
                },
            )

            # Store in cache
            self.cache.set(
                cache_key,
                "nasa_power",
                {
                    "summary": summary.model_dump(),
                    "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                    "raw": raw_data,
                },
            )
            return summary, prov, raw_data

        except Exception as exc:
            logger.warning(
                f"NASA POWER API request failed ({exc}). Falling back to calibrated Egyptian fixture."
            )
            return self._load_fallback_fixture(latitude, longitude)

    def _parse_nasa_response(self, raw_data: Dict[str, Any]) -> ClimateSummary:
        """Parse monthly and annual values from NASA POWER climatology JSON."""
        props = raw_data.get("properties", {}).get("parameter", {})

        def get_ann_val(param_name: str, fallback: float) -> float:
            vals = props.get(param_name, {})
            # NASA climatology usually has keys 'JAN'..'DEC' and 'ANN'
            ann = vals.get("ANN")
            if ann is not None and ann != -999.0:
                return float(ann)
            # Average monthly if ANN missing
            valid_months = [v for k, v in vals.items() if k != "ANN" and v != -999.0]
            if valid_months:
                return float(sum(valid_months) / len(valid_months))
            return fallback

        def get_season_temp(months: list[str], fallback: float) -> float:
            t2m_vals = props.get("T2M", {})
            season_vals = [t2m_vals.get(m) for m in months if t2m_vals.get(m) is not None and t2m_vals.get(m) != -999.0]
            if season_vals:
                return round(sum(season_vals) / len(season_vals), 2)
            return fallback

        ann_temp = round(get_ann_val("T2M", 22.0), 2)
        summer_temp = round(get_season_temp(["JUN", "JUL", "AUG"], ann_temp + 6.0), 2)
        winter_temp = round(get_season_temp(["DEC", "JAN", "FEB"], ann_temp - 7.0), 2)
        rh = round(get_ann_val("RH2M", 55.0), 2)
        ws = round(get_ann_val("WS2M", 3.5), 2)
        solar = round(get_ann_val("ALLSKY_SFC_SW_DWN", 5.5), 2)
        # PRECTOTCORR in climatology is often mm/day or mm/month; annual sum estimated
        precip_daily = get_ann_val("PRECTOTCORR", 0.08)
        annual_precip = round(precip_daily * 365.25 if precip_daily < 10.0 else precip_daily, 1)

        return ClimateSummary(
            annual_mean_temp_c=ann_temp,
            summer_mean_temp_c=summer_temp,
            winter_mean_temp_c=winter_temp,
            relative_humidity_pct=rh,
            wind_speed_ms=ws,
            solar_radiation_kwh_m2_day=solar,
            annual_precipitation_mm=annual_precip,
        )
