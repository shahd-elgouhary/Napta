"""Normalization and conversion utilities for environmental data."""

from typing import Dict, Any


def classify_usda_texture(clay_pct: float, silt_pct: float, sand_pct: float) -> str:
    """Classify soil into standard USDA Soil Texture Triangle classes.
    
    Args:
        clay_pct: percentage of clay (0-100)
        silt_pct: percentage of silt (0-100)
        sand_pct: percentage of sand (0-100)
    
    Returns:
        USDA texture classification string.
    """
    # Normalize fractions if needed
    total = clay_pct + silt_pct + sand_pct
    if total > 0 and abs(total - 100.0) > 0.5:
        clay_pct = (clay_pct / total) * 100.0
        silt_pct = (silt_pct / total) * 100.0
        sand_pct = (sand_pct / total) * 100.0

    if clay_pct >= 40.0:
        if silt_pct >= 40.0:
            return "Silty Clay"
        elif sand_pct <= 45.0:
            return "Clay"
        else:
            return "Sandy Clay"
    elif clay_pct >= 27.0:
        if sand_pct <= 20.0:
            return "Silty Clay Loam"
        elif sand_pct <= 45.0:
            return "Clay Loam"
        else:
            return "Sandy Clay Loam"
    elif clay_pct >= 20.0:
        if sand_pct >= 52.0:
            return "Sandy Clay Loam"
        elif silt_pct >= 50.0:
            return "Silt Loam"
        else:
            return "Loam"
    elif clay_pct >= 7.0:
        if silt_pct >= 50.0:
            return "Silt Loam"
        elif sand_pct <= 52.0:
            return "Loam"
        else:
            return "Sandy Loam"
    else:  # clay < 7%
        if silt_pct >= 80.0:
            return "Silt"
        elif silt_pct >= 50.0:
            return "Silt Loam"
        elif sand_pct >= 85.0:
            return "Sand"
        elif sand_pct >= 70.0:
            return "Loamy Sand"
        else:
            return "Sandy Loam"


def normalize_soilgrids_units(raw_property: str, raw_value: float) -> float:
    """Convert raw SoilGrids integer representation into standard scientific units.
    
    SoilGrids REST API v2 returns values multiplied by scale factors:
    - phh2o: pH * 10 -> standard pH
    - soc: dg/kg (decigrams per kilogram) -> g/kg (divide by 10)
    - clay, silt, sand: g/kg (parts per thousand) -> % (divide by 10)
    - bdod: cg/cm³ (centigrams per cm³) -> standard cg/cm³ (or divide by 100 for g/cm³)
    - cec: mmol(c)/kg -> cmol(+)/kg (divide by 10)
    """
    if raw_property == "phh2o":
        return round(raw_value / 10.0, 2)
    elif raw_property == "soc":
        return round(raw_value / 10.0, 2)  # g/kg
    elif raw_property in ("clay", "silt", "sand"):
        return round(raw_value / 10.0, 2)  # percentage %
    elif raw_property == "bdod":
        return round(raw_value, 2)  # cg/cm³
    elif raw_property == "cec":
        return round(raw_value / 10.0, 2)  # cmol(+)/kg
    return round(raw_value, 2)


def calculate_depth_weighted_average(depth_slices: list[Dict[str, Any]], target_depth_cm: float = 30.0) -> float:
    """Calculate depth-weighted average for agricultural topsoil (0-30cm)."""
    if not depth_slices:
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0

    # Common SoilGrids intervals: 0-5cm (5cm thick), 5-15cm (10cm thick), 15-30cm (15cm thick)
    interval_weights = {
        "0-5cm": 5.0,
        "5-15cm": 10.0,
        "15-30cm": 15.0,
    }

    for item in depth_slices:
        label = item.get("label")
        mean_val = item.get("values", {}).get("mean")
        if label in interval_weights and mean_val is not None:
            w = interval_weights[label]
            weighted_sum += mean_val * w
            total_weight += w

    if total_weight == 0:
        # Fallback to simple average of whatever is available
        valid_vals = [item.get("values", {}).get("mean") for item in depth_slices if item.get("values", {}).get("mean") is not None]
        return float(sum(valid_vals) / len(valid_vals)) if valid_vals else 0.0

    return round(weighted_sum / total_weight, 2)
