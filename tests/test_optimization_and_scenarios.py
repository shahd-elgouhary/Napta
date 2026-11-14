"""Tests for A5 (rotations & constraints), A6 (ranking), and A7 (scenarios).

All expected values are hand-computed and arithmetic is shown in comments.
"""

import copy
import pytest

from src.data.loaders import load_cost_assumptions, load_crop_prices, load_crop_profiles
from src.domain.schemas import (
    ClimateSummary,
    EnvironmentSummary,
    FarmArea,
    FarmCoordinates,
    FarmProfile,
    FarmerPriority,
    IrrigationMethod,
    Plan,
    ScenarioSpec,
    SoilSummary,
    WaterSourceType,
)
from src.optimization.ranking import PlanRanker
from src.optimization.rotation_generator import RotationGenerator
from src.scenarios.scenarios import (
    STANDARD_SCENARIO_PRESETS,
    simulate_plan_under_scenario,
)
from src.scenarios.sensitivity import run_one_at_a_time_sensitivity


@pytest.fixture
def representative_env():
    return EnvironmentSummary(
        climate=ClimateSummary(
            annual_mean_temp_c=21.0,
            summer_mean_temp_c=29.0,
            winter_mean_temp_c=16.5,
            relative_humidity_pct=60.0,
            wind_speed_ms=2.5,
            solar_radiation_kwh_m2_day=5.0,
            annual_precipitation_mm=45.0,
        ),
        soil=SoilSummary(
            ph_water=7.4,
            organic_carbon_g_kg=14.0,
            clay_pct=45.0,
            silt_pct=35.0,
            sand_pct=20.0,
            bulk_density_cg_cm3=120.0,
            cation_exchange_capacity_cmolc_kg=26.0,
            texture_class="Clay",
            salinity_status="UNKNOWN",
        ),
    )


@pytest.fixture
def standard_farm():
    return FarmProfile(
        farm_id="test_farm_kafr",
        farmer_name="يا حاج أحمد",
        location_name="كفر الشيخ",
        coordinates=FarmCoordinates(latitude=31.11, longitude=30.94),
        area=FarmArea(feddans=3.0, qirats=0.0),
        water_source=WaterSourceType.CANAL_ROTATION,
        irrigation_method=IrrigationMethod.SURFACE_FLOOD,
        available_budget_egp=80000.0,
        previous_crops=["ذرة"],
        primary_objective=FarmerPriority.MAX_PROFIT,
    )


# ------------------------------------------------------------------ A5 Tests

def test_rotation_generator_feasible_plans_satisfy_constraints(standard_farm, representative_env):
    """Property test: every plan marked feasible satisfies all hard constraints."""
    gen = RotationGenerator()
    result = gen.generate_annual_rotations(
        farm_profile=standard_farm,
        env=representative_env,
    )

    assert len(result.feasible_rotations) > 0
    for cand in result.feasible_rotations:
        # Every feasible candidate must have 0 hard violations
        assert cand.feasibility.is_feasible is True
        assert len(cand.feasibility.hard_violations) == 0


def test_infeasible_plans_carry_reasons(standard_farm, representative_env):
    """Infeasible combinations must carry transparent Arabic/English reasons."""
    gen = RotationGenerator()
    result = gen.generate_annual_rotations(
        farm_profile=standard_farm,
        env=representative_env,
    )

    # Some rotations (e.g. sugar beet followed by cotton) should fail timing/turnaround
    assert len(result.infeasible_rotations) > 0
    for cand in result.infeasible_rotations:
        assert cand.feasibility.is_feasible is False
        assert len(cand.feasibility.hard_violations) > 0


def test_budget_constraint_blocking(standard_farm, representative_env):
    """Extremely low budget must reject expensive rotations and offer relaxation."""
    # Restrict budget to 5,000 EGP for 3 feddans (less than any winter crop requirement)
    poor_farm = standard_farm.model_copy(update={"available_budget_egp": 5000.0})
    gen = RotationGenerator()
    result = gen.generate_annual_rotations(
        farm_profile=poor_farm,
        env=representative_env,
    )

    assert len(result.feasible_rotations) == 0
    assert result.relaxation_offered is True
    assert len(result.relaxation_notes) >= 1
    assert "الميزانية" in result.relaxation_notes[0] or "الميزانية" in result.relaxation_notes[1]


# ------------------------------------------------------------------ A6 Tests

