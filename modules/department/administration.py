from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from fusion_auth.client import get_client
from modules.department import permissions as p
from modules.department.domain import OFFICIAL_TRANSITIONS
from modules.department.models import (
    DepartmentDetails,
    DepartmentProposal,
    LabResource,
    TimetableSlot,
)
from modules.department.roles import ADMIN_DEPARTMENTS, HOD_DEPARTMENTS, office_lane
from modules.department.services import _department, _next_state

TIMETABLE_OVERLAP_CONSTRAINTS = {
    "dept_timetable_room_overlap",
    "dept_timetable_instructor_overlap",
    "dept_timetable_cohort_overlap",
}


@transaction.atomic
def save_lab(*, actor, name, details):
    department = _department(actor, p.UPDATE_LABS, ADMIN_DEPARTMENTS)
    lab, _ = LabResource.objects.update_or_create(
        department=department, name=name, defaults={"details": details},
    )
    return lab


def _lock_department(department):
    row, _ = DepartmentDetails.objects.get_or_create(department=department)
    return DepartmentDetails.objects.select_for_update().get(pk=row.pk)


def _is_timetable_overlap(error):
    diag = getattr(error.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None) in TIMETABLE_OVERLAP_CONSTRAINTS


def _check_instructors(department, instructor_ids):
    instructors = get_client().get_users(sorted(instructor_ids))
    if any(
        not (user and user.is_active and user.kind == "faculty"
             and user.department.strip() == department)
        for user in (instructors.get(user_id) for user_id in instructor_ids)
    ):
        raise NotFoundError("Choose an active instructor in your department.")


def upload_timetable(*, actor, slots):
    department = _department(actor, p.UPDATE_TIMETABLE, ADMIN_DEPARTMENTS)
    _check_instructors(department, {slot["instructor_id"] for slot in slots})
    try:
        with transaction.atomic():
            _lock_department(department)
            return TimetableSlot.objects.bulk_create([
                TimetableSlot(department=department, **slot) for slot in slots
            ])
    except IntegrityError as exc:
        if not _is_timetable_overlap(exc):
            raise
        raise ConflictError(
            "Choose times that do not overlap for the room, instructor or cohort.",
        ) from exc


def replace_timetable_slot(*, actor, slot_id, values):
    department = _department(actor, p.UPDATE_TIMETABLE, ADMIN_DEPARTMENTS)
    _check_instructors(department, {values["instructor_id"]})
    rows = TimetableSlot.objects.select_for_update().filter(pk=slot_id, department=department)
    try:
        with transaction.atomic():
            _lock_department(department)
            slot = rows.first()
            if slot is None:
                raise NotFoundError()
            for field, value in values.items():
                setattr(slot, field, value)
            slot.save(update_fields=values.keys())
            return slot
    except IntegrityError as exc:
        if not _is_timetable_overlap(exc):
            raise
        raise ConflictError(
            "Choose times that do not overlap for the room, instructor or cohort.",
        ) from exc


@transaction.atomic
def update_general_details(*, actor, general_information):
    department = _department(actor, p.UPDATE_DETAILS, ADMIN_DEPARTMENTS)
    row = _lock_department(department)
    row.general_information = general_information
    row.save(update_fields=["general_information"])
    return row


@transaction.atomic
def propose_official_details(*, actor, field, value):
    department = _department(actor, p.PROPOSE_DETAILS, ADMIN_DEPARTMENTS)
    row = _lock_department(department)
    if field not in DepartmentProposal.Field.values:
        raise ConflictError("Choose Official name or Core policies for an official change.")
    if DepartmentProposal.objects.filter(department=row, field=field, status="pending").exists():
        raise ConflictError(
            "Wait for the pending change to this field to be decided before submitting another."
        )
    return DepartmentProposal.objects.create(department=row, field=field, value=value,
                                             proposed_by_id=actor.user_id)


@transaction.atomic
def decide_official_details(*, actor, proposal_id, action):
    department = _department(actor, p.APPROVE_DETAILS, HOD_DEPARTMENTS)
    row = DepartmentDetails.objects.select_for_update().filter(department=department).first()
    if row is None:
        raise NotFoundError()
    proposal = DepartmentProposal.objects.filter(pk=proposal_id, department=row).first()
    if proposal is None:
        raise NotFoundError()
    proposal.status = _next_state(OFFICIAL_TRANSITIONS, proposal.status, action, office_lane(actor))
    if proposal.status == "approved":
        if proposal.field not in DepartmentProposal.Field.values:
            raise ConflictError("Choose Official name or Core policies for an official change.")
        setattr(row, proposal.field, proposal.value)
        row.save(update_fields=[proposal.field])
    proposal.decided_at = timezone.now()
    proposal.decided_by_id = actor.user_id
    proposal.save(update_fields=["status", "decided_at", "decided_by_id"])
    return proposal
