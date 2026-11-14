"""Fellahi Agricultural Lexicon and Dialect Normalization for FieldWise AI.

Version: 1.2.0
Contains Egyptian dialect vocabulary for crops, irrigation systems, land measurements,
and financial/risk priorities. Logs unknown agricultural words for agronomist review.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("fieldwise.lexicon")

LEXICON_VERSION = "1.2.0"

# Egyptian Governorate and Region synonyms
LOCATION_SYNONYMS: Dict[str, str] = {
    "كفر الشيخ": "Kafr El-Sheikh",
    "كفرالشيخ": "Kafr El-Sheikh",
    "المنيا": "Minya",
    "منيا": "Minya",
    "الوادي الجديد": "New Valley",
    "الخارجة": "New Valley",
    "الداخلة": "New Valley",
    "الفرافرة": "New Valley",
    "الدقهلية": "Dakahlia",
    "المنصورة": "Dakahlia",
    "الشرقية": "Sharqia",
    "الزقازيق": "Sharqia",
    "البحيرة": "Beheira",
    "دمنهور": "Beheira",
    "الغربية": "Gharbia",
    "طنطا": "Gharbia",
    "أسيوط": "Asyut",
    "سوهاج": "Sohag",
    "قنا": "Qena",
    "بني سويف": "Beni Suef",
    "الفيوم": "Fayoum",
}

# Egyptian Land Area Units (Feddans, Qirats, Sahms)
AREA_UNITS: Dict[str, float] = {
    "فدان": 1.0,
    "فدانين": 2.0,
    "تلات فدادين": 3.0,
    "اربع فدادين": 4.0,
    "خمس فدادين": 5.0,
    "ست فدادين": 6.0,
    "سبع فدادين": 7.0,
    "تمان فدادين": 8.0,
    "تسع فدادين": 9.0,
    "عشر فدادين": 10.0,
    "نص فدان": 0.5,
    "ربع فدان": 0.25,
    "فدان ونص": 1.5,
    "فدان وربع": 1.25,
    "فدانين ونص": 2.5,
    "قيراط": 1.0 / 24.0,
    "قيراطين": 2.0 / 24.0,
    "ست قراريط": 6.0 / 24.0,
    "تمان قراريط": 8.0 / 24.0,
    "عشر قراريط": 10.0 / 24.0,
    "نص قيراط": 0.5 / 24.0,
}

# Egyptian Irrigation & Water Terminology
WATER_SOURCE_TERMS: Dict[str, str] = {
    "ترعة": "canal_rotation",
    "مناوبة": "canal_rotation",
    "دور المية": "canal_rotation",
    "دور مية": "canal_rotation",
    "مسقى": "canal_rotation",
    "ترعة مستمرة": "canal_continuous",
    "بحر": "canal_continuous",
    "النيل": "nile_direct",
    "ري مباشر": "nile_direct",
    "بئر": "groundwater_well",
    "بير": "groundwater_well",
    "ارتوازي": "groundwater_well",
    "طلمبة أعماق": "groundwater_well",
    "صرف": "drainage_reuse",
    "مية مخلوطة": "drainage_reuse",
    "صرف زراعي": "drainage_reuse",
}

# Egyptian Crop Aliases & Local Varieties
CROP_ALIASES: Dict[str, str] = {
    # Wheat
    "قمح": "wheat",
    "غلة": "wheat",
    "حنطة": "wheat",
    "قمح جيزة": "wheat",
    "قمح مصر": "wheat",
    "قمح سدس": "wheat",
    "غله": "wheat",
    # Berseem
    "برسيم": "berseem",
    "برسيم مسقاوي": "berseem",
    "برسيم خضرة": "berseem",
    "حشة": "berseem",
    "تحريش": "berseem",
    "برسيم فحل": "berseem",
    # Fava Beans
    "فول": "fava_beans",
    "فول بلدي": "fava_beans",
    "فول حبة عريضة": "fava_beans",
    "فول رومي": "fava_beans",
    # Maize
    "ذرة": "maize",
    "درة": "maize",
    "ذرة شامية": "maize",
    "درة شامية": "maize",
    "ذرة صفرا": "maize",
    "ذرة بيضا": "maize",
    "كيزان": "maize",
    # Cotton
    "قطن": "cotton",
    "الذهب الأبيض": "cotton",
    "قطن جيزة": "cotton",
    "قنطار": "cotton",
    # Tomatoes
    "طماطم": "tomatoes",
    "قوطة": "tomatoes",
    "بندورة": "tomatoes",
    "طماطم سلك": "tomatoes",
}

# Egyptian Farmer Strategic Priorities
PRIORITY_TERMS: Dict[str, str] = {
    "أكسب": "max_profit",
    "اكسب": "max_profit",
    "أعلى عائد": "max_profit",
    "مكسب": "max_profit",
    "فلوس أكتر": "max_profit",
    "قرشين حلوين": "max_profit",
    "أوفر في المية": "save_water",
    "اوفر في المية": "save_water",
    "توفير مية": "save_water",
    "المية قليلة": "save_water",
    "عطش": "save_water",
    "بنوفر مية": "save_water",
    "الأأمن": "low_risk",
    "الامن": "low_risk",
    "أمان": "low_risk",
    "مضمون": "low_risk",
    "تسويق مضمون": "low_risk",
    "تسليم صوامع": "low_risk",
    "مش عايز مجازفة": "low_risk",
}


class FellahiLexicon:
    """Interface to query Egyptian agricultural terminology and track unknown dialect terms."""

    def __init__(self, log_path: str = "data/lexicon/unrecognized_terms.json"):
        self.version = LEXICON_VERSION
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def normalize_arabic_text(self, text: str) -> str:
        """Normalize Arabic orthography (alif variants, hamza, taa marbuta)."""
        if not text:
            return ""
        # Remove diacritics / tashkeel
        text = re.sub(r"[\u064B-\u0652]", "", text)
        # Normalize Alif
        text = re.sub(r"[إأآا]", "ا", text)
        # Normalize Taa Marbuta / Haa
        text = re.sub(r"ة", "ه", text)
        # Normalize Yaa / Alif Maqsura
        text = re.sub(r"ى", "ي", text)
        return text.strip()

    def identify_crops(self, utterance: str) -> List[str]:
        """Match known crop names from Egyptian speech."""
        norm_utterance = self.normalize_arabic_text(utterance)
        detected = set()
        for alias, crop_id in CROP_ALIASES.items():
            norm_alias = self.normalize_arabic_text(alias)
            if re.search(r"\b" + re.escape(norm_alias) + r"\b", norm_utterance):
                detected.add(crop_id)
        return list(detected)

    def identify_water_source(self, utterance: str) -> Optional[str]:
        """Identify Egyptian irrigation source and regime."""
        norm_utterance = self.normalize_arabic_text(utterance)
        for term, source_type in WATER_SOURCE_TERMS.items():
            norm_term = self.normalize_arabic_text(term)
            if norm_term in norm_utterance:
                return source_type
        return None

    def identify_location(self, utterance: str) -> Optional[str]:
        """Identify Egyptian agricultural governorate or district."""
        norm_utterance = self.normalize_arabic_text(utterance)
        for loc_name, standard_name in LOCATION_SYNONYMS.items():
            norm_loc = self.normalize_arabic_text(loc_name)
            if norm_loc in norm_utterance:
                return standard_name
        return None

    def identify_priority(self, utterance: str) -> Optional[str]:
        """Identify farmer economic/resource priority."""
        norm_utterance = self.normalize_arabic_text(utterance)
        for term, priority in PRIORITY_TERMS.items():
            norm_term = self.normalize_arabic_text(term)
            if norm_term in norm_utterance:
                return priority
        return None

    def log_unrecognized_term(self, term: str, utterance_context: str) -> None:
        """Record unknown agricultural dialect term for agronomist review in Expert Console."""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
            logs.append({
                "term": term,
                "context": utterance_context,
                "logged_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending_review",
            })
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            logger.info(f"Logged unrecognized agricultural term: {term}")
        except Exception as exc:
            logger.error(f"Failed to log unrecognized term: {exc}")
