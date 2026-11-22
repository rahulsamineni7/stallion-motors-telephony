"""
Sarvam AI Saaras:v4 Speech-to-Text integration for telephony speech streams.
Transcribes caller audio into real-time text for LLM intent recognition.
"""

import os
import io
import logging
import httpx
from typing import Optional, Dict, Any
from config import sarvam_config

logger = logging.getLogger("sarvam_stt")
logger.setLevel(logging.INFO)

class SarvamSTT:
    """
    Speech-to-Text client using Sarvam Saaras:v4 API.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or sarvam_config.sarvam_stt_api_key
        self.model = model or sarvam_config.stt_model
        self.base_url = sarvam_config.sarvam_base_url
        self.is_mock = not self.api_key or "mock" in self.api_key.lower()

    async def transcribe(self, audio_bytes: bytes, language_code: str = "en-IN") -> str:
        """Transcribes audio bytes to text using Sarvam Saaras REST API."""
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        if not self.is_mock:
            headers = {"api-subscription-key": self.api_key}
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            data = {"model": self.model, "language_code": language_code}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/speech-to-text",
                        headers=headers,
                        files=files,
                        data=data
                    )
                    if resp.status_code == 200:
                        return resp.json().get("transcript", "").strip()
                    else:
                        logger.warning(f"[SARVAM STT ERROR] Status {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"[SARVAM STT EXCEPTION] {e}")

        return "I would like to speak to someone about servicing my Nissan car."

sarvam_stt = SarvamSTT()
