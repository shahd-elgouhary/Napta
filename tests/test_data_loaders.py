"""Tests for data/ CSV loaders and validation.

All expected values are hand-computed and arithmetic is shown in comments.
"""

import pytest
from src.data.loaders import (
    CropProfileRecord,
    CropPriceRecord,
    get_crop_cost_items,
    load_cost_assumptions,
    load_crop_prices,
    load_crop_profiles,
    load_regulations,
    load_rotation_rules,
    load_sources_registry,
    validate_crop_price,
    validate_crop_profile,
)


def test_load_crop_profiles_actual_file():
    """Verify loading and validation of all 8 crops in data/crop_profiles.csv."""
    crops = load_crop_profiles()
    assert len(crops) == 8
    expected_ids = {"wheat", "berseem", "faba_bean", "sugar_beet", "onion", "maize", "rice", "cotton"}
    assert set(crops.keys()) == expected_ids

    # Wheat check
    wheat = crops["wheat"]
    assert wheat.name_en == "Wheat"
    assert wheat.name_ar == "قمح"
    assert "غلة" in wheat.aliases_ar
    assert wheat.season == "winter"
    assert not wheat.is_legume
    assert wheat.sow_start_month == 11
    assert wheat.sow_end_month == 12
    # Temperature ordering: 5 <= 15 <= 22 <= 32
    assert wheat.temp_abs_min_c <= wheat.temp_opt_min_c <= wheat.temp_opt_max_c <= wheat.temp_abs_max_c
    # pH ordering: 5.5 <= 6.0 <= 7.5 <= 8.0
    assert wheat.ph_abs_min <= wheat.ph_opt_min <= wheat.ph_opt_max <= wheat.ph_abs_max
    assert wheat.status == "ai_draft_unverified"

    # Legume check
    assert crops["faba_bean"].is_legume is True
    assert crops["berseem"].is_legume is True
    assert crops["maize"].is_legume is False


def test_validate_crop_profile_invalid_temp():
    """Invalid temperature ordering must raise ValueError."""
    # opt_min (25) > opt_max (20) -> invalid
    p = CropProfileRecord(
        crop_id="bad_crop",
        name_en="Bad",
        name_ar="رديء",
        aliases_ar=[],
        season="winter",
        family="Test",
        is_legume=False,
        cycle_days_min=100,
        cycle_days_max=120,
        sow_start_month=10,
        sow_end_month=11,
        temp_abs_min_c=10.0,
        temp_opt_min_c=25.0,  # inverted!
        temp_opt_max_c=20.0,
        temp_abs_max_c=35.0,
        ph_abs_min=6.0,
        ph_opt_min=6.5,
        ph_opt_max=7.5,
        ph_abs_max=8.0,
        salinity_threshold_ece_dsm=2.0,
        kc_ini=0.3,
        kc_mid=1.1,
        kc_end=0.4,
        local_sale_unit="ton",
        yield_low_t_per_feddan=2.0,
        yield_high_t_per_feddan=3.0,
        yield_source="test",
        policy_flags="none",
        source_basis="test",
        status="ai_draft_unverified",
        confidence="low",
        notes="test",
    )
    with pytest.raises(ValueError, match="Invalid temperature range"):
        validate_crop_profile(p)


def test_validate_crop_profile_invalid_ph():
    """Invalid pH ordering must raise ValueError."""
    # ph_abs_min (7.0) > ph_opt_min (6.0) -> invalid
    p = CropProfileRecord(
        crop_id="bad_ph",
        name_en="Bad",
        name_ar="رديء",
        aliases_ar=[],
        season="winter",
        family="Test",
        is_legume=False,
        cycle_days_min=100,
        cycle_days_max=120,
        sow_start_month=10,
        sow_end_month=11,
        temp_abs_min_c=10.0,
        temp_opt_min_c=15.0,
        temp_opt_max_c=25.0,
        temp_abs_max_c=35.0,
        ph_abs_min=7.0,  # inverted!
        ph_opt_min=6.0,
        ph_opt_max=7.5,
        ph_abs_max=8.0,
        salinity_threshold_ece_dsm=2.0,
        kc_ini=0.3,
        kc_mid=1.1,
        kc_end=0.4,
        local_sale_unit="ton",
        yield_low_t_per_feddan=2.0,
        yield_high_t_per_feddan=3.0,
        yield_source="test",
        policy_flags="none",
        source_basis="test",
        status="ai_draft_unverified",
        confidence="low",
        notes="test",
    )
    with pytest.raises(ValueError, match="Invalid pH range"):
        validate_crop_profile(p)


