"""Regression tests for two problems found when the overnight build was reviewed.

1. The three archetype plans must not be identical copies of each other.
2. Staple crops must not be hard-excluded by the Kafr El-Sheikh fixture soil
   (SoilGrids pH 8.05): Delta soils are alkaline and wheat is grown there.
"""
from tests.test_golden_e2e import load_demo_farm_profile
from src.agronomy.suitability import evaluate_crop_suitability
from src.data.loaders import load_crop_profiles
from src.data.nasa_power_client import NasaPowerClient
from src.data.soilgrids_client import SoilGridsClient
from src.domain.schemas import EnvironmentSummary
from src.services.decision_engine_adapter import DecisionEngineAdapter


def _demo_env(farm):
    lat, lon = farm.coordinates.latitude, farm.coordinates.longitude
    c, cp, _ = NasaPowerClient()._load_fallback_fixture(lat, lon)
    s, sp, _ = SoilGridsClient()._load_fallback_fixture(lat, lon)
    return EnvironmentSummary(
        climate=c, soil=s, provenance=[cp, sp], missing_data_warnings=[], is_fixture=True
    )


def test_three_archetype_plans_are_distinct():
    farm = load_demo_farm_profile()
    plans = DecisionEngineAdapter().generate_recommendations(profile=farm, env=_demo_env(farm))
    assert len(plans) == 3
    sequences = {tuple(p.rotation_sequence) for p in plans}
    assert len(sequences) == 3, "The three plans must be three different rotations"


def test_wheat_and_maize_not_hard_excluded_by_delta_soil():
    farm = load_demo_farm_profile()
    env = _demo_env(farm)
    profiles = load_crop_profiles()
    for crop_id in ("wheat", "maize", "rice"):
        rec = profiles[crop_id]
        res = evaluate_crop_suitability(
            crop=rec, env=env, planting_month=rec.sow_start_month, measured_salinity_ece_dsm=None
        )
        assert res.hard_exclusions == [], f"{crop_id} excluded: {res.hard_exclusions}"
