"""Recommendation orchestration service connecting farm profiles to the decision engine."""

from datetime import datetime, timezone
from typing import Optional, Tuple
from src.data.environment_service import EnvironmentService
from src.domain.schemas import FarmProfile, RecommendationResponse
from src.services.decision_engine_adapter import DecisionEngineAdapter


class RecommendationService:
    """Coordinates environmental retrieval and agricultural plan generation."""

    def __init__(
        self,
        env_service: Optional[EnvironmentService] = None,
        engine_adapter: Optional[DecisionEngineAdapter] = None,
    ):
        self.env_service = env_service or EnvironmentService()
        self.engine_adapter = engine_adapter or DecisionEngineAdapter()

    async def get_recommendations_for_farm(
        self, profile: FarmProfile
    ) -> Tuple[RecommendationResponse, dict]:
        """Generate comprehensive 3-plan recommendations for a given farm profile."""
        env_summary, raw_env = await self.env_service.get_environment_summary(
            latitude=profile.coordinates.latitude,
            longitude=profile.coordinates.longitude,
        )

        plans = self.engine_adapter.generate_recommendations(profile=profile, env=env_summary)

        response = RecommendationResponse(
            farm_id=profile.farm_id or "farm_egypt_01",
            farm_location=profile.location_name,
            total_feddans=profile.area.total_feddans,
            environment_summary=env_summary,
            recommendations=plans,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        audit_data = {
            "profile": profile.model_dump(),
            "raw_environment": raw_env,
            "generated_plans_count": len(plans),
        }

        return response, audit_data
