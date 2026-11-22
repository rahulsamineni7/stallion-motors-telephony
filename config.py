"""
Configuration for Stallion Motor Dealership Telephony & Voice Agent.
Supports Kros AI CPaaS, Sarvam AI Voice, and LLM backends (Groq/SambaNova/OpenAI).
"""

import os
from pydantic import BaseModel
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class TelephonyConfig(BaseModel):
    provider: str = os.getenv("TELEPHONY_PROVIDER", "kros_ai")
    kros_api_key: str = os.getenv("KROS_API_KEY", "kros_mock_demo_key_xyz")
    kros_api_base: str = os.getenv("KROS_API_BASE", "https://api.krosai.com/api/v1")
    kros_virtual_number: str = os.getenv("KROS_VIRTUAL_NUMBER", "+23418880199")  # Stallion Dealership inbound DID
    webhook_base_url: str = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8028")

    # Extension Hunt Group Settings
    ring_timeout_seconds: int = int(os.getenv("RING_TIMEOUT_SECONDS", "5"))
    max_hunt_attempts: int = int(os.getenv("MAX_HUNT_ATTEMPTS", "3"))

class SarvamConfig(BaseModel):
    sarvam_stt_api_key: str = os.getenv("SARVAM_STT_API_KEY", "sk_f79w2hnk_kt2dDzs9ALyXjAsN6p9nGeEQ")
    sarvam_tts_api_key: str = os.getenv("SARVAM_TTS_API_KEY", "sk_crksriq1_P6krlqXUiKVC4AywDXU59dKS")
    sarvam_base_url: str = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai")
    tts_model: str = os.getenv("SARVAM_TTS_MODEL", "bulbul:v4-flash")
    stt_model: str = os.getenv("SARVAM_STT_MODEL", "saaras:v4")
    speaker: str = os.getenv("SARVAM_SPEAKER", "kavitha_te_conversation")
    pace: float = float(os.getenv("SARVAM_PACE", "1.05"))

class LLMConfig(BaseModel):
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    sambanova_api_key: str = os.getenv("SAMBANOVA_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    temperature: float = 0.3

class DealershipConfig(BaseModel):
    dealership_name: str = "Stallion Motors"
    tagline: str = "Your Trusted Multi-Brand Automotive Destination"
    location: str = "Victoria Island & Ikeja Showrooms, Lagos"
    brands_represented: List[str] = [
        "Nissan", "Honda", "Hyundai", "Changan", "Audi", "Porsche", "Ashok Leyland"
    ]
    operating_hours: str = "Monday to Saturday, 8:00 AM to 6:00 PM"

class FishAudioConfig(BaseModel):
    api_key: str = os.getenv("FISH_API_KEY", "sk-fish-g4dXwpEsehLnA8aPY_Fj-5t7NjJ6lIKi5MlGvSeAYOc")
    voice_id: str = os.getenv("FISH_VOICE_ID", "88cac40533e34672ae5d66e73759c487")
    model: str = os.getenv("FISH_MODEL", "s2.1-pro-free")
    enabled: bool = os.getenv("FISH_TTS", "1") == "1"

# Global Config Instances
telephony_config = TelephonyConfig()
sarvam_config = SarvamConfig()
fish_audio_config = FishAudioConfig()
llm_config = LLMConfig()
dealership_config = DealershipConfig()
