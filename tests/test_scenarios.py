"""Judge-style scenarios injected into a closed world (not part of the generator's planted set)."""
import pytest

from jarvis.agent import personas
from jarvis.agent.session import Session


@pytest.fixture()
def s():
    sess = Session(7, fresh=True, quiet=True)
    sess.run_all(controller=True)
    return sess


def kinds(r):
    return {i["kind"] for i in r["items"]}


def test_unknown_debit_asks(s):
    r = s.inject(template="unknown_debit", params={"amount": 742.18, "description": "SQ *MOONLIGHT GEAR CO",
                                                    "date": "2026-09-29"})
    assert r["items"] and r["items"][0]["state"] == "NEEDS_INFO"


def test_personal_purchase_reclassed(s):
    r = s.inject(template="personal_card", params={"merchant": "SEPHORA #2210", "amount": 96.40,
                                                    "cardholder": "J. Ortiz", "date": "2026-09-27"})
    assert "reclass" in kinds(r)


def test_duplicate_bill_caught(s):
    r = s.inject(template="duplicate_bill", params={"vendor": "Anthropic", "amount": 96.00, "date": "2026-09-14"})
    assert "duplicate" in kinds(r)


def test_paypal_bundle_split(s):
    r = s.inject(template="paypal_bundle")
    it = r["items"][0]
    assert it["kind"] == "paypal_split", it


def test_free_text_parsing(s):
    r = s.inject(text="Unknown $129.99 debit 'ACME LASER SUPPLY' showed up on the 29th")
    assert r["template"] == "unknown_debit"
    assert r["items"][0]["state"] == "NEEDS_INFO"
