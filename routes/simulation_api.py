"""
Interactive Simulation & Telephony Testing Endpoints.
Allows visual and programmatic testing of the multi-line retry and handover flow.
"""

import os
import uuid
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from telephony.routing_table import STALLION_DEPARTMENTS, list_departments, get_department
from telephony.hunt_group_manager import hunt_group_manager
from agent.dealership_agent import StallionDealershipAgent
from audio.sarvam_tts import sarvam_tts
from audio.fish_tts import fish_tts
from config import fish_audio_config

logger = logging.getLogger("simulation_api")
sim_router = APIRouter(prefix="/api", tags=["Simulation & Demo"])

# Store simulated agents in memory
_SIM_AGENTS: Dict[str, StallionDealershipAgent] = {}

class StartCallRequest(BaseModel):
    caller_phone: str = "+2348031234567"
    caller_name: str = "Chief Adeleke"

class TurnRequest(BaseModel):
    call_id: str
    utterance: str

class StepHuntRequest(BaseModel):
    call_id: str
    force_pickup: Optional[bool] = None

class ToggleExtensionRequest(BaseModel):
    department_id: str
    extension_id: str
    simulated_pickup: bool

@sim_router.get("/dealership/departments")
async def get_departments_list():
    """Returns all departments, representatives, and current simulated availability."""
    return JSONResponse({"departments": list_departments()})

@sim_router.post("/dealership/toggle-extension")
async def toggle_extension_pickup(req: ToggleExtensionRequest):
    """Dynamically configure whether an extension answers or encounters difficulty."""
    dept = get_department(req.department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    target = None
    for ext in dept.hunt_group:
        if ext.extension_id == req.extension_id:
            ext.simulated_pickup = req.simulated_pickup
            target = ext
            break

    if not target:
        raise HTTPException(status_code=404, detail="Extension not found")

    return JSONResponse({
        "status": "updated",
        "extension_id": target.extension_id,
        "name": target.representative_name,
        "simulated_pickup": target.simulated_pickup
    })

@sim_router.post("/dealership/set-all-busy")
async def set_all_busy(department_id: str = Query(..., description="Department to set all busy")):
    """Sets all extensions in a department to encounter difficulty/busy (demonstrates 'call back in a while')."""
    dept = get_department(department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    for ext in dept.hunt_group:
        ext.simulated_pickup = False

    return JSONResponse({
        "status": "all_set_busy",
        "department": dept.name,
        "extensions_configured": len(dept.hunt_group)
    })

@sim_router.post("/dealership/reset-defaults")
async def reset_defaults():
    """Resets all extensions to their standard demonstration defaults."""
    # Sales: Line 1 & 2 difficulty, Line 3 picks up
    for ext in STALLION_DEPARTMENTS["sales"].hunt_group:
        ext.simulated_pickup = (ext.extension_id == "ext_sales_103")
    # Service: Line 1 difficulty, Line 2 picks up
    for ext in STALLION_DEPARTMENTS["service"].hunt_group:
        ext.simulated_pickup = (ext.extension_id != "ext_serv_201")
    # Support: All busy
    for ext in STALLION_DEPARTMENTS["support"].hunt_group:
        ext.simulated_pickup = False

    return JSONResponse({"status": "reset_to_defaults", "message": "Standard demo hunt states restored."})

@sim_router.post("/simulate/start-call")
async def simulate_start_call(req: StartCallRequest):
    """Initiates a simulated incoming call and delivers the opening greeting."""
    call_id = f"sim_{uuid.uuid4().hex[:8]}"
    agent = StallionDealershipAgent(call_id=call_id, caller_phone=req.caller_phone)
    _SIM_AGENTS[call_id] = agent

    greeting = agent.get_greeting()
    return JSONResponse({
        "call_id": call_id,
        "status": "CALL_CONNECTED",
        "agent_greeting": greeting,
        "caller_phone": req.caller_phone,
        "caller_name": req.caller_name
    })

@sim_router.post("/simulate/submit-concern")
async def simulate_submit_concern(req: TurnRequest):
    """
    Submits caller's concern:
    Agent classifies the department and prepares the hunt group.
    """
    agent = _SIM_AGENTS.get(req.call_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Call session not found")

    result = await agent.process_user_turn(req.utterance)
    return JSONResponse({
        "call_id": req.call_id,
        "turn_result": result
    })

@sim_router.post("/simulate/step-hunt")
async def simulate_step_hunt(req: StepHuntRequest):
    """
    Steps through a single dial in the hunt group:
    Returns either:
    - DIFFICULTY_FORWARDING ('Sorry, some difficulty in the number I dialed, let me forward to another...')
    - HANDOVER_COMPLETE ('Thank you for holding! I have [Name] on the line...')
    - ALL_BUSY ('I'm sorry, all our representatives are currently busy. Please call back in a while.')
    """
    step_result = await hunt_group_manager.step_hunt(
        call_id=req.call_id,
        simulate_pickup_override=req.force_pickup,
        ring_delay_seconds=0.2
    )
    return JSONResponse(step_result)

@sim_router.post("/simulate/auto-flow")
async def simulate_auto_flow(req: TurnRequest):
    """
    Runs the complete end-to-end conversation turn and telephony hunt automatically!
    Returns full transcript of every message spoken during retries and conclusion.
    """
    agent = _SIM_AGENTS.get(req.call_id)
    if not agent:
        # Create on the fly if needed
        agent = StallionDealershipAgent(call_id=req.call_id)
        _SIM_AGENTS[req.call_id] = agent

    # 1. Process Concern
    routing_turn = await agent.process_user_turn(req.utterance)

    # 2. Automatically execute hunt sequence
    sequence_events = []
    session = hunt_group_manager.get_session(req.call_id)
    if session:
        while session.status == "HUNTING":
            step = await hunt_group_manager.step_hunt(req.call_id, ring_delay_seconds=0.1)
            sequence_events.append(step)
            if step["status"] in ("HANDOVER_COMPLETE", "ALL_BUSY", "ERROR"):
                break

    return JSONResponse({
        "call_id": req.call_id,
        "caller_utterance": req.utterance,
        "routing_turn": routing_turn,
        "telephony_hunt_steps": sequence_events,
        "final_status": session.status if session else "UNKNOWN"
    })

@sim_router.get("/audio/tts")
async def get_tts_audio(
    text: str = Query(..., description="Text to synthesize"),
    provider: str = Query("fish", description="TTS provider: 'fish' or 'sarvam'")
):
    """
    Returns audio bytes for testing spoken prompts.
    Prioritizes Fish Audio (MP3) or Sarvam AI (WAV).
    """
    if provider == "fish" or fish_audio_config.enabled:
        audio_bytes = await fish_tts.synthesize(text, format="mp3")
        if audio_bytes and len(audio_bytes) > 200:
            return Response(content=audio_bytes, media_type="audio/mpeg")

    # Fallback to Sarvam TTS
    audio_bytes = await sarvam_tts.synthesize(text)
    return Response(content=audio_bytes, media_type="audio/wav")

@sim_router.get("/audio/fish-tts")
async def get_fish_tts_endpoint(text: str = Query(..., description="Text to synthesize with Fish Audio")):
    """Dedicated Fish Audio MP3 endpoint."""
    audio_bytes = await fish_tts.synthesize(text, format="mp3")
    if audio_bytes and len(audio_bytes) > 200:
        return Response(content=audio_bytes, media_type="audio/mpeg")
    # Fallback
    audio_bytes = await sarvam_tts.synthesize(text)
    return Response(content=audio_bytes, media_type="audio/wav")
