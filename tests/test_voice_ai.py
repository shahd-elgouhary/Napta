"""Unit and pipeline tests for Egyptian Arabic Voice AI."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.voice.dialog import ConfirmationDialogueManager
from src.voice.lexicon import FellahiLexicon
from src.voice.nlu import EgyptianArabicNLU
from src.voice.phrase_bank import EgyptianPhraseBank

client = TestClient(app)


def test_fellahi_lexicon_normalization_and_aliases():
    lexicon = FellahiLexicon()
    assert lexicon.normalize_arabic_text("أَرْضِي") == "ارضي"
    assert lexicon.normalize_arabic_text("مِيَاهٌ") == "مياه"
    assert lexicon.normalize_arabic_text("تُرْعَةٌ") == "ترعه"

    # Crop recognition
    crops = lexicon.identify_crops("كنت زارع غلة وبرسيم تحريش الموسم اللي فات")
    assert "wheat" in crops
    assert "berseem" in crops

    # Water source
    src = lexicon.identify_water_source("المية بتجيلنا من الترعة بالمناوبة كل أسبوع")
    assert src == "canal_rotation"

    # Location
    loc = lexicon.identify_location("أرضي في كفر الشيخ في بحري")
    assert loc == "Kafr El-Sheikh"


def test_nlu_area_and_budget_extraction():
    nlu = EgyptianArabicNLU()

    # Compound area: 3 feddans and 6 qirats
    slots1 = nlu.parse_utterance("عندي ٣ فدادين و ٦ قراريط في المنيا والمية من البير")
    assert slots1.location_name == "Minya"
    assert slots1.area_feddans == 3.0
    assert slots1.area_qirats == 6.0
    assert slots1.water_source.value == "groundwater_well"

    # Word area & budget
    slots2 = nlu.parse_utterance("عندي فدان ونص في كفر الشيخ ومعايا ٥٠ الف جنيه")
    assert slots2.area_feddans == 1.5
    assert slots2.available_budget_egp == 50000.0


def test_confirmation_dialogue_state_flow():
    nlu = EgyptianArabicNLU()
    manager = ConfirmationDialogueManager()

    slots = nlu.parse_utterance("عندي تلات فدادين في كفر الشيخ والمية بالمناوبة وكنت زارع قمح")
    state = manager.start_session(slots)
    assert state.status == "PENDING_CONFIRMATION"
    assert "كفر الشيخ" in state.confirmation_phrase_ar
    assert "٣.٠ فدان" in state.confirmation_phrase_ar or "3.0 فدان" in state.confirmation_phrase_ar

    # Test affirmative response
    updated_state, reply = manager.handle_farmer_response(state.session_id, "أيوه صح كده")
    assert updated_state.status == "CONFIRMED"
    assert "جاري الآن" in reply

    # Test agricultural engineer trigger
    state2 = manager.start_session(slots)
    eng_state, eng_reply = manager.handle_farmer_response(state2.session_id, "عايز اكلم الباشمهندس الزراعي")
    assert eng_state.status == "SPEAK_TO_ENGINEER"
    assert "المرشد الزراعي" in eng_reply


def test_phrase_bank_disclaimer():
    disclaimer = EgyptianPhraseBank.DISCLAIMER
    assert "ده تقدير" in disclaimer
    assert "مش ضمان" in disclaimer


def test_voice_api_end_to_end():
    # 1. Process farmer voice transcript
    utt_payload = {
        "utterance": "عندي تلات فدادين في كفر الشيخ والمية بتيجي من الترعة بالمناوبة وكنت زارع قمح"
    }
    utt_res = client.post("/api/voice/process-utterance", json=utt_payload)
    assert utt_res.status_code == 200
    utt_data = utt_res.json()
    session_id = utt_data["session_id"]
    assert "صح كده يا حاج؟" in utt_data["spoken_prompt_ar"]

    # 2. Farmer confirms with "أيوه"
    conf_payload = {
        "session_id": session_id,
        "farmer_reply": "أيوه تمام",
    }
    conf_res = client.post("/api/voice/confirm", json=conf_payload)
    assert conf_res.status_code == 200
    conf_data = conf_res.json()
    assert conf_data["status"] == "CONFIRMED"
    rec_res = conf_data["recommendation_response"]
    assert rec_res is not None
    assert len(rec_res["recommendations"]) == 3
    assert conf_data["spoken_recommendations_ar"] is not None
    assert "ده تقدير استرشادي مش ضمان" in conf_data["spoken_recommendations_ar"]
