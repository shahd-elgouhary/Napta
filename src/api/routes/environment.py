"""Environmental data retrieval endpoints."""

from fastapi import APIRouter, Query, status
from src.data.environment_service import EnvironmentService
from src.domain.schemas import EnvironmentSummary, FarmCoordinates

router = APIRouter(prefix="/api/environment", tags=["Environmental Data"])
env_service = EnvironmentService()


@router.get("/point", response_model=EnvironmentSummary)
async def get_environment_by_point(
    lat: float = Query(..., ge=21.0, le=32.0, description="Latitude in Egypt"),
    lon: float = Query(..., ge=24.0, le=37.0, description="Longitude in Egypt"),
):
    """Retrieve climatological and soil profiles for any coordinate point in Egypt."""
    summary, _ = await env_service.get_environment_summary(latitude=lat, longitude=lon)
    return summary


@router.post("", response_model=EnvironmentSummary)
async def get_environment_by_coordinates(coords: FarmCoordinates):
    """Retrieve environmental profile using coordinate schema."""
    summary, _ = await env_service.get_environment_summary(
        latitude=coords.latitude, longitude=coords.longitude
    )
    return summary
