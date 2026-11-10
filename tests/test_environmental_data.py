"""Unit and integration tests for environmental data clients, cache, and normalization."""

import pytest
import os
from src.data.cache import EnvironmentalDataCache
from src.data.environment_service import EnvironmentService
from src.data.nasa_power_client import NasaPowerClient
from src.data.normalize import (
    calculate_depth_weighted_average,
    classify_usda_texture,
    normalize_soilgrids_units,
)
from src.data.soilgrids_client import SoilGridsClient
from src.data.validation import validate_egyptian_coordinates


def test_validate_egyptian_coordinates():
    # Valid Cairo / Delta
    valid, errors = validate_egyptian_coordinates(30.04, 31.23)
    assert valid is True
    assert len(errors) == 0

    # Invalid (London)
    invalid, errors = validate_egyptian_coordinates(51.5, -0.12)
    assert invalid is False
    assert len(errors) == 2


def test_classify_usda_texture():
    assert classify_usda_texture(50.0, 35.0, 15.0) == "Clay"
    assert classify_usda_texture(10.0, 20.0, 70.0) == "Sandy Loam"
    assert classify_usda_texture(30.0, 40.0, 30.0) == "Clay Loam"


def test_normalize_soilgrids_units():
    # phh2o: 80 -> 8.0
    assert normalize_soilgrids_units("phh2o", 80.0) == 8.0
    # soc: 120 -> 12.0 g/kg
    assert normalize_soilgrids_units("soc", 120.0) == 12.0
    # clay: 450 -> 45.0%
    assert normalize_soilgrids_units("clay", 450.0) == 45.0
    # bdod: 135 -> 135 cg/cm³
    assert normalize_soilgrids_units("bdod", 135.0) == 135.0


def test_calculate_depth_weighted_average():
    slices = [
        {"label": "0-5cm", "values": {"mean": 80.0}},   # weight 5
        {"label": "5-15cm", "values": {"mean": 82.0}},  # weight 10
        {"label": "15-30cm", "values": {"mean": 85.0}}, # weight 15
    ]
    # (80*5 + 82*10 + 85*15) / (5 + 10 + 15) = (400 + 820 + 1275) / 30 = 2495 / 30 = 83.17
    avg = calculate_depth_weighted_average(slices)
    assert avg == 83.17


def test_cache_set_and_get(tmp_path):
    cache_file = tmp_path / "test_cache.sqlite"
    cache = EnvironmentalDataCache(db_path=str(cache_file), ttl_days=1)
    
    key = "test:1"
    data = {"test_val": 42}
    cache.set(key, "service_a", data)
    
    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved["test_val"] == 42
    
    assert cache.get("non_existent") is None


@pytest.mark.asyncio
async def test_nasa_power_client_fallback_and_provenance(tmp_path):
    cache_file = tmp_path / "test_nasa_cache.sqlite"
    cache = EnvironmentalDataCache(db_path=str(cache_file))
    client = NasaPowerClient(cache=cache, timeout_seconds=0.1)  # immediate timeout to test fallback
    
    # Query Kafr El-Sheikh coordinates
    summary, prov, _ = await client.fetch_climate_data(31.11, 30.94)
    assert summary.annual_mean_temp_c > 15.0
    assert prov.source_name in ("NASA_POWER_API", "NASA_POWER_OFFLINE_FIXTURE")
    assert prov.quality_flag in ("VALID_API", "DEGRADED_FALLBACK_FIXTURE")


@pytest.mark.asyncio
async def test_soilgrids_client_salinity_unknown(tmp_path):
    cache_file = tmp_path / "test_soil_cache.sqlite"
    cache = EnvironmentalDataCache(db_path=str(cache_file))
    client = SoilGridsClient(cache=cache, timeout_seconds=0.1)
    
    summary, prov, _ = await client.fetch_soil_data(31.11, 30.94)
    assert summary.ph_water > 6.0
    # Crucial scientific check: Salinity must be explicitly UNKNOWN
    assert summary.salinity_status == "UNKNOWN"
    assert summary.salinity_estimated_dsm is None


@pytest.mark.asyncio
async def test_environment_service_unified_summary(tmp_path):
    cache_file = tmp_path / "test_env_cache.sqlite"
    cache = EnvironmentalDataCache(db_path=str(cache_file))
    service = EnvironmentService(cache=cache)
    
    env_summary, raw_data = await service.get_environment_summary(28.11, 30.75) # Minya
    assert env_summary.climate is not None
    assert env_summary.soil is not None
    assert len(env_summary.provenance) == 2
    # Verify salinity warning is included in missing data warnings
    salinity_warn = any("salinity" in w.lower() for w in env_summary.missing_data_warnings)
    assert salinity_warn is True
