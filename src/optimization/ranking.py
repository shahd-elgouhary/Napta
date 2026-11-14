"""Archetype selection and ranking engine for farmer recommendations (A6).

Selects exactly the three required farmer archetypes from feasible rotations:
  1. الأكسب (Highest Profit)
  2. الأوفر في المية (Most Water-Saving)
  3. الأأمن (Safest / Lowest Downside Risk)

If fewer than three distinct feasible plans exist, returns fewer with transparent explanations.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.agronomy.suitability import SuitabilityEvaluation, evaluate_crop_suitability
from src.agronomy.water import CropWaterDemand, calculate_crop_water_demand
from src.data.loaders import (
    CostItemRecord,
    CropPriceRecord,
    CropProfileRecord,
    load_crop_prices,
)
from src.domain.schemas import AgriculturalSeason, EnvironmentSummary, FarmProfile, Plan
from src.optimization.objective import (
    RotationMetrics,
    evaluate_rotation_objectives,
    rotation_metrics_to_plan_metrics,
)
from src.optimization.rotation_generator import CandidateRotation, RotationGenerator


class PlanRanker:
    """Ranks feasible crop plans and extracts the three archetypes."""

    def __init__(
        self,
        crop_prices: Optional[Dict[str, CropPriceRecord]] = None,
    ):
        self.crop_prices = crop_prices or load_crop_prices()

    def select_three_archetypes(
        self,
        candidate_rotations: List[CandidateRotation],
        cost_assumptions: Dict[str, List[CostItemRecord]],
        env: EnvironmentSummary,
        farm_profile: FarmProfile,
        include_rent: bool = False,
    ) -> List[Plan]:
        """Rank feasible rotations and select the 3 farmer archetypes: الأكسب, الأوفر في المية, الأأمن."""
        if not candidate_rotations:
            return []

        # 1. Compute water demands and suitability evaluations
        water_demands: Dict[str, CropWaterDemand] = {}
        suit_evals: Dict[str, SuitabilityEvaluation] = {}

        for cand in candidate_rotations:
            for c in cand.crops:
                if c.crop_id not in water_demands:
                    water_demands[c.crop_id] = calculate_crop_water_demand(
                        crop=c,
                        climate=env.climate,
                        latitude_deg=farm_profile.coordinates.latitude,
                    )
                if c.crop_id not in suit_evals:
                    suit_evals[c.crop_id] = evaluate_crop_suitability(
                        crop=c,
                        env=env,
                        planting_month=c.sow_start_month,
                        measured_salinity_ece_dsm=env.soil.salinity_estimated_dsm,
                    )

        # 2. Evaluate multi-objective metrics for all feasible candidates
        evaluated: List[Tuple[CandidateRotation, RotationMetrics]] = []
        for cand in candidate_rotations:
            m = evaluate_rotation_objectives(
                crops=cand.crops,
                crop_prices=self.crop_prices,
                cost_assumptions=cost_assumptions,
                water_demands=water_demands,
                area_feddans=farm_profile.area.total_feddans,
                include_rent=include_rent,
            )
            evaluated.append((cand, m))

        if not evaluated:
            return []

        # --------------------------------------------------------
        # Archetype 1: الأكسب (Highest Profit)
        # --------------------------------------------------------
        sorted_by_profit = sorted(
            evaluated, key=lambda pair: pair[1].operating_profit_per_feddan_egp, reverse=True
        )
        best_profit_cand, best_profit_m = sorted_by_profit[0]

        # --------------------------------------------------------
        # Archetype 2: الأوفر في المية (Most Water-Saving)
        # --------------------------------------------------------
        # Sort by lowest water demand per feddan
        sorted_by_water = sorted(
            evaluated, key=lambda pair: pair[1].water_demand_m3_per_feddan
        )
        # Pick best water-saver that is distinct from best_profit (if possible)
        best_water_cand, best_water_m = sorted_by_water[0]
        if best_water_cand.rotation_id == best_profit_cand.rotation_id and len(sorted_by_water) > 1:
            best_water_cand, best_water_m = sorted_by_water[1]

        # --------------------------------------------------------
        # Archetype 3: الأأمن (Safest / Lowest Risk)
        # --------------------------------------------------------
        # Prefer low-risk crops (wheat with government procurement guarantee)
        # and lowest cost downside
        def safety_key(pair: Tuple[CandidateRotation, RotationMetrics]) -> Tuple[int, float]:
            cand, m = pair
            # Priority: 0 if Low risk, 1 if Medium, 2 if High
            risk_score = 0 if m.risk_level == "Low" else (1 if m.risk_level == "Medium" else 2)
            # Secondarily prefer lower upfront cash needed
            return (risk_score, m.upfront_cash_needed_egp)

        sorted_by_safety = sorted(evaluated, key=safety_key)
        best_safe_cand, best_safe_m = sorted_by_safety[0]
        # Ensure distinctness if multiple options exist
        for cand, m in sorted_by_safety:
            if cand.rotation_id not in (best_profit_cand.rotation_id, best_water_cand.rotation_id):
                best_safe_cand, best_safe_m = cand, m
                break

        # --------------------------------------------------------
        # Build Plan schemas
        # --------------------------------------------------------
        plans: List[Plan] = []

        # Plan 1: الأكسب
        p1 = self._build_plan(
            plan_id="plan_max_profit",
            archetype="الأكسب",
            cand=best_profit_cand,
            metrics=best_profit_m,
            suit_evals=suit_evals,
            advice_ar=(
                f"أعلى عائد ربحي متوقع ({best_profit_m.operating_profit_per_feddan_egp:,.0f} جنيه/فدان) "
                f"من خلال تعاقب {best_profit_cand.crops[0].name_ar} ثم {best_profit_cand.crops[1].name_ar}."
            ),
        )
        plans.append(p1)

        # Plan 2: الأوفر في المية (if distinct)
        if best_water_cand.rotation_id != best_profit_cand.rotation_id:
            p2 = self._build_plan(
                plan_id="plan_water_saver",
                archetype="الأوفر في المية",
                cand=best_water_cand,
                metrics=best_water_m,
                suit_evals=suit_evals,
                advice_ar=(
                    f"أوفر استهلاك للمياه ({best_water_m.water_demand_m3_per_feddan:,.0f} م³/فدان) "
                    f"يوفر سولار طلمبات الرفع ويحمي الأرض من نقص مياه الترع بالمناوبة."
                ),
            )
            plans.append(p2)

        # Plan 3: الأأمن (if distinct from P1 and P2)
        used_ids = {p.plan_id for p in plans}
        if best_safe_cand.rotation_id not in (best_profit_cand.rotation_id, best_water_cand.rotation_id):
            p3 = self._build_plan(
                plan_id="plan_lowest_risk",
                archetype="الأأمن",
                cand=best_safe_cand,
                metrics=best_safe_m,
                suit_evals=suit_evals,
                advice_ar=(
                    f"خيار مستقر منخفض المخاطر يعتمد على {best_safe_cand.crops[0].name_ar} "
                    f"المدعوم بسعر توريد حكومي وضمان تسليم نقدي سريع."
                ),
            )
            plans.append(p3)

        return plans

    def _build_plan(
        self,
        plan_id: str,
        archetype: str,
        cand: CandidateRotation,
        metrics: RotationMetrics,
        suit_evals: Dict[str, SuitabilityEvaluation],
        advice_ar: str,
    ) -> Plan:
        primary_crop = cand.crops[0]
        # Calculate mean suitability score across the rotation
        scores = [suit_evals[c.crop_id].overall_score for c in cand.crops if c.crop_id in suit_evals]
        avg_suit = sum(scores) / len(scores) if scores else 80.0

        rotation_seq = [
            f"{c.name_ar} ({'شتوي' if c.season == 'winter' else 'صيفي'})"
            for c in cand.crops
        ]

        season_enum = (
            AgriculturalSeason.WINTER
            if primary_crop.season == "winter"
            else AgriculturalSeason.SUMMER
        )

        return Plan(
            plan_id=plan_id,
            archetype=archetype,
            primary_crop_en=primary_crop.name_en,
            primary_crop_ar=primary_crop.name_ar,
            season=season_enum,
            rotation_sequence=rotation_seq,
            suitability_score=round(avg_suit, 1),
            metrics=rotation_metrics_to_plan_metrics(metrics),
            key_advice_ar=advice_ar,
            disclaimer_ar="ده تقدير مش ضمان، والأسعار والمحصول بيتغيروا حسب السوق والخدمة.",
        )
