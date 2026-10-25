"""Who may do what, to which kind of resource. Enforced in code on every call - never by prompt.

Shape follows the Hyphenate workshop: ROLES[role][resource] -> allowed actions; no role but
the gateway can post; nobody can approve what they proposed.
"""
from __future__ import annotations

from dataclasses import dataclass

ROLES: dict[str, dict[str, set[str]]] = {
    "sync":             {"work_item": {"create"}, "record": {"write"}},
    "ai_agent":         {"work_item": {"propose", "ask", "revise", "dismiss", "withdraw"},
                         "policy": {"propose"}, "message": {"send"}},
    "ai_reviewer":      {"work_item": {"review"}},
    "policy_engine":    {"work_item": {"approve"}},          # only under standing policy P-001 (checked below)
    "human_accountant": {"work_item": {"approve", "reject", "answer"}},
    "human_controller": {"work_item": {"approve", "reject", "answer"}, "policy": {"approve", "reject"}},
    "gateway":          {"work_item": {"post"}, "ledger": {"write"}, "vendor_master": {"write"}},
}

# Actors (identities). The agent and the reviewer are different identities with different roles.
ACTORS = {
    "sync": ("sync", "Sync job"),
    "jarvis": ("ai_agent", "Jarvis (preparer agent)"),
    "jarvis-reviewer": ("ai_reviewer", "Jarvis reviewer (critic)"),
    "policy:P-001": ("policy_engine", "Standing policy P-001 (set by Maya Chen)"),
    "dev": ("human_accountant", "Dev Patel (staff accountant)"),
    "maya": ("human_controller", "Maya Chen (Controller)"),
    "gateway": ("gateway", "Gateway (only writer to the ledger)"),
}

# kinds a standing policy may approve without a human (Controller's P-001)
P001_KINDS = {"match", "bill_payment", "card_statement_payment", "receivable_receipt"}
P001_BANK_FEE_LIMIT = 25_000


@dataclass(frozen=True)
class Actor:
    id: str

    @property
    def role(self) -> str:
        return ACTORS[self.id][0]

    @property
    def display(self) -> str:
        return ACTORS[self.id][1]


def actor(actor_id: str) -> Actor:
    if actor_id not in ACTORS:
        raise KeyError(f"unknown actor {actor_id}")
    return Actor(actor_id)


def can(a: Actor, action: str, resource_kind: str, res: dict | None = None) -> tuple[bool, str]:
    allowed = ROLES.get(a.role, {}).get(resource_kind, set())
    if action not in allowed:
        return False, f"role '{a.role}' may not '{action}' a {resource_kind}"
    if res is not None and action == "approve":
        if res.get("proposed_by") == a.id:
            return False, "separation of duties: the proposer cannot approve its own work"
        if a.role == "policy_engine":
            kind = res.get("kind")
            prop = res.get("proposal") or {}
            if kind == "bank_fee":
                amt = sum(l["cents"] for l in prop.get("lines", []) if l["cents"] > 0)
                if amt >= P001_BANK_FEE_LIMIT:
                    return False, "P-001 covers bank fees under $250 only"
            elif kind not in P001_KINDS:
                return False, f"P-001 does not cover '{kind}' - needs the Controller"
            if (res.get("confidence") or 0) < 0.95:
                return False, "P-001 requires confidence >= 0.95"
    return True, "ok"
