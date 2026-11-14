"""Farm economics for FieldWise AI (A2).

Internal units (see CLAUDE.md): area in m2, yield in kg/m2, price in EGP/kg,
money in EGP. Converting to feddan etc. happens only through units_eg.

Formulas (implementation plan, section 6.4):
    Revenue         = yield x price x area
    TotalCost       = sum of the cost items given (rent optional)
    OperatingProfit = Revenue - TotalCost
    ROI (%)         = OperatingProfit / TotalCost x 100
    BreakEvenYield  = TotalCost / (price x area)        [kg/m2]
    BreakEvenPrice  = TotalCost / (yield x area)        [EGP/kg]

Rules:
  * Costs are NEVER invented: only the items the caller passes are summed.
  * Ratios that cannot be defined (division by zero) return None, not 0.
  * Negative yield, price, area or cost items raise ValueError.
  * "OperatingProfit" is not net profit: financing, tax and depreciation
    are not included.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from src.egypt.units_eg import FEDDAN_M2

RENT_KEY = "rent"


def _non_negative(value: float, name: str) -> float:
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


# ------------------------------------------------------------------ pieces
def revenue_egp(yield_kg_per_m2: float, price_egp_per_kg: float, area_m2: float) -> float:
    """Revenue = yield x price x area."""
    return (
        _non_negative(yield_kg_per_m2, "yield_kg_per_m2")
        * _non_negative(price_egp_per_kg, "price_egp_per_kg")
        * _non_negative(area_m2, "area_m2")
    )


def total_cost_egp(items: Mapping[str, float], include_rent: bool = True) -> float:
    """Sum of the cost items given. Item 'rent' is skipped if include_rent=False."""
    total = 0.0
    for name, value in items.items():
        _non_negative(value, f"cost item '{name}'")
        if name == RENT_KEY and not include_rent:
            continue
        total += value
    return total


def operating_profit_egp(revenue: float, total_cost: float) -> float:
    """Can be negative (a loss)."""
    return revenue - total_cost


def roi_percent(profit: float, total_cost: float) -> Optional[float]:
    """ROI = profit / cost x 100. None if cost is 0 (undefined)."""
    if total_cost == 0:
        return None
    return profit / total_cost * 100


def break_even_yield_kg_per_m2(
    total_cost: float, price_egp_per_kg: float, area_m2: float
) -> Optional[float]:
    """Yield needed to cover the cost. None if price or area is 0."""
    _non_negative(price_egp_per_kg, "price_egp_per_kg")
    _non_negative(area_m2, "area_m2")
    denominator = price_egp_per_kg * area_m2
    if denominator == 0:
        return None
    return total_cost / denominator


def break_even_price_egp_per_kg(
    total_cost: float, yield_kg_per_m2: float, area_m2: float
) -> Optional[float]:
    """Price needed to cover the cost. None if yield or area is 0."""
    _non_negative(yield_kg_per_m2, "yield_kg_per_m2")
    _non_negative(area_m2, "area_m2")
    denominator = yield_kg_per_m2 * area_m2
    if denominator == 0:
        return None
    return total_cost / denominator


def per_feddan(total_egp: float, area_m2: float) -> Optional[float]:
    """Whole-farm EGP -> EGP per feddan. None if area is 0."""
    _non_negative(area_m2, "area_m2")
    if area_m2 == 0:
        return None
    return total_egp / area_m2 * FEDDAN_M2


# ------------------------------------------------------------- full result
@dataclass(frozen=True)
class PlanEconomics:
    revenue_egp: float
    total_cost_egp: float
    operating_profit_egp: float
    roi_percent: Optional[float]
    break_even_yield_kg_per_m2: Optional[float]
    break_even_price_egp_per_kg: Optional[float]
    profit_per_feddan_egp: Optional[float]


def calculate_economics(
    yield_kg_per_m2: float,
    price_egp_per_kg: float,
    area_m2: float,
    cost_items: Mapping[str, float],
    include_rent: bool = True,
) -> PlanEconomics:
    """One crop, one season: all the numbers in one call."""
    revenue = revenue_egp(yield_kg_per_m2, price_egp_per_kg, area_m2)
    cost = total_cost_egp(cost_items, include_rent)
    profit = operating_profit_egp(revenue, cost)
    return PlanEconomics(
        revenue_egp=revenue,
        total_cost_egp=cost,
        operating_profit_egp=profit,
        roi_percent=roi_percent(profit, cost),
        break_even_yield_kg_per_m2=break_even_yield_kg_per_m2(cost, price_egp_per_kg, area_m2),
        break_even_price_egp_per_kg=break_even_price_egp_per_kg(cost, yield_kg_per_m2, area_m2),
        profit_per_feddan_egp=per_feddan(profit, area_m2),
    )