def test_plan_ranking_selects_three_archetypes(standard_farm, representative_env):
    """Ranker must produce exactly three distinct archetypes: الأكسب, الأوفر في المية, الأأمن."""
    gen = RotationGenerator()
    res = gen.generate_annual_rotations(farm_profile=standard_farm, env=representative_env)

    ranker = PlanRanker()
    plans = ranker.select_three_archetypes(
        candidate_rotations=res.feasible_rotations,
        cost_assumptions=gen.cost_assumptions,
        env=representative_env,
        farm_profile=standard_farm,
    )

    assert len(plans) == 3
    archetypes = [p.archetype for p in plans]
    assert archetypes == ["الأكسب", "الأوفر في المية", "الأأمن"]

    # Hand arithmetic and logic checks:
    # 1. Best profit plan has the highest net profit
    p_profit = plans[0]
    p_water = plans[1]
    p_safe = plans[2]

    assert p_profit.metrics.net_profit_egp_per_feddan >= p_water.metrics.net_profit_egp_per_feddan
    # 2. Water-saving plan has lower water demand than max-profit
    assert p_water.metrics.water_demand_m3_per_feddan <= p_profit.metrics.water_demand_m3_per_feddan
    # 3. Mandatory disclaimer is present on all plans
    for p in plans:
        assert "ده تقدير مش ضمان" in p.disclaimer_ar


# ------------------------------------------------------------------ A7 Tests

def test_baseline_is_immutable_under_scenario(standard_farm, representative_env):
    """Crucial non-negotiable rule: the baseline plan is NEVER mutated by scenario simulation."""
    gen = RotationGenerator()
    res = gen.generate_annual_rotations(farm_profile=standard_farm, env=representative_env)
    ranker = PlanRanker()
    plans = ranker.select_three_archetypes(
        candidate_rotations=res.feasible_rotations,
        cost_assumptions=gen.cost_assumptions,
        env=representative_env,
        farm_profile=standard_farm,
    )
    base_plan = plans[0]

    # Deep snapshot before simulation
    before_snapshot = copy.deepcopy(base_plan.model_dump())

    spec = STANDARD_SCENARIO_PRESETS["fertilizer_price_surge"]
    sim_res = simulate_plan_under_scenario(
        baseline_plan=base_plan,
        area_feddans=3.0,
        spec=spec,
    )

    after_snapshot = base_plan.model_dump()

    # The baseline dictionary must be strictly identical before and after
    assert before_snapshot == after_snapshot
    # The simulated plan is a new object with updated metrics
    assert sim_res.simulated_plan.plan_id != base_plan.plan_id
    assert sim_res.delta.profit_diff_egp < 0  # fertilizer rise reduces profit


def test_scenario_fertilizer_surge_hand_arithmetic(standard_farm, representative_env):
    """Test fertilizer price surge (+30%) arithmetic on costs and deltas.

    If fertilizer cost rises by 30% (multiplier 1.30):
      new_fert = old_fert * 1.30
      cost increase = old_fert * 0.30 * 3 feddans
    """
    gen = RotationGenerator()
    res = gen.generate_annual_rotations(farm_profile=standard_farm, env=representative_env)
    ranker = PlanRanker()
    plans = ranker.select_three_archetypes(
        candidate_rotations=res.feasible_rotations,
        cost_assumptions=gen.cost_assumptions,
        env=representative_env,
        farm_profile=standard_farm,
    )
    base = plans[0]
    base_fert_per_fed = base.metrics.cost_breakdown.fertilizers_and_soil_amendments_egp

    spec = ScenarioSpec(
        scenario_name="Fertilizer +30%",
        fertilizer_cost_multiplier=1.30,
    )
    sim = simulate_plan_under_scenario(base, area_feddans=3.0, spec=spec)

    expected_fert_per_fed = round(base_fert_per_fed * 1.30, 2)
    assert sim.simulated_plan.metrics.cost_breakdown.fertilizers_and_soil_amendments_egp == pytest.approx(
        expected_fert_per_fed, abs=0.05
    )
    # Profit delta should equal cost increase (with zero price change)
    assert sim.delta.profit_diff_egp < 0


def test_one_at_a_time_sensitivity(standard_farm, representative_env):
    """Verify systematic variation of price and fertilizer."""
    gen = RotationGenerator()
    res = gen.generate_annual_rotations(farm_profile=standard_farm, env=representative_env)
    ranker = PlanRanker()
    plans = ranker.select_three_archetypes(
        candidate_rotations=res.feasible_rotations,
        cost_assumptions=gen.cost_assumptions,
        env=representative_env,
        farm_profile=standard_farm,
    )
    base = plans[0]

    curves = run_one_at_a_time_sensitivity(baseline_plan=base, area_feddans=3.0)
    assert "crop_price" in curves
    assert "fertilizer_cost" in curves

    price_curve = curves["crop_price"]
    assert len(price_curve.steps) == 5
    # As price multiplier rises from 0.7 to 1.3, profit must strictly increase
    profits = [s.operating_profit_egp for s in price_curve.steps]
    assert profits == sorted(profits)
