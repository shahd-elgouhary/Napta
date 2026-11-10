"""Validation logic for geographic coordinates and environmental bounds."""

from typing import Tuple, List

# Geographic bounding box for the Arab Republic of Egypt
EGYPT_LAT_MIN = 21.5
EGYPT_LAT_MAX = 31.8
EGYPT_LON_MIN = 24.5
EGYPT_LON_MAX = 36.9


def validate_egyptian_coordinates(latitude: float, longitude: float) -> Tuple[bool, List[str]]:
    """Verify that given coordinates fall within Egyptian territory."""
    errors = []
    if not (EGYPT_LAT_MIN <= latitude <= EGYPT_LAT_MAX):
        errors.append(
            f"Latitude {latitude} is outside Egypt's geographical boundary ({EGYPT_LAT_MIN}°N to {EGYPT_LAT_MAX}°N)."
        )
    if not (EGYPT_LON_MIN <= longitude <= EGYPT_LON_MAX):
        errors.append(
            f"Longitude {longitude} is outside Egypt's geographical boundary ({EGYPT_LON_MIN}°E to {EGYPT_LON_MAX}°E)."
        )
    return len(errors) == 0, errors


def validate_climate_ranges(temp_c: float, rh_pct: float, solar_rad: float) -> Tuple[bool, List[str]]:
    """Validate that climate metrics are within physically plausible Egyptian ranges."""
    warnings = []
    if not (-5.0 <= temp_c <= 55.0):
        warnings.append(f"Temperature value {temp_c}°C is outside typical Egyptian bounds.")
    if not (0.0 <= rh_pct <= 100.0):
        warnings.append(f"Relative humidity {rh_pct}% is invalid.")
    if not (0.0 <= solar_rad <= 12.0):
        warnings.append(f"Solar radiation {solar_rad} kWh/m²/day is unusual.")
    return len(warnings) == 0, warnings


def validate_soil_ranges(ph: float, clay: float, silt: float, sand: float) -> Tuple[bool, List[str]]:
    """Validate that soil parameters follow physical constraints."""
    warnings = []
    if not (3.5 <= ph <= 10.5):
        warnings.append(f"Soil pH {ph} is outside arable range.")
    total_texture = clay + silt + sand
    if abs(total_texture - 100.0) > 2.0:
        warnings.append(f"Soil texture fractions do not sum to 100% (sum: {total_texture:.1f}%).")
    return len(warnings) == 0, warnings
