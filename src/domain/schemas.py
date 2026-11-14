"""Core domain schemas and contracts for FieldWise AI (Napta).

These schemas define the single source of truth between the FastAPI backend,
the decision engine (Track A contract), the Farmer Voice Assistant, and the Expert Console.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.domain.provenance import ProvenanceRecord, DataSourceType


class AgriculturalSeason(str, Enum):
    """Agricultural seasons in Egypt."""
    WINTER = "winter"  # شتوي (Oct/Nov - Apr/May)
    SUMMER = "summer"  # صيفي (May/Jun - Sep/Oct)
    NILI = "nili"      # نيلي (Late Summer/Autumn - Aug to Dec)
    PERENNIAL = "perennial"  # مستديم (e.g. Citrus/Orchards)


class WaterSourceType(str, Enum):
    """Common Egyptian water sources and canal systems."""
    CANAL_ROTATION = "canal_rotation"      # ترعة بالمناوبة (Canal with rotation schedule)
    CANAL_CONTINUOUS = "canal_continuous"  # ترعة مستمرة (Continuous branch canal)
    GROUNDWATER_WELL = "groundwater_well"  # بئر ارتوازي (Deep or shallow groundwater well)
    DRAINAGE_REUSE = "drainage_reuse"      # مياه صرف زراعي مخلوطة (Drainage reuse)
    NILE_DIRECT = "nile_direct"            # ري مباشر من النيل
    UNKNOWN = "unknown"


class IrrigationMethod(str, Enum):
    """Irrigation method used on the plot."""
    SURFACE_FLOOD = "surface_flood"  # غمر تقليدي
    DRIP = "drip"                    # تنقيط حديث
    SPRINKLER = "sprinkler"          # رش
    IMPROVED_SURFACE = "improved_surface" # تطوير ري مساقي


class FarmerPriority(str, Enum):
    """Primary economic or strategic objective of the farmer."""
    MAX_PROFIT = "max_profit"      # الأكسب (Highest net return)
    SAVE_WATER = "save_water"      # الأوفر في المية (Minimum water consumption)
    LOW_RISK = "low_risk"          # الأأمن (Stable yield, guaranteed marketing)
    BALANCED = "balanced"          # متوازن


# ============================================================================
# 1. FarmProfile
# ============================================================================

class FarmCoordinates(BaseModel):
    """Geographic coordinates for environmental retrieval."""
    latitude: float = Field(..., ge=21.0, le=32.0, description="Egypt latitude range (22-31.8N)")
    longitude: float = Field(..., ge=24.0, le=37.0, description="Egypt longitude range (24.7-36.9E)")


class FarmArea(BaseModel):
    """Egyptian land area measurement."""
    feddans: float = Field(default=0.0, ge=0.0, description="1 Feddan = 4,200.83 m² = 24 Qirats")
    qirats: float = Field(default=0.0, ge=0.0, le=24.0, description="1 Qirat = 175.03 m² = 24 Sahms")

    @property
    def total_feddans(self) -> float:
        """Normalized area expressed strictly in feddans."""
        return round(self.feddans + (self.qirats / 24.0), 3)


class FarmProfile(BaseModel):
    """Comprehensive farmer profile representing plot attributes and constraints."""
    farm_id: Optional[str] = Field(None, description="Unique farm identifier")
    farmer_name: Optional[str] = Field("يا حاج", description="Farmer name or formal greeting")
    location_name: str = Field(..., description="Governorate or district name (e.g. Kafr El-Sheikh, Minya)")
    coordinates: FarmCoordinates = Field(..., description="GPS location for NASA & SoilGrids")
    area: FarmArea = Field(..., description="Total agricultural area")
    water_source: WaterSourceType = Field(WaterSourceType.CANAL_ROTATION, description="Source of irrigation water")
    irrigation_method: IrrigationMethod = Field(IrrigationMethod.SURFACE_FLOOD, description="Field irrigation type")
    available_budget_egp: Optional[float] = Field(None, ge=0.0, description="Working capital in Egyptian Pounds")
    previous_crops: List[str] = Field(default_factory=list, description="Crops cultivated in prior seasons")
    primary_objective: FarmerPriority = Field(FarmerPriority.MAX_PROFIT, description="Farmer objective")
    notes: Optional[str] = Field(None, description="Additional field notes")


# ============================================================================
# 2. Environmental Summary
# ============================================================================

class ClimateSummary(BaseModel):
    """NASA POWER climatological averages."""
    annual_mean_temp_c: float = Field(..., description="T2M annual average (°C)")
    summer_mean_temp_c: float = Field(..., description="T2M summer average (°C)")
    winter_mean_temp_c: float = Field(..., description="T2M winter average (°C)")
    relative_humidity_pct: float = Field(..., description="RH2M annual average (%)")
    wind_speed_ms: float = Field(..., description="WS2M annual average (m/s)")
    solar_radiation_kwh_m2_day: float = Field(..., description="ALLSKY_SFC_SW_DWN (kWh/m²/day)")
    annual_precipitation_mm: float = Field(..., description="PRECTOTCORR annual total (mm)")


class SoilSummary(BaseModel):
    """SoilGrids properties at standard agricultural rooting depths (0-30cm)."""
    ph_water: float = Field(..., description="Soil pH in H2O")
    organic_carbon_g_kg: float = Field(..., description="Soil organic carbon in g/kg")
    clay_pct: float = Field(..., description="Clay fraction percentage")
    silt_pct: float = Field(..., description="Silt fraction percentage")
    sand_pct: float = Field(..., description="Sand fraction percentage")
    bulk_density_cg_cm3: float = Field(..., description="Bulk density in cg/cm³ (or 10 kg/m³)")
    cation_exchange_capacity_cmolc_kg: float = Field(..., description="CEC in cmol(+)/kg")
    texture_class: str = Field(..., description="USDA soil texture class (e.g. Clay, Silty Clay, Sandy Loam)")
    salinity_status: str = Field(
        "UNKNOWN",
        description="SoilGrids does NOT measure salinity. Unknown salinity must remain explicitly UNKNOWN."
    )
    salinity_estimated_dsm: Optional[float] = Field(None, description="Only provided if measured locally or entered")


class EnvironmentSummary(BaseModel):
    """Unified environmental profile with provenance and missing-data indicators."""
    climate: ClimateSummary
    soil: SoilSummary
    provenance: List[ProvenanceRecord] = Field(default_factory=list)
    missing_data_warnings: List[str] = Field(default_factory=list)
    is_fixture: bool = Field(False, description="True if loaded from offline fallback fixtures")


# ============================================================================
# 3. CropProfile
# ============================================================================

class CropRequirements(BaseModel):
    """Agronomic bounds for crop suitability."""
    temp_min_c: float
    temp_opt_min_c: float
    temp_opt_max_c: float
    temp_max_c: float
    soil_ph_min: float
    soil_ph_max: float
    salinity_threshold_dsm: float  # ECe at which yield starts declining
    water_demand_m3_per_feddan: float  # Typical water requirement per feddan in Egypt


class CropProfile(BaseModel):
    """Crop catalog item with Egyptian agronomic benchmarks."""
    crop_id: str
    name_en: str
    name_ar: str
    season: AgriculturalSeason
    growth_duration_days: int
    requirements: CropRequirements
    average_yield_ton_per_feddan: float
    benchmark_selling_price_egp_per_ton: float
    typical_cost_per_feddan_egp: float
    sources: Dict[str, str] = Field(default_factory=dict, description="Provenance for each metric (FAO, MALR, ARC)")


# ============================================================================
# 4. Plan & Recommendation Metrics
# ============================================================================

class CostBreakdown(BaseModel):
    """Itemized farm operating costs per feddan in EGP."""
    seeds_seedlings_egp: float = 0.0
    fertilizers_and_soil_amendments_egp: float = 0.0
    fuel_and_irrigation_electricity_egp: float = 0.0
    labor_and_machinery_egp: float = 0.0
    land_preparation_egp: float = 0.0
    total_cost_per_feddan_egp: float = 0.0


class PlanMetrics(BaseModel):
    """Financial and natural resource metrics for a crop plan."""
    gross_revenue_egp_per_feddan: float
    total_gross_revenue_egp: float
    cost_breakdown: CostBreakdown
    total_cost_egp: float
    net_profit_egp_per_feddan: float
    total_net_profit_egp: float
    roi_percentage: float
    water_demand_m3_per_feddan: float
    total_water_demand_m3: float
    risk_level: str = Field(..., description="Low, Medium, or High risk")
    risk_rationale: str


class Plan(BaseModel):
    """A crop recommendation plan for a specific season or rotation."""
    plan_id: str
    archetype: str = Field(..., description="الأكسب (Highest Profit) | الأوفر في المية (Water Saving) | الأأمن (Lowest Risk)")
    primary_crop_en: str
    primary_crop_ar: str
    season: AgriculturalSeason
    rotation_sequence: List[str] = Field(default_factory=list, description="e.g. ['قمح (شتوي)', 'ذرة شامية (صيفي)']")
    suitability_score: float = Field(..., ge=0.0, le=100.0, description="Overall agronomic fit (0-100)")
    metrics: PlanMetrics
    key_advice_ar: str = Field(..., description="Actionable Egyptian agricultural advice in Arabic")
    disclaimer_ar: str = Field(
        "ده تقدير مش ضمان، والأسعار والمحصول بيتغيروا حسب السوق والخدمة.",
        description="Mandatory disclaimer: estimate, not guarantee"
    )


class RecommendationResponse(BaseModel):
    """Complete recommendation package presenting 3 plans."""
    farm_id: Optional[str]
    farm_location: str
    total_feddans: float
    environment_summary: EnvironmentSummary
    recommendations: List[Plan] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="Exactly the three archetypes: الأكسب, الأوفر في المية, الأأمن"
    )
    generated_at: str


# ============================================================================
# 5. Scenario Simulation Spec
# ============================================================================

class ScenarioSpec(BaseModel):
    """Simulation parameters for stress-testing farm plans."""
    scenario_name: str
    water_availability_multiplier: float = Field(1.0, ge=0.4, le=1.6, description="e.g. 0.8 = 20% water shortage")
    fertilizer_cost_multiplier: float = Field(1.0, ge=0.5, le=2.5, description="e.g. 1.3 = 30% price inflation")
    crop_price_multiplier: float = Field(1.0, ge=0.5, le=2.0, description="e.g. 0.9 = 10% market price dip")
    temp_anomaly_c: float = Field(0.0, ge=-5.0, le=6.0, description="e.g. +2.0°C heatwave scenario")


# ============================================================================
# 6. Voice AI Dialogue Schemas
# ============================================================================

class ParsedVoiceSlots(BaseModel):
    """Structured slots extracted from Egyptian farmer speech."""
    location_name: Optional[str] = None
    area_feddans: Optional[float] = None
    area_qirats: Optional[float] = None
    water_source: Optional[WaterSourceType] = None
    previous_crops: List[str] = Field(default_factory=list)
    available_budget_egp: Optional[float] = None
    primary_objective: Optional[FarmerPriority] = None
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    unrecognized_terms: List[str] = Field(default_factory=list)


class ConfirmationDialogueState(BaseModel):
    """Tracks voice assistant confirmation flow."""
    session_id: str
    status: str = Field("PENDING_CONFIRMATION", description="PENDING_CONFIRMATION | CONFIRMED | REJECTED | CLARIFYING")
    confirmation_phrase_ar: str
    parsed_slots: ParsedVoiceSlots
    needs_clarification_on: List[str] = Field(default_factory=list)
