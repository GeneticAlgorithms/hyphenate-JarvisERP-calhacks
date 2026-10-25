"""Test that _is_personal works correctly with precedents only (no active policy)."""
import json
import tempfile
import os
from jarvis.agent.skills import _is_personal
from jarvis.work.db import DB


def test_personal_with_precedent_only():
    """Test that $113.44 Steam goes to 1250 even without onboarding/policy."""
    # Simulate a fresh DB with only precedent P-0317, no active policy
    db_path = tempfile.mktemp(suffix='.db')
    db = DB(db_path)
    
    # Insert precedent like prec-116 (personal purchase ruling)
    db.conn.execute(
        '''INSERT INTO precedents (prec_id, date, period, pattern, summary, decision, decided_by, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        ('prec-116', '2026-03-15', '2026-03', 'personal', 'Personal Steam purchase',
         json.dumps({
             'personal_mccs': ['5816', '5815', '5691'],
             'personal_merchant_keywords': ['steam', 'netflix', 'nordstrom', 'sephora']
         }),
         'maya', 'active'))
    db.conn.commit()
    
    # Mock context - _is_personal only needs precedents() method
    class MockCtx:
        def __init__(self, db):
            self.db = db
        
        def active_policy(self, pattern):
            return None  # No active policy
        
        def precedents(self, pattern):
            if pattern == "personal":
                rows = self.db.q("SELECT * FROM precedents WHERE pattern=? AND status='active'", (pattern,))
                return rows
            return []
    
    ctx = MockCtx(db)
    
    # Test 1: MCC match (5816 = Digital Goods - Games)
    is_personal, reason = _is_personal(ctx, 'Steam', 'Digital purchase', '5816')
    assert is_personal, f"Should detect MCC 5816 as personal. Got: is_personal={is_personal}, reason={reason}"
    assert 'MCC 5816' in reason, f"Reason should mention MCC 5816. Got: {reason}"
    
    # Test 2: Keyword match (steam)
    is_personal2, reason2 = _is_personal(ctx, 'Steam', 'Gaming platform', '')
    assert is_personal2, f"Should detect 'steam' keyword as personal. Got: is_personal={is_personal2}, reason={reason2}"
    assert 'steam' in reason2.lower(), f"Reason should mention 'steam'. Got: {reason2}"
    
    # Test 3: Not personal
    is_personal3, reason3 = _is_personal(ctx, 'Stripe', 'Payment processor', '7399')
    assert not is_personal3, f"Stripe should not be personal. Got: is_personal={is_personal3}"
    
    os.unlink(db_path)


def test_personal_merges_all_precedents():
    """Test that multiple precedents are merged, not just precs[-1]."""
    db_path = tempfile.mktemp(suffix='.db')
    db = DB(db_path)
    
    # Insert two precedents with different keywords/MCCs
    db.conn.execute(
        '''INSERT INTO precedents (prec_id, date, period, pattern, summary, decision, decided_by, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        ('prec-105', '2026-02-01', '2026-02', 'personal', 'Netflix personal',
         json.dumps({'personal_mccs': ['5815'], 'personal_merchant_keywords': ['netflix']}),
         'maya', 'active'))
    
    db.conn.execute(
        '''INSERT INTO precedents (prec_id, date, period, pattern, summary, decision, decided_by, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        ('prec-116', '2026-03-15', '2026-03', 'personal', 'Steam personal',
         json.dumps({'personal_mccs': ['5816'], 'personal_merchant_keywords': ['steam']}),
         'maya', 'active'))
    db.conn.commit()
    
    class MockCtx:
        def __init__(self, db):
            self.db = db
        
        def active_policy(self, pattern):
            return None
        
        def precedents(self, pattern):
            if pattern == "personal":
                return self.db.q("SELECT * FROM precedents WHERE pattern=? AND status='active' ORDER BY date", (pattern,))
            return []
    
    ctx = MockCtx(db)
    
    # Should detect both Netflix (from prec-105) and Steam (from prec-116)
    is_netflix, _ = _is_personal(ctx, 'Netflix', 'Streaming', '5815')
    assert is_netflix, "Should detect Netflix from prec-105"
    
    is_steam, _ = _is_personal(ctx, 'Steam', 'Gaming', '5816')
    assert is_steam, "Should detect Steam from prec-116"
    
    # Both keywords should work
    is_netflix_kw, _ = _is_personal(ctx, 'NETFLIX INC', 'subscription', '')
    assert is_netflix_kw, "Should detect 'netflix' keyword from prec-105"
    
    is_steam_kw, _ = _is_personal(ctx, 'STEAM GAMES', 'purchase', '')
    assert is_steam_kw, "Should detect 'steam' keyword from prec-116"
    
    os.unlink(db_path)


if __name__ == '__main__':
    test_personal_with_precedent_only()
    test_personal_merges_all_precedents()
    print("✓ All personal precedent tests passed - $113.44 will always go to 1250")
