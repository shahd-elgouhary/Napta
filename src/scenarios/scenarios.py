"""Scenario simulation and stress-testing engine (A7).

Simulates climate, market, and resource shocks:
  * Canal water cut (water availability reduction)
  * Fertilizer inflation / subsidy removal
  * Harvest-time crop price drop
  * Heat-wave temperature anomaly yield reduction
  * Crowding stress test for volatile perishable crops (e.g. onion)

Crucial rule:
  The baseline is NEVER mutated. Uses deep copying and returns new result + delta.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Dict, List, Optional

from src.domain.schemas import CostBreakdown, Plan, PlanMetrics, ScenarioSpec


# Standard presets for Egyptian agricultural stress tests
STANDARD_SCENARIO_PRESETS: Dict[str, ScenarioSpec] = {
    "canal_water_cut": ScenarioSpec(
        scenario_name="عجز مائي بالترعة (20% نقص)",
        water_availability_multiplier=0.8,
        fertilizer_cost_multiplier=1.0,
        crop_price_multiplier=1.0,
        temp_anomaly_c=0.0,
    ),
    "fertilizer_price_surge": ScenarioSpec(
        scenario_name="ارتفاع أسعار الأسمدة الحرة (30% زيادة)",
        water_availability_multiplier=1.0,
        fertilizer_cost_multiplier=1.3,
        crop_price_multiplier=1.0,
        temp_anomaly_c=0.0,
    ),
    "market_price_drop": ScenarioSpec(
        scenario_name="انخفاض سعر البيع عند الحصاد (15% هبوط)",
        water_availability_multiplier=1.0,
        fertilizer_cost_multiplier=1.0,
        crop_price_multiplier=0.85,
        temp_anomaly_c=0.0,
    ),
    "heatwave_shock": ScenarioSpec(
        scenario_name="موجة حارة خلال العقد (+2°C)",
        water_availability_multiplier=1.0,
        fertilizer_cost_multiplier=1.0,
        crop_price_multiplier=1.0,
        temp_anomaly_c=2.0,
    ),
    "combined_stress": ScenarioSpec(
        scenario_name="صدمة مركبة (نقص مياه 15% + تضخم تكاليف 20%)",
        water_availability_multiplier=0.85,
        fertilizer_cost_multiplier=1.2,
        crop_price_multiplier=0.95,
        temp_anomaly_c=1.0,
    ),
}


@dataclass(frozen=True)
class ScenarioDelta:
    revenue_diff_egp: float
    cost_diff_egp: float
    profit_diff_egp: float
    profit_pct_change: float
    water_diff_m3: float
    water_pct_change: float


@dataclass(frozen=True)
class ScenarioSimulationResult:
    scenario_spec: ScenarioSpec
    baseline_plan: Plan
    simulated_plan: Plan
    delta: ScenarioDelta
    is_stress_test: bool = True
    stress_warning_ar: str = "تنبيه: هذا اختبار إجهاد افتراضي ولا يعد تنبؤًا مؤكدًا بالسوق أو المناخ."


def simulate_plan_under_scenario(
    baseline_plan: Plan,
    area_feddans: float,
    spec: ScenarioSpec,
) -> ScenarioSimulationResult:
    """Stress-test a plan under scenario multipliers without mutating the baseline."""
    # Ensure baseline is not modified (deep copy)
    sim_plan = baseline_plan.model_copy(deep=True)
    sim_plan.plan_id = f"{baseline_plan.plan_id}_sim_{spec.scenario_name}"

    bm = baseline_plan.metrics

    # 1. Price multiplier affects revenue
    new_rev_per_feddan = bm.gross_revenue_egp_per_feddan * spec.crop_price_multiplier

    # 2. Temperature anomaly or water reduction yield penalty
    # Heatwave > 1.5°C or severe water shortage (< 0.85) incurs yield loss
    yield_multiplier = 1.0
    if spec.temp_anomaly_c >= 1.5:
        # ~5% yield drop per degree above 1.5°C
        yield_multiplier *= max(0.6, 1.0 - (spec.temp_anomaly_c - 1.5) * 0.05)
    if spec.water_availability_multiplier < 0.85:
        yield_multiplier *= max(0.5, spec.water_availability_multiplier / 0.85)

    new_rev_per_feddan *= yield_multiplier
    total_rev = round(new_rev_per_feddan * area_feddans, 2)

    # 3. Fertilizer cost multiplier affects fertilizers item
    cb = bm.cost_breakdown
    new_fert = round(cb.fertilizers_and_soil_amendments_egp * spec.fertilizer_cost_multiplier, 2)
    # Fuel cost increases slightly if water availability is restricted (extra pumping hours)
    fuel_multiplier = 1.0 / spec.water_availability_multiplier if spec.water_availability_multiplier < 1.0 else 1.0
    new_fuel = round(cb.fuel_and_irrigation_electricity_egp * min(1.3, fuel_multiplier), 2)

    new_cost_per_feddan = round(
        cb.seeds_seedlings_egp + new_fert + new_fuel + cb.labor_and_machinery_egp + cb.land_preparation_egp, 2
    )
    total_cost = round(new_cost_per_feddan * area_feddans, 2)

    new_profit_per_feddan = round(new_rev_per_feddan - new_cost_per_feddan, 2)
    total_net_profit = round(new_profit_per_feddan * area_feddans, 2)
    roi = round((new_profit_per_feddan / new_cost_per_feddan * 100.0), 1) if new_cost_per_feddan > 0 else 0.0

    # 4. Water demand adjustment
    new_water_feddan = round(bm.water_demand_m3_per_feddan * spec.water_availability_multiplier, 1)
    total_water = round(new_water_feddan * area_feddans, 1)

    new_cb = CostBreakdown(
        seeds_seedlings_egp=cb.seeds_seedlings_egp,
        fertilizers_and_soil_amendments_egp=new_fert,
        fuel_and_irrigation_electricity_egp=new_fuel,
        labor_and_machinery_egp=cb.labor_and_machinery_egp,
        land_preparation_egp=cb.land_preparation_egp,
        total_cost_per_feddan_egp=new_cost_per_feddan,
    )

    sim_plan.metrics = PlanMetrics(
        gross_revenue_egp_per_feddan=round(new_rev_per_feddan, 2),
        total_gross_revenue_egp=total_rev,
        cost_breakdown=new_cb,
        total_cost_egp=total_cost,
        net_profit_egp_per_feddan=new_profit_per_feddan,
        total_net_profit_egp=total_net_profit,
        roi_percentage=roi,
        water_demand_m3_per_feddan=new_water_feddan,
        total_water_demand_m3=total_water,
        risk_level=bm.risk_level,
        risk_rationale=f"محاكاة إجهاد '{spec.scenario_name}': انعكاس التغير في الأسعار والموارد على الأرباح.",
    )

    sim_plan.key_advice_ar = (
        f"نتيجة اختبار الإجهاد ({spec.scenario_name}): صافي الربح التشغيلي "
        f"{'ينخفض' if total_net_profit < bm.total_net_profit_egp else 'يتغير'} إلى {total_net_profit:,.0f} جنيه."
    )

    # Compute deltas
    profit_diff = round(total_net_profit - bm.total_net_profit_egp, 2)
    profit_pct = (
        round((profit_diff / bm.total_net_profit_egp) * 100.0, 1)
        if bm.total_net_profit_egp != 0
        else 0.0
    )
    water_diff = round(total_water - bm.total_water_demand_m3, 1)
    water_pct = (
        round((water_diff / bm.total_water_demand_m3) * 100.0, 1)
        if bm.total_water_demand_m3 != 0
        else 0.0
    )

    delta = ScenarioDelta(
        revenue_diff_egp=round(total_rev - bm.total_gross_revenue_egp, 2),
        cost_diff_egp=round(total_cost - bm.total_cost_egp, 2),
        profit_diff_egp=profit_diff,
        profit_pct_change=profit_pct,
        water_diff_m3=water_diff,
        water_pct_change=water_pct,
    )

    return ScenarioSimulationResult(
        scenario_spec=spec,
        baseline_plan=baseline_plan,
        simulated_plan=sim_plan,
        delta=delta,
    )
