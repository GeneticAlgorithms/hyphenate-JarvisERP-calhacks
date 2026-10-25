"""Money is always integer cents internally. Decimal only at the edges."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def to_cents(value) -> int:
    if isinstance(value, int):
        return value
    d = Decimal(str(value).replace(",", "").replace("$", "").strip() or "0")
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def fmt(cents: int, currency: str = "USD", sign: bool = False) -> str:
    neg = cents < 0
    a = abs(cents)
    s = f"{a // 100:,}.{a % 100:02d}"
    sym = {"USD": "$", "EUR": "€"}.get(currency, "")
    out = f"{sym}{s}" if sym else f"{s} {currency}"
    if neg:
        return f"-{out}"
    return f"+{out}" if sign else out


def plain(cents: int) -> str:
    """'1234.50' style, signed, no thousands separator (for CSV exports)."""
    neg = cents < 0
    a = abs(cents)
    return f"{'-' if neg else ''}{a // 100}.{a % 100:02d}"


def mul_rate(cents: int, rate: float | Decimal) -> int:
    return int((Decimal(cents) * Decimal(str(rate))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
