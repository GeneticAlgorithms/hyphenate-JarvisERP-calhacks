"""Stable record ids, shared by the generator (answer key anchors) and the sync job.

Chase CSV exports carry no transaction id, so - like the Hyphenate deck suggests -
we derive one: md5(account | posting date | amount | description | occurrence#).
Re-syncing the same file therefore never creates duplicates.
"""
from __future__ import annotations

import hashlib


def bank_id(account: str, post_date_us: str, amount_plain: str, desc: str, occurrence: int) -> str:
    raw = f"{account}|{post_date_us}|{amount_plain}|{desc.strip()}|{occurrence}"
    return "CHK-" + hashlib.md5(raw.encode()).hexdigest()[:10].upper()


def record_id(source: str, src_id: str) -> str:
    return hashlib.md5(f"{source}|{src_id}".encode()).hexdigest()[:16]
