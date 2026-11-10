"""Environmental data orchestration service combining NASA POWER and SoilGrids."""

import logging
from typing import Optional, Tuple
from src.data.cache import EnvironmentalDataCache
from src.data.nasa_power_client import NasaPowerClient
from src.data.soilgrids_client import SoilGridsClient
from src.data.validation import validate_egyptian_coordinates
from src.domain.schemas import EnvironmentSummary

logger = logging.getLogger("fieldwise.environment")


class EnvironmentService:
    """Orchestrates environmental data retrieval, provenance tracking, and quality validation."""

    def __init__(
        self,
        cache: Optional[EnvironmentalDataCache] = None,
        nasa_client: Optional[NasaPowerClient] = None,
        soil_client: Optional[SoilGridsClient] = None,
    ):
        self.cache = cache or EnvironmentalDataCache()
        self.nasa_client = nasa_client or NasaPowerClient(cache=self.cache)
        self.soil_client = soil_client or SoilGridsClient(cache=self.cache)

    async def get_environment_summary(
        self, latitude: float, longitude: float
    ) -> Tuple[EnvironmentSummary, dict]:
        """Retrieve unified environmental profile for Egyptian coordinates."""
        valid, warnings = validate_egyptian_coordinates(latitude, longitude)
        missing_data_warnings = list(warnings)

        # Retrieve climate
        climate_summary, climate_prov, raw_nasa = await self.nasa_client.fetch_climate_data(latitude, longitude)

        # Retrieve soil
        soil_summary, soil_prov, raw_soil = await self.soil_client.fetch_soil_data(latitude, longitude)

        # Strict domain rule: SoilGrids does NOT supply salinity. Must explicitly warn experts and farmers!
        missing_data_warnings.append(
            "Soil salinity is explicitly UNKNOWN (SoilGrids does not measure electrical conductivity ECe). "
            "Local soil test or well test is recommended if soil is reclaimed or in North Delta."
        )

        is_fixture = (
            climate_prov.quality_flag == "DEGRADED_FALLBACK_FIXTURE"
            or soil_prov.quality_flag == "DEGRADED_FALLBACK_FIXTURE"
        )
        if is_fixture:
            missing_data_warnings.append(
                "Notice: Retrieved from calibrated regional Egyptian fixture due to external API latency or offline mode."
            )

        summary = EnvironmentSummary(
            climate=climate_summary,
            soil=soil_summary,
            provenance=[climate_prov, soil_prov],
            missing_data_warnings=missing_data_warnings,
            is_fixture=is_fixture,
        )

        raw_combined = {
            "nasa_power_raw": raw_nasa,
            "soilgrids_raw": raw_soil,
        }

        return summary, raw_combined