def test_load_crop_prices_actual_file():
    """Verify loading and price bounds from data/crop_prices.csv."""
    prices = load_crop_prices()
    assert len(prices) == 8

    # Wheat price check: low 16.00, high 16.67
    # Hand calculation: mid = (16.00 + 16.67) / 2 = 16.335
    wheat_p = prices["wheat"]
    assert wheat_p.price_low_egp_per_kg == 16.00
    assert wheat_p.price_high_egp_per_kg == 16.67
    assert wheat_p.price_mid_egp_per_kg == pytest.approx(16.335)
    assert wheat_p.status == "needs_verification"

    # Sugar beet check: low 2.00, high 2.40
    # Hand calculation: mid = (2.00 + 2.40) / 2 = 2.20
    beet_p = prices["sugar_beet"]
    assert beet_p.price_low_egp_per_kg == 2.00
    assert beet_p.price_high_egp_per_kg == 2.40
    assert beet_p.price_mid_egp_per_kg == pytest.approx(2.20)
    assert beet_p.status == "conflicting"


def test_validate_crop_price_negative_or_inverted():
    p_neg = CropPriceRecord(
        crop_id="test",
        price_type="farm_gate",
        price_low_egp_per_kg=-1.0,
        price_high_egp_per_kg=10.0,
        original_quote="test",
        price_date="2026-11",
        source_url="",
        status="test",
        confidence="low",
        notes="",
    )
    with pytest.raises(ValueError):
        validate_crop_price(p_neg)

    p_inv = CropPriceRecord(
        crop_id="test",
        price_type="farm_gate",
        price_low_egp_per_kg=20.0,
        price_high_egp_per_kg=10.0,
        original_quote="test",
        price_date="2026-11",
        source_url="",
        status="test",
        confidence="low",
        notes="",
    )
    with pytest.raises(ValueError):
        validate_crop_price(p_inv)


def test_load_cost_assumptions_actual_file():
    """Verify loading itemized costs and summing with/without rent."""
    costs = load_cost_assumptions()
    assert "wheat" in costs
    wheat_items_no_rent = get_crop_cost_items(costs, "wheat", include_rent=False)
    assert "rent" not in wheat_items_no_rent

    # Hand arithmetic for wheat cost without rent:
    #   seed: 2500
    #   fertilizer: 4500
    #   crop_protection: 600
    #   hired_labor: 3920
    #   machinery_hire: 5000
    #   irrigation_pumping: 2500
    #   transport: 800
    #   trader_commission: 0
    #   other: 500
    # Total without rent = 2500 + 4500 + 600 + 3920 + 5000 + 2500 + 800 + 0 + 500 = 20320.0 EGP
    total_no_rent = sum(wheat_items_no_rent.values())
    assert total_no_rent == 20320.0

    # Hand arithmetic for wheat cost with rent:
    #   rent: 12000
    # Total with rent = 20320.0 + 12000.0 = 32320.0 EGP
    wheat_items_with_rent = get_crop_cost_items(costs, "wheat", include_rent=True)
    assert wheat_items_with_rent["rent"] == 12000.0
    total_with_rent = sum(wheat_items_with_rent.values())
    assert total_with_rent == 32320.0


def test_load_regulations_actual_file():
    regs = load_regulations()
    assert len(regs) == 4
    rule_ids = [r.rule_id for r in regs]
    assert "wheat_procurement" in rule_ids
    assert "rice_area_limit" in rule_ids
    assert "sugar_beet_contract" in rule_ids
    assert "cotton_area_policy" in rule_ids

    rice_rule = next(r for r in regs if r.rule_id == "rice_area_limit")
    assert rice_rule.rule_type == "flag"
    assert rice_rule.crop_id == "rice"


def test_load_rotation_rules_actual_file():
    rules = load_rotation_rules()
    assert len(rules) == 4
    rule_types = [r.rule_type for r in rules]
    assert "bonus" in rule_types
    assert "hard" in rule_types
    assert "soft" in rule_types


def test_load_sources_registry_actual_file():
    sources = load_sources_registry()
    assert len(sources) >= 15
    source_map = {s.source: s for s in sources}
    assert source_map["NASA POWER"].covers_egypt is True
    assert source_map["ISRIC SoilGrids"].covers_egypt is True
    # US-only datasets must NOT cover Egypt
    assert source_map["OpenET"].covers_egypt is False
    assert source_map["USDA Web Soil Survey"].covers_egypt is False
