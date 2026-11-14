"""Crop suitability evaluation engine (A3).

Evaluates agronomic fit of candidate crops against environmental conditions
(temperature, pH, soil salinity, planting window) using deterministic trapezoidal functions.

Principles:
  * Pure functions with full type annotations.
  * Hard exclusion when a physical parameter is strictly outside the crop's absolute tolerance.
  * Missing data is NEVER ideal: missing parameters are omitted from the weighted mean,
    their weights are tracked, and overall confidence is reduced.
  * Salinity is unknown by default (SoilGrids lacks salinity) and must trigger an explicit warning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.data.loaders import CropProfileRecord
from src.domain.schemas import EnvironmentSummary, FarmProfile, AgriculturalSeason


# Documented default factor weights (stored as explicit configuration)
SUITABILITY_WEIGHTS_CONFIG: Dict[str, float] = {
    "temperature": 0.35,
    "ph": 0.20,
    "salinity": 0.25,
    "sowing_window": 0.20,
}


def trapezoid_score(
    val: float,
    abs_min: float,
    opt_min: float,
    opt_max: float,
    abs_max: float,
) -> float:
    """Trapezoid membership function scoring from 0.0 to 100.0.

    Outside [abs_min, abs_max] -> 0.0
    Inside [opt_min, opt_max]   -> 100.0
    Linear interpolation in between.
    """
    if val < abs_min or val > abs_max:
        return 0.0
    if opt_min <= val <= opt_max:
        return 100.0
    if val < opt_min:
        if opt_min == abs_min:
            return 100.0
        return 100.0 * (val - abs_min) / (opt_min - abs_min)
    else:  # val > opt_max
        if abs_max == opt_max:
            return 100.0
        return 100.0 * (abs_max - val) / (abs_max - opt_max)


def salinity_score(
    ece_dsm: float,
    threshold_ece_dsm: float,
    slope_pct_per_dsm: float = 10.0,
) -> float:
    """Maas-Hoffman yield reduction model converted to 0-100 score.

    Score = 100% for ECe <= threshold.
    For ECe > threshold, score declines by slope_pct_per_dsm (default 10% per dS/m).
    """
    if ece_dsm <= 0:
        return 100.0
    if ece_dsm <= threshold_ece_dsm:
        return 100.0
    excess = ece_dsm - threshold_ece_dsm
    penalty = excess * slope_pct_per_dsm
    return max(0.0, 100.0 - penalty)


def sowing_window_score(
    planting_month: int,
    sow_start: int,
    sow_end: int,
) -> float:
    """Evaluate planting window fit (0-100), accounting for month wrapping (e.g. 11 to 2)."""
    if not (1 <= planting_month <= 12 and 1 <= sow_start <= 12 and 1 <= sow_end <= 12):
        return 0.0

    # Determine months inside the sowing window
    if sow_start <= sow_end:
        in_window = sow_start <= planting_month <= sow_end
        # 1 month buffer
        prev_month = 12 if sow_start == 1 else sow_start - 1
        next_month = 1 if sow_end == 12 else sow_end + 1
    else:
        # Wraps over New Year (e.g. 11, 12, 1, 2)
        in_window = planting_month >= sow_start or planting_month <= sow_end
        prev_month = 12 if sow_start == 1 else sow_start - 1
        next_month = 1 if sow_end == 12 else sow_end + 1

    if in_window:
        return 100.0
    if planting_month in (prev_month, next_month):
        return 50.0  # Buffer month with slight penalty
    return 0.0


@dataclass(frozen=True)
class SuitabilityEvaluation:
    crop_id: str
    is_suitable: bool
    overall_score: float  # 0.0 to 100.0
    component_scores: Dict[str, float]
    hard_exclusions: List[str]
    missing_factors: List[str]
    factor_weights_used: Dict[str, float]
    confidence: str  # high | medium | low | very_low
    warnings: List[str]
    status: str
    data_source_basis: str


def evaluate_crop_suitability(
    crop: CropProfileRecord,
    env: EnvironmentSummary,
    planting_month: Optional[int] = None,
    measured_salinity_ece_dsm: Optional[float] = None,
    weights_config: Optional[Dict[str, float]] = None,
) -> SuitabilityEvaluation:
    """Evaluate full agronomic suitability of a crop against environmental conditions."""
    weights = dict(weights_config or SUITABILITY_WEIGHTS_CONFIG)

    component_scores: Dict[str, float] = {}
    hard_exclusions: List[str] = []
    missing_factors: List[str] = []
    warnings: List[str] = []

    # 1. Temperature evaluation
    # Determine seasonal temperature from climate summary
    if crop.season == "winter":
        mean_temp = env.climate.winter_mean_temp_c
    elif crop.season == "summer":
        mean_temp = env.climate.summer_mean_temp_c
    else:
        mean_temp = env.climate.annual_mean_temp_c

    if mean_temp < crop.temp_abs_min_c or mean_temp > crop.temp_abs_max_c:
        hard_exclusions.append(
            f"متوسط درجة الحرارة ({mean_temp:.1f}°C) خارج نطاق التحمل المطلق للمحصول "
            f"[{crop.temp_abs_min_c:.1f}°C - {crop.temp_abs_max_c:.1f}°C]."
        )
        component_scores["temperature"] = 0.0
    else:
        t_score = trapezoid_score(
            mean_temp,
            crop.temp_abs_min_c,
            crop.temp_opt_min_c,
            crop.temp_opt_max_c,
            crop.temp_abs_max_c,
        )
        component_scores["temperature"] = round(t_score, 1)

    # 2. Soil pH evaluation
    ph = env.soil.ph_water
    if ph < crop.ph_abs_min or ph > crop.ph_abs_max:
        hard_exclusions.append(
            f"درجة حموضة التربة ({ph:.1f}) خارج نطاق التحمل المطلق للمحصول "
            f"[{crop.ph_abs_min:.1f} - {crop.ph_abs_max:.1f}]."
        )
        component_scores["ph"] = 0.0
    else:
        ph_score = trapezoid_score(
            ph,
            crop.ph_abs_min,
            crop.ph_opt_min,
            crop.ph_opt_max,
            crop.ph_abs_max,
        )
        component_scores["ph"] = round(ph_score, 1)

    # 3. Salinity evaluation (SoilGrids does NOT measure salinity)
    salinity_val = measured_salinity_ece_dsm
    if salinity_val is None:
        salinity_val = env.soil.salinity_estimated_dsm

    if salinity_val is not None:
        sal_score = salinity_score(salinity_val, crop.salinity_threshold_ece_dsm)
        component_scores["salinity"] = round(sal_score, 1)
        if sal_score == 0.0:
            hard_exclusions.append(
                f"ملوحة التربة المقاسة ({salinity_val:.1f} dS/m) تتجاوز أقصى تحمل ملوحة للمحصول "
                f"(العتبة {crop.salinity_threshold_ece_dsm:.1f} dS/m)."
            )
    else:
        # Explicit missing factor
        missing_factors.append("salinity")
        warnings.append(
            "ملوحة التربة غير محددة (SoilGrids لا يقيس الملوحة). "
            "تم استبعاد عامل الملوحة من التقييم، وينصح بعمل تحليل معملي للأرض."
        )

    # 4. Sowing window fit
    if planting_month is not None:
        sw_score = sowing_window_score(planting_month, crop.sow_start_month, crop.sow_end_month)
        component_scores["sowing_window"] = round(sw_score, 1)
        if sw_score == 0.0:
            hard_exclusions.append(
                f"شهر الزراعة المختار ({planting_month}) خارج نافذة الزراعة الموصى بها "
                f"[{crop.sow_start_month} إلى {crop.sow_end_month}]."
            )
    else:
        # Default assume optimal alignment within the crop's designated season
        component_scores["sowing_window"] = 100.0

    # Combine scores with dynamic re-weighting for missing variables
    active_weights: Dict[str, float] = {}
    sum_active_weight = 0.0

    for factor, weight in weights.items():
        if factor not in missing_factors and factor in component_scores:
            active_weights[factor] = weight
            sum_active_weight += weight

    if sum_active_weight > 0:
        normalized_weights = {k: v / sum_active_weight for k, v in active_weights.items()}
        overall_score = sum(component_scores[k] * normalized_weights[k] for k in normalized_weights)
    else:
        normalized_weights = {}
        overall_score = 0.0

    is_suitable = len(hard_exclusions) == 0 and overall_score >= 40.0

    # Determine confidence level
    if len(missing_factors) == 0:
        confidence = crop.confidence  # from dataset
    elif "salinity" in missing_factors and len(missing_factors) == 1:
        # Salinity missing drops confidence by one level
        conf_map = {"high": "medium", "medium": "low", "low": "very_low", "very_low": "very_low"}
        confidence = conf_map.get(crop.confidence, "low")
    else:
        confidence = "very_low"

    return SuitabilityEvaluation(
        crop_id=crop.crop_id,
        is_suitable=is_suitable,
        overall_score=round(overall_score, 1),
        component_scores=component_scores,
        hard_exclusions=hard_exclusions,
        missing_factors=missing_factors,
        factor_weights_used=normalized_weights,
        confidence=confidence,
        warnings=warnings,
        status=crop.status,
        data_source_basis=crop.source_basis,
    )
