"""Limits are enforced in code, not prompts - these tests prove it."""
import pytest

from jarvis.agent import personas
from jarvis.agent.session import Session
from jarvis.work import gateway
from jarvis.work.roles import actor
from jarvis.work.transition import Denied, get_item, transition, verify_chain


@pytest.fixture(scope="module")
def s():
    sess = Session(2026, fresh=True, quiet=True)
    sess.connect()
    sess.onboard()
    personas.auto_controller(sess.engine)
    sess.run_close()
    return sess


def pending(s, kind=None):
    rows = s.db.q("SELECT item_id FROM work_items WHERE state='PROPOSED'" + (" AND kind=?" if kind else ""),
                  (kind,) if kind else ())
    return rows[0]["item_id"]


def test_agent_cannot_approve_its_own_work(s):
    iid = pending(s)
    with pytest.raises(Denied):
        transition(s.db, iid, "approve", actor("jarvis"))
    assert s.db.one("SELECT COUNT(*) n FROM audit_log WHERE subject=? AND allowed=0", (iid,))["n"] >= 1


def test_only_gateway_posts(s):
    iid = pending(s)
    with pytest.raises(Denied):
        transition(s.db, iid, "post", actor("maya"))


def test_gateway_refuses_unapproved(s):
    iid = pending(s)
    with pytest.raises(Denied):
        gateway.post(s.db, iid)


def test_policy_engine_cannot_approve_judgment(s):
    iid = pending(s, "paypal_split")
    with pytest.raises(Denied):
        transition(s.db, iid, "approve", actor("policy:P-001"))


def test_controller_approval_posts_balanced_entry(s):
    iid = pending(s, "paypal_split")
    out = s.approve(iid)
    assert out["state"] == "POSTED"
    je = s.db.one("SELECT entry_id FROM ledger_entries WHERE work_item_id=?", (iid,))
    tot = s.db.one("SELECT SUM(amount_cents) t FROM ledger_lines WHERE entry_id=?", (je["entry_id"],))["t"]
    assert tot == 0


def test_resync_never_duplicates(s):
    before = s.db.one("SELECT COUNT(*) n FROM records")["n"]
    items = s.db.one("SELECT COUNT(*) n FROM work_items")["n"]
    r = s.resync()
    assert s.db.one("SELECT COUNT(*) n FROM records")["n"] == before
    assert s.db.one("SELECT COUNT(*) n FROM work_items")["n"] == items
    assert r["bank"]["new"] == 0


def test_audit_log_is_append_only_and_chained(s):
    with pytest.raises(Exception):
        s.db.x("UPDATE audit_log SET reason='tampered' WHERE seq=1")
    assert verify_chain(s.db)["ok"]


def test_paypal_outage_falls_back_to_export(s):
    s.set_fault("down")
    try:
        r = s.resync()
        assert r["paypal"]["fallback_months"], r
        assert s.db.one("SELECT COUNT(*) n FROM audit_log WHERE action='fallback'")["n"] >= 1
    finally:
        s.set_fault(None)


def test_locked_period_rejected(s):
    iid = pending(s)
    it = get_item(s.db, iid)
    it["proposal"]["date"] = "2026-08-31"
    it["proposal"]["lines"] = [{"acct": "6810", "cents": 100}, {"acct": "1010", "cents": -100}]
    assert any("locked period" in e for e in gateway.validate(s.db, it))
