"""
Stallion Motors Dealership Conversational Agent.
Orchestrates prompt instructions, intent classification, function calling,
and bridges directly to the sequential telephony hunt-group engine.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

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
        "You are Zola, senior virtual AI concierge for Stallion Motors Dealership. "
        "Ask the caller their concern and route to sales, service, parts, finance, or support. "
        "When an extension has difficulty, speak: 'Sorry, some difficulty in the number I dialed, let me forward to another...'. "
        "When all numbers are busy, speak: 'I'm sorry, all our representatives are currently busy. Please call back in a while.'"
    )

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "route_call_to_department",
            "description": "Routes the incoming call to the appropriate dealership department hunt group based on caller's concern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "enum": ["sales", "service", "parts", "finance", "support"],
                        "description": "Target department matching the caller's concern."
                    },
                    "concern": {
                        "type": "string",
                        "description": "Brief summary of what the caller needs (e.g., 'Inquire about Hyundai Santa Fe', 'Routine service appointment', 'Brake pad replacement')."
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Name of the caller if mentioned, otherwise 'Valued Customer'."
                    },
                    "vehicle_details": {
                        "type": "string",
                        "description": "Vehicle brand, model, or year if mentioned by caller."
                    }
                },
                "required": ["department", "concern"]
            }
        }
    }
]

class StallionDealershipAgent:
    """
    Manages conversational dialog and telephony routing for Stallion Motors.
    """

    def __init__(self, call_id: str, caller_phone: str = "+2348000000000"):
        self.call_id = call_id
        self.caller_phone = caller_phone
        self.history: List[Dict[str, str]] = []
        self.detected_department: Optional[str] = None
        self.client = None
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
        return greeting

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
            # Default to sales for vehicle purchase, prices, test drives, new cars
            return "sales", "New vehicle sales, pricing, and showroom inquiry"

    async def process_user_turn(self, user_utterance: str) -> Dict[str, Any]:
        """
        Processes a caller utterance:
        1. Classifies caller's concern into appropriate department.
        2. Initiates the hunt group routing sequence.
        3. Returns the action payload and spoken message.
        """
        self.history.append({"role": "user", "content": user_utterance})

        # Check if LLM with function calling is available
        if self.client and self.llm_provider in ("groq", "openai"):
            try:
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history
                model_name = "llama-3.3-70b-versatile" if self.llm_provider == "groq" else "gpt-4o-mini"
                
                resp = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.2
                )
                msg = resp.choices[0].message
                if msg.tool_calls:
                    tc = msg.tool_calls[0]
                    args = json.loads(tc.function.arguments)
                    dept = args.get("department", "sales")
                    concern = args.get("concern", user_utterance)
                    cust_name = args.get("customer_name", "Valued Customer")
                    return await self._initiate_routing(dept, concern, cust_name)
                elif msg.content:
                    self.history.append({"role": "assistant", "content": msg.content})
                    return {
                        "type": "dialog",
                        "message_to_speak": msg.content,
                        "status": "AWAITING_INPUT"
                    }
            except Exception as e:
                logger.warning(f"LLM call failed: {e}. Falling back to heuristic classifier.")

        # Fallback Heuristic
        dept, concern = self._classify_intent_heuristic(user_utterance)
        return await self._initiate_routing(dept, concern, "Valued Customer")

    async def _initiate_routing(self, department: str, concern: str, customer_name: str) -> Dict[str, Any]:
        """Starts hunt group sequence for identified department."""
        self.detected_department = department
        session, intro_speech = hunt_group_manager.start_hunt(
            call_id=self.call_id,
            department_id=department,
            caller_phone=self.caller_phone,
            caller_name=customer_name,
            concern=concern
        )
        self.history.append({"role": "assistant", "content": intro_speech})
        return {
            "type": "routing_initiated",
            "department": department,
            "department_name": session.department_name,
            "concern": concern,
            "message_to_speak": intro_speech,
            "status": "HUNTING"
        }
