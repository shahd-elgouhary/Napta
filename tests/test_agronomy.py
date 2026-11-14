"""Tests for A3 (suitability) and A4 (water requirements).

All expected values are hand-computed and arithmetic is shown in comments.
"""

import math
import pytest

from src.agronomy.suitability import (
    evaluate_crop_suitability,
    salinity_score,
    sowing_window_score,
    trapezoid_score,
)
from src.agronomy.water import (
    calculate_crop_water_demand,
    calculate_daily_et0_from_climate,
    calculate_fao56_penman_monteith_et0,
    calculate_weighted_kc,
    extraterrestrial_radiation,
    mean_saturation_vapour_pressure,
    net_radiation,
    psychrometric_constant,
    saturation_vapour_pressure,
    slope_vapour_pressure_curve,
    SOLAR_KWH_TO_MJ,
)
from src.data.loaders import load_crop_profiles
from src.domain.schemas import ClimateSummary, EnvironmentSummary, SoilSummary


# ------------------------------------------------------------------ A3 Tests

def test_trapezoid_score_hand_values():
    """Test trapezoid score with hand-computed arithmetic.

    Range: abs_min=10, opt_min=20, opt_max=30, abs_max=40
    - Inside optimal: 25 -> 100.0
    - Outside absolute: 5 -> 0.0, 45 -> 0.0
    - Rising edge: 15 -> (15-10)/(20-10) * 100 = 50.0
    - Falling edge: 35 -> (40-35)/(40-30) * 100 = 50.0
    - Quarter rising: 12.5 -> (12.5-10)/10 * 100 = 25.0
    """
    assert trapezoid_score(25, 10, 20, 30, 40) == 100.0
    assert trapezoid_score(5, 10, 20, 30, 40) == 0.0
    assert trapezoid_score(45, 10, 20, 30, 40) == 0.0
    assert trapezoid_score(15, 10, 20, 30, 40) == 50.0
    assert trapezoid_score(35, 10, 20, 30, 40) == 50.0
    assert trapezoid_score(12.5, 10, 20, 30, 40) == 25.0


def test_salinity_score_maas_hoffman_arithmetic():
    """Test Maas-Hoffman salinity penalty hand calculation.

    Threshold = 6.0 dS/m, slope = 10% per dS/m
    - ECe = 4.0 <= 6.0 -> 100.0 (no penalty)
    - ECe = 8.0: excess = 8.0 - 6.0 = 2.0 dS/m.
      Penalty = 2.0 * 10% = 20%. Score = 100 - 20 = 80.0.
    - ECe = 16.0: excess = 16.0 - 6.0 = 10.0 dS/m.
      Penalty = 10.0 * 10% = 100%. Score = 0.0.
    """
    assert salinity_score(4.0, threshold_ece_dsm=6.0) == 100.0
    assert salinity_score(8.0, threshold_ece_dsm=6.0) == 80.0
    assert salinity_score(16.0, threshold_ece_dsm=6.0) == 0.0


def test_sowing_window_score():
    """Test sowing window with wrapping months.

    Window: Nov (11) to Jan (1)
    - Month 12 (Dec) -> in window -> 100.0
    - Month 1 (Jan) -> in window -> 100.0
    - Month 10 (Oct) -> buffer month (1 month before 11) -> 50.0
    - Month 2 (Feb) -> buffer month (1 month after 1) -> 50.0
    - Month 6 (June) -> out of window -> 0.0
    """
    assert sowing_window_score(12, 11, 1) == 100.0
    assert sowing_window_score(1, 11, 1) == 100.0
    assert sowing_window_score(10, 11, 1) == 50.0
    assert sowing_window_score(2, 11, 1) == 50.0
    assert sowing_window_score(6, 11, 1) == 0.0


