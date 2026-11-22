"""MMS's public surface. Plural by signature; the only thing other modules may import."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class UserBrief:
    user_id: int
    username: str
    display_name: str
    kind: str


def get_users(user_ids: Sequence[int]) -> dict[int, UserBrief]:
    """Batched directory brief for notification recipients and display."""
    from modules.directory import contracts as directory

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = directory.get_users(ids)
    return {uid: UserBrief(uid, r.username, r.display_name, r.kind) for uid, r in rows.items()}


@dataclass(frozen=True)
class SpecialFoodChargeDTO:
    request_id: int
    student_user_id: int
    month: str
    amount: str


def get_special_food_charges(
    student_ids: Sequence[int], month: str
) -> dict[int, list[SpecialFoodChargeDTO]]:
    """Charges for approved special food requests, per student, for a month."""
    ids = {int(i) for i in student_ids if i is not None}
    if not ids:
        return {}
    from modules.mms.models import SpecialFoodCharge

    rows = SpecialFoodCharge.objects.filter(student_user_id__in=ids, month=month).order_by(
        "student_user_id", "-created_at"
    )
    out: dict[int, list[SpecialFoodChargeDTO]] = {uid: [] for uid in ids}
    for row in rows:
        out[row.student_user_id].append(
            SpecialFoodChargeDTO(
                row.request_id, row.student_user_id, str(row.month), str(row.amount)
            )
        )
    return out


@dataclass(frozen=True)
class MenuDayDTO:
    day: str
    meals: dict[str, list[str]]


def get_menu_for_days(days: Sequence[str]) -> dict[str, MenuDayDTO]:
    """Day-wise, meal-wise menu items for a collection of days."""
    if not days:
        return {}
    from modules.mms.models import MenuItem

    rows = MenuItem.objects.filter(day__in=days).order_by("day", "meal")
    out: dict[str, MenuDayDTO] = {}
    for row in rows:
        d_str = str(row.day)
        if d_str not in out:
            out[d_str] = MenuDayDTO(d_str, {})
        out[d_str].meals.setdefault(row.meal, []).append(row.item)
    return out


@dataclass(frozen=True)
class SurveySummaryDTO:
    survey_id: int
    yes: int
    no: int
    default_no: int


def get_vacation_survey_summaries(survey_ids: Sequence[int]) -> dict[int, SurveySummaryDTO]:
    """Yes / No / default-No counts per survey."""
    ids = {int(i) for i in survey_ids if i is not None}
    if not ids:
        return {}
    from django.db.models import Count

    from modules.mms.models import VacationResponse

    rows = (
        VacationResponse.objects.filter(survey__in=ids)
        .values("survey", "response")
        .annotate(n=Count("id"))
    )
    tallies: dict[int, dict[str, int]] = {sid: {"yes": 0, "no": 0, "default_no": 0} for sid in ids}
    for row in rows:
        sid = row["survey"]
        resp = row["response"]
        if sid in tallies and resp in tallies[sid]:
            tallies[sid][resp] += row["n"]
    return {
        sid: SurveySummaryDTO(
            survey_id=sid,
            yes=counts["yes"],
            no=counts["no"],
            default_no=counts["default_no"],
        )
        for sid, counts in tallies.items()
    }
