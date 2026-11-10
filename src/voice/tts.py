"""Text-to-speech (TTS) synthesis helper for Egyptian Arabic."""

import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("fieldwise.tts")


class EgyptianArabicTTS:
    """TTS manager supporting audio caching, browser speech synthesis, and phonetic preparation."""

    def __init__(self, cache_dir: str = "data/demo/audio"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def prepare_phonetics_for_egyptian_speech(self, text: str) -> str:
        """Improve Arabic speech engine prosody and pronunciation for Egyptian terms."""
        phonetic = text
        # Ensure numbers sound natural
        phonetic = phonetic.replace("٣", "تلاتة")
        phonetic = phonetic.replace("٢", "اتنين")
        phonetic = phonetic.replace("١", "واحد")
        # Ensure punctuation creates natural pauses
        phonetic = phonetic.replace("،", " ، ")
        return phonetic

    def get_audio_playback_spec(self, text: str) -> Dict[str, Any]:
        """Generate audio synthesis configuration for browser and client playback."""
        clean_text = text.strip()
        phonetic = self.prepare_phonetics_for_egyptian_speech(clean_text)
        text_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()[:12]
        audio_filename = f"tts_{text_hash}.mp3"
        cached_file = self.cache_dir / audio_filename

        return {
            "text": clean_text,
            "phonetic_text": phonetic,
            "voice_target": "ar-EG",
            "lang": "ar-EG",
            "rate": 0.95,  # Slightly slower for elderly farmers and clarity
            "pitch": 1.0,
            "cached_audio_available": cached_file.exists(),
            "cached_audio_url": f"/audio/{audio_filename}" if cached_file.exists() else None,
        }
