"""Egyptian Arabic Natural Language Understanding (NLU) parser.

Extracts structured farm slots (location, area in feddans/qirats, water source,
previous crops, budget, and priorities) from Egyptian farmer speech.
Strictly separates natural language understanding from agronomic decision-making.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from src.domain.schemas import FarmerPriority, ParsedVoiceSlots, WaterSourceType
from src.voice.lexicon import FellahiLexicon

logger = logging.getLogger("fieldwise.nlu")

# Egyptian Arabic numerals map
ARABIC_DIGITS_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

WORD_NUMBERS: Dict[str, float] = {
    "صفر": 0.0,
    "واحد": 1.0,
    "فدان": 1.0,
    "فدانين": 2.0,
    "اتنين": 2.0,
    "تلاتة": 3.0,
    "تلات": 3.0,
    "تلاته": 3.0,
    "اربعة": 4.0,
    "اربع": 4.0,
    "خمسة": 5.0,
    "خمس": 5.0,
    "ستة": 6.0,
    "ست": 6.0,
    "سبعة": 7.0,
    "سبع": 7.0,
    "تمانية": 8.0,
    "تمان": 8.0,
    "تسعة": 9.0,
    "تسع": 9.0,
    "عشرة": 10.0,
    "عشر": 10.0,
    "خمسطاشر": 15.0,
    "عشرين": 20.0,
    "تلاتين": 30.0,
    "اربعين": 40.0,
    "خمسين": 50.0,
    "مية": 100.0,
    "ميتين": 200.0,
    "الف": 1000.0,
    "الفين": 2000.0,
    "تلاف": 1000.0,
}


class EgyptianArabicNLU:
    """Deterministic slot parser for Egyptian colloquial farmer speech."""

    def __init__(self, lexicon: Optional[FellahiLexicon] = None):
        self.lexicon = lexicon or FellahiLexicon()

    def parse_utterance(self, utterance: str) -> ParsedVoiceSlots:
        """Parse raw Egyptian speech transcript into validated structured slots."""
        if not utterance:
            return ParsedVoiceSlots(confidence_score=0.0)

        cleaned = utterance.translate(ARABIC_DIGITS_MAP)
        norm_text = self.lexicon.normalize_arabic_text(cleaned)

        # 1. Location extraction
        location = self.lexicon.identify_location(norm_text)

        # 2. Area extraction (feddans and qirats)
        feddans, qirats = self._extract_area(norm_text)

        # 3. Water source extraction
        water_source_str = self.lexicon.identify_water_source(norm_text)
        water_source = WaterSourceType(water_source_str) if water_source_str else None

        # 4. Previous crops extraction
        previous_crops = self.lexicon.identify_crops(norm_text)

        # 5. Budget extraction (EGP)
        budget = self._extract_budget(norm_text)

        # 6. Priority extraction
        priority_str = self.lexicon.identify_priority(norm_text)
        priority = FarmerPriority(priority_str) if priority_str else None

        # Calculate confidence based on extracted informative slots
        matched_slots = sum([
            location is not None,
            feddans is not None or qirats is not None,
            water_source is not None,
            len(previous_crops) > 0,
            budget is not None,
            priority is not None,
        ])
        # Base confidence from length and slot coverage
        confidence = min(1.0, max(0.4, matched_slots * 0.25))

        return ParsedVoiceSlots(
            location_name=location,
            area_feddans=feddans,
            area_qirats=qirats,
            water_source=water_source,
            previous_crops=previous_crops,
            available_budget_egp=budget,
            primary_objective=priority,
            confidence_score=round(confidence, 2),
            unrecognized_terms=[],
        )

    def _extract_area(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse Egyptian area expressions: e.g. 'عندي ٣ فدادين و ٦ قراريط' or 'فدانين ونص'."""
        feddans: Optional[float] = None
        qirats: Optional[float] = None

        # Direct compound phrases
        if "فدان ونص" in text:
            return 1.5, 0.0
        elif "فدانين ونص" in text:
            return 2.5, 0.0
        elif "فدان وربع" in text:
            return 1.25, 0.0
        elif "فدانين" in text:
            feddans = 2.0
        elif "نص فدان" in text:
            return 0.5, 0.0
        elif "ربع فدان" in text:
            return 0.25, 0.0

        # Numeric matches: e.g. "3 فدادين", "5 فدان"
        match_feddan = re.search(r"(\d+(?:\.\d+)?)\s*(?:فدان|فدادين)", text)
        if match_feddan:
            feddans = float(match_feddan.group(1))
        else:
            # Word numerals: e.g. "تلات فدادين", "اربع فدادين"
            for word, val in WORD_NUMBERS.items():
                if f"{word} فدادين" in text or f"{word} فدان" in text:
                    feddans = val
                    break

        # Check for qirats
        if "قيراطين" in text:
            qirats = 2.0
        else:
            match_qirat = re.search(r"(\d+(?:\.\d+)?)\s*(?:قيراط|قراريط)", text)
            if match_qirat:
                qirats = float(match_qirat.group(1))

        return feddans, qirats

    def _extract_budget(self, text: str) -> Optional[float]:
        """Parse Egyptian currency phrases: e.g. 'معايا ٥٠ الف جنيه' or 'ميزانيتي 30000'."""
        # Match pattern: 50 الف / 50 ألف
        match_thousand = re.search(r"(\d+(?:\.\d+)?)\s*(?:الف|الاف)\s*(?:جنيه)?", text)
        if match_thousand:
            return float(match_thousand.group(1)) * 1000.0

        # Match direct number followed by جنيه
        match_direct = re.search(r"(\d{3,7})\s*(?:جنيه)?", text)
        if match_direct:
            val = float(match_direct.group(1))
            if val >= 500.0:  # Sensible budget threshold
                return val

        # Word numbers: e.g. خمسين الف
        if "خمسين الف" in text or "خمسين ألف" in text:
            return 50000.0
        elif "عشرين الف" in text:
            return 20000.0
        elif "تلاتين الف" in text:
            return 30000.0

        return None
