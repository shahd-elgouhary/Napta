"""Scenario simulation and plan comparison endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
from src.domain.schemas import Plan, ScenarioSpec
from src.services.comparison_service import ComparisonService

router = APIRouter(prefix="/api/scenarios", tags=["Scenarios & Comparisons"])
comparison_service = ComparisonService()


class ScenarioSimulationRequest(BaseModel):
    base_plan: Plan
    area_feddans: float = Field(..., gt=0.0)
    scenario_spec: ScenarioSpec


class PlanComparisonRequest(BaseModel):
    plans: List[Plan]


@router.post("/simulate")
async def simulate_scenario(payload: ScenarioSimulationRequest) -> Dict[str, Any]:
    """Recalculate plan metrics under climate, water, or price stress scenarios."""
    return comparison_service.simulate_scenario(
        base_plan=payload.base_plan,
        area_feddans=payload.area_feddans,
        spec=payload.scenario_spec,
    )


@router.post("/compare")
async def compare_plans(payload: PlanComparisonRequest) -> Dict[str, Any]:
    """Generate side-by-side comparison across economic, water, and risk metrics."""
    return comparison_service.compare_plans(payload.plans)
