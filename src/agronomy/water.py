"""Crop water requirements and FAO-56 Penman-Monteith ET0 calculation (A4).

Formulas (FAO Irrigation and Drainage Paper 56):
  1. Solar radiation conversion:
     NASA POWER ALLSKY_SFC_SW_DWN is in kWh/m2/day.
     1 kWh/m2/day = 3.6 MJ/m2/day (physics).
  2. Wind speed height assumption:
     NASA POWER WS2M is measured at 2.0 meters above ground surface.
     FAO-56 reference grass requires wind speed u2 at 2.0 m.
     Therefore u2 = WS2M directly (no height conversion factor needed).
  3. Reference Evapotranspiration ET0 (FAO-56 Eq. 6):
     ET0 = [0.408 * Delta * (Rn - G) + gamma * (900 / (T + 273)) * u2 * (es - ea)] /
           [Delta + gamma * (1 + 0.34 * u2)]
     where G = 0 for daily/seasonal averages.
  4. Crop Evapotranspiration ETc (FAO-56 Eq. 58):
     ETc = Kc * ET0
     with stage-specific Kc (ini, mid, end) from crop profile.
  5. Water volume conversions:
     Strictly through src.egypt.units_eg (mm -> m3/m2 -> m3/feddan).
  6. Non-negotiable rule:
     Never infer irrigation water availability from NASA data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.data.loaders import CropProfileRecord
from src.domain.schemas import ClimateSummary, EnvironmentSummary
from src.egypt.units_eg import FEDDAN_M2, mm_to_m3, m3_per_m2_to_m3_per_feddan


# Standard physical and agronomic constants
SOLAR_KWH_TO_MJ: float = 3.6  # 1 kWh = 3.6 MJ
STEFAN_BOLTZMANN_CONSTANT: float = 4.903e-9  # MJ K-4 m-2 day-1
STANDARD_ALBEDO_GRASS: float = 0.23  # FAO-56 hypothetical grass albedo (1 - 0.23 = 0.77)

# Documented crop stage lengths as fractions of total cycle (FAO-56 default approximation)
STAGE_LENGTH_FRACTIONS: Dict[str, float] = {
    "initial": 0.20,      # 20% initial growth (Kc_ini)
    "development": 0.30,  # 30% vegetative development (linear ramp ini -> mid)
    "mid_season": 0.35,   # 35% mid-season / flowering / yield formation (Kc_mid)
    "late_season": 0.15,  # 15% ripening / senescence (linear ramp mid -> end)
}


# ------------------------------------------------------------------ FAO-56 primitives

def saturation_vapour_pressure(temp_c: float) -> float:
    """Saturation vapour pressure e°(T) in kPa (FAO-56 Eq. 11)."""
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def mean_saturation_vapour_pressure(t_max_c: float, t_min_c: float) -> float:
    """Mean saturation vapour pressure es in kPa (FAO-56 Eq. 12)."""
    return (saturation_vapour_pressure(t_max_c) + saturation_vapour_pressure(t_min_c)) / 2.0


def actual_vapour_pressure_from_rh(es_kpa: float, rh_pct: float) -> float:
    """Actual vapour pressure ea in kPa from relative humidity percentage (FAO-56 Eq. 19)."""
    rh_clamped = max(0.0, min(100.0, rh_pct))
    return es_kpa * (rh_clamped / 100.0)


def slope_vapour_pressure_curve(temp_c: float) -> float:
    """Slope of saturation vapour pressure curve Delta in kPa/°C (FAO-56 Eq. 13)."""
    e0 = saturation_vapour_pressure(temp_c)
    return (4098.0 * e0) / ((temp_c + 237.3) ** 2)


def atmospheric_pressure(elevation_m: float = 20.0) -> float:
    """Mean atmospheric pressure P in kPa at elevation z (FAO-56 Eq. 7).

    Default elevation 20 m corresponds to typical Nile Delta elevation.
    """
    return 101.3 * (((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26)


def psychrometric_constant(elevation_m: float = 20.0) -> float:
    """Psychrometric constant gamma in kPa/°C (FAO-56 Eq. 8)."""
    p = atmospheric_pressure(elevation_m)
    return 0.000665 * p


def extraterrestrial_radiation(latitude_deg: float, day_of_year: int) -> float:
    """Extraterrestrial radiation Ra in MJ/m2/day (FAO-56 Eqs. 21-28)."""
    lat_rad = math.radians(latitude_deg)
    # Inverse relative distance Earth-Sun (Eq. 23)
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * day_of_year / 365.0)
    # Solar declination (Eq. 24)
    solar_dec = 0.409 * math.sin((2.0 * math.pi * day_of_year / 365.0) - 1.39)
    # Sunset hour angle (Eq. 25)
    tan_prod = -math.tan(lat_rad) * math.tan(solar_dec)
    ws = math.acos(max(-1.0, min(1.0, tan_prod)))
    # Extraterrestrial radiation (Eq. 21)
    gsc = 0.0820  # Solar constant in MJ m-2 min-1
    ra = (
        (24.0 * 60.0 / math.pi)
        * gsc
        * dr
        * (
            ws * math.sin(lat_rad) * math.sin(solar_dec)
            + math.cos(lat_rad) * math.cos(solar_dec) * math.sin(ws)
        )
    )
    return max(0.0, ra)


def net_radiation(
    solar_radiation_mj_m2_day: float,
    t_max_c: float,
    t_min_c: float,
    ea_kpa: float,
    latitude_deg: float,
    day_of_year: int,
    elevation_m: float = 20.0,
) -> float:
    """Net radiation Rn = Rns - Rnl in MJ/m2/day (FAO-56 Eqs. 37-40)."""
    rs = solar_radiation_mj_m2_day
    # Net solar radiation with standard albedo 0.23 (Eq. 38)
    rns = (1.0 - STANDARD_ALBEDO_GRASS) * rs

    # Clear-sky radiation Rso (Eq. 37)
    ra = extraterrestrial_radiation(latitude_deg, day_of_year)
    rso = (0.75 + 2e-5 * elevation_m) * ra
    rso = max(1e-3, rso)

    # Net longwave radiation Rnl (Eq. 39)
    t_max_k4 = (t_max_c + 273.16) ** 4
    t_min_k4 = (t_min_c + 273.16) ** 4
    temp_term = STEFAN_BOLTZMANN_CONSTANT * ((t_max_k4 + t_min_k4) / 2.0)
    vapour_term = 0.34 - 0.14 * math.sqrt(max(0.0, ea_kpa))
    cloud_ratio = min(1.0, max(0.3, rs / rso))
    cloud_term = 1.35 * cloud_ratio - 0.35

    rnl = temp_term * vapour_term * cloud_term
    return rns - rnl


# ------------------------------------------------------------- Penman-Monteith ET0

def calculate_fao56_penman_monteith_et0(
    t_mean_c: float,
    u2_m_s: float,
    rn_mj_m2_day: float,
    es_kpa: float,
    ea_kpa: float,
    delta_kpa_c: float,
    gamma_kpa_c: float,
) -> float:
    """Direct implementation of FAO-56 Eq. 6 for reference evapotranspiration ET0 (mm/day)."""
    if u2_m_s < 0:
        raise ValueError(f"Wind speed u2 must be >= 0, got {u2_m_s}")
    vpd = max(0.0, es_kpa - ea_kpa)
    numerator = 0.408 * delta_kpa_c * rn_mj_m2_day + gamma_kpa_c * (900.0 / (t_mean_c + 273.0)) * u2_m_s * vpd
    denominator = delta_kpa_c + gamma_kpa_c * (1.0 + 0.34 * u2_m_s)
    if denominator == 0:
        return 0.0
    return max(0.0, numerator / denominator)


def calculate_daily_et0_from_climate(
    climate: ClimateSummary,
    latitude_deg: float = 30.0,
    day_of_year: int = 135,
    elevation_m: float = 20.0,
) -> float:
    """Calculate daily reference ET0 (mm/day) using NASA POWER climate summary.

    Converts ALLSKY_SFC_SW_DWN (kWh/m2/day) to MJ/m2/day.
    Uses WS2M directly as FAO-56 u2 wind speed (both measured at 2m height).
    """
    t_mean = climate.annual_mean_temp_c
    # Estimate diurnal spread: typical Egypt Delta spread is ~12-14°C
    t_max = t_mean + 6.5
    t_min = t_mean - 6.5

    # Vapour pressure
    es = mean_saturation_vapour_pressure(t_max, t_min)
    ea = actual_vapour_pressure_from_rh(es, climate.relative_humidity_pct)

    # Slope Delta and Psychrometric constant gamma
    delta = slope_vapour_pressure_curve(t_mean)
    gamma = psychrometric_constant(elevation_m)

    # Radiation conversion from kWh/m2/day to MJ/m2/day
    rs_mj = climate.solar_radiation_kwh_m2_day * SOLAR_KWH_TO_MJ
    rn = net_radiation(
        solar_radiation_mj_m2_day=rs_mj,
        t_max_c=t_max,
        t_min_c=t_min,
        ea_kpa=ea,
        latitude_deg=latitude_deg,
        day_of_year=day_of_year,
        elevation_m=elevation_m,
    )

    u2 = climate.wind_speed_ms  # NASA POWER WS2M is already at 2m

    return calculate_fao56_penman_monteith_et0(
        t_mean_c=t_mean,
        u2_m_s=u2,
        rn_mj_m2_day=rn,
        es_kpa=es,
        ea_kpa=ea,
        delta_kpa_c=delta,
        gamma_kpa_c=gamma,
    )


# ------------------------------------------------------------- Crop water requirements

def calculate_weighted_kc(kc_ini: float, kc_mid: float, kc_end: float) -> float:
    """Compute seasonal weighted mean Kc based on documented FAO-56 stage length fractions."""
    f_ini = STAGE_LENGTH_FRACTIONS["initial"]          # 0.20
    f_dev = STAGE_LENGTH_FRACTIONS["development"]      # 0.30
    f_mid = STAGE_LENGTH_FRACTIONS["mid_season"]       # 0.35
    f_late = STAGE_LENGTH_FRACTIONS["late_season"]     # 0.15

    kc_dev_mean = (kc_ini + kc_mid) / 2.0
    kc_late_mean = (kc_mid + kc_end) / 2.0

    return (
        f_ini * kc_ini
        + f_dev * kc_dev_mean
        + f_mid * kc_mid
        + f_late * kc_late_mean
    )


@dataclass(frozen=True)
class CropWaterDemand:
    crop_id: str
    cycle_days: int
    daily_et0_mm_day: float
    weighted_kc: float
    seasonal_etc_mm: float
    water_demand_m3_per_m2: float
    water_demand_m3_per_feddan: float
    effective_rainfall_mm: float
    net_irrigation_need_m3_per_feddan: float
    notes: str


def calculate_crop_water_demand(
    crop: CropProfileRecord,
    climate: ClimateSummary,
    latitude_deg: float = 30.0,
    elevation_m: float = 20.0,
) -> CropWaterDemand:
    """Calculate seasonal water requirement in mm, m3/m2, and m3/feddan."""
    # Representative day of year for the crop season:
    # Winter crops (wheat, faba, berseem) peak in Jan/Feb (day 45)
    # Summer crops (maize, cotton, rice) peak in Jun/Jul (day 180)
    day_of_year = 45 if crop.season == "winter" else 180

    daily_et0 = calculate_daily_et0_from_climate(
        climate=climate,
        latitude_deg=latitude_deg,
        day_of_year=day_of_year,
        elevation_m=elevation_m,
    )

    weighted_kc = calculate_weighted_kc(crop.kc_ini, crop.kc_mid, crop.kc_end)
    cycle_days = int((crop.cycle_days_min + crop.cycle_days_max) / 2)

    # Seasonal ETc in mm = daily ET0 * weighted Kc * cycle days
    seasonal_etc_mm = daily_et0 * weighted_kc * cycle_days

    # Water demand per m2: 1 mm over 1 m2 = 0.001 m3 = 1 litre
    demand_m3_per_m2 = mm_to_m3(seasonal_etc_mm, area_m2=1.0)

    # Water demand per feddan: using units_eg
    demand_m3_per_feddan = m3_per_m2_to_m3_per_feddan(demand_m3_per_m2)

    # Egyptian rainfall: PRECTOTCORR is small.
    # Effective rainfall (FAO approximation: ~70% of seasonal rainfall)
    seasonal_rain_mm = (climate.annual_precipitation_mm / 365.0) * cycle_days
    effective_rain_mm = max(0.0, seasonal_rain_mm * 0.70)
    net_irrigation_mm = max(0.0, seasonal_etc_mm - effective_rain_mm)
    net_irrigation_m3_per_feddan = m3_per_m2_to_m3_per_feddan(mm_to_m3(net_irrigation_mm, area_m2=1.0))

    return CropWaterDemand(
        crop_id=crop.crop_id,
        cycle_days=cycle_days,
        daily_et0_mm_day=round(daily_et0, 2),
        weighted_kc=round(weighted_kc, 3),
        seasonal_etc_mm=round(seasonal_etc_mm, 1),
        water_demand_m3_per_m2=round(demand_m3_per_m2, 4),
        water_demand_m3_per_feddan=round(demand_m3_per_feddan, 1),
        effective_rainfall_mm=round(effective_rain_mm, 1),
        net_irrigation_need_m3_per_feddan=round(net_irrigation_m3_per_feddan, 1),
        notes=(
            f"Kc ini={crop.kc_ini}, mid={crop.kc_mid}, end={crop.kc_end}. "
            f"Stage weights: 20% ini, 30% dev, 35% mid, 15% late. "
            f"Computed strictly through units_eg conversions."
        ),
    )
