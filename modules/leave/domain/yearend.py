"""Year-end outcomes per category (BR-EL-002 to 009, EL-UC-020)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from modules.leave.domain import categories as cat

LAPSE = "lapse"
CARRY_OUT = "carry_out"
CARRY_IN = "carry_in"
CONVERT_OUT = "convert_out"
CONVERT_IN = "convert_in"


@dataclass(frozen=True)
class Movement:
    entry_type: str
    category: str
    delta: Decimal
    #: The year this entry is booked in: the closing year, or the next for an opening entry.
    next_year: bool = False


def outcome(balances: dict[str, Decimal]) -> list[Movement]:
    """Close every category of one account; the closing year sums to zero afterwards."""
    moves: list[Movement] = []
    converted = Decimal(0)
    for code in cat.ALL:
        balance = balances.get(code, Decimal(0))
        if balance == 0:
            continue
        if balance < 0:
            raise ValueError(f"{code} closes the year negative ({balance}); refusing to guess.")
        rule = cat.get(code).year_end
        if rule == cat.LAPSE:
            moves.append(Movement(LAPSE, code, -balance))
        elif rule == cat.CARRY:
            moves.append(Movement(CARRY_OUT, code, -balance))
            moves.append(Movement(CARRY_IN, code, balance, next_year=True))
        else:
            moves.append(Movement(CONVERT_OUT, code, -balance))
            converted += balance / cat.VL_PER_EL
    if converted:
        moves.append(Movement(CONVERT_IN, cat.EL, converted.quantize(Decimal("0.01")),
                              next_year=True))
    return moves
