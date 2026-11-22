"""Timetables (UC-DEPT-009), lab resources (UC-DEPT-017) and profile records (UC-DEPT-016)."""

from __future__ import annotations

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError, DomainError
from modules.department.domain import rules
from modules.department.domain.roles import ActorContext, normalise_department
from modules.department.models import LabResource, ProfileRecord, TimetableSlot
from modules.department.selectors import scoping
from modules.department.services.common import get_scoped, own_department, translated
from modules.directory import contracts as directory

SLOT_FIELDS = (
    "kind",
    "programme",
    "batch_year",
    "course_code",
    "day_of_week",
    "starts_at",
    "ends_at",
    "room",
)


def _as_slot(key: str, data: dict) -> rules.Slot:
    return rules.Slot(
        key=key,
        day_of_week=data["day_of_week"],
        starts_at=data["starts_at"],
        ends_at=data["ends_at"],
        room=data.get("room", ""),
        programme=data.get("programme", ""),
        batch_year=data.get("batch_year"),
    )


def _saved(dept, exclude_pk=None) -> list[rules.Slot]:
    qs = TimetableSlot.objects.filter(department=dept)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return [_as_slot(f"saved:{s.pk}", {f: getattr(s, f) for f in SLOT_FIELDS}) for s in qs]


def _check(candidates: list[rules.Slot], saved: list[rules.Slot]) -> None:
    """BR-DEPT-010, AFR-DEPT-031 with Q6: nothing is saved while any clash remains."""
    with translated():
        for slot in candidates:
            rules.validate_slot(slot)
        clashes = rules.find_overlaps(candidates, saved)
        if clashes:
            raise rules.RuleViolation(
                "timetable_conflict",
                "These slots overlap; move them and save again. Nothing was saved.",
                [{"slot": a, "clashes_with": b} for a, b in clashes],
            )


@transaction.atomic
def upload(ctx: ActorContext, slots: list[dict]) -> list[TimetableSlot]:
    """AFR-DEPT-029: the whole batch is saved, or none of it."""
    dept = own_department(ctx, lock=True)
    _check([_as_slot(f"new:{i}", s) for i, s in enumerate(slots)], _saved(dept))
    return [
        TimetableSlot.objects.create(
            department=dept,
            updated_by=ctx.user_id,
            **{f: s.get(f, "" if f in ("programme", "room") else None) for f in SLOT_FIELDS},
        )
        for s in slots
    ]


@transaction.atomic
def modify(ctx: ActorContext, slot_id: int, **changes) -> TimetableSlot:
    """AFR-DEPT-030."""
    own_department(ctx, lock=True)
    slot = get_scoped(scoping.timetable_for(ctx), slot_id, lock=True, what="timetable slot")
    merged = {f: changes.get(f, getattr(slot, f)) for f in SLOT_FIELDS}
    _check([_as_slot(f"saved:{slot.pk}", merged)], _saved(slot.department, exclude_pk=slot.pk))
    for field, value in merged.items():
        setattr(slot, field, value)
    slot.updated_by = ctx.user_id
    slot.save()
    return slot


@transaction.atomic
def remove(ctx: ActorContext, slot_id: int) -> None:
    get_scoped(scoping.timetable_for(ctx), slot_id, lock=True, what="timetable slot").delete()


@transaction.atomic
def save_lab(ctx: ActorContext, lab_id: int | None = None, **fields) -> LabResource:
    """AFR-DEPT-034."""
    if lab_id is None:
        lab = LabResource(department=own_department(ctx))
    else:
        lab = get_scoped(scoping.lab_resources_for(ctx), lab_id, lock=True, what="lab resource")
    for field, value in fields.items():
        setattr(lab, field, value)
    if not (lab.name or "").strip():
        raise DomainError("Give the lab or resource a name.", code="lab_incomplete")
    lab.updated_by = ctx.user_id
    try:
        with transaction.atomic():
            lab.save()
    except IntegrityError as exc:
        raise ConflictError(
            f"{lab.name} already exists in this department.", code="lab_exists"
        ) from exc
    return lab


@transaction.atomic
def create_profile(
    ctx: ActorContext, *, kind: str, user_id: int | None = None, display_name: str = "", **fields
) -> ProfileRecord:
    """AFR-DEPT-024 with Q8: a login user must belong here; an alumnus may have no login."""
    dept = own_department(ctx)
    if kind != "alumni":
        if user_id is None:
            raise DomainError("Choose the person this profile is for.", code="profile_needs_user")
        user = directory.get_users([user_id]).get(user_id)
        home = None
        if user is not None:
            home = normalise_department(user.discipline if kind == "student" else user.department)
        if user is None or user.kind != kind or home != dept.code:
            raise DomainError(
                f"That person is not a {kind} of {dept.code}.", code="not_in_department"
            )
        display_name = display_name or user.display_name
    if not (display_name or "").strip():
        raise DomainError("Give the profile a name.", code="profile_incomplete")
    try:
        with transaction.atomic():
            return ProfileRecord.objects.create(
                department=dept,
                kind=kind,
                user_id=user_id,
                display_name=display_name.strip(),
                updated_by=ctx.user_id,
                **fields,
            )
    except IntegrityError as exc:
        raise ConflictError(
            "This person already has a profile in this department; edit it instead.",
            code="profile_exists",
        ) from exc


@transaction.atomic
def update_profile(ctx: ActorContext, profile_id: int, **fields) -> ProfileRecord:
    record = get_scoped(scoping.profiles_for(ctx), profile_id, lock=True, what="profile")
    if "display_name" in fields and not (fields["display_name"] or "").strip():
        raise DomainError("A profile needs a name.", code="profile_incomplete")
    for field, value in fields.items():
        setattr(record, field, value)
    record.updated_by = ctx.user_id
    record.save()
    return record
