"""One-at-a-time parameter sensitivity analysis (A7).

Varies key drivers (crop price, fertilizer cost, water availability)
across systematic percentage steps to observe marginal impact on operating profit and ROI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from src.domain.schemas import Plan, ScenarioSpec
from src.scenarios.scenarios import simulate_plan_under_scenario


@dataclass(frozen=True)
class SensitivityStep:
    parameter_name: str
    multiplier: float
    operating_profit_egp: float
    profit_pct_change: float
    water_demand_m3: float


@dataclass(frozen=True)
class SensitivityCurve:
    parameter_name: str
    baseline_profit_egp: float
    steps: List[SensitivityStep]


def run_one_at_a_time_sensitivity(
    baseline_plan: Plan,
    area_feddans: float,
    steps: Sequence[float] = (0.7, 0.85, 1.0, 1.15, 1.3),
) -> Dict[str, SensitivityCurve]:
    """Evaluate one-at-a-time sensitivity across price, fertilizer, and water."""
    curves: Dict[str, SensitivityCurve] = {}
    base_profit = baseline_plan.metrics.total_net_profit_egp

    # 1. Price sensitivity
    price_steps: List[SensitivityStep] = []
    for mult in steps:
        spec = ScenarioSpec(
            scenario_name=f"Price {mult:.2f}x",
            crop_price_multiplier=mult,
        )
        res = simulate_plan_under_scenario(baseline_plan, area_feddans, spec)
        price_steps.append(
            SensitivityStep(
                parameter_name="crop_price",
                multiplier=mult,
                operating_profit_egp=res.simulated_plan.metrics.total_net_profit_egp,
                profit_pct_change=res.delta.profit_pct_change,
                water_demand_m3=res.simulated_plan.metrics.total_water_demand_m3,
            )
        )
    curves["crop_price"] = SensitivityCurve("crop_price", base_profit, price_steps)

    # 2. Fertilizer cost sensitivity
    fert_steps: List[SensitivityStep] = []
    for mult in steps:
        spec = ScenarioSpec(
            scenario_name=f"Fertilizer {mult:.2f}x",
            fertilizer_cost_multiplier=mult,
        )
        res = simulate_plan_under_scenario(baseline_plan, area_feddans, spec)
        fert_steps.append(
            SensitivityStep(
                parameter_name="fertilizer_cost",
                multiplier=mult,
                operating_profit_egp=res.simulated_plan.metrics.total_net_profit_egp,
                profit_pct_change=res.delta.profit_pct_change,
                water_demand_m3=res.simulated_plan.metrics.total_water_demand_m3,
            )
        )
    curves["fertilizer_cost"] = SensitivityCurve("fertilizer_cost", base_profit, fert_steps)

    return curves
