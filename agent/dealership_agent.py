"""
Stallion Motors Dealership Conversational Agent.
Orchestrates prompt instructions, intent classification, function calling,
and per-call mini memory tracking for interruptions and stateful context.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from config import llm_config, dealership_config
from telephony.hunt_group_manager import hunt_group_manager, MSG_DIFFICULTY_RETRY, MSG_ALL_BUSY
from telephony.routing_table import STALLION_DEPARTMENTS

logger = logging.getLogger("dealership_agent")
logger.setLevel(logging.INFO)

# Load System Prompt
PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "prompts", "stallion_motors_prompt.md")
try:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
except Exception:
    SYSTEM_PROMPT = (
        "You are Zola, senior virtual AI concierge for Stallion Motors Dealership in Nigeria. "
        "Ask the caller their concern and route to sales, service, parts, finance, or support. "
        "Keep responses concise and automotive-savvy. Remember the customer vehicle and past context."
    )

class CallMemory(BaseModel):
    call_id: str
    caller_phone: str = "+2348000000000"
    caller_name: str = "Valued Customer"
    vehicle_interest: Optional[str] = None
    previous_vehicle: Optional[str] = None
    department: Optional[str] = None
    concern_summary: Optional[str] = None
    turn_count: int = 0
    interrupted: bool = False
    interruption_count: int = 0
    notes: List[str] = Field(default_factory=list)

# Global Memory Store per Call
CALL_MEMORIES: Dict[str, CallMemory] = {}

class StallionDealershipAgent:
    """
    Manages conversational dialog, per-call mini-memory, and telephony routing.
    """

    def __init__(self, call_id: str, caller_phone: str = "+2348000000000"):
        self.call_id = call_id
        self.caller_phone = caller_phone
        self.history: List[Dict[str, str]] = []
        self.detected_department: Optional[str] = None
        self.client = None

        # Mini Memory per call
        if call_id in CALL_MEMORIES:
            self.memory = CALL_MEMORIES[call_id]
        else:
            self.memory = CallMemory(call_id=call_id, caller_phone=caller_phone)
            CALL_MEMORIES[call_id] = self.memory

        self._init_llm_client()

    def _init_llm_client(self):
        """Initializes Groq or OpenAI client if keys are present."""
        if llm_config.groq_api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=llm_config.groq_api_key)
                self.llm_provider = "groq"
                return
            except Exception as e:
                logger.warning(f"Failed to load Groq: {e}")

        if llm_config.openai_api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=llm_config.openai_api_key)
                self.llm_provider = "openai"
                return
            except Exception as e:
                logger.warning(f"Failed to load OpenAI: {e}")

        self.client = None
        self.llm_provider = "fallback_heuristic"

    def get_greeting(self) -> str:
        """Standard opening greeting when inbound call connects."""
        greeting = (
            "Hello! Thank you for calling Stallion Motors Dealership. "
            "I am Zola, your virtual concierge. How may I direct your call or assist you with your vehicle today?"
        )
        self.history.append({"role": "assistant", "content": greeting})
        self.memory.turn_count = 1
        return greeting

    def _extract_vehicle_mention(self, text: str) -> Optional[str]:
        t = text.lower()
        brands = ["nissan patrol", "nissan", "hyundai santa fe", "hyundai tucson", "hyundai",
                  "honda accord", "honda cr-v", "honda", "changan cs35", "changan",
                  "audi", "porsche", "ashok leyland", "truck", "suv"]
        for b in brands:
            if b in t:
                return b.title()
        return None

    def _classify_intent_heuristic(self, user_text: str) -> Tuple[str, str]:
        """High-accuracy fallback classification if LLM API is unavailable."""
        text = user_text.lower()
        if any(w in text for w in ["complain", "complaint", "manager", "escalat", "disappointed", "feedback", "dispute", "billing", "unresolved", "grievance"]):
            return "support", "Customer feedback and management escalation"
        elif any(w in text for w in ["finance", "loan", "emi", "hire purchase", "lease", "installment", "insurance", "claim"]):
            return "finance", "Vehicle finance and insurance inquiry"
        elif any(w in text for w in ["part", "parts", "battery", "tyre", "tire", "accessories", "gear", "brake pad", "filter", "plug"]):
            return "parts", "Genuine spare parts & accessories inquiry"
        elif any(w in text for w in ["service", "repair", "maintenance", "oil change", "mechanic", "breakdown", "bodyshop", "dent", "paint", "faulty", "engine"]):
            return "service", "Vehicle maintenance and service inquiry"
        else:
            return "sales", "New vehicle sales, pricing, and showroom inquiry"

    async def process_user_turn(self, user_utterance: str, is_interruption: bool = False) -> Dict[str, Any]:
        """
        Processes a caller utterance:
        Updates per-call mini memory, notes interruptions, classifies concern, and initiates routing.
        """
        self.memory.turn_count += 1
        self.history.append({"role": "user", "content": user_utterance})

        if is_interruption:
            self.memory.interrupted = True
            self.memory.interruption_count += 1
            self.memory.notes.append(f"Interrupted at turn {self.memory.turn_count}: '{user_utterance}'")

        # Update Vehicle Memory
        new_vehicle = self._extract_vehicle_mention(user_utterance)
        if new_vehicle:
            if self.memory.vehicle_interest and self.memory.vehicle_interest.lower() != new_vehicle.lower():
                self.memory.previous_vehicle = self.memory.vehicle_interest
            self.memory.vehicle_interest = new_vehicle

        # Classification
        dept, concern = self._classify_intent_heuristic(user_utterance)
        self.memory.department = dept
        self.memory.concern_summary = concern

        return await self._initiate_routing(dept, concern, self.memory.caller_name, is_interruption=is_interruption)

    async def _initiate_routing(self, department: str, concern: str, customer_name: str, is_interruption: bool = False) -> Dict[str, Any]:
        """Starts hunt group sequence for identified department using mini memory."""
        self.detected_department = department
        session, base_speech = hunt_group_manager.start_hunt(
            call_id=self.call_id,
            department_id=department,
            caller_phone=self.caller_phone,
            caller_name=customer_name,
            concern=concern
        )

        # Context-aware phrasing using mini memory
        if is_interruption and self.memory.vehicle_interest:
            spoken_message = (
                f"Understood, I hear you! Switching your request to {self.memory.vehicle_interest} "
                f"with our {session.department_name} specialist. Please stay on the line."
            )
        elif is_interruption:
            spoken_message = (
                f"Understood, I hear you! Let me connect you directly to our {session.department_name} specialist. "
                f"Please stay on the line."
            )
        elif self.memory.previous_vehicle and self.memory.previous_vehicle != self.memory.vehicle_interest:
            spoken_message = (
                f"Understood! Switching your request to {self.memory.vehicle_interest}. "
                f"Let me connect you directly to our {session.department_name} specialist."
            )
        elif self.memory.vehicle_interest:
            spoken_message = (
                f"Certainly! I would be glad to help you with your {self.memory.vehicle_interest} inquiry. "
                f"Let me connect you directly to our {session.department_name} specialist. Please stay on the line."
            )
        else:
            spoken_message = base_speech

        self.history.append({"role": "assistant", "content": spoken_message})

        return {
            "type": "routing_initiated",
            "department": department,
            "department_name": session.department_name,
            "concern": concern,
            "vehicle": self.memory.vehicle_interest,
            "message_to_speak": spoken_message,
            "status": "HUNTING",
            "memory": self.memory.model_dump()
        }
