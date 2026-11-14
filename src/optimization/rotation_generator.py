"""Rotation generator for Egyptian multi-season farming (A5).

Enumerates possible crop rotations (e.g. Winter -> Summer) from the verified
crop catalog and filters them against agronomic, temporal, water, budget,
and regulatory constraints.

If no plan is feasible, reports blocking constraints and offers controlled relaxation.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from src.agronomy.suitability import SuitabilityEvaluation, evaluate_crop_suitability
from src.agronomy.water import CropWaterDemand, calculate_crop_water_demand
from src.data.loaders import (
    CostItemRecord,
    CropProfileRecord,
    RegulationRecord,
    RotationRuleRecord,
    load_cost_assumptions,
    load_crop_profiles,
    load_regulations,
    load_rotation_rules,
)
from src.domain.schemas import EnvironmentSummary, FarmProfile
from src.optimization.constraints import (
    ConstraintCheck,
    RotationFeasibility,
    evaluate_rotation_feasibility,
)


@dataclass(frozen=True)
class CandidateRotation:
    rotation_id: str
    crops: Tuple[CropProfileRecord, ...]
    season_names: Tuple[str, ...]
    feasibility: RotationFeasibility


@dataclass(frozen=True)
class RotationGenerationResult:
    feasible_rotations: List[CandidateRotation]
    infeasible_rotations: List[CandidateRotation]
    blocking_reasons_summary: Dict[str, int]
    relaxation_offered: bool
    relaxation_notes: List[str]


class RotationGenerator:
    """Deterministic rotation enumerator and constraint filtering engine."""

    def __init__(
        self,
        crop_profiles: Optional[Dict[str, CropProfileRecord]] = None,
        cost_assumptions: Optional[Dict[str, List[CostItemRecord]]] = None,
        rotation_rules: Optional[List[RotationRuleRecord]] = None,
        regulations: Optional[List[RegulationRecord]] = None,
    ):
        self.crop_profiles = crop_profiles or load_crop_profiles()
        self.cost_assumptions = cost_assumptions or load_cost_assumptions()
        self.rotation_rules = rotation_rules or load_rotation_rules()
        self.regulations = regulations or load_regulations()

    def generate_annual_rotations(
        self,
        farm_profile: FarmProfile,
        env: EnvironmentSummary,
        user_rice_limit_feddans: Optional[float] = None,
        include_rent: bool = False,
    ) -> RotationGenerationResult:
        """Enumerate and filter all Winter -> Summer crop pairs."""
        winter_crops = [c for c in self.crop_profiles.values() if c.season == "winter"]
        summer_crops = [c for c in self.crop_profiles.values() if c.season == "summer"]

        # Pre-compute suitability and water demand for each candidate crop
        suitability_evals: Dict[str, SuitabilityEvaluation] = {}
        water_demands: Dict[str, CropWaterDemand] = {}

        for c in itertools.chain(winter_crops, summer_crops):
            suitability_evals[c.crop_id] = evaluate_crop_suitability(
                crop=c,
                env=env,
                planting_month=c.sow_start_month,
                measured_salinity_ece_dsm=env.soil.salinity_estimated_dsm,
            )
            water_demands[c.crop_id] = calculate_crop_water_demand(
                crop=c,
                climate=env.climate,
                latitude_deg=farm_profile.coordinates.latitude,
            )

        # Cartesian product of winter and summer crops
        candidate_pairs = list(itertools.product(winter_crops, summer_crops))

        feasible: List[CandidateRotation] = []
        infeasible: List[CandidateRotation] = []
        blocking_counts: Dict[str, int] = {}

        for idx, (w_crop, s_crop) in enumerate(candidate_pairs, 1):
            rotation_crops = (w_crop, s_crop)
            season_names = ("winter", "summer")
            rot_id = f"rot_{w_crop.crop_id}_{s_crop.crop_id}"

            feas = evaluate_rotation_feasibility(
                crops=rotation_crops,
                suitability_evals=suitability_evals,
                water_demands=water_demands,
                cost_assumptions=self.cost_assumptions,
                rotation_rules=self.rotation_rules,
                regulations=self.regulations,
                farm_profile=farm_profile,
                user_rice_limit_feddans=user_rice_limit_feddans,
                include_rent=include_rent,
            )

            cand = CandidateRotation(
                rotation_id=rot_id,
                crops=rotation_crops,
                season_names=season_names,
                feasibility=feas,
            )

            if feas.is_feasible:
                feasible.append(cand)
            else:
                infeasible.append(cand)
                for reason in feas.hard_violations:
                    blocking_counts[reason] = blocking_counts.get(reason, 0) + 1

        relaxation_offered = False
        relaxation_notes: List[str] = []

        # If no plan is feasible: explain which constraints blocked it and offer controlled relaxation
        if len(feasible) == 0 and len(infeasible) > 0:
            relaxation_offered = True
            relaxation_notes.append(
                "لم تتوفر أي خطة مستوفية لكافة الشروط الحتمية. "
                "الأسباب الأكثر تكرارًا للمنع: " + "; ".join(f"{r} ({cnt} مرة)" for r, cnt in blocking_counts.items())
            )
            # Check if budget was the sole blocker
            budget_blocked_only = [
                cand for cand in infeasible
                if all("الميزانية" in v for v in cand.feasibility.hard_violations)
            ]
            if budget_blocked_only:
                relaxation_notes.append(
                    "يمكن إتاحة خيارات زراعية إضافية في حال زيادة الميزانية التشغيلية بنسبة 15-20% أو تفعيل التمويل الزراعي."
                )

        return RotationGenerationResult(
            feasible_rotations=feasible,
            infeasible_rotations=infeasible,
            blocking_reasons_summary=blocking_counts,
            relaxation_offered=relaxation_offered,
            relaxation_notes=relaxation_notes,
        )
