from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.department import permissions as p
from modules.department.domain import OFFICIAL_TRANSITIONS
from modules.department.models import (
    DepartmentDetails,
    DepartmentProposal,
    LabResource,
    TimetableSlot,
)
from modules.department.roles import ADMIN_DEPARTMENTS, HOD_DEPARTMENTS
from modules.department.services import _department, _next_state


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


def _assert_slot_available(department, slot, current_id=None):
    overlapping = TimetableSlot.objects.filter(
        Q(room__iexact=slot["room"]) | Q(instructor_id=slot["instructor_id"])
        | Q(programme=slot["programme"], batch_year=slot["batch_year"]),
        department=department, term=slot["term"], day=slot["day"],
        starts_at__lt=slot["ends_at"], ends_at__gt=slot["starts_at"],
    ).exclude(pk=current_id)
    if overlapping.exists():
        raise ConflictError("This slot overlaps another slot for its room, instructor or cohort.")


@transaction.atomic
def upload_timetable(*, actor, slots):
    department = _department(actor, p.UPDATE_TIMETABLE, ADMIN_DEPARTMENTS)
    _lock_department(department)
    saved = []
    for slot in slots:
        _assert_slot_available(department, slot)
        saved.append(TimetableSlot.objects.create(department=department, **slot))
    return saved


@transaction.atomic
def replace_timetable_slot(*, actor, slot_id, values):
    department = _department(actor, p.UPDATE_TIMETABLE, ADMIN_DEPARTMENTS)
    _lock_department(department)
    rows = TimetableSlot.objects.filter(pk=slot_id, department=department)
    if not rows.exists():
        raise NotFoundError()
    _assert_slot_available(department, values, current_id=slot_id)
    rows.update(**values)
    return rows.get()


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
        raise ConflictError("This field is outside the official-change workflow.")
    if DepartmentProposal.objects.filter(department=row, field=field, status="pending").exists():
        raise ConflictError("A change to this field is already awaiting review.")
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
    proposal.status = _next_state(OFFICIAL_TRANSITIONS, proposal.status, action)
    if proposal.status == "approved":
        if proposal.field not in DepartmentProposal.Field.values:
            raise ConflictError("This field is outside the official-change workflow.")
        setattr(row, proposal.field, proposal.value)
        row.save(update_fields=[proposal.field])
    proposal.decided_at = timezone.now()
    proposal.decided_by_id = actor.user_id
    proposal.save(update_fields=["status", "decided_at", "decided_by_id"])
    return proposal
