"""Multi-objective evaluation and economic metrics for crop rotations (A6).

Computes:
  1. Operating Profit (EGP) and ROI (%) using src.business.profitability
  2. Water use (m3/feddan and total m3)
  3. Soil health proxy (explicitly labelled as a proxy: legume in rotation)
  4. Climate and market risk score (procurement backing, price volatility)
  5. Cash view (pre-harvest cash requirement and payment delay)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.agronomy.water import CropWaterDemand, calculate_crop_water_demand
from src.business.profitability import (
    PlanEconomics,
    calculate_economics,
    per_feddan,
    revenue_egp,
    total_cost_egp,
)
from src.data.loaders import (
    CostItemRecord,
    CropPriceRecord,
    CropProfileRecord,
    get_crop_cost_items,
    load_crop_prices,
)
from src.domain.schemas import CostBreakdown, PlanMetrics
from src.egypt.units_eg import FEDDAN_M2, yield_local_unit_per_feddan_to_kg_per_m2


@dataclass(frozen=True)
class RotationMetrics:
    rotation_id: str
    primary_crop: CropProfileRecord
    all_crops: Tuple[CropProfileRecord, ...]
    area_feddans: float
    area_m2: float
    gross_revenue_egp: float
    total_cost_egp: float
    operating_profit_egp: float
    operating_profit_per_feddan_egp: float
    roi_percent: Optional[float]
    total_water_demand_m3: float
    water_demand_m3_per_feddan: float
    soil_health_proxy_score: float  # 0 to 100, explicitly a proxy
    risk_level: str  # Low | Medium | High
    risk_rationale_ar: str
    risk_rationale_en: str
    upfront_cash_needed_egp: float
    payment_delay_days: int
    itemized_costs_per_feddan: Dict[str, float]
    provenance_status: str
    confidence: str


def evaluate_rotation_objectives(
    crops: Tuple[CropProfileRecord, ...],
    crop_prices: Dict[str, CropPriceRecord],
    cost_assumptions: Dict[str, List[CostItemRecord]],
    water_demands: Dict[str, CropWaterDemand],
    area_feddans: float,
    include_rent: bool = False,
) -> RotationMetrics:
    """Compute consolidated multi-objective metrics across an entire rotation sequence."""
    area_m2 = area_feddans * FEDDAN_M2

    total_rev = 0.0
    total_cost = 0.0
    total_water = 0.0
    aggregated_cost_items: Dict[str, float] = {}
    upfront_cash = 0.0
    statuses = []
    confidences = []

    for idx, c in enumerate(crops):
        # 1. Yield & price in SI units
        # Midpoint of yield in t/feddan -> kg/m2
        yield_t_per_feddan = (c.yield_low_t_per_feddan + c.yield_high_t_per_feddan) / 2.0
        yield_kg_per_m2 = (yield_t_per_feddan * 1000.0) / FEDDAN_M2

        price_rec = crop_prices.get(c.crop_id)
        price_per_kg = price_rec.price_mid_egp_per_kg if price_rec else 15.0

        # Cost items from cost_assumptions.csv
        c_items = get_crop_cost_items(cost_assumptions, c.crop_id, include_rent=include_rent)
        # Convert cost items per feddan to total EGP for the field
        field_cost_items = {k: v * area_feddans for k, v in c_items.items()}

        econ = calculate_economics(
            yield_kg_per_m2=yield_kg_per_m2,
            price_egp_per_kg=price_per_kg,
            area_m2=area_m2,
            cost_items=field_cost_items,
            include_rent=include_rent,
        )

        total_rev += econ.revenue_egp
        total_cost += econ.total_cost_egp

        # Itemized cost per feddan accumulation
        for k, v in c_items.items():
            aggregated_cost_items[k] = aggregated_cost_items.get(k, 0.0) + v

        # First season determines upfront cash needed before any harvest revenue
        if idx == 0:
            upfront_cash = econ.total_cost_egp

        # Water
        w_demand = water_demands.get(c.crop_id)
        if w_demand:
            total_water += w_demand.water_demand_m3_per_feddan * area_feddans

        statuses.append(c.status)
        confidences.append(c.confidence)

    op_profit = total_rev - total_cost
    profit_per_fed = op_profit / area_feddans if area_feddans > 0 else 0.0
    water_per_fed = total_water / area_feddans if area_feddans > 0 else 0.0
    roi = (op_profit / total_cost * 100.0) if total_cost > 0 else None

    # Soil health proxy: presence of legume in rotation (faba_bean or berseem)
    has_legume = any(c.is_legume for c in crops)
    soil_health_score = 90.0 if has_legume else 45.0

    # Risk evaluation
    has_wheat = any(c.crop_id == "wheat" for c in crops)
    has_onion = any(c.crop_id == "onion" for c in crops)
    if has_wheat and not has_onion:
        risk_level = "Low"
        risk_ar = "مخاطر منخفضة: مدعوم بمنظومة توريد حكومية للقمح وسعر ضمان معتمد ودفع سريع."
        risk_en = "Low risk: backed by national wheat procurement guarantee and rapid payment."
        payment_delay = 2  # 48 hours per regulations.csv
    elif has_onion:
        risk_level = "High"
        risk_ar = "مخاطر مرتفعة: محصول البصل سريع التأثر بتزاحم الزراعات وتقلبات أسعار الجملة."
        risk_en = "High risk: market crowding and wholesale price volatility for perishable crops."
        payment_delay = 14
    else:
        risk_level = "Medium"
        risk_ar = "مخاطر متوسطة: أسعار مجزية ترتبط بأسعار الأعلاف الحرة وحركة السوق المحلي."
        risk_en = "Medium risk: market prices track open fodder and local demand."
        payment_delay = 7

    rot_id = "_".join(c.crop_id for c in crops)
    provenance_status = "ai_draft_unverified" if any("draft" in s for s in statuses) else "source"
    overall_confidence = "low" if "low" in confidences else "medium"

    return RotationMetrics(
        rotation_id=rot_id,
        primary_crop=crops[0],
        all_crops=crops,
        area_feddans=area_feddans,
        area_m2=area_m2,
        gross_revenue_egp=round(total_rev, 2),
        total_cost_egp=round(total_cost, 2),
        operating_profit_egp=round(op_profit, 2),
        operating_profit_per_feddan_egp=round(profit_per_fed, 2),
        roi_percent=round(roi, 1) if roi is not None else None,
        total_water_demand_m3=round(total_water, 1),
        water_demand_m3_per_feddan=round(water_per_fed, 1),
        soil_health_proxy_score=soil_health_score,
        risk_level=risk_level,
        risk_rationale_ar=risk_ar,
        risk_rationale_en=risk_en,
        upfront_cash_needed_egp=round(upfront_cash, 2),
        payment_delay_days=payment_delay,
        itemized_costs_per_feddan=aggregated_cost_items,
        provenance_status=provenance_status,
        confidence=overall_confidence,
    )


def rotation_metrics_to_plan_metrics(m: RotationMetrics) -> PlanMetrics:
    """Map pure rotation metrics to Track B PlanMetrics schema."""
    # Convert itemized costs
    cb = CostBreakdown(
        seeds_seedlings_egp=round(m.itemized_costs_per_feddan.get("seed", 0.0), 2),
        fertilizers_and_soil_amendments_egp=round(m.itemized_costs_per_feddan.get("fertilizer", 0.0), 2),
        fuel_and_irrigation_electricity_egp=round(m.itemized_costs_per_feddan.get("irrigation_pumping", 0.0), 2),
        labor_and_machinery_egp=round(
            m.itemized_costs_per_feddan.get("hired_labor", 0.0) + m.itemized_costs_per_feddan.get("machinery_hire", 0.0), 2
        ),
        land_preparation_egp=round(
            m.itemized_costs_per_feddan.get("other", 0.0)
            + m.itemized_costs_per_feddan.get("crop_protection", 0.0)
            + m.itemized_costs_per_feddan.get("transport", 0.0)
            + m.itemized_costs_per_feddan.get("trader_commission", 0.0),
            2,
        ),
        total_cost_per_feddan_egp=round(m.total_cost_egp / m.area_feddans, 2) if m.area_feddans > 0 else 0.0,
    )

    return PlanMetrics(
        gross_revenue_egp_per_feddan=round(m.gross_revenue_egp / m.area_feddans, 2) if m.area_feddans > 0 else 0.0,
        total_gross_revenue_egp=m.gross_revenue_egp,
        cost_breakdown=cb,
        total_cost_egp=m.total_cost_egp,
        net_profit_egp_per_feddan=m.operating_profit_per_feddan_egp,
        total_net_profit_egp=m.operating_profit_egp,
        roi_percentage=m.roi_percent or 0.0,
        water_demand_m3_per_feddan=m.water_demand_m3_per_feddan,
        total_water_demand_m3=m.total_water_demand_m3,
        risk_level=m.risk_level,
        risk_rationale=m.risk_rationale_ar,
    )
