"""Data provenance and lineage models for FieldWise AI."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DataSourceType(str, Enum):
    """Categorization of data origins for scientific and audit transparency."""
    SOURCED = "sourced"           # Directly fetched from validated API (e.g., NASA POWER, SoilGrids)
    FARMER_ENTERED = "farmer"     # Provided directly by the farmer via voice or UI
    ESTIMATED = "estimated"       # Agronomic empirical estimation (e.g. FAO-56 ETo formula)
    SIMULATED = "simulated"       # Scenario simulation model outputs
    FIXTURE = "fixture"           # Offline local demonstration fallback
    UNKNOWN = "unknown"           # Explicitly unknown or unmeasured


class ProvenanceRecord(BaseModel):
    """Lineage and provenance metadata for an individual observation or dataset."""
    source_name: str = Field(..., description="External source name (e.g., NASA_POWER, SoilGrids, Farmer_Voice)")
    source_type: DataSourceType = Field(..., description="Classification of how data was obtained")
    retrieval_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when data was retrieved or recorded"
    )
    original_units: Optional[str] = Field(None, description="Units returned by raw source")
    standardized_units: Optional[str] = Field(None, description="Units in FieldWise domain model")
    transformation_applied: Optional[str] = Field(None, description="Transformation description (e.g., dS/m, depth average)")
    quality_flag: str = Field("VALID", description="Data quality assessment (VALID, ESTIMATED, MISSING, DEGRADED)")
    notes: Optional[str] = Field(None, description="Audit or caveat notes (e.g., SoilGrids lacks salinity)")
    raw_payload_snippet: Optional[Dict[str, Any]] = Field(None, description="Snippet of raw upstream response for traceability")


class ProvenanceContainer(BaseModel):
    """Wrapper that attaches provenance records to any domain entity."""
    provenance_records: List[ProvenanceRecord] = Field(default_factory=list)

    def add_record(self, record: ProvenanceRecord) -> None:
        self.provenance_records.append(record)
