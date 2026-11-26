from typing import Any

import django.db.transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.department.domain.timetable import find_conflicts
from modules.department.models import Department
from modules.department.models.timetable import AcademicProgram as AcademicProgramModel
from modules.department.models.timetable import LabResource as LabResourceModel
from modules.department.models.timetable import TimetableSlot as TimetableSlotModel
from modules.department.selectors.scoping import department_ids_for_role
from modules.department.services.authz import require


def _held(actor, department_id: int) -> Department:
    """Locks and returns the Department if actor has dept_admin role for it."""
    if department_id not in department_ids_for_role(actor, "dept_admin"):
        raise NotFoundError("Department not held by actor as dept_admin")

    with django.db.transaction.atomic():
        department = Department.objects.select_for_update().get(pk=department_id)
        return department

def _slot_dict(slot: TimetableSlotModel) -> dict[str, Any]:
    """Returns a plain dict representation of a TimetableSlotModel instance."""
    return slot.__dict__

def upload_slots(*, actor, department_id: int, slots: list[dict[str, Any]]):
    """Uploads new timetable slots after conflict checking."""
    require(actor, "department.timetable.create")

    with django.db.transaction.atomic():
        try:
            department = _held(actor, department_id)
        except NotFoundError as e:
            raise e

        # Fetch existing slots for conflict checking
        existing_slots_queryset = TimetableSlotModel.objects.filter(department=department)
        existing_slots = [_slot_dict(slot) for slot in existing_slots_queryset]

        # Prepare candidates (ensure they have an ID if they are being created, though find_conflicts handles this)
        # We assume incoming slots are new and don't have IDs yet.
        candidates = slots

        conflicts = find_conflicts(candidates, existing_slots)

        if conflicts:
            # Raise ConflictError with a sentence and code timetable_conflict
            raise ConflictError("Timetable slot conflicts found.", code="timetable_conflict")

        # Create all slots
        created_slots = []
        for slot_data in slots:
            slot = TimetableSlotModel.objects.create(department=department, **slot_data)
            created_slots.append(_slot_dict(slot))

        return created_slots

def update_slot(*, actor, slot_id: int, **changes):
    """Updates an existing timetable slot after conflict checking."""
    require(actor, "department.timetable.update")

    with django.db.transaction.atomic():
        try:
            # 1. Find the slot and its department, locking the department
            slot = TimetableSlotModel.objects.select_for_update().get(pk=slot_id)
            department = _held(actor, slot.department_id)
        except TimetableSlotModel.DoesNotExist:
            raise NotFoundError("Timetable slot not found")
        except NotFoundError as e:
            raise e

        # 2. Build the changed slot dict
        current_slot_dict = _slot_dict(slot)
        updated_slot_data = {**current_slot_dict, **changes}

        # Remove ID and timestamps before checking conflicts, as they are immutable for this check
        updated_slot_data.pop('id', None)
        updated_slot_data.pop('created_at', None)
        updated_slot_data.pop('updated_at', None)

        # 3. Check against other slots in the department
        existing_slots_queryset = TimetableSlotModel.objects.filter(
            department=department
        ).exclude(pk=slot_id)
        existing_slots = [_slot_dict(slot) for slot in existing_slots_queryset]

        candidates = [updated_slot_data]

        conflicts = find_conflicts(candidates, existing_slots)

        if conflicts:
            raise ConflictError("Update conflicts with existing slots.", code="timetable_conflict")

        # 4. Save and return
        slot.title = updated_slot_data.get('title', slot.title)
        slot.weekday = updated_slot_data.get('weekday', slot.weekday)
        slot.start_time = updated_slot_data.get('start_time', slot.start_time)
        slot.end_time = updated_slot_data.get('end_time', slot.end_time)
        slot.room = updated_slot_data.get('room', slot.room)
        slot.faculty_user_id = updated_slot_data.get('faculty_user_id', slot.faculty_user_id)
        slot.programme = updated_slot_data.get('programme', slot.programme)
        slot.batch_year = updated_slot_data.get('batch_year', slot.batch_year)

        slot.save()
        return slot

def delete_slot(*, actor, slot_id: int):
    """Deletes a timetable slot."""
    require(actor, "department.timetable.delete")

    with django.db.transaction.atomic():
        try:
            slot = TimetableSlotModel.objects.select_for_update().get(pk=slot_id)
            department = _held(actor, slot.department_id)
        except TimetableSlotModel.DoesNotExist:
            raise NotFoundError("Timetable slot not found")
        except NotFoundError as e:
            raise e

        slot.delete()
        return {"message": "Slot deleted successfully"}

def save_lab(*, actor, department_id: int = None, lab_id: int = None, **fields):
    """Creates or updates a LabResource within a department."""
    require(actor, "department.lab.update")

    with django.db.transaction.atomic():
        try:
            if department_id is not None:
                department = _held(actor, department_id)
            else:
                # If department_id is None, we must find the department the actor belongs to,
                # but the spec implies we should use held departments if department_id is provided.
                # If not provided, we assume the actor's primary department context is used,
                # but since we don't have a direct way to get the actor's department without context,
                # we rely on department_id being present or raise if it's critical.
                # Following the pattern, if department_id is None, we cannot lock a specific department.
                # We'll assume department_id must be provided for locking/context.
                raise BadRequestError("Department ID must be provided to save a lab resource.")

            if lab_id is not None:
                # Update existing lab
                lab_resource = LabResourceModel.objects.select_for_update().get(pk=lab_id)

                # Ensure the lab belongs to the department context if it's an update
                if lab_resource.department_id != department_id:
                    raise NotFoundError("Lab resource does not belong to the specified department.")

                for key, value in fields.items():
                    setattr(lab_resource, key, value)
                lab_resource.save()
                return lab_resource
            # Create new lab
            lab_resource = LabResourceModel.objects.create(
                department=department,
                **fields
            )
            return lab_resource
        except LabResourceModel.DoesNotExist:
            raise NotFoundError("Lab resource not found")
        except NotFoundError as e:
            raise e

def save_program(*, actor, department_id: int = None, program_id: int = None, **fields):
    """Creates or updates an AcademicProgram within a department."""
    require(actor, "department.program.update")

    with django.db.transaction.atomic():
        try:
            if department_id is not None:
                department = _held(actor, department_id)
            else:
                raise BadRequestError("Department ID must be provided to save an academic program.")

            if program_id is not None:
                # Update existing program
                program = AcademicProgramModel.objects.select_for_update().get(pk=program_id)

                # Ensure the program belongs to the department context if it's an update
                if program.department_id != department_id:
                    raise NotFoundError("Academic program does not belong to the specified department.")

                for key, value in fields.items():
                    setattr(program, key, value)
                program.save()
                return program
            # Create new program
            program = AcademicProgramModel.objects.create(
                department=department,
                **fields
            )
            return program
        except AcademicProgramModel.DoesNotExist:
            raise NotFoundError("Academic program not found")
        except NotFoundError as e:
            raise e
