"""Test that duplicate_bill handles inexact vendor names gracefully."""
import pytest
from jarvis.agent.session import Session


def test_duplicate_bill_exact_vendor():
    """Test duplicate_bill with exact vendor name works."""
    s = Session(401, fresh=True, quiet=True)
    s.run_all(controller=True)
    
    # Use exact vendor name from bible
    result = s.inject(template='duplicate_bill', params={
        'vendor': 'Anthropic',
        'amount': 500,
        'date': '2026-10-15'
    })
    
    items = result.get('items', [])
    assert items, "Should create items for exact vendor match"


def test_duplicate_bill_inexact_vendor_needs_info():
    """Test that duplicate_bill with unknown vendor name (e.g., 'SparkPost') creates NEEDS_INFO.
    
    Previously crashed with TypeError at injector.py:620 because db.one() returned None
    and code tried to access ["vendor_id"] on None.
    
    Now should use _match_vendor and fall back to NEEDS_INFO.
    """
    s = Session(402, fresh=True, quiet=True)
    s.run_all(controller=True)
    
    # 'SparkPost' is not in the vendor master
    result = s.inject(template='duplicate_bill', params={
        'vendor': 'SparkPost',
        'amount': 500,
        'date': '2026-10-15'
    })
    
    items = result.get('items', [])
    assert items, "Should create at least one item"
    
    # Should create NEEDS_INFO asking about vendor
    needs_info_item = next((item for item in items if item.get('state') == 'NEEDS_INFO'), None)
    assert needs_info_item, f"Should create NEEDS_INFO for unknown vendor, got: {items}"
    
    # Check that it mentions the vendor in title or rationale
    title = needs_info_item.get('title', '').lower()
    rationale = needs_info_item.get('rationale', '').lower()
    assert ('vendor' in title or 'vendor' in rationale) and 'sparkpost' in (title + rationale), \
        f"Should mention vendor SparkPost, got title: {title}, rationale: {rationale}"


def test_duplicate_bill_nonexistent_vendor():
    """Test that duplicate_bill with completely unknown vendor creates NEEDS_INFO."""
    s = Session(403, fresh=True, quiet=True)
    s.run_all(controller=True)
    
    result = s.inject(template='duplicate_bill', params={
        'vendor': 'UnknownVendorXYZ',
        'amount': 500,
        'date': '2026-10-15'
    })
    
    items = result.get('items', [])
    assert items, "Should create at least one item"
    
    # Should create NEEDS_INFO
    needs_info_item = next((item for item in items if item.get('state') == 'NEEDS_INFO'), None)
    assert needs_info_item, f"Should create NEEDS_INFO for unknown vendor, got: {items}"
    
    title = needs_info_item.get('title', '').lower()
    assert 'unknownvendorxyz' in title or 'vendor' in title, \
        f"Should mention the unknown vendor, got title: {title}"
