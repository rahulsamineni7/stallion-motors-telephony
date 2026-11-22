# Stallion Motors Dealership — Kros AI Voice Telephony & Concierge

A production-ready voice agent and telephony forwarding demo designed for **Stallion Motors Dealership** (West Africa's leading automotive conglomerate representing Nissan, Honda, Hyundai, Changan, Audi, and Ashok Leyland).

Powered by **Kros AI CPaaS** for carrier telecommunications infrastructure and **Sarvam AI** for conversational speech synthesis and recognition.

---

## 🌟 Key Features

1. **Automated Concern Discovery**:
   - Greets incoming callers as **Zola**, Senior AI Concierge for Stallion Motors Dealership.
   - Discovers caller concerns across 5 distinct automotive departments:
     - 🚗 **Sales**: New vehicle purchase, brochures, quotes, test drives.
     - 🔧 **Service & Bodyshop**: Maintenance, repairs, diagnostics, crash repairs.
     - ⚙️ **Spare Parts & Accessories**: Genuine OEM parts, batteries, tires.
     - 💳 **Finance & Insurance**: Auto loans, EMI calculations, insurance renewal.
     - ⚠️ **Customer Support & Escalation**: Grievances, management escalations.

2. **Sequential Hunt-Group Telephony Retries (Kros AI)**:
   - Connects to internal extension pools without requiring caller to memorize or dial direct phone numbers.
   - **Difficulty Handling**: If a dialed representative is busy or does not answer, the agent immediately reassures the caller:
     > *"Sorry, some difficulty in the number I dialed, let me forward to another..."*
   - Automatically dials the next representative in the hunt list and repeats if needed.

3. **Live Handover**:
   - The moment any representative answers, the agent confirms:
     > *"Thank you for holding! I have [Name], our [Role], on the line for you now. Handing you over right away — have a great day!"*
   - Kros AI bridges the call leg to the human specialist.

4. **All-Lines-Busy Fallback**:
   - If all representative lines in the department pool are unavailable:
     > *"I'm sorry, all our representatives are currently busy. Please call back in a while."*

5. **Dual Architecture (Kros AI + Sarvam AI)**:
   - Integrates with **Kros AI** call control APIs (`/v1/outbound-calls`, `/calls/{id}/transfer`).
   - Retains **Sarvam AI Bulbul:v4-flash** TTS and **Saaras:v4** STT for low-latency conversational audio.
   - Includes local simulation mode so the demo runs 100% offline or without active telecom carrier credentials.

---

## 📁 Project Architecture

```
stallion_motors_telephony/
├── .env.example                       # Environment variables template
├── requirements.txt                   # Dependencies (FastAPI, Uvicorn, httpx, etc.)
├── config.py                          # App settings, Kros AI config, Sarvam keys
├── server.py                          # FastAPI application & webhook gateway
├── demo_runner.py                     # CLI automated verification suite
├── prompts/
│   └── stallion_motors_prompt.md      # World-class Dealership System Prompt
├── telephony/
│   ├── routing_table.py               # Department hunt groups & extension pools
│   ├── kros_client.py                 # Kros AI CPaaS client (call control & transfer)
│   └── hunt_group_manager.py          # Multi-line retry loop & state tracker
├── audio/
│   ├── sarvam_tts.py                  # Sarvam Bulbul TTS (REST & fallback generator)
│   └── sarvam_stt.py                  # Sarvam Saaras STT API client
├── agent/
│   └── dealership_agent.py            # Conversational Agent with function calling
├── routes/
│   ├── kros_webhooks.py               # Inbound call & lifecycle event webhooks
│   └── simulation_api.py              # Interactive simulation & softphone endpoints
└── static/
    └── index.html                     # Visual Dealership Telephony Dashboard
```

---

## 🚀 Quickstart Guide

### 1. Run the Automated Demo Suite
To immediately verify the full multi-line retry and handover flow in your terminal:
```bash
python demo_runner.py
```
This tests both:
- **Scenario 1**: Line 1 fails → Line 2 fails → Line 3 answers → Handover.
- **Scenario 2**: All lines busy → *"Please call back in a while"*.

### 2. Launch the Interactive Web Dashboard & Server
```bash
python -m uvicorn server:app --host 0.0.0.0 --port 8028 --reload
```
Open your browser to:
👉 **[http://localhost:8028](http://localhost:8028)**

The dashboard includes:
- Interactive Inbound Softphone with 1-click test scenarios.
- Visual Telephony Hunt Stage showing real-time line retries and exact prompts.
- Toggle switches to customize individual representative availability.
- Audio player streaming synthesized voice prompts.

---

## 🔒 Strict Isolation Notice
The original source directory at `C:\Users\rahul\OneDrive\Desktop\localcodegenbackup` was **only read** for architectural reference. No files in that directory were modified or created.