def test_suitability_suitable_wheat_case():
    """Wheat evaluated under representative Nile Delta winter conditions."""
    crops = load_crop_profiles()
    wheat = crops["wheat"]

    env = EnvironmentSummary(
        climate=ClimateSummary(
            annual_mean_temp_c=20.5,
            summer_mean_temp_c=28.0,
            winter_mean_temp_c=17.0,  # inside optimal 15-22°C
            relative_humidity_pct=65.0,
            wind_speed_ms=2.5,
            solar_radiation_kwh_m2_day=5.2,
            annual_precipitation_mm=55.0,
        ),
        soil=SoilSummary(
            ph_water=7.2,  # inside optimal 6.0-7.5
            organic_carbon_g_kg=12.0,
            clay_pct=45.0,
            silt_pct=35.0,
            sand_pct=20.0,
            bulk_density_cg_cm3=125.0,
            cation_exchange_capacity_cmolc_kg=28.0,
            texture_class="Clay",
            salinity_status="UNKNOWN",
        ),
    )

    eval_result = evaluate_crop_suitability(
        crop=wheat,
        env=env,
        planting_month=11,  # optimal sowing month
        measured_salinity_ece_dsm=None,  # unknown salinity
    )

    assert eval_result.is_suitable is True
    assert eval_result.overall_score >= 90.0
    assert "salinity" in eval_result.missing_factors
    assert len(eval_result.warnings) >= 1
    assert "ملوحة التربة غير محددة" in eval_result.warnings[0]
    assert eval_result.confidence == "low"  # lowered from medium because salinity is missing


def test_suitability_hard_exclusion_extreme_temperature():
    """Extreme heat during winter crop cycle triggers hard exclusion."""
    crops = load_crop_profiles()
    wheat = crops["wheat"]

    env = EnvironmentSummary(
        climate=ClimateSummary(
            annual_mean_temp_c=36.0,
            summer_mean_temp_c=42.0,
            winter_mean_temp_c=35.0,  # wheat abs_max is 32.0°C!
            relative_humidity_pct=30.0,
            wind_speed_ms=3.0,
            solar_radiation_kwh_m2_day=6.0,
            annual_precipitation_mm=5.0,
        ),
        soil=SoilSummary(
            ph_water=7.2,
            organic_carbon_g_kg=10.0,
            clay_pct=40.0,
            silt_pct=30.0,
            sand_pct=30.0,
            bulk_density_cg_cm3=130.0,
            cation_exchange_capacity_cmolc_kg=20.0,
            texture_class="Clay Loam",
            salinity_status="UNKNOWN",
        ),
    )

    eval_result = evaluate_crop_suitability(
        crop=wheat,
        env=env,
        planting_month=11,
    )

    assert eval_result.is_suitable is False
    assert len(eval_result.hard_exclusions) >= 1
    assert "متوسط درجة الحرارة" in eval_result.hard_exclusions[0]


# ------------------------------------------------------------------ A4 Tests

