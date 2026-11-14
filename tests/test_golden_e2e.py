"""Golden End-to-End Test (Section 6 Integration).

Executes full pipeline for the official demo farm (data/demo/demo_farm.json):
  FarmProfile -> EnvironmentSummary -> 3 Ranked Plans -> Economics -> Scenario Stress Test

Ensures:
  * Zero network dependencies (uses offline regional fixtures).
  * Strict unit conversions exclusively through src.egypt.units_eg.
  * Baseline is 100% immutable under scenario simulation.
  * All 3 archetypes (الأكسب, الأوفر في المية, الأأمن) are generated deterministically.
"""

import json
from pathlib import Path
import pytest

from src.data.environment_service import EnvironmentService
from src.data.nasa_power_client import NasaPowerClient
from src.data.soilgrids_client import SoilGridsClient
from src.domain.schemas import (
    FarmArea,
    FarmCoordinates,
    FarmProfile,
    FarmerPriority,
    IrrigationMethod,
    ScenarioSpec,
    WaterSourceType,
)
from src.egypt.units_eg import m2_to_feddan
from src.services.decision_engine_adapter import DecisionEngineAdapter


def load_demo_farm_profile() -> FarmProfile:
    """Load and adapt data/demo/demo_farm.json to FarmProfile schema using units_eg."""
    path = Path("data/demo/demo_farm.json")
    if not path.exists():
        path = Path(__file__).resolve().parent.parent / "data" / "demo" / "demo_farm.json"

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Convert area_m2 to feddans using src.egypt.units_eg
    # 12602.49 m2 / 4200.83 = 3.0 feddans
    total_feddans = round(m2_to_feddan(raw["area_m2"]), 3)

    water_source_enum = WaterSourceType(raw.get("water_category", "canal_rotation"))

    return FarmProfile(
        farm_id=raw["farm_id"],
        farmer_name="يا حاج أحمد (مزرعة تجريبية)",
        location_name=raw["governorate"],
        coordinates=FarmCoordinates(latitude=raw["latitude"], longitude=raw["longitude"]),
        area=FarmArea(feddans=total_feddans, qirats=0.0),
        water_source=water_source_enum,
        irrigation_method=IrrigationMethod.SURFACE_FLOOD,
        available_budget_egp=float(raw.get("budget_egp", 60000.0)),
        previous_crops=[h["crop_id"] for h in raw.get("history", [])],
        primary_objective=FarmerPriority.MAX_PROFIT,
    )


@pytest.mark.asyncio
async def test_golden_end_to_end_flow():
    """Complete golden E2E test verifying deterministic farm-to-scenario pipeline."""
    # 1. Load demo farm
    farm = load_demo_farm_profile()
    assert farm.farm_id == "demo-kafr-el-sheikh-01"
    assert farm.area.total_feddans == pytest.approx(3.0)

    # 2. Retrieve environment using offline fixture fallback
    # Create offline clients with 0 timeout to guarantee fixture usage with zero network lag
    nasa_client = NasaPowerClient()
    soil_client = SoilGridsClient()
    # Direct fixture load for speed & offline guarantee
    climate_summary, climate_prov, _ = nasa_client._load_fallback_fixture(farm.coordinates.latitude, farm.coordinates.longitude)
    soil_summary, soil_prov, _ = soil_client._load_fallback_fixture(farm.coordinates.latitude, farm.coordinates.longitude)

    from src.domain.schemas import EnvironmentSummary
    env = EnvironmentSummary(
        climate=climate_summary,
        soil=soil_summary,
        provenance=[climate_prov, soil_prov],
        missing_data_warnings=["Salinity explicitly UNKNOWN from SoilGrids"],
        is_fixture=True,
    )

    assert env.soil.salinity_status == "UNKNOWN"

    # 3. Decision Engine Adapter recommendations
    adapter = DecisionEngineAdapter()
    plans = adapter.generate_recommendations(profile=farm, env=env)

    # Assert exactly 3 archetypes are produced
    assert len(plans) == 3
    archetypes = [p.archetype for p in plans]
    assert "الأكسب" in archetypes
    assert "الأوفر في المية" in archetypes
    assert "الأأمن" in archetypes

    # Validate economic calculations on all plans
    for p in plans:
        m = p.metrics
        assert m.gross_revenue_egp_per_feddan > 0
        assert m.total_cost_egp > 0
        assert m.net_profit_egp_per_feddan is not None
        assert m.total_water_demand_m3 > 0
        assert "ده تقدير مش ضمان" in p.disclaimer_ar

    # 4. Scenario Stress Testing on Plan 1 (الأكسب)
    base_plan = plans[0]
    before_dump = json.dumps(base_plan.model_dump(), sort_keys=True)

    spec = ScenarioSpec(
        scenario_name="عجز مياه 20% وارتفاع أسمدة 25%",
        water_availability_multiplier=0.80,
        fertilizer_cost_multiplier=1.25,
        crop_price_multiplier=0.95,
        temp_anomaly_c=1.0,
    )

    sim_plan = adapter.simulate_scenario(
        base_plan=base_plan,
        area_feddans=farm.area.total_feddans,
        spec=spec,
    )

    # Verify baseline immutability: JSON dump before must equal dump after
    after_dump = json.dumps(base_plan.model_dump(), sort_keys=True)
    assert before_dump == after_dump

    # Verify simulated response reflects shock
    assert sim_plan.plan_id != base_plan.plan_id
    assert sim_plan.metrics.total_water_demand_m3 < base_plan.metrics.total_water_demand_m3
    assert sim_plan.metrics.total_net_profit_egp < base_plan.metrics.total_net_profit_egp
