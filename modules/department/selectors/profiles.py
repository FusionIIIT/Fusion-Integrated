"""Profiles at the viewer's tier (BR-DEPT-019); identity from directory in one batched call."""

from __future__ import annotations

from collections.abc import Sequence

from modules.department.domain.roles import FACULTY, ActorContext
from modules.department.domain.rules import TIER_FIELDS, tier_for
from modules.department.models import Department, ProfileRecord, TimetableSlot
from modules.department.selectors.actors import current_holders
from modules.directory import contracts as directory


def _full_row(record: ProfileRecord, user) -> dict:
    return {
        "id": record.pk,
        "kind": record.kind,
        "user_id": record.user_id,
        "username": getattr(user, "username", ""),
        "display_name": getattr(user, "display_name", "") or record.display_name,
        "programme": getattr(user, "programme", ""),
        "department": record.department.code,
        "discipline": getattr(user, "discipline", ""),
        "batch_year": getattr(user, "batch_year", None),
        "email": getattr(user, "email", ""),
        "office": record.office,
        "research_interests": record.research_interests,
        "bio": record.bio,
        "graduation_year": record.graduation_year,
        "current_position": record.current_position,
        "is_active": record.is_active,
    }


def taught_cohorts(ctx: ActorContext) -> set[tuple[str, int]]:
    """Q2: the (programme, batch year) pairs of the slots this Faculty member teaches here."""
    if ctx.role != FACULTY or ctx.user_id is None or ctx.department is None:
        return set()
    rows = (
        TimetableSlot.objects.filter(
            department__code=ctx.department, instructor_user_id=ctx.user_id
        )
        .exclude(programme="")
        .exclude(batch_year=None)
        .values_list("programme", "batch_year")
        .distinct()
    )
    return set(rows)


def _in_course(ctx: ActorContext, record: ProfileRecord, user, cohorts) -> bool:
    if not cohorts or record.kind != "student" or user is None:
        return False
    if record.department.code != ctx.department:
        return False
    return (getattr(user, "programme", ""), getattr(user, "batch_year", None)) in cohorts


def profile_views(ctx: ActorContext, records: Sequence[ProfileRecord]) -> list[dict]:
    users = directory.get_users([r.user_id for r in records if r.user_id is not None])
    cohorts = taught_cohorts(ctx)
    out = []
    for record in records:
        tier = tier_for(
            ctx.role, record.kind, _in_course(ctx, record, users.get(record.user_id), cohorts)
        )
        if tier is None:
            continue
        row = _full_row(record, users.get(record.user_id))
        out.append({"tier": tier, **{k: row[k] for k in TIER_FIELDS[tier]}})
    return out


def headships(departments: Sequence[Department]) -> dict[int, dict | None]:
    """AFR-DEPT-053: headship is the HOD tenure in effect now, never a stored field."""
    holders = current_holders([d.pk for d in departments], "hod")
    users = directory.get_users(list(holders.values()))
    out: dict[int, dict | None] = {}
    for d in departments:
        uid = holders.get(d.pk)
        if uid is None:
            out[d.pk] = None
            continue
        user = users.get(uid)
        out[d.pk] = {
            "user_id": uid,
            "display_name": getattr(user, "display_name", "") or f"User {uid}",
        }
    return out
