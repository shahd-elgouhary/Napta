"""Unit conversions for FieldWise AI (Egypt edition).

Internal base units (everything inside the engine uses these):
    area    -> m2
    mass    -> kg
    volume  -> m3
    money   -> EGP
Conversion to/from feddan, qirat, sahm, ha, tonne, ardab, qantar happens ONLY here.

Crop-specific units (ardab, qantar, ...) have NO hardcoded values. They are
read from data/crop_units.csv (columns: crop, unit, kg_per_unit, source).
If a value is missing we raise MissingUnitError. We never guess.
"""
from __future__ import annotations

import csv
from pathlib import Path

# ---------------------------------------------------------------- constants
# TODO(A9): verify against an official source and write the source in
# data/sources.md before relying on it.
FEDDAN_M2: float = 4200.83

QIRAT_PER_FEDDAN: int = 24
SAHM_PER_QIRAT: int = 24
SAHM_PER_FEDDAN: int = QIRAT_PER_FEDDAN * SAHM_PER_QIRAT  # 576

QIRAT_M2: float = FEDDAN_M2 / QIRAT_PER_FEDDAN
SAHM_M2: float = FEDDAN_M2 / SAHM_PER_FEDDAN

M2_PER_HA: float = 10_000.0
KG_PER_TONNE: float = 1_000.0
LITRE_PER_M3: float = 1_000.0
M3_PER_HA_PER_MM: float = 10.0  # 1 mm of water over 1 ha = 10 m3 (physics)

# (crop, unit) -> kg per unit.  Example key: ("wheat", "ardab")
CropUnitTable = dict[tuple[str, str], float]


class MissingUnitError(KeyError):
    """A crop-specific unit has no documented value in crop_units.csv."""


def _non_negative(value: float, name: str = "value") -> float:
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


# --------------------------------------------------------------------- area
def feddan_to_m2(feddan: float) -> float:
    return _non_negative(feddan, "feddan") * FEDDAN_M2


def m2_to_feddan(m2: float) -> float:
    return _non_negative(m2, "m2") / FEDDAN_M2


def qirat_to_m2(qirat: float) -> float:
    return _non_negative(qirat, "qirat") * QIRAT_M2


def m2_to_qirat(m2: float) -> float:
    return _non_negative(m2, "m2") / QIRAT_M2


def sahm_to_m2(sahm: float) -> float:
    return _non_negative(sahm, "sahm") * SAHM_M2


def m2_to_sahm(m2: float) -> float:
    return _non_negative(m2, "m2") / SAHM_M2


def feddan_to_qirat(feddan: float) -> float:
    return _non_negative(feddan, "feddan") * QIRAT_PER_FEDDAN


def qirat_to_feddan(qirat: float) -> float:
    return _non_negative(qirat, "qirat") / QIRAT_PER_FEDDAN


def qirat_to_sahm(qirat: float) -> float:
    return _non_negative(qirat, "qirat") * SAHM_PER_QIRAT


def sahm_to_qirat(sahm: float) -> float:
    return _non_negative(sahm, "sahm") / SAHM_PER_QIRAT


def feddan_to_sahm(feddan: float) -> float:
    return _non_negative(feddan, "feddan") * SAHM_PER_FEDDAN


def sahm_to_feddan(sahm: float) -> float:
    return _non_negative(sahm, "sahm") / SAHM_PER_FEDDAN


def ha_to_m2(ha: float) -> float:
    return _non_negative(ha, "ha") * M2_PER_HA


def m2_to_ha(m2: float) -> float:
    return _non_negative(m2, "m2") / M2_PER_HA


def feddan_to_ha(feddan: float) -> float:
    return m2_to_ha(feddan_to_m2(feddan))


def ha_to_feddan(ha: float) -> float:
    return m2_to_feddan(ha_to_m2(ha))


def fqs_to_m2(feddan: float = 0, qirat: float = 0, sahm: float = 0) -> float:
    """'3 فدان و 12 قيراط و 6 سهم' -> m2."""
    return feddan_to_m2(feddan) + qirat_to_m2(qirat) + sahm_to_m2(sahm)


