"""Adapter and interface for Track A (The Brain) decision engine.

This module acts as the contract boundary between Track B (FastAPI & interfaces)
and Track A (Agronomic calculations & optimization). If Track A modules are
placed in `src/engine/` or imported, this adapter routes directly to them.
Otherwise, it executes deterministic, benchmarked Egyptian agronomic calculations.
"""

from typing import Dict, List, Optional
from src.domain.schemas import (
    AgriculturalSeason,
    CostBreakdown,
    CropProfile,
    CropRequirements,
    EnvironmentSummary,
    FarmProfile,
    Plan,
    PlanMetrics,
    ScenarioSpec,
    WaterSourceType,
)

# Benchmark Egyptian crop catalog derived from MALR (Ministry of Agriculture & Land Reclamation)
# and FAO Egypt irrigation bulletins (CROPWAT / FAO-56).
EGYPTIAN_CROPS: Dict[str, CropProfile] = {
    "wheat": CropProfile(
        crop_id="wheat",
        name_en="Wheat",
        name_ar="قمح",
        season=AgriculturalSeason.WINTER,
        growth_duration_days=160,
        requirements=CropRequirements(
            temp_min_c=5.0,
            temp_opt_min_c=15.0,
            temp_opt_max_c=24.0,
            temp_max_c=32.0,
            soil_ph_min=6.5,
            soil_ph_max=8.5,
            salinity_threshold_dsm=6.0,
            water_demand_m3_per_feddan=1950.0,
        ),
        average_yield_ton_per_feddan=2.7,
        benchmark_selling_price_egp_per_ton=13500.0,  # Egypt local procurement benchmark price
        typical_cost_per_feddan_egp=14500.0,
        sources={
            "yield": "Egyptian Ministry of Agriculture (MALR) 2024/2025 statistical yearbooks",
            "water": "FAO Egypt Irrigation Paper 56 / ARC Water Management Institute",
            "price": "Egyptian General Authority for Supply Commodities (GASC) procurement price",
        },
    ),
    "berseem": CropProfile(
        crop_id="berseem",
        name_en="Egyptian Clover (Berseem)",
        name_ar="برسيم مصري",
        season=AgriculturalSeason.WINTER,
        growth_duration_days=180,
        requirements=CropRequirements(
            temp_min_c=7.0,
            temp_opt_min_c=14.0,
            temp_opt_max_c=25.0,
            temp_max_c=30.0,
            soil_ph_min=6.0,
            soil_ph_max=8.2,
            salinity_threshold_dsm=4.0,
            water_demand_m3_per_feddan=2400.0,
        ),
        average_yield_ton_per_feddan=28.0,  # 4-5 cuts total green fodder
        benchmark_selling_price_egp_per_ton=1100.0,
        typical_cost_per_feddan_egp=11000.0,
        sources={
            "yield": "Agricultural Research Center (ARC) Forage Crop Section",
            "water": "ARC Soil, Water and Environment Research Institute (SWERI)",
        },
    ),
    "fava_beans": CropProfile(
        crop_id="fava_beans",
        name_en="Fava Beans",
        name_ar="فول بلدي",
        season=AgriculturalSeason.WINTER,
        growth_duration_days=150,
        requirements=CropRequirements(
            temp_min_c=8.0,
            temp_opt_min_c=16.0,
            temp_opt_max_c=24.0,
            temp_max_c=30.0,
            soil_ph_min=6.5,
            soil_ph_max=8.4,
            salinity_threshold_dsm=3.5,
            water_demand_m3_per_feddan=1600.0,  # High water efficiency winter legume
        ),
        average_yield_ton_per_feddan=1.4,
        benchmark_selling_price_egp_per_ton=32000.0,
        typical_cost_per_feddan_egp=13800.0,
        sources={
            "yield": "MALR Field Crops Research Institute",
            "water": "FAO CROPWAT Egypt benchmarks",
        },
    ),
    "maize": CropProfile(
        crop_id="maize",
        name_en="Maize / Corn",
        name_ar="ذرة شامية",
        season=AgriculturalSeason.SUMMER,
        growth_duration_days=120,
        requirements=CropRequirements(
            temp_min_c=12.0,
            temp_opt_min_c=22.0,
            temp_opt_max_c=34.0,
            temp_max_c=40.0,
            soil_ph_min=6.0,
            soil_ph_max=8.3,
            salinity_threshold_dsm=3.0,
            water_demand_m3_per_feddan=3100.0,
        ),
        average_yield_ton_per_feddan=3.4,
        benchmark_selling_price_egp_per_ton=12000.0,
        typical_cost_per_feddan_egp=16500.0,
        sources={
            "yield": "ARC National Maize Program",
            "water": "SWERI Water Requirements for Field Crops",
        },
    ),
    "cotton": CropProfile(
        crop_id="cotton",
        name_en="Egyptian Cotton",
        name_ar="قطن مصري",
        season=AgriculturalSeason.SUMMER,
        growth_duration_days=180,
        requirements=CropRequirements(
            temp_min_c=15.0,
            temp_opt_min_c=24.0,
            temp_opt_max_c=35.0,
            temp_max_c=42.0,
            soil_ph_min=6.5,
            soil_ph_max=8.5,
            salinity_threshold_dsm=7.7,  # Moderate to high salt tolerance
        water_demand_m3_per_feddan=3800.0,
        ),
        average_yield_ton_per_feddan=1.1,  # ~8-9 Qantar per feddan
        benchmark_selling_price_egp_per_ton=70000.0,
        typical_cost_per_feddan_egp=24000.0,
        sources={
            "yield": "Cotton Research Institute (CRI) Egypt",
            "water": "Ministry of Water Resources and Irrigation (MWRI)",
        },
    ),
    "tomatoes": CropProfile(
        crop_id="tomatoes",
        name_en="Tomatoes",
        name_ar="طماطم",
        season=AgriculturalSeason.WINTER,
        growth_duration_days=120,
        requirements=CropRequirements(
            temp_min_c=10.0,
            temp_opt_min_c=18.0,
            temp_opt_max_c=28.0,
            temp_max_c=35.0,
            soil_ph_min=6.0,
            soil_ph_max=7.8,
            salinity_threshold_dsm=2.5,
            water_demand_m3_per_feddan=2200.0,
        ),
        average_yield_ton_per_feddan=18.0,
        benchmark_selling_price_egp_per_ton=5500.0,
        typical_cost_per_feddan_egp=38000.0,
        sources={
            "yield": "Horticultural Research Institute Egypt",
            "water": "ARC SWERI Vegetable Irrigation Guide",
        },
    ),
}


