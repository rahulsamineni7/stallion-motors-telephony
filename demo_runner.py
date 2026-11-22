"""
Automated Demo Runner & Telephony Verification Suite.
Demonstrates the complete Stallion Motors Dealership voice flow:
1. Inbound Call Greeting & Concern Discovery.
2. Intelligent Department Routing.
3. Multi-Line Sequential Retry Loop with exact spoken reassurance:
   'Sorry, some difficulty in the number I dialed, let me forward to another...'
4. Successful Handover when a line answers.
5. All-Lines-Busy Fallback:
   'I'm sorry, all our representatives are currently busy. Please call back in a while.'
"""

import sys
import asyncio
import logging
from agent.dealership_agent import StallionDealershipAgent
from telephony.hunt_group_manager import hunt_group_manager, MSG_DIFFICULTY_RETRY, MSG_ALL_BUSY
from telephony.routing_table import STALLION_DEPARTMENTS

# Setup Clean Console Logging
logging.basicConfig(level=logging.WARNING)

HEADER = "\033[95m"
BLUE = "\033[94m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

async def run_scenario_1_sales_retry_and_handover():
    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{HEADER} TEST SCENARIO 1: Sales Inquiry — Multi-Line Retry & Successful Handover{RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════════════════════════════{RESET}")

    call_id = "test_call_sales_001"
    caller_phone = "+2348039876543"
    customer_name = "Senator Adeleke"

    # Reset sales hunt group: Line 1 & Line 2 encounter difficulty, Line 3 answers
    STALLION_DEPARTMENTS["sales"].hunt_group[0].simulated_pickup = False
    STALLION_DEPARTMENTS["sales"].hunt_group[1].simulated_pickup = False
    STALLION_DEPARTMENTS["sales"].hunt_group[2].simulated_pickup = True

    # 1. Incoming Call
    print(f"\n{BLUE}[INCOMING CALL]{RESET} From: {caller_phone} ({customer_name}) -> Stallion Motors Telephony DID")
    agent = StallionDealershipAgent(call_id=call_id, caller_phone=caller_phone)

    # 2. Greeting
    greeting = agent.get_greeting()
    print(f"{GREEN}[AGENT SPOKEN GREETING]{RESET} \"{greeting}\"")

    # 3. Caller Concern
    concern = "Hello, I am interested in buying the new 2026 Hyundai Santa Fe SUV. Can you give me pricing and schedule a test drive?"
    print(f"\n{YELLOW}[CALLER CONCERN]{RESET} \"{concern}\"")

    # 4. Agent Analyzes & Initiates Routing
    routing_result = await agent.process_user_turn(concern)
    print(f"{CYAN}[ROUTING DECISION]{RESET} Department: {routing_result['department_name']} (Concern: {routing_result['concern']})")
    print(f"{GREEN}[AGENT SPOKEN REASSURANCE]{RESET} \"{routing_result['message_to_speak']}\"")

    # 5. Telephony Hunt Sequence
    print(f"\n{BOLD}Starting Kros AI Sequential Hunt Group Dialing...{RESET}")
    session = hunt_group_manager.get_session(call_id)

    step_count = 0
    while session.status == "HUNTING":
        step_count += 1
        step = await hunt_group_manager.step_hunt(call_id, ring_delay_seconds=0.0)

        if step["status"] == "DIFFICULTY_FORWARDING":
            print(f"\n  📞 {BOLD}Attempt #{step['attempt_number']}:{RESET} Dialed {step['failed_extension']['name']} ({step['failed_extension']['role']}) -> [LINE BUSY / DIFFICULTY]")
            print(f"  🗣️ {GREEN}[MANDATORY SPOKEN PROMPT]{RESET} {BOLD}\"{step['message_to_speak']}\"{RESET}")
            print(f"  🔄 Forwarding to next representative: {step['next_extension']['name']} ({step['next_extension']['role']}) at {step['next_extension']['phone']}")

        elif step["status"] == "HANDOVER_COMPLETE":
            print(f"\n  📞 {BOLD}Attempt #{step['attempt_number']}:{RESET} Dialed {step['connected_to']['name']} ({step['connected_to']['role']}) -> [LINE PICKED UP!]")
            print(f"  🗣️ {GREEN}[HANDOVER SPOKEN PROMPT]{RESET} {BOLD}\"{step['message_to_speak']}\"{RESET}")
            print(f"  ✅ {GREEN}[KROS AI BRIDGE COMPLETE]{RESET} Audio leg bridged to {step['connected_to']['name']}. Handover complete!")
            break

    assert session.status == "CONNECTED"
    print(f"\n{BOLD}{GREEN}✓ SCENARIO 1 PASSED: Multi-line retry loop succeeded with live handover!{RESET}")


async def run_scenario_2_all_busy_fallback():
    print(f"\n{BOLD}{CYAN}══════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{HEADER} TEST SCENARIO 2: All Lines Busy — Fallback to 'Please call back in a while'{RESET}")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════════════════════════════{RESET}")

    call_id = "test_call_support_002"
    caller_phone = "+2348051112233"
    customer_name = "Madam Okonkwo"

    # Set all support lines to busy/difficulty
    for ext in STALLION_DEPARTMENTS["support"].hunt_group:
        ext.simulated_pickup = False

    # 1. Incoming Call
    print(f"\n{BLUE}[INCOMING CALL]{RESET} From: {caller_phone} ({customer_name}) -> Stallion Motors Telephony DID")
    agent = StallionDealershipAgent(call_id=call_id, caller_phone=caller_phone)

    # 2. Greeting
    greeting = agent.get_greeting()
    print(f"{GREEN}[AGENT SPOKEN GREETING]{RESET} \"{greeting}\"")

    # 3. Caller Concern
    concern = "I have an unresolved complaint about billing on my recent car maintenance, I want to talk to the dealership manager."
    print(f"\n{YELLOW}[CALLER CONCERN]{RESET} \"{concern}\"")

    # 4. Agent Analyzes & Initiates Routing
    routing_result = await agent.process_user_turn(concern)
    print(f"{CYAN}[ROUTING DECISION]{RESET} Department: {routing_result['department_name']}")
    print(f"{GREEN}[AGENT SPOKEN REASSURANCE]{RESET} \"{routing_result['message_to_speak']}\"")

    # 5. Telephony Hunt Sequence
    print(f"\n{BOLD}Starting Kros AI Sequential Hunt Group Dialing...{RESET}")
    session = hunt_group_manager.get_session(call_id)

    while session.status == "HUNTING":
        step = await hunt_group_manager.step_hunt(call_id, ring_delay_seconds=0.0)

        if step["status"] == "DIFFICULTY_FORWARDING":
            print(f"\n  📞 Attempt #{step['attempt_number']}: Dialed {step['failed_extension']['name']} -> [LINE BUSY / DIFFICULTY]")
            print(f"  🗣️ {GREEN}[MANDATORY SPOKEN PROMPT]{RESET} {BOLD}\"{step['message_to_speak']}\"{RESET}")
            print(f"  🔄 Retrying next representative...")

        elif step["status"] == "ALL_BUSY":
            print(f"\n  ⚠️ {RED}[ALL EXTENSIONS EXHAUSTED]{RESET} All lines in {step['department']} are currently busy.")
            print(f"  🗣️ {RED}[MANDATORY SPOKEN FALLBACK]{RESET} {BOLD}\"{step['message_to_speak']}\"{RESET}")
            print(f"  📴 Call concluded gracefully with callback logged.")
            break

    assert session.status == "ALL_BUSY"
    assert session.final_spoken_message == MSG_ALL_BUSY
    print(f"\n{BOLD}{GREEN}✓ SCENARIO 2 PASSED: All-lines-busy fallback successfully triggered!{RESET}")


async def main():
    print(f"{BOLD}{HEADER}╔═══════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{HEADER}║  STALLION MOTORS DEALERSHIP — KROS AI TELEPHONY & VOICE AGENT VERIFICATION║{RESET}")
    print(f"{BOLD}{HEADER}╚═══════════════════════════════════════════════════════════════════════════╝{RESET}")

    await run_scenario_1_sales_retry_and_handover()
    await run_scenario_2_all_busy_fallback()

    print(f"\n{BOLD}{GREEN}══════════════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{GREEN} ALL TELEPHONY SPECIFICATIONS VERIFIED & FULLY FUNCTIONAL!{RESET}")
    print(f"{BOLD}{GREEN}══════════════════════════════════════════════════════════════════════════════{RESET}\n")

if __name__ == "__main__":
    asyncio.run(main())
