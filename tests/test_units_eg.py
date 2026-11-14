"""Tests for units_eg. Expected values are computed by hand.

Hand facts used:
    1 feddan = 24 qirat; 1 qirat = 24 sahm; 1 feddan = 576 sahm
    1 feddan = 4200.83 m2  ->  10 feddan = 42008.3 m2
    1 ha = 10000 m2; 1 tonne = 1000 kg; 1 m3 = 1000 L; 1 mm = 10 m3/ha
NOTE: 'test_crop' / 'test_unit' values below are FAKE numbers used only to
test the math. They are not agronomic facts.
"""
import pytest

from src.egypt import units_eg as u

FAKE_TABLE = {("testcrop", "ardab"): 100.0, ("testcrop", "qantar"): 50.0}


# ------------------------------------------------------------------ area
def test_feddan_split():
    assert u.feddan_to_qirat(1) == 24
    assert u.qirat_to_sahm(1) == 24
    assert u.feddan_to_sahm(1) == 576
    assert u.qirat_to_feddan(12) == 0.5
    assert u.sahm_to_qirat(48) == 2
    assert u.sahm_to_feddan(288) == 0.5


def test_feddan_to_m2():
    assert u.feddan_to_m2(10) == pytest.approx(42008.3)
    assert u.m2_to_feddan(42008.3) == pytest.approx(10)


def test_qirat_sahm_m2_consistent():
    assert u.qirat_to_m2(24) == pytest.approx(u.feddan_to_m2(1))
    assert u.sahm_to_m2(576) == pytest.approx(u.feddan_to_m2(1))


def test_ha():
    assert u.ha_to_m2(1) == 10_000
    assert u.m2_to_ha(5_000) == 0.5
    assert u.ha_to_feddan(1) == pytest.approx(2.3805, rel=1e-4)
    assert u.feddan_to_ha(10) == pytest.approx(4.20083)


def test_roundtrip_feddan_ha():
    assert u.ha_to_feddan(u.feddan_to_ha(7.3)) == pytest.approx(7.3)


def test_fqs_to_m2():
    # 3 feddan 12 qirat = 3.5 feddan
    assert u.fqs_to_m2(3, 12, 0) == pytest.approx(3.5 * 4200.83)
    # 1 qirat 12 sahm = 1.5 qirat
    assert u.fqs_to_m2(0, 1, 12) == pytest.approx(1.5 * 4200.83 / 24)


def test_m2_to_fqs():
    assert u.m2_to_fqs(u.fqs_to_m2(3, 12, 0)) == (3, 12, 0)
    assert u.m2_to_fqs(u.fqs_to_m2(10, 5, 7)) == (10, 5, 7)
    assert u.m2_to_fqs(0) == (0, 0, 0)


def test_negative_rejected():
    with pytest.raises(ValueError):
        u.feddan_to_m2(-1)
    with pytest.raises(ValueError):
        u.kg_to_tonne(-5)


# ------------------------------------------------------------ mass / volume
def test_mass():
    assert u.tonne_to_kg(2.5) == 2500
    assert u.kg_to_tonne(500) == 0.5


def test_volume():
    assert u.m3_to_litre(2) == 2000
    assert u.litre_to_m3(500) == 0.5


def test_mm_water():
    assert u.mm_to_m3_per_ha(5) == 50
    assert u.m3_per_ha_to_mm(100) == 10
    # 10 mm over 1 ha (10000 m2) = 100 m3
    assert u.mm_to_m3(10, 10_000) == pytest.approx(100)


# --------------------------------------------------- crop-specific units
def test_ardab_qantar():
    assert u.ardab_to_kg(3, "testcrop", FAKE_TABLE) == 300
    assert u.kg_to_ardab(250, "TestCrop", FAKE_TABLE) == 2.5  # case-insensitive
    assert u.qantar_to_kg(2, "testcrop", FAKE_TABLE) == 100
    assert u.kg_to_qantar(25, "testcrop", FAKE_TABLE) == 0.5


def test_missing_unit_raises_not_guesses():
    with pytest.raises(u.MissingUnitError):
        u.ardab_to_kg(1, "unknowncrop", FAKE_TABLE)
    with pytest.raises(u.MissingUnitError):
        u.qantar_to_kg(1, "unknowncrop", FAKE_TABLE)


def test_load_crop_units(tmp_path):
    f = tmp_path / "crop_units.csv"
    f.write_text(
        "crop,unit,kg_per_unit,source\n"
        "testcrop,ardab,100,unit-test\n"
        "emptycrop,ardab,,\n",
        encoding="utf-8",
    )
    table = u.load_crop_units(f)
    assert table == {("testcrop", "ardab"): 100.0}  # empty row skipped


def test_load_rejects_value_without_source(tmp_path):
    f = tmp_path / "crop_units.csv"
    f.write_text("crop,unit,kg_per_unit,source\ntestcrop,ardab,100,\n", encoding="utf-8")
    with pytest.raises(ValueError):
        u.load_crop_units(f)


# ------------------------------------------------------------- composites
def test_yield_conversion():
    # 4200.83 kg/feddan = 10000 kg/ha
    assert u.yield_kg_per_feddan_to_kg_per_ha(4200.83) == pytest.approx(10_000)
    assert u.yield_kg_per_ha_to_kg_per_feddan(10_000) == pytest.approx(4200.83)


def test_yield_local_unit():
    # 10 fake-ardab/feddan = 1000 kg/feddan -> 1000/4200.83 kg/m2
    v = u.yield_local_unit_per_feddan_to_kg_per_m2(10, "testcrop", "ardab", FAKE_TABLE)
    assert v == pytest.approx(1000 / 4200.83)
    back = u.kg_per_m2_to_local_unit_per_feddan(v, "testcrop", "ardab", FAKE_TABLE)
    assert back == pytest.approx(10)


def test_price():
    assert u.price_per_tonne_to_per_kg(20_000) == 20
    assert u.price_per_kg_to_per_tonne(20) == 20_000
    # 2000 EGP per fake-ardab (100 kg) = 20 EGP/kg
    assert u.price_per_local_unit_to_per_kg(2000, "testcrop", "ardab", FAKE_TABLE) == 20
    assert u.price_per_kg_to_per_local_unit(20, "testcrop", "ardab", FAKE_TABLE) == 2000


def test_money_and_water_per_area():
    assert u.egp_per_feddan_to_egp_per_m2(4200.83) == pytest.approx(1)
    assert u.egp_per_m2_to_egp_per_feddan(1) == pytest.approx(4200.83)
    assert u.m3_per_feddan_to_m3_per_m2(4200.83) == pytest.approx(1)
    assert u.m3_per_m2_to_m3_per_feddan(1) == pytest.approx(4200.83)