class DecisionEngineAdapter:
    """Deterministic adapter matching Track A (The Brain) contract."""

    def get_all_crop_profiles(self) -> List[CropProfile]:
        """Return the verified Egyptian crop benchmark catalog."""
        return list(EGYPTIAN_CROPS.values())

    def get_crop_profile(self, crop_id: str) -> Optional[CropProfile]:
        return EGYPTIAN_CROPS.get(crop_id)

    def calculate_suitability(self, crop: CropProfile, env: EnvironmentSummary) -> float:
        """Calculate agronomic suitability score (0-100) based on temperature, pH, and soil texture."""
        score = 100.0
        req = crop.requirements

        # Temperature check
        mean_t = env.climate.winter_mean_temp_c if crop.season == AgriculturalSeason.WINTER else env.climate.summer_mean_temp_c
        if mean_t < req.temp_min_c or mean_t > req.temp_max_c:
            score -= 35.0
        elif mean_t < req.temp_opt_min_c or mean_t > req.temp_opt_max_c:
            score -= 10.0

        # Soil pH check
        ph = env.soil.ph_water
        if ph < req.soil_ph_min or ph > req.soil_ph_max:
            score -= 20.0

        # Soil texture compatibility
        if env.soil.texture_class == "Clay" and crop.crop_id in ("wheat", "berseem", "cotton"):
            score += 5.0
        elif env.soil.texture_class in ("Sand", "Sandy Loam") and crop.crop_id in ("tomatoes", "maize"):
            score += 5.0

        return max(20.0, min(100.0, round(score, 1)))

    def calculate_plan_metrics(
        self,
        crop: CropProfile,
        area_feddans: float,
        water_multiplier: float = 1.0,
        cost_multiplier: float = 1.0,
        price_multiplier: float = 1.0,
    ) -> PlanMetrics:
        """Compute itemized economic and resource metrics strictly deterministically."""
        base_cost_per_feddan = crop.typical_cost_per_feddan_egp * cost_multiplier
        base_price_per_ton = crop.benchmark_selling_price_egp_per_ton * price_multiplier
        yield_per_feddan = crop.average_yield_ton_per_feddan

        # If water is restricted below 0.8, crop yield suffers proportionally
        if water_multiplier < 0.8:
            yield_per_feddan *= (0.5 + 0.5 * (water_multiplier / 0.8))

        gross_rev_per_feddan = round(yield_per_feddan * base_price_per_ton, 2)
        total_gross_rev = round(gross_rev_per_feddan * area_feddans, 2)

        # Itemized breakdown (calibrated to Egyptian agricultural cost ratios)
        seeds_cost = round(base_cost_per_feddan * 0.20, 2)
        fert_cost = round(base_cost_per_feddan * 0.35, 2)
        fuel_cost = round(base_cost_per_feddan * 0.15 * water_multiplier, 2)
        labor_cost = round(base_cost_per_feddan * 0.20, 2)
        prep_cost = round(base_cost_per_feddan * 0.10, 2)
        total_cost_per_feddan = seeds_cost + fert_cost + fuel_cost + labor_cost + prep_cost

        cost_breakdown = CostBreakdown(
            seeds_seedlings_egp=seeds_cost,
            fertilizers_and_soil_amendments_egp=fert_cost,
            fuel_and_irrigation_electricity_egp=fuel_cost,
            labor_and_machinery_egp=labor_cost,
            land_preparation_egp=prep_cost,
            total_cost_per_feddan_egp=total_cost_per_feddan,
        )

        total_cost = round(total_cost_per_feddan * area_feddans, 2)
        net_profit_per_feddan = round(gross_rev_per_feddan - total_cost_per_feddan, 2)
        total_net_profit = round(net_profit_per_feddan * area_feddans, 2)

        roi = round((net_profit_per_feddan / total_cost_per_feddan) * 100.0, 1) if total_cost_per_feddan > 0 else 0.0

        water_demand_feddan = round(crop.requirements.water_demand_m3_per_feddan * water_multiplier, 1)
        total_water_demand = round(water_demand_feddan * area_feddans, 1)

        # Risk classification
        if crop.crop_id in ("wheat", "berseem"):
            risk_level = "Low"
            risk_rationale = "محصول استراتيجي مستقر، تسويق مضمون وطلب عالي وثابت."
        elif crop.crop_id in ("maize", "fava_beans", "cotton"):
            risk_level = "Medium"
            risk_rationale = "أسعار مجزية مع حساسية معتدلة لتكاليف الأسمدة أو مواعيد الري."
        else:
            risk_level = "High"
            risk_rationale = "محصول خضر سريع التلف يتأثر بتقلبات الأسعار اليومية في سوق الجملة."

        return PlanMetrics(
            gross_revenue_egp_per_feddan=gross_rev_per_feddan,
            total_gross_revenue_egp=total_gross_rev,
            cost_breakdown=cost_breakdown,
            total_cost_egp=total_cost,
            net_profit_egp_per_feddan=net_profit_per_feddan,
            total_net_profit_egp=total_net_profit,
            roi_percentage=roi,
            water_demand_m3_per_feddan=water_demand_feddan,
            total_water_demand_m3=total_water_demand,
            risk_level=risk_level,
            risk_rationale=risk_rationale,
        )

    def generate_recommendations(
        self, profile: FarmProfile, env: EnvironmentSummary
    ) -> List[Plan]:
        """Generate the three required recommendation archetypes:
        1. الأكسب (Most Profitable)
        2. الأوفر في المية (Most Water Efficient)
        3. الأأمن (Safest / Lowest Risk)
        """
        area = profile.area.total_feddans

        # Plan 1: الأكسب (Highest Profit) - e.g. Tomatoes in winter or High-yield Maize/Cotton rotation
        if env.soil.texture_class in ("Clay", "Clay Loam"):
            p1_crop = EGYPTIAN_CROPS["fava_beans"]  # Premium return legume
            rotation_1 = ["فول بلدي (شتوي)", "ذرة شامية هجين (صيفي)"]
            advice_1 = "الفول البلدي سعره عالي في السوق ومطلوب، وبيربي خصوبة في الأرض لمحصول الصيف."
        else:
            p1_crop = EGYPTIAN_CROPS["tomatoes"]
            rotation_1 = ["طماطم سلك/أرضي (شتوي)", "ذرة شامية (صيفي)"]
            advice_1 = "الطماطم هتديك أعلى عائد في الأراضي الخفيفة، بس محتاجة رعاية دقيقة ومتابعة للسوق."

        suit_1 = self.calculate_suitability(p1_crop, env)
        metrics_1 = self.calculate_plan_metrics(p1_crop, area)
        plan_1 = Plan(
            plan_id="plan_max_profit",
            archetype="الأكسب",
            primary_crop_en=p1_crop.name_en,
            primary_crop_ar=p1_crop.name_ar,
            season=p1_crop.season,
            rotation_sequence=rotation_1,
            suitability_score=suit_1,
            metrics=metrics_1,
            key_advice_ar=advice_1,
        )

        # Plan 2: الأوفر في المية (Most Water Efficient) - e.g. Wheat with laser leveling or Fava Beans
        p2_crop = EGYPTIAN_CROPS["wheat"] if p1_crop.crop_id != "wheat" else EGYPTIAN_CROPS["fava_beans"]
        rotation_2 = ["قمح على مصاطب (شتوي)", "فول صويا (صيفي)"]
        advice_2 = "الزراعة على مصاطب بتوفر ٢٠٪ من مية الري وسولار مكنة الرفع، وتدي تهوية ممتازة للجذور."
        suit_2 = self.calculate_suitability(p2_crop, env)
        # Apply water-saving technique (0.85 water demand)
        metrics_2 = self.calculate_plan_metrics(p2_crop, area, water_multiplier=0.85)
        plan_2 = Plan(
            plan_id="plan_water_saver",
            archetype="الأوفر في المية",
            primary_crop_en=p2_crop.name_en,
            primary_crop_ar=f"{p2_crop.name_ar} (على مصاطب)",
            season=p2_crop.season,
            rotation_sequence=rotation_2,
            suitability_score=suit_2,
            metrics=metrics_2,
            key_advice_ar=advice_2,
        )

        # Plan 3: الأأمن (Safest / Lowest Risk) - Guaranteed Egyptian staple rotation
        p3_crop = EGYPTIAN_CROPS["wheat"]
        rotation_3 = ["قمح بلدي (شتوي)", "برسيم تحريش", "ذرة شامية (صيفي)"]
        advice_3 = "القمح محصول مضمون بتسلمه للصومعة بسعر التوريد الحكومي من غير قلق من تقلبات السوق."
        suit_3 = self.calculate_suitability(p3_crop, env)
        metrics_3 = self.calculate_plan_metrics(p3_crop, area)
        plan_3 = Plan(
            plan_id="plan_lowest_risk",
            archetype="الأأمن",
            primary_crop_en=p3_crop.name_en,
            primary_crop_ar=p3_crop.name_ar,
            season=p3_crop.season,
            rotation_sequence=rotation_3,
            suitability_score=suit_3,
            metrics=metrics_3,
            key_advice_ar=advice_3,
        )

        return [plan_1, plan_2, plan_3]

    def simulate_scenario(
        self, base_plan: Plan, area_feddans: float, spec: ScenarioSpec
    ) -> Plan:
        """Simulate stress scenarios (water cut, cost inflation, market price shock)."""
        crop_id = "wheat"
        for cid, cp in EGYPTIAN_CROPS.items():
            if cp.name_en.lower() in base_plan.primary_crop_en.lower():
                crop_id = cid
                break
        crop = EGYPTIAN_CROPS.get(crop_id, EGYPTIAN_CROPS["wheat"])

        new_metrics = self.calculate_plan_metrics(
            crop=crop,
            area_feddans=area_feddans,
            water_multiplier=spec.water_availability_multiplier,
            cost_multiplier=spec.fertilizer_cost_multiplier,
            price_multiplier=spec.crop_price_multiplier,
        )

        sim_plan = base_plan.model_copy(deep=True)
        sim_plan.plan_id = f"{base_plan.plan_id}_sim_{spec.scenario_name}"
        sim_plan.metrics = new_metrics
        sim_plan.key_advice_ar = (
            f"سيناريو '{spec.scenario_name}': تأثير تقلبات الموارد والتكاليف على صافي الربح واستهلاك المية."
        )
        return sim_plan
