"""Comparison and scenario evaluation service."""

from typing import List, Dict, Any, Optional
from src.domain.schemas import Plan, ScenarioSpec
from src.services.decision_engine_adapter import DecisionEngineAdapter


class ComparisonService:
    """Provides side-by-side comparison tables and scenario simulations for plans."""

    def __init__(self, engine_adapter: Optional[DecisionEngineAdapter] = None):
        self.engine_adapter = engine_adapter or DecisionEngineAdapter()

    def compare_plans(self, plans: List[Plan]) -> Dict[str, Any]:
        """Generate structured comparison table across financial, water, and risk metrics."""
        rows = []
        for p in plans:
            m = p.metrics
            rows.append({
                "plan_id": p.plan_id,
                "archetype": p.archetype,
                "crop": f"{p.primary_crop_ar} ({p.primary_crop_en})",
                "suitability_score": p.suitability_score,
                "net_profit_per_feddan_egp": m.net_profit_egp_per_feddan,
                "total_profit_egp": m.total_net_profit_egp,
                "roi_percentage": m.roi_percentage,
                "water_demand_m3_per_feddan": m.water_demand_m3_per_feddan,
                "total_water_m3": m.total_water_demand_m3,
                "risk_level": m.risk_level,
                "risk_rationale": m.risk_rationale,
            })
        return {
            "comparison_table": rows,
            "metric_units": {
                "profit": "EGP (جنيه مصري)",
                "water": "m³ (متر مكعب)",
                "suitability": "Points (0-100)",
                "roi": "%",
            },
        }

    def simulate_scenario(self, base_plan: Plan, area_feddans: float, spec: ScenarioSpec) -> Dict[str, Any]:
        """Simulate stress scenario and return delta comparison."""
        simulated = self.engine_adapter.simulate_scenario(base_plan, area_feddans, spec)
        base_m = base_plan.metrics
        sim_m = simulated.metrics

        delta = {
            "net_profit_diff_egp": round(sim_m.total_net_profit_egp - base_m.total_net_profit_egp, 2),
            "profit_pct_change": round(
                ((sim_m.total_net_profit_egp - base_m.total_net_profit_egp) / base_m.total_net_profit_egp) * 100.0, 1
            ) if base_m.total_net_profit_egp > 0 else 0.0,
            "water_diff_m3": round(sim_m.total_water_demand_m3 - base_m.total_water_demand_m3, 1),
            "water_pct_change": round(
                ((sim_m.total_water_demand_m3 - base_m.total_water_demand_m3) / base_m.total_water_demand_m3) * 100.0, 1
            ) if base_m.total_water_demand_m3 > 0 else 0.0,
        }

        return {
            "base_plan": base_plan.model_dump(),
            "simulated_plan": simulated.model_dump(),
            "scenario": spec.model_dump(),
            "deltas": delta,
        }
