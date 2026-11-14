"""Data loaders and validators for FieldWise AI Egypt knowledge base.

Loads and validates CSV files in data/:
  * crop_profiles.csv
  * crop_prices.csv
  * cost_assumptions.csv
  * regulations.csv
  * rotation_rules.csv
  * sources_registry.csv

All data rows preserve status (e.g. ai_draft_unverified, needs_verification)
and confidence (low, medium, high) so they can be surfaced in API responses and UIs.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_DATA_DIR = Path("data")


def _resolve_path(path: str | Path, filename: str) -> Path:
    p = Path(path)
    if p.is_dir():
        p = p / filename
    if not p.exists():
        # Fallback to look relative to repo root
        root_candidate = Path(__file__).resolve().parent.parent.parent / "data" / filename
        if root_candidate.exists():
            return root_candidate
    return p


# ============================================================================
# 1. Crop Profiles
# ============================================================================

@dataclass(frozen=True)
class CropProfileRecord:
    crop_id: str
    name_en: str
    name_ar: str
    aliases_ar: List[str]
    season: str
    family: str
    is_legume: bool
    cycle_days_min: int
    cycle_days_max: int
    sow_start_month: int
    sow_end_month: int
    temp_abs_min_c: float
    temp_opt_min_c: float
    temp_opt_max_c: float
    temp_abs_max_c: float
    ph_abs_min: float
    ph_opt_min: float
    ph_opt_max: float
    ph_abs_max: float
    salinity_threshold_ece_dsm: float
    kc_ini: float
    kc_mid: float
    kc_end: float
    local_sale_unit: str
    yield_low_t_per_feddan: float
    yield_high_t_per_feddan: float
    yield_source: str
    policy_flags: str
    source_basis: str
    status: str
    confidence: str
    notes: str


def validate_crop_profile(c: CropProfileRecord) -> None:
    """Validate agronomic ranges and orderings."""
    if not (c.temp_abs_min_c <= c.temp_opt_min_c <= c.temp_opt_max_c <= c.temp_abs_max_c):
        raise ValueError(
            f"Invalid temperature range for {c.crop_id}: "
            f"expected abs_min ({c.temp_abs_min_c}) <= opt_min ({c.temp_opt_min_c}) <= "
            f"opt_max ({c.temp_opt_max_c}) <= abs_max ({c.temp_abs_max_c})"
        )
    if not (c.ph_abs_min <= c.ph_opt_min <= c.ph_opt_max <= c.ph_abs_max):
        raise ValueError(
            f"Invalid pH range for {c.crop_id}: "
            f"expected abs_min ({c.ph_abs_min}) <= opt_min ({c.ph_opt_min}) <= "
            f"opt_max ({c.ph_opt_max}) <= abs_max ({c.ph_abs_max})"
        )
    if c.cycle_days_min <= 0 or c.cycle_days_max < c.cycle_days_min:
        raise ValueError(
            f"Invalid cycle days for {c.crop_id}: {c.cycle_days_min}-{c.cycle_days_max}"
        )
    if not (1 <= c.sow_start_month <= 12 and 1 <= c.sow_end_month <= 12):
        raise ValueError(
            f"Invalid sowing months for {c.crop_id}: start={c.sow_start_month}, end={c.sow_end_month}"
        )
    if c.yield_low_t_per_feddan < 0 or c.yield_high_t_per_feddan < c.yield_low_t_per_feddan:
        raise ValueError(
            f"Invalid yield range for {c.crop_id}: {c.yield_low_t_per_feddan}-{c.yield_high_t_per_feddan}"
        )
    if not c.status:
        raise ValueError(f"Missing status for crop profile: {c.crop_id}")


def load_crop_profiles(path: str | Path = "data/crop_profiles.csv") -> Dict[str, CropProfileRecord]:
    """Load and validate all rows from crop_profiles.csv."""
    resolved = _resolve_path(path, "crop_profiles.csv")
    crops: Dict[str, CropProfileRecord] = {}
    with open(resolved, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            crop_id = (row.get("crop_id") or "").strip().lower()
            if not crop_id:
                continue

            aliases = [a.strip() for a in (row.get("aliases_ar") or "").split("|") if a.strip()]

            profile = CropProfileRecord(
                crop_id=crop_id,
                name_en=(row.get("name_en") or "").strip(),
                name_ar=(row.get("name_ar") or "").strip(),
                aliases_ar=aliases,
                season=(row.get("season") or "").strip().lower(),
                family=(row.get("family") or "").strip(),
                is_legume=(row.get("is_legume") or "").strip().lower() in ("true", "1", "yes"),
                cycle_days_min=int(row.get("cycle_days_min") or 0),
                cycle_days_max=int(row.get("cycle_days_max") or 0),
                sow_start_month=int(row.get("sow_start_month") or 0),
                sow_end_month=int(row.get("sow_end_month") or 0),
                temp_abs_min_c=float(row.get("temp_abs_min_c") or 0.0),
                temp_opt_min_c=float(row.get("temp_opt_min_c") or 0.0),
                temp_opt_max_c=float(row.get("temp_opt_max_c") or 0.0),
                temp_abs_max_c=float(row.get("temp_abs_max_c") or 0.0),
                ph_abs_min=float(row.get("ph_abs_min") or 0.0),
                ph_opt_min=float(row.get("ph_opt_min") or 0.0),
                ph_opt_max=float(row.get("ph_opt_max") or 0.0),
                ph_abs_max=float(row.get("ph_abs_max") or 0.0),
                salinity_threshold_ece_dsm=float(row.get("salinity_threshold_ece_dsm") or 0.0),
                kc_ini=float(row.get("kc_ini") or 0.0),
                kc_mid=float(row.get("kc_mid") or 0.0),
                kc_end=float(row.get("kc_end") or 0.0),
                local_sale_unit=(row.get("local_sale_unit") or "").strip(),
                yield_low_t_per_feddan=float(row.get("yield_low_t_per_feddan") or 0.0),
                yield_high_t_per_feddan=float(row.get("yield_high_t_per_feddan") or 0.0),
                yield_source=(row.get("yield_source") or "").strip(),
                policy_flags=(row.get("policy_flags") or "").strip(),
                source_basis=(row.get("source_basis") or "").strip(),
                status=(row.get("status") or "").strip(),
                confidence=(row.get("confidence") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            )
            validate_crop_profile(profile)
            crops[crop_id] = profile

    return crops


# ============================================================================
# 2. Crop Prices
# ============================================================================

@dataclass(frozen=True)
class CropPriceRecord:
    crop_id: str
    price_type: str
    price_low_egp_per_kg: float
    price_high_egp_per_kg: float
    original_quote: str
    price_date: str
    source_url: str
    status: str
    confidence: str
    notes: str

    @property
    def price_mid_egp_per_kg(self) -> float:
        return (self.price_low_egp_per_kg + self.price_high_egp_per_kg) / 2.0


def validate_crop_price(p: CropPriceRecord) -> None:
    if p.price_low_egp_per_kg < 0 or p.price_high_egp_per_kg < p.price_low_egp_per_kg:
        raise ValueError(
            f"Invalid price range for {p.crop_id}: {p.price_low_egp_per_kg}-{p.price_high_egp_per_kg}"
        )
    if not p.status:
        raise ValueError(f"Missing status for crop price: {p.crop_id}")


def load_crop_prices(path: str | Path = "data/crop_prices.csv") -> Dict[str, CropPriceRecord]:
    """Load price ranges per kg per crop from crop_prices.csv."""
    resolved = _resolve_path(path, "crop_prices.csv")
    prices: Dict[str, CropPriceRecord] = {}
    with open(resolved, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            crop_id = (row.get("crop_id") or "").strip().lower()
            if not crop_id:
                continue
            rec = CropPriceRecord(
                crop_id=crop_id,
                price_type=(row.get("price_type") or "").strip(),
                price_low_egp_per_kg=float(row.get("price_low_egp_per_kg") or 0.0),
                price_high_egp_per_kg=float(row.get("price_high_egp_per_kg") or 0.0),
                original_quote=(row.get("original_quote") or "").strip(),
                price_date=(row.get("price_date") or "").strip(),
                source_url=(row.get("source_url") or "").strip(),
                status=(row.get("status") or "").strip(),
                confidence=(row.get("confidence") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            )
            validate_crop_price(rec)
            prices[crop_id] = rec
    return prices


# ============================================================================
# 3. Cost Assumptions
# ============================================================================

@dataclass(frozen=True)
class CostItemRecord:
    crop_id: str
    item: str
    value_egp_per_feddan_per_season: float
    basis: str
    date: str
    source: str
    status: str
    confidence: str
    default_included: bool


def load_cost_assumptions(path: str | Path = "data/cost_assumptions.csv") -> Dict[str, List[CostItemRecord]]:
    """Load itemized costs per feddan for each crop from cost_assumptions.csv."""
    resolved = _resolve_path(path, "cost_assumptions.csv")
    costs: Dict[str, List[CostItemRecord]] = {}
    with open(resolved, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            crop_id = (row.get("crop_id") or "").strip().lower()
            if not crop_id:
                continue
            val_str = (row.get("value_egp_per_feddan_per_season") or "").strip()
            val = float(val_str) if val_str else 0.0
            if val < 0:
                raise ValueError(f"Cost item {row.get('item')} for {crop_id} must be >= 0, got {val}")

            def_inc = (row.get("default_included") or "true").strip().lower() in ("true", "1", "yes")

            rec = CostItemRecord(
                crop_id=crop_id,
                item=(row.get("item") or "").strip(),
                value_egp_per_feddan_per_season=val,
                basis=(row.get("basis") or "").strip(),
                date=(row.get("date") or "").strip(),
                source=(row.get("source") or "").strip(),
                status=(row.get("status") or "").strip(),
                confidence=(row.get("confidence") or "").strip(),
                default_included=def_inc,
            )
            costs.setdefault(crop_id, []).append(rec)
    return costs


def get_crop_cost_items(
    costs_by_crop: Dict[str, List[CostItemRecord]],
    crop_id: str,
    include_rent: bool = False,
) -> Dict[str, float]:
    """Return dictionary of itemized cost names -> EGP/feddan for a crop."""
    items: Dict[str, float] = {}
    records = costs_by_crop.get(crop_id.strip().lower(), [])
    for r in records:
        if r.item == "rent" and not include_rent:
            continue
        items[r.item] = r.value_egp_per_feddan_per_season
    return items


# ============================================================================
# 4. Regulations
# ============================================================================

@dataclass(frozen=True)
class RegulationRecord:
    rule_id: str
    crop_id: str
    scope: str
    season: str
    rule_type: str  # info | flag | hard
    rule_text: str
    source: str
    last_checked: str
    status: str


def load_regulations(path: str | Path = "data/regulations.csv") -> List[RegulationRecord]:
    """Load regulatory policy rules from regulations.csv."""
    resolved = _resolve_path(path, "regulations.csv")
    rules: List[RegulationRecord] = []
    with open(resolved, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rule_id = (row.get("rule_id") or "").strip()
            if not rule_id:
                continue
            rules.append(
                RegulationRecord(
                    rule_id=rule_id,
                    crop_id=(row.get("crop_id") or "").strip().lower(),
                    scope=(row.get("scope") or "").strip(),
                    season=(row.get("season") or "").strip(),
                    rule_type=(row.get("rule_type") or "").strip().lower(),
                    rule_text=(row.get("rule_text") or "").strip(),
                    source=(row.get("source") or "").strip(),
                    last_checked=(row.get("last_checked") or "").strip(),
                    status=(row.get("status") or "").strip(),
                )
            )
    return rules


# ============================================================================
# 5. Rotation Rules
# ============================================================================

@dataclass(frozen=True)
class RotationRuleRecord:
    rule_id: str
    rule_type: str  # bonus | hard | soft
    applies_to: str
    effect: str
    rule_text: str
    source_basis: str
    status: str


def load_rotation_rules(path: str | Path = "data/rotation_rules.csv") -> List[RotationRuleRecord]:
    """Load agronomic rotation rules from rotation_rules.csv."""
    resolved = _resolve_path(path, "rotation_rules.csv")
    rules: List[RotationRuleRecord] = []
    with open(resolved, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rule_id = (row.get("rule_id") or "").strip()
            if not rule_id:
                continue
            rules.append(
                RotationRuleRecord(
                    rule_id=rule_id,
                    rule_type=(row.get("rule_type") or "").strip().lower(),
                    applies_to=(row.get("applies_to") or "").strip(),
                    effect=(row.get("effect") or "").strip(),
                    rule_text=(row.get("rule_text") or "").strip(),
                    source_basis=(row.get("source_basis") or "").strip(),
                    status=(row.get("status") or "").strip(),
                )
            )
    return rules


# ============================================================================
# 6. Sources Registry
# ============================================================================

@dataclass(frozen=True)
class SourceRegistryRecord:
    source: str
    url: str
    covers_egypt: bool
    what_it_feeds: str
    priority: str
    notes: str
    checked_date: str


def load_sources_registry(path: str | Path = "data/sources_registry.csv") -> List[SourceRegistryRecord]:
    """Load data source coverage registry."""
    resolved = _resolve_path(path, "sources_registry.csv")
    sources: List[SourceRegistryRecord] = []
    with open(resolved, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = (row.get("source") or "").strip()
            if not src:
                continue
            covers = (row.get("covers_egypt") or "").strip().lower() in ("true", "1", "yes")
            sources.append(
                SourceRegistryRecord(
                    source=src,
                    url=(row.get("url") or "").strip(),
                    covers_egypt=covers,
                    what_it_feeds=(row.get("what_it_feeds") or "").strip(),
                    priority=(row.get("priority") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                    checked_date=(row.get("checked_date") or "").strip(),
                )
            )
    return sources
