"""Farm profile submission and management endpoints."""

import uuid
from typing import Dict
from fastapi import APIRouter, HTTPException, status
from src.domain.schemas import FarmProfile

router = APIRouter(prefix="/api/farm-profile", tags=["Farm Profile"])

# In-memory storage for demonstration and fast retrieval
FARM_STORAGE: Dict[str, FarmProfile] = {}


@router.post("", response_model=FarmProfile, status_code=status.HTTP_201_CREATED)
async def submit_farm_profile(profile: FarmProfile):
    """Submit a validated farm profile containing coordinates, area in feddans, water source, and history."""
    farm_id = profile.farm_id or f"farm_{uuid.uuid4().hex[:8]}"
    profile.farm_id = farm_id
    FARM_STORAGE[farm_id] = profile
    return profile


@router.get("/{farm_id}", response_model=FarmProfile)
async def get_farm_profile(farm_id: str):
    """Retrieve an existing farm profile by ID."""
    if farm_id not in FARM_STORAGE:
        raise HTTPException(status_code=404, detail=f"Farm profile '{farm_id}' not found.")
    return FARM_STORAGE[farm_id]
