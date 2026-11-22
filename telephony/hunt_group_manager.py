"""
Hunt Group & Sequential Telephony Forwarding Engine for Stallion Motors.
Implements the multi-number retry logic:
- Dials target extension in department pool.
- If difficulty/busy/no-answer: tells user 'Sorry, some difficulty in the number I dialed, let me forward to another...'
- Continues until an extension picks up -> hands over call.
- If all numbers busy: tells user 'I'm sorry, all our representatives are currently busy. Please call back in a while.'
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Callable, Any
from pydantic import BaseModel, Field

from telephony.routing_table import STALLION_DEPARTMENTS, Department, ExtensionTarget, get_department
from telephony.kros_client import kros_client

logger = logging.getLogger("hunt_group_manager")
logger.setLevel(logging.INFO)

# Exact Spoken Messages Required by Business Spec
MSG_DIFFICULTY_RETRY = "Sorry, some difficulty in the number I dialed, let me forward to another..."
MSG_ALL_BUSY = "I'm sorry, all our representatives are currently busy. Please call back in a while."

class HuntAttemptRecord(BaseModel):
    attempt_number: int
    extension_id: str
    representative_name: str
    role: str
    phone_number: str
    status: str  # 'ringing', 'busy', 'no-answer', 'connected', 'failed'
    duration_seconds: float = 0.0

class HuntSession(BaseModel):
    call_id: str
    caller_phone: str
    caller_name: str = "Valued Customer"
    concern: str = ""
    department_id: str
    department_name: str
    current_index: int = 0
    max_extensions: int = 0
    attempts: List[HuntAttemptRecord] = Field(default_factory=list)
    status: str = "INITIALIZED"  # 'INITIALIZED', 'HUNTING', 'CONNECTED', 'ALL_BUSY'
    connected_extension: Optional[ExtensionTarget] = None
    final_spoken_message: Optional[str] = None

class HuntGroupManager:
    """
    Manages active hunt groups across all active dealership phone calls.
    """

    def __init__(self):
        self._sessions: Dict[str, HuntSession] = {}

    def get_session(self, call_id: str) -> Optional[HuntSession]:
        return self._sessions.get(call_id)

    def start_hunt(
        self,
        call_id: str,
        department_id: str,
        caller_phone: str = "+2348000000000",
        caller_name: str = "Valued Customer",
        concern: str = "General Assistance"
    ) -> Tuple[HuntSession, str]:
        """
        Initializes a hunt session for a call and department.
        Returns the session and the initial spoken acknowledgment to the caller.
        """
        dept = get_department(department_id)
        if not dept:
            dept = STALLION_DEPARTMENTS["sales"]

        session = HuntSession(
            call_id=call_id,
            caller_phone=caller_phone,
            caller_name=caller_name,
            concern=concern,
            department_id=dept.id,
            department_name=dept.name,
            current_index=0,
            max_extensions=len(dept.hunt_group),
            status="HUNTING"
        )
        self._sessions[call_id] = session

        intro_speech = (
            f"Certainly! I'd be glad to help you with that. Let me connect you directly to our "
            f"{dept.name} specialist. Please stay on the line for just a moment."
        )
        logger.info(f"[HUNT START] Call {call_id} -> {dept.name} ({len(dept.hunt_group)} extensions in pool)")
        return session, intro_speech

    async def step_hunt(
        self,
        call_id: str,
        simulate_pickup_override: Optional[bool] = None,
        ring_delay_seconds: float = 0.5
    ) -> Dict[str, Any]:
        """
        Executes a single dial step in the hunt group sequence.
        Returns the event dict with step outcome, status, and spoken audio/text prompt.
        """
        session = self._sessions.get(call_id)
        if not session:
            return {"error": "Session not found", "status": "ERROR"}

        dept = get_department(session.department_id)
        if not dept or session.current_index >= len(dept.hunt_group):
            session.status = "ALL_BUSY"
            session.final_spoken_message = MSG_ALL_BUSY
            return {
                "call_id": call_id,
                "status": "ALL_BUSY",
                "message_to_speak": MSG_ALL_BUSY,
                "department": session.department_name,
                "attempts_made": len(session.attempts),
                "action": "conclude_call"
            }

        target_ext = dept.hunt_group[session.current_index]
        attempt_num = len(session.attempts) + 1

        logger.info(
            f"[HUNT DIAL] Attempt {attempt_num} for Call {call_id}: "
            f"Dialing {target_ext.representative_name} ({target_ext.role}) at {target_ext.phone_number}"
        )

        # Trigger outbound dial leg via Kros AI Outbound Calls API (B2BUA)
        outbound_res = await kros_client.dial_outbound_leg(
            customer_call_id=call_id,
            destination_number=target_ext.phone_number,
            department=dept.name,
            caller_name=session.caller_name
        )

        if ring_delay_seconds > 0:
            await asyncio.sleep(ring_delay_seconds)

        # Determine pickup outcome (configured simulated_pickup or override)
        did_pickup = target_ext.simulated_pickup if simulate_pickup_override is None else simulate_pickup_override

        if did_pickup:
            # Extension answered! Handover time
            record = HuntAttemptRecord(
                attempt_number=attempt_num,
                extension_id=target_ext.extension_id,
                representative_name=target_ext.representative_name,
                role=target_ext.role,
                phone_number=target_ext.phone_number,
                status="connected",
                duration_seconds=ring_delay_seconds
            )
            session.attempts.append(record)
            session.status = "CONNECTED"
            session.connected_extension = target_ext

            # Bridge Customer (Leg A) and Staff (Leg B) audio streams
            bridge_res = await kros_client.complete_handover_bridge(customer_call_id=call_id)

            handover_speech = (
                f"Thank you for holding! I have {target_ext.representative_name}, our "
                f"{target_ext.role}, on the line for you now. Handing you over right away — have a wonderful day!"
            )
            session.final_spoken_message = handover_speech

            logger.info(f"[HUNT SUCCESS] Call {call_id} successfully handed over to {target_ext.representative_name}")

            return {
                "call_id": call_id,
                "status": "HANDOVER_COMPLETE",
                "message_to_speak": handover_speech,
                "connected_to": {
                    "extension_id": target_ext.extension_id,
                    "name": target_ext.representative_name,
                    "role": target_ext.role,
                    "phone": target_ext.phone_number
                },
                "department": session.department_name,
                "attempt_number": attempt_num,
                "kros_bridge": bridge_res,
                "action": "bridge_audio"
            }

        else:
            # Extension did NOT pick up (busy / difficulty / no-answer)
            record = HuntAttemptRecord(
                attempt_number=attempt_num,
                extension_id=target_ext.extension_id,
                representative_name=target_ext.representative_name,
                role=target_ext.role,
                phone_number=target_ext.phone_number,
                status="difficulty_busy",
                duration_seconds=ring_delay_seconds
            )
            session.attempts.append(record)

            # Move to next extension in pool
            session.current_index += 1

            if session.current_index < len(dept.hunt_group):
                # More extensions available -> Tell user about difficulty and forward to another
                next_ext = dept.hunt_group[session.current_index]
                logger.info(
                    f"[HUNT RETRY] Extension {target_ext.extension_id} failed. "
                    f"Forwarding to next extension: {next_ext.representative_name}"
                )
                return {
                    "call_id": call_id,
                    "status": "DIFFICULTY_FORWARDING",
                    "message_to_speak": MSG_DIFFICULTY_RETRY,
                    "failed_extension": {
                        "name": target_ext.representative_name,
                        "role": target_ext.role
                    },
                    "next_extension": {
                        "name": next_ext.representative_name,
                        "role": next_ext.role,
                        "phone": next_ext.phone_number
                    },
                    "department": session.department_name,
                    "attempt_number": attempt_num,
                    "action": "dial_next"
                }
            else:
                # All extensions exhausted!
                session.status = "ALL_BUSY"
                session.final_spoken_message = MSG_ALL_BUSY
                logger.warning(f"[HUNT EXHAUSTED] All {len(dept.hunt_group)} lines in {dept.name} were busy.")
                return {
                    "call_id": call_id,
                    "status": "ALL_BUSY",
                    "message_to_speak": MSG_ALL_BUSY,
                    "department": session.department_name,
                    "attempts_made": len(session.attempts),
                    "action": "conclude_call"
                }

    async def run_hunt_sequence(
        self,
        call_id: str,
        department_id: str,
        caller_phone: str = "+2348000000000",
        caller_name: str = "Valued Customer",
        concern: str = "General Inquiry",
        on_event: Optional[Callable[[Dict[str, Any]], Any]] = None,
        ring_delay_seconds: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Runs the complete hunt sequence asynchronously until pickup or all busy,
        invoking on_event callback at each transition.
        """
        session, intro = self.start_hunt(call_id, department_id, caller_phone, caller_name, concern)
        events = [{
            "call_id": call_id,
            "status": "STARTED",
            "message_to_speak": intro,
            "department": session.department_name
        }]
        if on_event:
            on_event(events[-1])

        while session.status == "HUNTING":
            step_result = await self.step_hunt(call_id, ring_delay_seconds=ring_delay_seconds)
            events.append(step_result)
            if on_event:
                on_event(step_result)

            if step_result["status"] in ("HANDOVER_COMPLETE", "ALL_BUSY", "ERROR"):
                break

        return events

hunt_group_manager = HuntGroupManager()
