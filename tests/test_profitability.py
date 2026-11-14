"""Tests for profitability.py. All expected numbers are computed by hand.

The inputs below are INVENTED numbers chosen to make the arithmetic easy.
They are not real crop yields, prices or costs.

Hand example (1 ha = 10,000 m2):
    yield 0.6 kg/m2, price 10 EGP/kg, area 10,000 m2
    revenue = 0.6 x 10 x 10,000                    = 60,000
    costs: seed 5,000 + fertilizer 8,000 + labor 7,000
           + irrigation 6,000 + rent 14,000        = 40,000 (26,000 without rent)
    profit  = 60,000 - 40,000                      = 20,000
    ROI     = 20,000 / 40,000 x 100                = 50 %
    break-even yield = 40,000 / (10 x 10,000)      = 0.4 kg/m2
    break-even price = 40,000 / (0.6 x 10,000)     = 6.6667 EGP/kg
"""
import pytest

from src.business import profitability as p
from src.egypt.units_eg import FEDDAN_M2

COSTS = {
    "seed": 5_000,
    "fertilizer": 8_000,
    "hired_labor": 7_000,
    "irrigation": 6_000,
    "rent": 14_000,
}
AREA = 10_000.0
YIELD = 0.6
PRICE = 10.0


def test_revenue():
    assert p.revenue_egp(YIELD, PRICE, AREA) == pytest.approx(60_000)


def test_total_cost_with_and_without_rent():
    assert p.total_cost_egp(COSTS) == 40_000
    assert p.total_cost_egp(COSTS, include_rent=False) == 26_000


def test_total_cost_empty_is_zero_not_invented():
    assert p.total_cost_egp({}) == 0


def test_profit_and_loss():
    assert p.operating_profit_egp(60_000, 40_000) == 20_000
    assert p.operating_profit_egp(30_000, 40_000) == -10_000  # loss stays negative


def test_roi():
    assert p.roi_percent(20_000, 40_000) == pytest.approx(50)
    assert p.roi_percent(-10_000, 40_000) == pytest.approx(-25)
    assert p.roi_percent(34_000, 26_000) == pytest.approx(130.769, rel=1e-4)


def test_roi_undefined_when_cost_zero():
    assert p.roi_percent(1_000, 0) is None


def test_break_even_yield():
    assert p.break_even_yield_kg_per_m2(40_000, PRICE, AREA) == pytest.approx(0.4)


def test_break_even_price():
    assert p.break_even_price_egp_per_kg(40_000, YIELD, AREA) == pytest.approx(6.6667, rel=1e-4)


def test_break_even_at_break_even_gives_zero_profit():
    be_yield = p.break_even_yield_kg_per_m2(40_000, PRICE, AREA)
    revenue = p.revenue_egp(be_yield, PRICE, AREA)
    assert p.operating_profit_egp(revenue, 40_000) == pytest.approx(0)


def test_zero_price_handled():
    assert p.revenue_egp(YIELD, 0, AREA) == 0
    assert p.break_even_yield_kg_per_m2(40_000, 0, AREA) is None


def test_zero_yield_handled():
    assert p.revenue_egp(0, PRICE, AREA) == 0
    assert p.break_even_price_egp_per_kg(40_000, 0, AREA) is None


def test_zero_area_handled():
    assert p.break_even_yield_kg_per_m2(40_000, PRICE, 0) is None
    assert p.per_feddan(1_000, 0) is None


def test_negative_inputs_rejected():
    with pytest.raises(ValueError):
        p.revenue_egp(-1, PRICE, AREA)
    with pytest.raises(ValueError):
        p.revenue_egp(YIELD, -10, AREA)
    with pytest.raises(ValueError):
        p.total_cost_egp({"seed": -5})


def test_per_feddan():
    # when area is exactly 1 feddan, per-feddan value equals the total
    assert p.per_feddan(7_000, FEDDAN_M2) == pytest.approx(7_000)
    # 2 feddan: half
    assert p.per_feddan(7_000, 2 * FEDDAN_M2) == pytest.approx(3_500)


def test_calculate_economics_full():
    r = p.calculate_economics(YIELD, PRICE, AREA, COSTS)
    assert r.revenue_egp == pytest.approx(60_000)
    assert r.total_cost_egp == 40_000
    assert r.operating_profit_egp == pytest.approx(20_000)
    assert r.roi_percent == pytest.approx(50)
    assert r.break_even_yield_kg_per_m2 == pytest.approx(0.4)
    assert r.break_even_price_egp_per_kg == pytest.approx(6.6667, rel=1e-4)
    # 20,000 EGP over 10,000 m2 -> 2 EGP/m2 -> 2 x 4200.83 per feddan
    assert r.profit_per_feddan_egp == pytest.approx(2 * FEDDAN_M2)


def test_calculate_economics_without_rent():
    r = p.calculate_economics(YIELD, PRICE, AREA, COSTS, include_rent=False)
    assert r.total_cost_egp == 26_000
    assert r.operating_profit_egp == pytest.approx(34_000)
