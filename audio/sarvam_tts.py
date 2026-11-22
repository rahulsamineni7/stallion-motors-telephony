"""
Sarvam AI Bulbul:v4-flash TTS engine for low-latency conversational telephony.
Outputs native 8kHz mu-law / PCM audio for Kros AI telecom infrastructure.
Includes fallback audio generation for offline demonstration.
"""

import os
import io
import wave
import math
import base64
import logging
import httpx
from typing import Optional, AsyncGenerator
from config import sarvam_config

logger = logging.getLogger("sarvam_tts")
logger.setLevel(logging.INFO)

class SarvamTTS:
    """
    Text-to-Speech synthesis using Sarvam AI Bulbul models.
    Supports English, Hindi, and Indian English accents.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        speaker: Optional[str] = None,
        pace: Optional[float] = None
    ):
        self.api_key = api_key or sarvam_config.sarvam_tts_api_key
        self.model = model or sarvam_config.tts_model
        self.speaker = speaker or sarvam_config.speaker
        self.pace = pace or sarvam_config.pace
        self.base_url = sarvam_config.sarvam_base_url
        self.is_mock = not self.api_key or "mock" in self.api_key.lower()

    async def synthesize(self, text: str, language_code: str = "en-IN") -> bytes:
        """
        Synthesizes text into audio bytes (WAV 8kHz for telephony).
        Falls back to synthesized tone WAV if Sarvam API is unreachable or mock.
        """
        if not text or not text.strip():
            return b""

        if not self.is_mock:
            headers = {
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "inputs": [text.strip()],
                "target_language_code": language_code,
                "speaker": self.speaker,
                "pace": self.pace,
                "speech_sample_rate": 8000,
                "enable_preprocessing": True,
                "model": self.model
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/text-to-speech",
                        headers=headers,
                        json=payload
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        audios = data.get("audios", [])
                        if audios:
                            return base64.b64decode(audios[0])
                    else:
                        logger.warning(f"[SARVAM TTS WARNING] API returned {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.warning(f"[SARVAM TTS ERROR] {e} - falling back to simulated speech audio.")

        # Local fallback tone generator for offline demo audio
        return self._generate_fallback_audio(text)

    def _generate_fallback_audio(self, text: str) -> bytes:
        """Generates a pleasant audible WAV audio chunk for simulation testing."""
        sample_rate = 8000
        duration = min(2.0, max(0.5, len(text) * 0.05))
        total_samples = int(sample_rate * duration)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            # Gentle chime waveform
            data = bytearray()
            for i in range(total_samples):
                t = i / sample_rate
                freq = 440 + 80 * math.sin(2 * math.pi * 2 * t)
                val = int(8000 * math.sin(2 * math.pi * freq * t) * (1 - t / duration))
                data.extend(val.to_bytes(2, byteorder='little', signed=True))
            wav.writeframes(data)
        return buf.getvalue()

sarvam_tts = SarvamTTS()
