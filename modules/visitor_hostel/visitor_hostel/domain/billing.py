"""Bill arithmetic (BR-VH-033..035). Lines carry their own rate, so a bill
never re-reads a tariff after it is generated (BR-VH-024, BR-VH-037)."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from modules.visitor_hostel.domain import tariffs

ROOM = "room"
MEAL = "meal"
CANCELLATION = "cancellation"
LINE_KINDS = (ROOM, MEAL, CANCELLATION)

TWO_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class Line:
    kind: str
    description: str
    quantity: int
    unit_rate: Decimal
    amount: Decimal
    tariff_ref: int | None = None


@dataclass(frozen=True)
class Totals:
    room: Decimal
    meal: Decimal
    cancellation: Decimal

    @property
    def total(self) -> Decimal:
        return self.room + self.meal + self.cancellation


def money(value) -> Decimal:
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def nights(check_in: date, check_out: date) -> int:
    """Nights charged. A same-day stay is still one day's rent."""
    return max(1, (check_out - check_in).days)


def room_lines(allotments: Iterable[tuple[str, str]], *, category: str,
               check_in: date, check_out: date,
               rates: Iterable[tariffs.TariffRow]) -> list[Line]:
    """One line per allotted room, at the tariff in force on check-in day."""
    rates = list(rates)
    n = nights(check_in, check_out)
    out = []
    for room_number, occupancy in allotments:
        row = tariffs.select(rates, key=tariffs.room_key(category, occupancy),
                             on=check_in)
        out.append(Line(ROOM, f"Room {room_number} ({occupancy}, category "
                              f"{category}) x {n} day(s)",
                        n, money(row.rate), money(row.rate * n), row.id))
    return out


def meal_lines(meals: Iterable[tuple[date, str, int]],
               rates: Iterable[tariffs.TariffRow]) -> list[Line]:
    """One line per (item, date), each at the rate in force that day."""
    rates = list(rates)
    out = []
    for meal_date, item, quantity in sorted(meals):
        row = tariffs.select(rates, key=tariffs.meal_key(item), on=meal_date)
        out.append(Line(MEAL, f"{item.replace('_', ' ').title()} on "
                              f"{meal_date.isoformat()}",
                        quantity, money(row.rate), money(row.rate * quantity), row.id))
    return out


def one_day_rent(occupancies: Iterable[str], *, category: str, on: date,
                 rates: Iterable[tariffs.TariffRow]) -> Decimal:
    """The base the cancellation schedule takes a percentage of."""
    rates = list(rates)
    return money(sum(
        (tariffs.select(rates, key=tariffs.room_key(category, occ), on=on).rate
         for occ in occupancies), Decimal("0")))


def totals(lines: Iterable[Line]) -> Totals:
    by = {k: Decimal("0.00") for k in LINE_KINDS}
    for line in lines:
        by[line.kind] += line.amount
    return Totals(money(by[ROOM]), money(by[MEAL]), money(by[CANCELLATION]))
