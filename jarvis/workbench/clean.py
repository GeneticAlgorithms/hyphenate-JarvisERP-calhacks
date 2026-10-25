"""Deterministic cleaning primitives. Each returns (clean_value, note) so the caller can log what changed."""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from pathlib import Path

WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
         "ten": 10, "eleven": 11, "twelve": 12}


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def money(s) -> tuple[int | None, str]:
    """'$1,042.17' -> 104217 ; '(49,306.71)' -> -4930671 ; '1,O42.17' (OCR) -> 104217."""
    if s is None:
        return None, "empty"
    if isinstance(s, (int, float)):
        return int(round(float(s) * 100)), ""
    raw = str(s).strip()
    if not raw:
        return None, "empty"
    t = raw
    notes = []
    if re.search(r"\d[Oo]|[Oo]\d", t):
        t = re.sub(r"(?<=\d)[Oo]|[Oo](?=\d)", "0", t)
        notes.append("OCR letter O→0")
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1]
        notes.append("parentheses→negative")
    if "$" in t:
        t = t.replace("$", "")
        notes.append("stripped $")
    if "," in t:
        t = t.replace(",", "")
        notes.append("stripped thousands separators")
    t = t.strip()
    if t.startswith("-"):
        neg, t = (not neg) if neg else True, t[1:]
    try:
        v = int(round(float(t) * 100))
    except ValueError:
        return None, f"unparseable '{raw}'"
    return (-v if neg else v), ", ".join(notes)


def day(s) -> tuple[str | None, str]:
    raw = str(s or "").strip()
    if not raw:
        return None, "empty"
    for fmt, note in (("%m/%d/%Y", ""), ("%Y-%m-%d", "ISO format normalized"), ("%m/%d/%y", "2-digit year expanded"),
                      ("%d-%b-%Y", "text month normalized")):
        try:
            d = datetime.strptime(raw, fmt).date()
            if fmt == "%m/%d/%Y" and not re.match(r"^\d{2}/\d{2}/\d{4}$", raw):
                note = "zero-padded"
            return d.isoformat(), note
        except ValueError:
            continue
    return None, f"unparseable date '{raw}'"


def hours(s) -> tuple[float | None, str]:
    raw = str(s or "").strip().lower()
    if not raw:
        return None, "blank hours"
    if raw in WORDS:
        return float(WORDS[raw]), f"word '{raw}'→{WORDS[raw]}"
    m = re.match(r"^([\d.]+)\s*(h|hr|hrs|hours)?$", raw)
    if m:
        return float(m.group(1)), (f"unit '{m.group(2)}' stripped" if m.group(2) else "")
    return None, f"unparseable hours '{raw}'"


def yes(s) -> bool:
    return str(s or "").strip().lower() in ("y", "yes", "true", "1", "approved")


def norm_name(s: str) -> str:
    t = re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())
    t = re.sub(r"\b(inc|llc|pbc|corp|corporation|co|ltd|gmbh|b v|bv|the)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def ocr_fix(text: str) -> tuple[str, int]:
    fixed, n = re.subn(r"(?<=\d)O|O(?=\d)", "0", text)
    return fixed, n
