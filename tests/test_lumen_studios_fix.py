"""Test that Lumen Studios doesn't incorrectly map to Lumen Crew LLC."""
import pytest
from jarvis.agent.session import Session


def test_lumen_studios_needs_info():
    """Test that 'Lumen Studios' is not matched to 'Lumen Crew LLC'.
    
    The 4th pass in _match_vendor was too loose and matched any 5+ letter token.
    'Lumen' (6 letters) matched 'Lumen Crew LLC', giving wrong phone number.
    
    With the 4th pass removed, 'Lumen Studios' should create NEEDS_INFO.
    """
    s = Session(301, fresh=True, quiet=True)
    s.run_all(controller=True)
    
    # Test via free text parsing
    result = s.inject(text="Jordan bought something at Lumen Studios for $96.40 on Oct 15")
    items = result.get('items', [])
    
    assert items, "Should create at least one item"
    
    # Check that it's asking for info about the vendor
    has_needs_info = any(
        item.get('state') == 'NEEDS_INFO' and 
        ('lumen' in item.get('title', '').lower() or 'vendor' in item.get('question', '').lower())
        for item in items
    )
    
    assert has_needs_info, f"Should create NEEDS_INFO for unknown 'Lumen Studios', got: {items}"


def test_lumen_crew_still_works():
    """Test that 'Lumen Crew' or 'Lumen Crew LLC' still matches correctly."""
    s = Session(302, fresh=True, quiet=True)
    s.run_all(controller=True)
    
    # Exact name should work
    result = s.inject(text="Jordan bought something at Lumen Crew LLC for $96.40 on Oct 15")
    items = result.get('items', [])
    
    assert items, "Should create items for Lumen Crew LLC"
    
    # Should not need info for exact match
    needs_info_states = [item.get('state') for item in items if item.get('state') == 'NEEDS_INFO']
    
    # If there's NEEDS_INFO, it shouldn't be about vendor identification
    for item in items:
        if item.get('state') == 'NEEDS_INFO':
            question = item.get('question', '').lower()
            assert 'which vendor' not in question, f"Should not ask about vendor for exact match: {question}"
