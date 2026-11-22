"""
Department Routing Table & Representative Pools for Stallion Motors Dealership.
Configures extensions, placeholder/virtual numbers, and hunt-group sequences.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel

class ExtensionTarget(BaseModel):
    extension_id: str
    representative_name: str
    role: str
    phone_number: str  # E.164 or SIP extension
    is_available: bool = True  # Can be toggled dynamically for demos
    simulated_pickup: bool = False  # Set to True if this line answers, False if difficulty/busy

class Department(BaseModel):
    id: str
    name: str
    description: str
    hunt_group: List[ExtensionTarget]

# Stallion Motor Dealership Department Configuration
STALLION_DEPARTMENTS: Dict[str, Department] = {
    "sales": Department(
        id="sales",
        name="New & Pre-Owned Vehicle Sales",
        description="Showroom inquiries, quotes, test drives, vehicle availability for Nissan, Honda, Hyundai, etc.",
        hunt_group=[
            ExtensionTarget(
                extension_id="ext_sales_101",
                representative_name="Emeka Okoye",
                role="Primary Sales Consultant",
                phone_number="+234801000101",
                simulated_pickup=False,  # Line 1 encounters difficulty to demonstrate retry
            ),
            ExtensionTarget(
                extension_id="ext_sales_102",
                representative_name="Amina Bello",
                role="Senior Sales Executive",
                phone_number="+234801000102",
                simulated_pickup=False,  # Line 2 encounters difficulty to demonstrate second retry
            ),
            ExtensionTarget(
                extension_id="ext_sales_103",
                representative_name="Tunde Bakare",
                role="Showroom Sales Manager",
                phone_number="+234801000103",
                simulated_pickup=True,   # Line 3 answers and picks up!
            ),
        ]
    ),
    "service": Department(
        id="service",
        name="Service, Maintenance & Bodyshop",
        description="Routine servicing, mechanical/electrical diagnostics, crash repairs, warranty maintenance.",
        hunt_group=[
            ExtensionTarget(
                extension_id="ext_serv_201",
                representative_name="Chioma Nwosu",
                role="Quick Service Advisor",
                phone_number="+234802000201",
                simulated_pickup=False,
            ),
            ExtensionTarget(
                extension_id="ext_serv_202",
                representative_name="Ibrahim Sani",
                role="Senior Diagnostic Specialist",
                phone_number="+234802000202",
                simulated_pickup=True,  # Picks up on 2nd attempt
            ),
            ExtensionTarget(
                extension_id="ext_serv_203",
                representative_name="Segun Adebayo",
                role="Workshop Floor Manager",
                phone_number="+234802000203",
                simulated_pickup=True,
            ),
        ]
    ),
    "parts": Department(
        id="parts",
        name="Genuine Spare Parts & Accessories",
        description="OEM replacement parts, batteries, tires, manufacturer accessories, wholesale supply.",
        hunt_group=[
            ExtensionTarget(
                extension_id="ext_parts_301",
                representative_name="Kelechi Obi",
                role="Parts Counter Lead",
                phone_number="+234803000301",
                simulated_pickup=False,
            ),
            ExtensionTarget(
                extension_id="ext_parts_302",
                representative_name="Fatima Lawal",
                role="Central Warehouse Dispatcher",
                phone_number="+234803000302",
                simulated_pickup=True,
            ),
        ]
    ),
    "finance": Department(
        id="finance",
        name="Auto Finance & Insurance Desk",
        description="Vehicle financing, hire purchase, insurance renewals, and claims processing.",
        hunt_group=[
            ExtensionTarget(
                extension_id="ext_fin_401",
                representative_name="David Adeleke",
                role="Finance & Leasing Specialist",
                phone_number="+234804000401",
                simulated_pickup=False,
            ),
            ExtensionTarget(
                extension_id="ext_fin_402",
                representative_name="Ngozi Eze",
                role="Insurance Desk Coordinator",
                phone_number="+234804000402",
                simulated_pickup=True,
            ),
        ]
    ),
    "support": Department(
        id="support",
        name="Customer Experience & Management Escalation",
        description="General customer support, grievances, billing reviews, management attention.",
        hunt_group=[
            ExtensionTarget(
                extension_id="ext_sup_501",
                representative_name="Blessing Johnson",
                role="Customer Relations Supervisor",
                phone_number="+234805000501",
                simulated_pickup=False,
            ),
            ExtensionTarget(
                extension_id="ext_sup_502",
                representative_name="Babajide Rhodes",
                role="Dealership Duty Manager",
                phone_number="+234805000502",
                simulated_pickup=False,  # Both busy in support to demonstrate ALL BUSY fallback!
            ),
        ]
    )
}

def get_department(dept_id: str) -> Optional[Department]:
    dept_id = (dept_id or "").lower().strip()
    return STALLION_DEPARTMENTS.get(dept_id)

def list_departments() -> List[Dict]:
    return [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "extension_count": len(d.hunt_group),
            "representatives": [
                {
                    "extension_id": ext.extension_id,
                    "name": ext.representative_name,
                    "role": ext.role,
                    "phone": ext.phone_number,
                    "simulated_pickup": ext.simulated_pickup
                }
                for ext in d.hunt_group
            ]
        }
        for d in STALLION_DEPARTMENTS.values()
    ]
