"""
Kros AI Webhook & Telephony Endpoints for Stallion Motors.
Handles inbound calls, event notifications, and audio websocket streaming.
"""

import os
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from agent.dealership_agent import StallionDealershipAgent
from telephony.hunt_group_manager import hunt_group_manager
from telephony.kros_client import kros_client
from audio.sarvam_tts import sarvam_tts

logger = logging.getLogger("kros_webhooks")
kros_router = APIRouter(prefix="/kros", tags=["Kros AI Telephony"])

# Active Agent Instances by Call ID
_ACTIVE_AGENTS: Dict[str, StallionDealershipAgent] = {}

@kros_router.post("/incoming")
async def kros_incoming_call(request: Request):
    """
    Kros AI Inbound Call Webhook (Answer URL).
    Fired when a caller dials the Stallion Motors dealership number.
    """
    try:
        body = await request.json()
    except Exception:
        body = dict(request.query_params)

    call_id = body.get("call_id") or f"call_{os.urandom(4).hex()}"
    from_number = body.get("from_number") or body.get("From") or "+2348000000000"
    to_number = body.get("to_number") or body.get("To") or "+23418880199"

    logger.info(f"[KROS INCOMING] Call {call_id} from {from_number} to {to_number}")

    # Initialize Dealership Agent for this call
    agent = StallionDealershipAgent(call_id=call_id, caller_phone=from_number)
    _ACTIVE_AGENTS[call_id] = agent

    # Generate Opening Greeting
    greeting_text = agent.get_greeting()

    # If Kros AI uses XML or JSON instruction response
    return JSONResponse({
        "status": "call_accepted",
        "call_id": call_id,
        "action": "play_and_collect",
        "speak": greeting_text,
        "listen_for_concern": True,
        "webhook_url": f"/kros/events?call_id={call_id}"
    })

@kros_router.post("/events")
async def kros_event_webhook(request: Request):
    """
    Kros AI Lifecycle Webhook:
    Subscribes to: call.initiated, call.ringing, call.answered, call.completed, call.failed
    """
    try:
        payload = await request.json()
    except Exception:
        payload = dict(request.query_params)

    event_type = payload.get("event") or payload.get("type", "unknown")
    call_id = payload.get("call_id") or payload.get("CallUUID", "")

    logger.info(f"[KROS EVENT] Received '{event_type}' for Call {call_id}")

    if event_type == "call.completed" and call_id in _ACTIVE_AGENTS:
        del _ACTIVE_AGENTS[call_id]

    return JSONResponse({"status": "received", "event": event_type})

@kros_router.websocket("/ws/{call_id}")
async def kros_audio_websocket(websocket: WebSocket, call_id: str):
    """
    Bidirectional audio stream over WebSocket between Kros AI and Sarvam AI pipeline.
    """
    await websocket.accept()
    logger.info(f"[KROS WS] Audio stream connected for Call {call_id}")

    agent = _ACTIVE_AGENTS.get(call_id) or StallionDealershipAgent(call_id=call_id)
    _ACTIVE_AGENTS[call_id] = agent

    try:
        # Send initial greeting audio
        greeting = agent.get_greeting()
        audio_bytes = await sarvam_tts.synthesize(greeting)
        if audio_bytes:
            await websocket.send_bytes(audio_bytes)

        while True:
            data = await websocket.receive_bytes()
            # Feed audio into Sarvam STT pipeline in real-time
            # When speech chunk completes, process agent turn
    except WebSocketDisconnect:
        logger.info(f"[KROS WS] Audio stream disconnected for Call {call_id}")
    except Exception as e:
        logger.error(f"[KROS WS ERROR] {e}")
