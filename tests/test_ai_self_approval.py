"""Test that AI agent cannot approve its own work (maker-checker rule)."""
import pytest
from pathlib import Path
from jarvis.work.db import DB
from jarvis.work.transition import create_item, transition, Denied
from jarvis.work.roles import actor


def test_ai_cannot_approve_proposed_item():
    """AI agent should be denied when trying to approve an item in PROPOSED state."""
    db = DB(Path(":memory:"))
    
    # Create item as sync (items are created by sync, not agents)
    sync = actor("sync")
    item = create_item(db, sync, "unknown_debit", "test-approval-1", 
                       "Unknown debit $100", "2026-10", 
                       [{"src": "bank", "id": "test-1"}])
    
    # Propose it as AI agent
    jarvis = actor("jarvis")
    proposal = {
        "lines": [{"acct": "6100", "cents": -10000}],
        "memo": "Test debit"
    }
    transition(db, item["item_id"], "propose", jarvis, 
               patch={"proposal": proposal, "confidence": 0.98, "rationale": "Test"})
    
    # Try to approve as ai_agent - should fail with role error
    with pytest.raises(Denied) as exc:
        transition(db, item["item_id"], "approve", jarvis, reason="Self-approval attempt")
    
    # Check that it's a role error, not just a state transition error
    assert "may not 'approve'" in str(exc.value) or "separation of duties" in str(exc.value)


def test_ai_cannot_approve_needs_info():
    """AI agent should be denied when trying to approve an item in NEEDS_INFO state.
    
    Even though there's no valid transition from NEEDS_INFO to approve,
    the role check should also prevent ai_agent from approving.
    """
    db = DB(Path(":memory:"))
    
    # Create item as sync
    sync = actor("sync")
    item = create_item(db, sync, "unknown_debit", "test-approval-2", 
                       "Unknown debit $100", "2026-10", 
                       [{"src": "bank", "id": "test-2"}])
    
    # Move it to NEEDS_INFO
    jarvis = actor("jarvis")
    transition(db, item["item_id"], "ask", jarvis, 
               patch={"question": "What account?"})
    
    # Try to approve from NEEDS_INFO - should fail
    with pytest.raises(Denied) as exc:
        transition(db, item["item_id"], "approve", jarvis, reason="Self-approval attempt")
    
    # Should fail (either for invalid transition or role check)
    assert "may not" in str(exc.value) or "no transition" in str(exc.value)


def test_human_can_approve():
    """Human accountant should be able to approve items proposed by AI."""
    db = DB(Path(":memory:"))
    
    # Create as sync, propose as AI
    sync = actor("sync")
    item = create_item(db, sync, "unknown_debit", "test-approval-3", 
                       "Unknown debit $100", "2026-10", 
                       [{"src": "bank", "id": "test-3"}])
    
    jarvis = actor("jarvis")
    proposal = {
        "lines": [{"acct": "6100", "cents": -10000}],
        "memo": "Test debit"
    }
    transition(db, item["item_id"], "propose", jarvis, 
               patch={"proposal": proposal, "confidence": 0.98, "rationale": "Test"})
    
    # Approve as human - should succeed
    dev = actor("dev")
    result = transition(db, item["item_id"], "approve", dev, reason="Looks good")
    
    assert result["state"] == "APPROVED"
    assert result["approved_by"] == "dev"
