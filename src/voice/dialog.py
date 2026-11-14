"""Confirmation dialogue manager for Egyptian farmer voice interactions."""

import re
import uuid
from typing import Dict, Any, Optional, Tuple
from src.domain.schemas import ConfirmationDialogueState, ParsedVoiceSlots, WaterSourceType
from src.voice.lexicon import FellahiLexicon
from src.voice.phrase_bank import EgyptianPhraseBank

# Arabic display mappings for confirmation speech
LOCATION_AR_MAP = {
    "Kafr El-Sheikh": "كفر الشيخ",
    "Minya": "المنيا",
    "New Valley": "الوادي الجديد",
    "Dakahlia": "الدقهلية",
    "Sharqia": "الشرقية",
    "Beheira": "البحيرة",
    "Gharbia": "الغربية",
    "Asyut": "أسيوط",
    "Sohag": "سوهاج",
    "Qena": "قنا",
    "Beni Suef": "بني سويف",
    "Fayoum": "الفيوم",
}

CROP_AR_MAP = {
    "wheat": "قمح",
    "berseem": "برسيم",
    "fava_beans": "فول بلدي",
    "maize": "ذرة",
    "cotton": "قطن",
    "tomatoes": "طماطم",
}

# Egyptian affirmative triggers
AFFIRMATIVE_TERMS = ["ايوه", "ايوة", "اه", "تمام", "صح", "مظبوط", "توكلنا على الله", "حصل", "يا مسهل"]

# Negative / correction triggers
NEGATIVE_TERMS = ["لا", "مش كده", "غلط", "عدل", "غير", "مش مظبوط", "لأ"]

# Agricultural engineer request triggers
ENGINEER_REQUEST_TERMS = ["باشمهندس", "مهندس", "مرشد زراعي", "الجمعية", "اكلم حد", "اتصل بمهندس"]


class ConfirmationDialogueManager:
    """Manages dialogue state and confirmation loops before submitting to decision engine."""

    def __init__(self, lexicon: Optional[FellahiLexicon] = None):
        self.lexicon = lexicon or FellahiLexicon()
        self.sessions: Dict[str, ConfirmationDialogueState] = {}

    def start_session(self, parsed_slots: ParsedVoiceSlots, session_id: Optional[str] = None) -> ConfirmationDialogueState:
        """Create new dialogue session and construct confirmation prompt."""
        s_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"

        loc_raw = parsed_slots.location_name or "أرضك"
        loc_str = LOCATION_AR_MAP.get(loc_raw, loc_raw)

        feddans = parsed_slots.area_feddans or 0.0
        qirats = parsed_slots.area_qirats or 0.0

        area_parts = []
        if feddans > 0:
            area_parts.append(f"{feddans:.1f} فدان")
        if qirats > 0:
            area_parts.append(f"{int(qirats)} قيراط")
        area_str = " و ".join(area_parts) if area_parts else "مساحتك"

        water_map = {
            WaterSourceType.CANAL_ROTATION: "الترعة بالمناوبة",
            WaterSourceType.CANAL_CONTINUOUS: "ترعة مستمرة",
            WaterSourceType.GROUNDWATER_WELL: "بئر ارتوازي",
            WaterSourceType.DRAINAGE_REUSE: "مياه صرف مخلوطة",
            WaterSourceType.NILE_DIRECT: "ري مباشر من النيل",
            WaterSourceType.UNKNOWN: "الترعة",
        }
        water_str = water_map.get(parsed_slots.water_source or WaterSourceType.CANAL_ROTATION, "الترعة")

        prev_crops_ar = [CROP_AR_MAP.get(c, c) for c in parsed_slots.previous_crops]
        prev_crop_str = " و ".join(prev_crops_ar) if prev_crops_ar else "محصولك السابق"

        confirmation_phrase = EgyptianPhraseBank.format_confirmation_request(
            location_ar=loc_str,
            area_str=area_str,
            water_source_ar=water_str,
            previous_crop_ar=prev_crop_str,
        )

        state = ConfirmationDialogueState(
            session_id=s_id,
            status="PENDING_CONFIRMATION",
            confirmation_phrase_ar=confirmation_phrase,
            parsed_slots=parsed_slots,
            needs_clarification_on=[],
        )
        self.sessions[s_id] = state
        return state

    def handle_farmer_response(self, session_id: str, farmer_utterance: str) -> Tuple[ConfirmationDialogueState, str]:
        """Process farmer confirmation or correction utterance."""
        state = self.sessions.get(session_id)
        if not state:
            return None, "الجلسة غير موجودة، يرجى التحدث من جديد."

        norm = self.lexicon.normalize_arabic_text(farmer_utterance)

        # Check for request to speak to agricultural engineer
        for term in ENGINEER_REQUEST_TERMS:
            if self.lexicon.normalize_arabic_text(term) in norm:
                state.status = "SPEAK_TO_ENGINEER"
                reply = (
                    "تحت أمرك يا حاج. رقم الإرشاد الزراعي التابع لوزارتك: 19561، "
                    "أو تقدر تتوجه لأقرب إدارة زراعية لمقابلة المرشد الزراعي المختص."
                )
                return state, reply

        # Check affirmative
        for aff in AFFIRMATIVE_TERMS:
            if re.search(r"\b" + re.escape(self.lexicon.normalize_arabic_text(aff)) + r"\b", norm):
                state.status = "CONFIRMED"
                reply = "عظيم، جاري الآن حساب أفضل دورة زراعية ومحصول يناسب أرضك..."
                return state, reply

        # Check negative or correction
        for neg in NEGATIVE_TERMS:
            if re.search(r"\b" + re.escape(self.lexicon.normalize_arabic_text(neg)) + r"\b", norm):
                state.status = "CORRECTION"
                reply = "حقك عليا يا حاج. قولي تاني مساحة أرضك إيه أو موقعك فين عشان أصححها."
                return state, reply

        # Ambiguous response -> re-ask confirmation
        reply = f"معلش يا حاج مسمعتكش كويس، {state.confirmation_phrase_ar}"
        return state, reply
