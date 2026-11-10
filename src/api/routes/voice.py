"""Voice AI pipeline endpoints connecting ASR, NLU, dialogue, and TTS."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.domain.schemas import ConfirmationDialogueState, FarmCoordinates, FarmArea, FarmProfile, WaterSourceType, RecommendationResponse
from src.services.recommendation_service import RecommendationService
from src.voice.asr import EgyptianArabicASR
from src.voice.dialog import ConfirmationDialogueManager
from src.voice.lexicon import FellahiLexicon
from src.voice.nlu import EgyptianArabicNLU
from src.voice.phrase_bank import EgyptianPhraseBank
from src.voice.tts import EgyptianArabicTTS

router = APIRouter(prefix="/api/voice", tags=["Egyptian Voice Assistant"])

lexicon = FellahiLexicon()
asr = EgyptianArabicASR(lexicon=lexicon)
nlu = EgyptianArabicNLU(lexicon=lexicon)
dialog_manager = ConfirmationDialogueManager(lexicon=lexicon)
tts_engine = EgyptianArabicTTS()
rec_service = RecommendationService()


class UtteranceRequest(BaseModel):
    utterance: str = Field(..., description="Raw farmer speech transcription from microphone")
    session_id: Optional[str] = None


class UtteranceResponse(BaseModel):
    session_id: str
    asr_result: Dict[str, Any]
    dialog_state: ConfirmationDialogueState
    spoken_prompt_ar: str


class ConfirmationRequest(BaseModel):
    session_id: str
    farmer_reply: str = Field(..., description="Farmer response e.g. 'أيوه' or 'لأ'")


class ConfirmationResponse(BaseModel):
    session_id: str
    status: str
    assistant_reply_ar: str
    recommendation_response: Optional[RecommendationResponse] = None
    spoken_recommendations_ar: Optional[str] = None


@router.post("/process-utterance", response_model=UtteranceResponse)
async def process_farmer_utterance(payload: UtteranceRequest):
    """Step 1 & 2: Process farmer speech transcript -> extract slots -> generate confirmation question."""
    asr_res = asr.process_transcription(payload.utterance)
    if not asr_res["is_valid"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=asr_res["message"])

    slots = nlu.parse_utterance(asr_res["normalized"])
    dialog_state = dialog_manager.start_session(parsed_slots=slots, session_id=payload.session_id)

    return UtteranceResponse(
        session_id=dialog_state.session_id,
        asr_result=asr_res,
        dialog_state=dialog_state,
        spoken_prompt_ar=dialog_state.confirmation_phrase_ar,
    )


@router.post("/confirm", response_model=ConfirmationResponse)
async def confirm_and_generate_plans(payload: ConfirmationRequest):
    """Step 3: Handle farmer confirmation. Only after explicit confirmation are plans generated!"""
    state, reply = dialog_manager.handle_farmer_response(
        session_id=payload.session_id, farmer_utterance=payload.farmer_reply
    )
    if not state:
        raise HTTPException(status_code=404, detail="Dialogue session not found.")

    if state.status == "CONFIRMED":
        # Formulate farm profile from validated slots
        slots = state.parsed_slots
        # Default coordinates for known Egyptian locations
        coords_map = {
            "Kafr El-Sheikh": (31.11, 30.94),
            "Minya": (28.11, 30.75),
            "New Valley": (25.45, 30.55),
        }
        lat, lon = coords_map.get(slots.location_name or "Kafr El-Sheikh", (31.11, 30.94))

        profile = FarmProfile(
            farm_id=f"voice_{state.session_id}",
            farmer_name="يا حاج",
            location_name=slots.location_name or "كفر الشيخ",
            coordinates=FarmCoordinates(latitude=lat, longitude=lon),
            area=FarmArea(
                feddans=slots.area_feddans or 2.0,
                qirats=slots.area_qirats or 0.0,
            ),
            water_source=slots.water_source or WaterSourceType.CANAL_ROTATION,
            previous_crops=slots.previous_crops,
            available_budget_egp=slots.available_budget_egp,
            primary_objective=slots.primary_objective or "max_profit",
        )

        rec_res, _ = await rec_service.get_recommendations_for_farm(profile)
        spoken_script = EgyptianPhraseBank.format_full_recommendation_audio_script(rec_res)

        return ConfirmationResponse(
            session_id=state.session_id,
            status=state.status,
            assistant_reply_ar=reply,
            recommendation_response=rec_res,
            spoken_recommendations_ar=spoken_script,
        )

    return ConfirmationResponse(
        session_id=state.session_id,
        status=state.status,
        assistant_reply_ar=reply,
        recommendation_response=None,
        spoken_recommendations_ar=None,
    )


@router.get("/lexicon/unrecognized")
async def get_unrecognized_lexicon_terms():
    """Retrieve unrecognized dialect words logged for agronomist review in Expert Console."""
    import json
    log_file = lexicon.log_path
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []
