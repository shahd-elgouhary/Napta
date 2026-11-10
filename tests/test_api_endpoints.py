"""Comprehensive API endpoint tests for Farm Profiles, Recommendations, Scenarios, and Sources."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_farm_profile_submission_and_retrieval():
    payload = {
        "farm_id": "test_farm_delta_01",
        "farmer_name": "يا حاج محمود",
        "location_name": "كفر الشيخ",
        "coordinates": {"latitude": 31.11, "longitude": 30.94},
        "area": {"feddans": 3.0, "qirats": 12.0},
        "water_source": "canal_rotation",
        "irrigation_method": "surface_flood",
        "available_budget_egp": 45000.0,
        "previous_crops": ["قمح", "برسيم"],
        "primary_objective": "max_profit",
    }
    # Submit
    res = client.post("/api/farm-profile", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["farm_id"] == "test_farm_delta_01"
    assert data["area"]["feddans"] == 3.0

    # Retrieve
    get_res = client.get("/api/farm-profile/test_farm_delta_01")
    assert get_res.status_code == 200
    assert get_res.json()["farmer_name"] == "يا حاج محمود"


def test_get_environment_point():
    res = client.get("/api/environment/point?lat=31.11&lon=30.94")
    assert res.status_code == 200
    data = res.json()
    assert "climate" in data
    assert "soil" in data
    assert len(data["provenance"]) >= 2
    assert data["soil"]["salinity_status"] == "UNKNOWN"


def test_list_crops():
    res = client.get("/api/crops")
    assert res.status_code == 200
    crops = res.json()
    assert len(crops) >= 5
    crop_ids = [c["crop_id"] for c in crops]
    assert "wheat" in crop_ids
    assert "fava_beans" in crop_ids


def test_generate_recommendations_three_archetypes():
    payload = {
        "farm_id": "farm_rec_test",
        "farmer_name": "يا حاج أحمد",
        "location_name": "المنيا",
        "coordinates": {"latitude": 28.11, "longitude": 30.75},
        "area": {"feddans": 5.0, "qirats": 0.0},
        "water_source": "canal_rotation",
        "irrigation_method": "surface_flood",
        "available_budget_egp": 60000.0,
        "previous_crops": ["ذرة"],
        "primary_objective": "max_profit",
    }
    res = client.post("/api/recommendations", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["total_feddans"] == 5.0
    plans = data["recommendations"]
    assert len(plans) == 3

    archetypes = [p["archetype"] for p in plans]
    assert "الأكسب" in archetypes
    assert "الأوفر في المية" in archetypes
    assert "الأأمن" in archetypes

    for p in plans:
        assert p["suitability_score"] > 0
        assert p["metrics"]["total_net_profit_egp"] is not None
        assert p["metrics"]["total_water_demand_m3"] > 0
        assert "ده تقدير مش ضمان" in p["disclaimer_ar"]


def test_crop_suitability_check():
    payload = {
        "farm_profile": {
            "location_name": "كفر الشيخ",
            "coordinates": {"latitude": 31.11, "longitude": 30.94},
            "area": {"feddans": 2.0, "qirats": 0.0},
            "water_source": "canal_rotation",
            "irrigation_method": "surface_flood",
        },
        "crop_id": "wheat",
    }
    res = client.post("/api/suitability", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["crop_id"] == "wheat"
    assert data["suitability_score"] >= 70.0


def test_scenario_simulation_and_plan_comparison():
    # 1. Get recommendations to obtain a base plan
    farm_payload = {
        "location_name": "المنيا",
        "coordinates": {"latitude": 28.11, "longitude": 30.75},
        "area": {"feddans": 4.0, "qirats": 0.0},
    }
    rec_res = client.post("/api/recommendations", json=farm_payload)
    base_plan = rec_res.json()["recommendations"][0]

    # 2. Simulate 20% water cut
    sim_payload = {
        "base_plan": base_plan,
        "area_feddans": 4.0,
        "scenario_spec": {
            "scenario_name": "عجز مائي بنسبة 20%",
            "water_availability_multiplier": 0.8,
            "fertilizer_cost_multiplier": 1.2,
            "crop_price_multiplier": 1.0,
            "temp_anomaly_c": 1.5,
        },
    }
    sim_res = client.post("/api/scenarios/simulate", json=sim_payload)
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "deltas" in sim_data
    assert sim_data["deltas"]["water_diff_m3"] < 0

    # 3. Compare all 3 plans
    all_plans = rec_res.json()["recommendations"]
    comp_res = client.post("/api/scenarios/compare", json={"plans": all_plans})
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert len(comp_data["comparison_table"]) == 3


def test_sources_metadata_transparency():
    res = client.get("/api/sources")
    assert res.status_code == 200
    data = res.json()
    assert "sources" in data
    source_ids = [s["id"] for s in data["sources"]]
    assert "nasa_power" in source_ids
    assert "soilgrids" in source_ids
    assert "lineage_categories" in data
