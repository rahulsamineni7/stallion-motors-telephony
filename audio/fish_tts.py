"""
Fish Audio TTS Engine (api.fish.audio).
Uses Fish Audio's state-of-the-art voice synthesis model with custom voice cloning.
Configured with Stallion Motors Concierge voice and in-memory phrase caching for real-time responsiveness.
"""

import os
import io
import logging
import httpx
from typing import Optional, Dict
from config import fish_audio_config

logger = logging.getLogger("fish_tts")
logger.setLevel(logging.INFO)

# In-memory audio cache for zero-latency telephony prompts
_AUDIO_CACHE: Dict[str, bytes] = {}

class FishAudioTTS:
    """
    Fish Audio TTS client for realistic, ultra-natural voice generation.
    Endpoint: https://api.fish.audio/v1/tts
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or fish_audio_config.api_key
        self.voice_id = voice_id or fish_audio_config.voice_id
        self.model = model or fish_audio_config.model
        self.base_url = "https://api.fish.audio/v1/tts"

    async def synthesize(self, text: str, format: str = "mp3") -> bytes:
        """
        Synthesizes speech using Fish Audio REST API.
        Returns audio bytes (MP3 or WAV).
        """
        if not text or not text.strip():
            return b""

        clean_text = text.strip()
        cache_key = f"{self.voice_id}:{clean_text}"
        if cache_key in _AUDIO_CACHE:
            return _AUDIO_CACHE[cache_key]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "model": self.model
        }
        payload = {
            "text": clean_text,
            "reference_id": self.voice_id,
            "format": format
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self.base_url, headers=headers, json=payload)
                if resp.status_code == 200 and len(resp.content) > 100:
                    logger.info(f"[FISH AUDIO SUCCESS] Generated {len(resp.content)} bytes for text: '{clean_text[:40]}...'")
                    _AUDIO_CACHE[cache_key] = resp.content
                    return resp.content
                elif resp.status_code == 402:
                    logger.warning("[FISH AUDIO 402] Trying with s2.1-pro-free fallback...")
                    headers["model"] = "s2.1-pro-free"
                    resp = await client.post(self.base_url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        _AUDIO_CACHE[cache_key] = resp.content
                        return resp.content
                    logger.error(f"[FISH AUDIO ERROR] Status {resp.status_code}: {resp.text}")
                else:
                    logger.error(f"[FISH AUDIO ERROR] Status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"[FISH AUDIO EXCEPTION] {e}")

        return b""

fish_tts = FishAudioTTS()