def m2_to_fqs(m2: float) -> tuple[int, int, int]:
    """m2 -> (feddan, qirat, sahm), rounded to the nearest whole sahm."""
    exact_sahm = m2_to_sahm(m2)
    
    feddan = int(exact_sahm // SAHM_PER_FEDDAN)
    rest_sahm = exact_sahm % SAHM_PER_FEDDAN
    
    qirat = int(rest_sahm // SAHM_PER_QIRAT)
    sahm_fraction = rest_sahm % SAHM_PER_QIRAT
    
    sahm = round(sahm_fraction)
    
    if sahm == SAHM_PER_QIRAT:
        sahm = 0
        qirat += 1
        
    if qirat == QIRAT_PER_FEDDAN:
        qirat = 0
        feddan += 1
        
    return feddan, qirat, sahm


# --------------------------------------------------------------------- mass
def kg_to_tonne(kg: float) -> float:
    return _non_negative(kg, "kg") / KG_PER_TONNE


def tonne_to_kg(tonne: float) -> float:
    return _non_negative(tonne, "tonne") * KG_PER_TONNE


# ------------------------------------------------------------------- volume
def m3_to_litre(m3: float) -> float:
    return _non_negative(m3, "m3") * LITRE_PER_M3


def litre_to_m3(litre: float) -> float:
    return _non_negative(litre, "litre") / LITRE_PER_M3


def mm_to_m3_per_ha(mm: float) -> float:
    """Water depth (mm) -> volume per hectare (m3/ha). 1 mm = 10 m3/ha."""
    return _non_negative(mm, "mm") * M3_PER_HA_PER_MM


def m3_per_ha_to_mm(m3_per_ha: float) -> float:
    return _non_negative(m3_per_ha, "m3_per_ha") / M3_PER_HA_PER_MM


def mm_to_m3(mm: float, area_m2: float) -> float:
    """Water depth (mm) over an area (m2) -> m3.  1 mm over 1 m2 = 1 litre."""
    return _non_negative(mm, "mm") * _non_negative(area_m2, "area_m2") / 1000.0


# ------------------------------------------------- crop-specific local units
def load_crop_units(path: str | Path) -> CropUnitTable:
    table: CropUnitTable = {}
    with open(path, newline="", encoding="utf-8") as f:
        for idx, row in enumerate(csv.DictReader(f), start=2):
            crop = (row.get("crop") or "").strip().lower()
            unit = (row.get("unit") or "").strip().lower()
            raw_kg = (row.get("kg_per_unit") or "").strip()
            source = (row.get("source") or "").strip()

            if not raw_kg:  
                continue
            if not source: 
                raise ValueError(
                    f"crop_units.csv (line {idx}): {crop}/{unit} has a value but no source"
                )
            try: 
                value = float(raw_kg)
            except ValueError:
                raise ValueError(
                    f"crop_units.csv (line {idx}): invalid kg_per_unit value '{raw_kg}'"
                ) from None
            if value <= 0:  
                raise ValueError(f"crop_units.csv (line {idx}): kg_per_unit must be > 0")

            table[(crop, unit)] = value 
    return table


def kg_per_local_unit(crop: str, unit: str, table: CropUnitTable) -> float:
    key = (crop.strip().lower(), unit.strip().lower())
    try:
        return table[key]
    except KeyError:
        raise MissingUnitError(
            f"No documented value for 1 {unit} of {crop}. Add it to crop_units.csv with a source."
        ) from None


def local_unit_to_kg(amount: float, crop: str, unit: str, table: CropUnitTable) -> float:
    """e.g. local_unit_to_kg(10, 'wheat', 'ardab', table)."""
    return _non_negative(amount, "amount") * kg_per_local_unit(crop, unit, table)


def kg_to_local_unit(kg: float, crop: str, unit: str, table: CropUnitTable) -> float:
    return _non_negative(kg, "kg") / kg_per_local_unit(crop, unit, table)


def ardab_to_kg(ardab: float, crop: str, table: CropUnitTable) -> float:
    return local_unit_to_kg(ardab, crop, "ardab", table)


def kg_to_ardab(kg: float, crop: str, table: CropUnitTable) -> float:
    return kg_to_local_unit(kg, crop, "ardab", table)


def qantar_to_kg(qantar: float, crop: str, table: CropUnitTable) -> float:
    return local_unit_to_kg(qantar, crop, "qantar", table)


def kg_to_qantar(kg: float, crop: str, table: CropUnitTable) -> float:
    return kg_to_local_unit(kg, crop, "qantar", table)


# ------------------------------------------------- composite (yield / price)
# Yield: kg per m2 is the internal form; kg/ha and kg/feddan are display forms.
def yield_kg_per_feddan_to_kg_per_ha(y: float) -> float:
    return _non_negative(y, "yield") * M2_PER_HA / FEDDAN_M2


def yield_kg_per_ha_to_kg_per_feddan(y: float) -> float:
    return _non_negative(y, "yield") * FEDDAN_M2 / M2_PER_HA


def yield_local_unit_per_feddan_to_kg_per_m2(
    amount: float, crop: str, unit: str, table: CropUnitTable
) -> float:
    """'12 إردب للفدان' -> kg/m2."""
    return local_unit_to_kg(amount, crop, unit, table) / FEDDAN_M2


def kg_per_m2_to_local_unit_per_feddan(
    kg_per_m2: float, crop: str, unit: str, table: CropUnitTable
) -> float:
    return kg_to_local_unit(kg_per_m2 * FEDDAN_M2, crop, unit, table)


# Price: EGP/kg internal.
def price_per_tonne_to_per_kg(egp_per_tonne: float) -> float:
    return _non_negative(egp_per_tonne, "price") / KG_PER_TONNE


def price_per_kg_to_per_tonne(egp_per_kg: float) -> float:
    return _non_negative(egp_per_kg, "price") * KG_PER_TONNE


def price_per_local_unit_to_per_kg(
    egp_per_unit: float, crop: str, unit: str, table: CropUnitTable
) -> float:
    """'سعر الإردب 2000 جنيه' -> EGP/kg."""
    return _non_negative(egp_per_unit, "price") / kg_per_local_unit(crop, unit, table)


def price_per_kg_to_per_local_unit(
    egp_per_kg: float, crop: str, unit: str, table: CropUnitTable
) -> float:
    return _non_negative(egp_per_kg, "price") * kg_per_local_unit(crop, unit, table)


# Money per area and water per area.
def egp_per_feddan_to_egp_per_m2(v: float) -> float:
    return v / FEDDAN_M2


def egp_per_m2_to_egp_per_feddan(v: float) -> float:
    return v * FEDDAN_M2


def m3_per_feddan_to_m3_per_m2(v: float) -> float:
    return _non_negative(v, "m3_per_feddan") / FEDDAN_M2


def m3_per_m2_to_m3_per_feddan(v: float) -> float:
    return _non_negative(v, "m3_per_m2") * FEDDAN_M2
