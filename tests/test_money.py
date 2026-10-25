"""Unit tests for money.py to_cents() and injector _dollars_to_cents()."""
import pytest
from jarvis.money import to_cents
from jarvis.agent.injector import _dollars_to_cents


def test_to_cents_with_float():
    """to_cents with float (dollars) should return cents."""
    assert to_cents(96.0) == 9600
    assert to_cents(1.50) == 150
    assert to_cents(1234.56) == 123456


def test_to_cents_with_int_returns_as_is():
    """to_cents with int returns it as-is (assumes already cents)."""
    # This is the current behavior - int is assumed to be cents
    assert to_cents(96) == 96
    assert to_cents(9600) == 9600


def test_to_cents_with_string():
    """to_cents with string should parse and return cents."""
    assert to_cents("96.40") == 9640
    assert to_cents("$1,234.56") == 123456
    assert to_cents("1234") == 123400


def test_dollars_to_cents_with_int():
    """_dollars_to_cents treats int as dollars, not cents."""
    assert _dollars_to_cents(96) == 9600
    assert _dollars_to_cents(1234) == 123400
    assert _dollars_to_cents(18400) == 1840000


def test_dollars_to_cents_with_float():
    """_dollars_to_cents treats float as dollars."""
    assert _dollars_to_cents(96.0) == 9600
    assert _dollars_to_cents(1234.56) == 123456
    assert _dollars_to_cents(18400.0) == 1840000


def test_dollars_to_cents_with_string():
    """_dollars_to_cents handles string amounts."""
    assert _dollars_to_cents("96") == 9600
    assert _dollars_to_cents("1234.56") == 123456
    assert _dollars_to_cents("$1,234.56") == 123456
