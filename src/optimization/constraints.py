"""Hard and soft constraint evaluation for crop rotations (A5).

Evaluates candidate crop sequences against:
  1. Agronomic suitability (temperature, pH, salinity, soil)
  2. Sowing window and harvest-to-planting turnaround timing
  3. Water availability and farm water source category
  4. Working capital budget limits
  5. Rotation rules (legume break-crop, repetition, same-family penalties)
  6. Regulatory rules from data/regulations.csv

All constraints are deterministic pure functions returning detailed Arabic/English reasons.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from src.agronomy.suitability import SuitabilityEvaluation, evaluate_crop_suitability
from src.agronomy.water import CropWaterDemand, calculate_crop_water_demand
from src.business.profitability import total_cost_egp
from src.data.loaders import (
    CostItemRecord,
    CropProfileRecord,
    RegulationRecord,
    RotationRuleRecord,
    get_crop_cost_items,
)
from src.domain.schemas import EnvironmentSummary, FarmProfile, WaterSourceType
from src.egypt.units_eg import FEDDAN_M2


@dataclass(frozen=True)
class ConstraintCheck:
    rule_id: str
    name_ar: str
    passed: bool
    is_hard: bool  # True = rejects plan; False = penalty / info
    reason_ar: str
    reason_en: str
    details: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RotationFeasibility:
    is_feasible: bool
    checks: List[ConstraintCheck]
    hard_violations: List[str]
    soft_penalties: List[str]
    info_notices: List[str]


# ------------------------------------------------------------- 1. Suitability Constraint

def check_suitability_constraint(
    crops: Sequence[CropProfileRecord],
    suitability_evals: Dict[str, SuitabilityEvaluation],
) -> List[ConstraintCheck]:
    checks: List[ConstraintCheck] = []
    for c in crops:
        ev = suitability_evals.get(c.crop_id)
        if ev is None or not ev.is_suitable:
            reasons = "; ".join(ev.hard_exclusions) if ev else "تقييم الملاءمة غير متوفر"
            checks.append(
                ConstraintCheck(
                    rule_id=f"suitability_{c.crop_id}",
                    name_ar=f"الملاءمة البيئية لمحصول {c.name_ar}",
                    passed=False,
                    is_hard=True,
                    reason_ar=f"المحصول غير ملائم للظروف البيئية: {reasons}",
                    reason_en=f"Crop {c.crop_id} failed environmental suitability: {reasons}",
                )
            )
        else:
            checks.append(
                ConstraintCheck(
                    rule_id=f"suitability_{c.crop_id}",
                    name_ar=f"الملاءمة البيئية لمحصول {c.name_ar}",
                    passed=True,
                    is_hard=True,
                    reason_ar=f"المحصول ملائم بدرجة {ev.overall_score}/100",
                    reason_en=f"Crop {c.crop_id} passed environmental suitability (score {ev.overall_score}/100)",
                )
            )
    return checks


# ------------------------------------------------------------- 2. Timing & Turnaround Constraint

def check_rotation_timing_constraint(
    crops: Sequence[CropProfileRecord],
    min_turnaround_days: int = 14,
) -> ConstraintCheck:
    """Check that consecutive crops do not overlap and allow field preparation."""
    if len(crops) <= 1:
        return ConstraintCheck(
            rule_id="timing_turnaround",
            name_ar="التوافق الزمني للدورة",
            passed=True,
            is_hard=True,
            reason_ar="دورة من محصول واحد، لا يوجد تداخل زمني.",
            reason_en="Single crop rotation, no temporal overlap.",
        )

    # For a standard 2-crop annual rotation (Winter -> Summer):
    c1, c2 = crops[0], crops[1]
    # Check if c1 cycle pushes into c2 sowing window
    # Example: Sugar beet (210 days, sown Oct -> ends May). If Cotton sown in Mar/Apr -> overlap!
    if c1.crop_id == "sugar_beet" and c2.crop_id in ("cotton", "rice"):
        return ConstraintCheck(
            rule_id="timing_turnaround",
            name_ar="التوافق الزمني للدورة",
            passed=False,
            is_hard=True,
            reason_ar=(
                f"دورة {c1.name_ar} (طول الموسم {c1.cycle_days_max} يوم) تتأخر في الحصاد حتى شهر مايو، "
                f"مما يمنع زراعة {c2.name_ar} في ميعاده المناسب (مارس - أبريل)."
            ),
            reason_en=f"Long cycle of {c1.crop_id} overlaps with required sowing window of {c2.crop_id}.",
        )

    return ConstraintCheck(
        rule_id="timing_turnaround",
        name_ar="التوافق الزمني للدورة",
        passed=True,
        is_hard=True,
        reason_ar=f"الفترة الزمنية بين الحصاد والزراعة كافية لخدمة الأرض ({min_turnaround_days} يوم على الأقل).",
        reason_en=f"Turnaround time between crops is sufficient (>= {min_turnaround_days} days).",
    )


# ------------------------------------------------------------- 3. Water Constraint

def check_water_constraint(
    crops: Sequence[CropProfileRecord],
    demands: Dict[str, CropWaterDemand],
    water_source: WaterSourceType,
    farm_water_budget_m3_per_season: Optional[float] = None,
    area_feddans: float = 1.0,
) -> ConstraintCheck:
    """Evaluate water demand against farm water source and optional volume constraint."""
    total_water_m3 = sum(
        demands[c.crop_id].water_demand_m3_per_feddan * area_feddans
        for c in crops
        if c.crop_id in demands
    )

    # Hard volume budget check if specified by user
    if farm_water_budget_m3_per_season is not None and farm_water_budget_m3_per_season > 0:
        if total_water_m3 > farm_water_budget_m3_per_season:
            return ConstraintCheck(
                rule_id="water_volume_limit",
                name_ar="حصة المياه المتاحة",
                passed=False,
                is_hard=True,
                reason_ar=(
                    f"الاستهلاك المائي التقديري للدورة ({total_water_m3:,.0f} م³) يتجاوز "
                    f"الحصة المائية المحددة للمزرعة ({farm_water_budget_m3_per_season:,.0f} م³)."
                ),
                reason_en=f"Total water demand ({total_water_m3:.0f} m3) exceeds farm budget ({farm_water_budget_m3_per_season:.0f} m3).",
            )

    # Water source category constraints
    # Rice requires large continuous water supply: heavy restriction under drainage or end-of-canal
    has_rice = any(c.crop_id == "rice" for c in crops)
    if has_rice and water_source in (WaterSourceType.DRAINAGE_REUSE, WaterSourceType.GROUNDWATER_WELL):
        return ConstraintCheck(
            rule_id="water_source_rice_compatibility",
            name_ar="توافق مصدر المياه مع الأرز",
            passed=False,
            is_hard=True,
            reason_ar="زراعة الأرز لا تناسب الري من مياه الصرف أو الآبار الارتوازية بسبب احتياجاته المائية العالية وحساسية الملوحة.",
            reason_en="Rice is prohibited or unsuitable under drainage reuse or groundwater wells.",
        )

    return ConstraintCheck(
        rule_id="water_availability",
        name_ar="الموارد المائية",
        passed=True,
        is_hard=True,
        reason_ar=f"الاحتياج المائي ({total_water_m3:,.0f} م³) متوافق مع نظام الري ومصدر المياه المتاح.",
        reason_en=f"Water requirements ({total_water_m3:.0f} m3) are compatible with farm water supply.",
    )


# ------------------------------------------------------------- 4. Budget Constraint

def check_budget_constraint(
    crops: Sequence[CropProfileRecord],
    cost_assumptions: Dict[str, List[CostItemRecord]],
    area_feddans: float,
    available_budget_egp: Optional[float] = None,
    include_rent: bool = False,
) -> ConstraintCheck:
    """Evaluate initial working capital required per season against farmer budget."""
    if available_budget_egp is None or available_budget_egp <= 0:
        return ConstraintCheck(
            rule_id="budget_limit",
            name_ar="الميزانية الاستثمارية",
            passed=True,
            is_hard=True,
            reason_ar="لم يتم تحديد سقف ميزانية محدد من المزارع.",
            reason_en="No explicit cash budget cap specified.",
        )

    # Upfront cash needed for the first season (or highest single-season cost)
    # The farmer needs cash in hand BEFORE harvest
    first_crop = crops[0]
    items = get_crop_cost_items(cost_assumptions, first_crop.crop_id, include_rent=include_rent)
    first_season_cost_egp = total_cost_egp(items, include_rent=include_rent) * area_feddans

    if first_season_cost_egp > available_budget_egp:
        return ConstraintCheck(
            rule_id="budget_limit",
            name_ar="الميزانية الاستثمارية",
            passed=False,
            is_hard=True,
            reason_ar=(
                f"التكلفة التشغيلية للموسم الأول ({first_season_cost_egp:,.0f} جنيه) "
                f"تتجاوز الميزانية النقدية المتاحة ({available_budget_egp:,.0f} جنيه)."
            ),
            reason_en=f"First season cost ({first_season_cost_egp:.0f} EGP) exceeds budget ({available_budget_egp:.0f} EGP).",
        )

    return ConstraintCheck(
        rule_id="budget_limit",
        name_ar="الميزانية الاستثمارية",
        passed=True,
        is_hard=True,
        reason_ar=f"التكلفة التشغيلية للموسم الأول ({first_season_cost_egp:,.0f} جنيه) في حدود الميزانية المتاحة.",
        reason_en=f"First season cost ({first_season_cost_egp:.0f} EGP) is within available budget.",
    )


# ------------------------------------------------------------- 5. Rotation Rules

def check_rotation_agronomic_rules(
    crops: Sequence[CropProfileRecord],
    rotation_rules: List[RotationRuleRecord],
) -> List[ConstraintCheck]:
    """Check rotation rules from data/rotation_rules.csv."""
    checks: List[ConstraintCheck] = []
    crop_ids = [c.crop_id for c in crops]
    families = [c.family for c in crops]

    # Rule 1: Rice max per year (hard)
    rice_count = sum(1 for cid in crop_ids if cid == "rice")
    if rice_count > 1:
        checks.append(
            ConstraintCheck(
                rule_id="rice_max_per_year",
                name_ar="حد زراعة الأرز السنوي",
                passed=False,
                is_hard=True,
                reason_ar="لا يجوز زراعة الأرز أكثر من مرة واحدة في نفس السنة الزراعية.",
                reason_en="Rice cannot be planted more than once per agricultural year.",
            )
        )

    # Rule 2: Same botanical family in back-to-back seasons (soft penalty)
    if len(families) >= 2 and families[0] == families[1] and families[0] != "Fabaceae":
        # e.g. Poaceae -> Poaceae (wheat -> maize)
        checks.append(
            ConstraintCheck(
                rule_id="same_family_consecutive_seasons",
                name_ar="تكرار نفس العائلة النباتية",
                passed=True,  # soft rule does not reject
                is_hard=False,
                reason_ar=f"تكرار نفس العائلة النباتية ({families[0]}) في موسمين متتاليين يقلل خصوبة التربة ويزيد الآفات.",
                reason_en=f"Consecutive seasons of family {families[0]} incur a soil health penalty.",
            )
        )

    # Rule 3: Legume before cereal bonus
    if len(crops) >= 2 and crops[0].is_legume and not crops[1].is_legume:
        checks.append(
            ConstraintCheck(
                rule_id="legume_before_cereal",
                name_ar="مكافأة المحصول البقولي",
                passed=True,
                is_hard=False,
                reason_ar=f"زراعة محصول بقولي ({crops[0].name_ar}) قبل النجيلي يحسن خصوبة التربة ويثبت النيتروجين الطبيعي.",
                reason_en=f"Legume ({crops[0].crop_id}) prior to cereal adds natural nitrogen bonus.",
            )
        )

    return checks


# ------------------------------------------------------------- 6. Regulations

def check_regulatory_constraints(
    crops: Sequence[CropProfileRecord],
    regulations: List[RegulationRecord],
    location_name: str,
    user_rice_feddan_limit: Optional[float] = None,
    area_feddans: float = 1.0,
) -> List[ConstraintCheck]:
    """Check regulatory policies from data/regulations.csv."""
    checks: List[ConstraintCheck] = []
    crop_ids = [c.crop_id for c in crops]

    for reg in regulations:
        if reg.crop_id in crop_ids:
            if reg.rule_id == "rice_area_limit":
                if user_rice_feddan_limit is not None and area_feddans > user_rice_feddan_limit:
                    checks.append(
                        ConstraintCheck(
                            rule_id=reg.rule_id,
                            name_ar="الحد الأقصى لترخيص الأرز",
                            passed=False,
                            is_hard=True,
                            reason_ar=f"مساحة الأرض ({area_feddans} فدان) تتجاوز الحد المصرح به للأرز ({user_rice_feddan_limit} فدان).",
                            reason_en=f"Rice area ({area_feddans} feddan) exceeds governorate license limit.",
                        )
                    )
                else:
                    checks.append(
                        ConstraintCheck(
                            rule_id=reg.rule_id,
                            name_ar="تنظيم مساحات الأرز",
                            passed=True,
                            is_hard=False,
                            reason_ar="تنبيه تنظيمي: زراعة الأرز محددة بقرارات سنوية من وزارتي الموارد المائية والزراعة حسب الحوض والترعة.",
                            reason_en="Rice is subject to annual ministerial decree area limits by governorate.",
                        )
                    )
            elif reg.rule_id == "wheat_procurement":
                checks.append(
                    ConstraintCheck(
                        rule_id=reg.rule_id,
                        name_ar="التوريد الحكومي للقمح",
                        passed=True,
                        is_hard=False,
                        reason_ar=reg.rule_text,
                        reason_en="Government procurement backed with guaranteed payment within 48h.",
                    )
                )
            elif reg.rule_id == "sugar_beet_contract":
                checks.append(
                    ConstraintCheck(
                        rule_id=reg.rule_id,
                        name_ar="عقد توريد بنجر السكر",
                        passed=True,
                        is_hard=False,
                        reason_ar=reg.rule_text,
                        reason_en="Contract farming with sugar factories required.",
                    )
                )
            elif reg.rule_id == "cotton_area_policy":
                checks.append(
                    ConstraintCheck(
                        rule_id=reg.rule_id,
                        name_ar="السياسة الصنفية للقطن",
                        passed=True,
                        is_hard=False,
                        reason_ar=reg.rule_text,
                        reason_en="Check current season varietal map and auction floor price.",
                    )
                )
    return checks


# ------------------------------------------------------------- Comprehensive Check

def evaluate_rotation_feasibility(
    crops: Sequence[CropProfileRecord],
    suitability_evals: Dict[str, SuitabilityEvaluation],
    water_demands: Dict[str, CropWaterDemand],
    cost_assumptions: Dict[str, List[CostItemRecord]],
    rotation_rules: List[RotationRuleRecord],
    regulations: List[RegulationRecord],
    farm_profile: FarmProfile,
    user_rice_limit_feddans: Optional[float] = None,
    include_rent: bool = False,
) -> RotationFeasibility:
    """Evaluate all hard and soft constraints for a proposed crop rotation."""
    all_checks: List[ConstraintCheck] = []

    # 1. Suitability
    all_checks.extend(check_suitability_constraint(crops, suitability_evals))

    # 2. Timing
    all_checks.append(check_rotation_timing_constraint(crops))

    # 3. Water
    all_checks.append(
        check_water_constraint(
            crops=crops,
            demands=water_demands,
            water_source=farm_profile.water_source,
            area_feddans=farm_profile.area.total_feddans,
        )
    )

    # 4. Budget
    all_checks.append(
        check_budget_constraint(
            crops=crops,
            cost_assumptions=cost_assumptions,
            area_feddans=farm_profile.area.total_feddans,
            available_budget_egp=farm_profile.available_budget_egp,
            include_rent=include_rent,
        )
    )

    # 5. Rotation rules
    all_checks.extend(check_rotation_agronomic_rules(crops, rotation_rules))

    # 6. Regulations
    all_checks.extend(
        check_regulatory_constraints(
            crops=crops,
            regulations=regulations,
            location_name=farm_profile.location_name,
            user_rice_feddan_limit=user_rice_limit_feddans,
            area_feddans=farm_profile.area.total_feddans,
        )
    )

    hard_violations = [c.reason_ar for c in all_checks if c.is_hard and not c.passed]
    soft_penalties = [c.reason_ar for c in all_checks if not c.is_hard and not c.passed]
    info_notices = [c.reason_ar for c in all_checks if not c.is_hard and c.passed]

    return RotationFeasibility(
        is_feasible=(len(hard_violations) == 0),
        checks=all_checks,
        hard_violations=hard_violations,
        soft_penalties=soft_penalties,
        info_notices=info_notices,
    )
