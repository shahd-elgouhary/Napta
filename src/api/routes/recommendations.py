"""Crop recommendations and suitability calculation endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from src.domain.schemas import CropProfile, FarmProfile, Plan, RecommendationResponse
from src.services.decision_engine_adapter import DecisionEngineAdapter
from src.services.recommendation_service import RecommendationService

router = APIRouter(tags=["Recommendations & Decision Engine"])
rec_service = RecommendationService()
engine_adapter = DecisionEngineAdapter()


class SuitabilityRequest(BaseModel):
    farm_profile: FarmProfile
    crop_id: str


class SuitabilityResponse(BaseModel):
    crop_id: str
    crop_name_ar: str
    crop_name_en: str
    suitability_score: float
    limiting_factors: List[str]
    water_requirement_m3_per_feddan: float


@router.get("/api/crops", response_model=List[CropProfile])
async def list_supported_crops():
    """List benchmarked Egyptian crops supported by the decision engine."""
    return engine_adapter.get_all_crop_profiles()


@router.post("/api/recommendations", response_model=RecommendationResponse)
async def generate_recommendations(profile: FarmProfile):
    """Generate the three distinct recommendation plans (الأكسب, الأوفر في المية, الأأمن)."""
    response, _ = await rec_service.get_recommendations_for_farm(profile)
    return response


@router.post("/api/suitability", response_model=SuitabilityResponse)
async def check_crop_suitability(payload: SuitabilityRequest):
    """Evaluate specific crop suitability against farm environmental conditions."""
    crop = engine_adapter.get_crop_profile(payload.crop_id)
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{payload.crop_id}' not found in catalog.")

    env_summary, _ = await rec_service.env_service.get_environment_summary(
        payload.farm_profile.coordinates.latitude,
        payload.farm_profile.coordinates.longitude,
    )

    score = engine_adapter.calculate_suitability(crop, env_summary)

    limiting_factors = []
    if score < 80.0:
        limiting_factors.append("درجات الحرارة الموسمية أو طبيعة التربة تتطلب معاملات خاصة.")
    limiting_factors.append("ملوحة التربة غير محددة من SoilGrids ويلزم اختبار حقلي.")

    return SuitabilityResponse(
        crop_id=crop.crop_id,
        crop_name_ar=crop.name_ar,
        crop_name_en=crop.name_en,
        suitability_score=score,
        limiting_factors=limiting_factors,
        water_requirement_m3_per_feddan=crop.requirements.water_demand_m3_per_feddan,
    )