def test_fao56_worked_example_18_box18():
    """Test Penman-Monteith ET0 against official FAO-56 Box 18 (Cairo, Egypt).

    FAO-56 Irrigation and Drainage Paper 56, Chapter 4, Box 18, page 74:
    Location: Cairo, Egypt
    Latitude: 30.08° N, Elevation: 74 m
    Date: 15 May (Day of year J = 135)
    Inputs:
      Tmax = 34.8 °C, Tmin = 19.4 °C -> Tmean = 27.1 °C
      ea = 1.77 kPa
      u2 = 2.0 m/s
      Rs = 22.4 MJ/m2/day
    Published FAO-56 Box 18 intermediate and final results:
      Ra = 40.0 MJ/m2/day
      Rso = 30.1 MJ/m2/day
      Rns = 17.25 MJ/m2/day
      Rnl = 4.03 MJ/m2/day
      Rn = 13.22 MJ/m2/day (published ~13.2 MJ/m2/day)
      Delta = 0.210 kPa/°C
      gamma = 0.067 kPa/°C
      es = 3.91 kPa
      ET0 = 6.17 mm/day (published 6.1 to 6.2 mm/day)
    """
    t_mean = 27.1
    t_max = 34.8
    t_min = 19.4
    u2 = 2.0
    ea = 1.77
    rs = 22.4
    z = 74.0
    lat = 30.08
    j = 135

    delta = slope_vapour_pressure_curve(t_mean)
    gamma = psychrometric_constant(z)
    es = mean_saturation_vapour_pressure(t_max, t_min)

    rn = net_radiation(
        solar_radiation_mj_m2_day=rs,
        t_max_c=t_max,
        t_min_c=t_min,
        ea_kpa=ea,
        latitude_deg=lat,
        day_of_year=j,
        elevation_m=z,
    )

    et0 = calculate_fao56_penman_monteith_et0(
        t_mean_c=t_mean,
        u2_m_s=u2,
        rn_mj_m2_day=rn,
        es_kpa=es,
        ea_kpa=ea,
        delta_kpa_c=delta,
        gamma_kpa_c=gamma,
    )

    # Validate against FAO-56 worked example
    assert delta == pytest.approx(0.210, abs=0.005)
    assert gamma == pytest.approx(0.067, abs=0.002)
    assert es == pytest.approx(3.91, abs=0.05)
    assert rn == pytest.approx(13.22, abs=0.2)
    # Target ET0 is 6.1 to 6.2 mm/day
    assert et0 == pytest.approx(6.17, abs=0.1)


def test_radiation_unit_conversion():
    """Verify radiation conversion from kWh/m2/day to MJ/m2/day."""
    # 5.0 kWh/m2/day * 3.6 MJ/kWh = 18.0 MJ/m2/day
    kwh = 5.0
    mj = kwh * SOLAR_KWH_TO_MJ
    assert mj == 18.0


def test_calculate_weighted_kc_hand_arithmetic():
    """Test stage-weighted Kc hand calculation for wheat.

    Wheat from crop_profiles.csv:
      kc_ini = 0.30
      kc_mid = 1.15
      kc_end = 0.25
    Stage length fractions (FAO-56 standard):
      f_ini = 0.20
      f_dev = 0.30  (mean = (0.30 + 1.15)/2 = 0.725)
      f_mid = 0.35
      f_late = 0.15 (mean = (1.15 + 0.25)/2 = 0.700)
    Hand arithmetic:
      term_ini  = 0.20 * 0.30  = 0.0600
      term_dev  = 0.30 * 0.725 = 0.2175
      term_mid  = 0.35 * 1.15  = 0.4025
      term_late = 0.15 * 0.700 = 0.1050
      Sum = 0.0600 + 0.2175 + 0.4025 + 0.1050 = 0.7850
    """
    kc = calculate_weighted_kc(kc_ini=0.30, kc_mid=1.15, kc_end=0.25)
    assert kc == pytest.approx(0.785, abs=1e-4)


def test_crop_water_demand_feddan_conversion():
    """Verify seasonal water demand conversion from mm to m3/feddan."""
    crops = load_crop_profiles()
    wheat = crops["wheat"]

    climate = ClimateSummary(
        annual_mean_temp_c=18.5,
        summer_mean_temp_c=27.0,
        winter_mean_temp_c=15.0,
        relative_humidity_pct=60.0,
        wind_speed_ms=2.2,
        solar_radiation_kwh_m2_day=4.5,
        annual_precipitation_mm=40.0,
    )

    demand = calculate_crop_water_demand(crop=wheat, climate=climate, latitude_deg=31.0)
    assert demand.crop_id == "wheat"
    assert demand.daily_et0_mm_day > 0.0
    assert demand.seasonal_etc_mm > 0.0
    # In Egypt, seasonal wheat water demand is typically 1800 - 2400 m3/feddan
    assert 1500.0 <= demand.water_demand_m3_per_feddan <= 2500.0
    # Check consistency: m3_per_feddan == m3_per_m2 * 4200.83
    assert demand.water_demand_m3_per_feddan == pytest.approx(
        demand.water_demand_m3_per_m2 * 4200.83, rel=1e-3
    )
