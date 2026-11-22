"""Pure Python validation functions implementing HM Business Rules (BR-HM-...)."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from modules.hostel.domain.enums import ComplaintCategory
from modules.hostel.domain.errors import (
    CapacityExceededError,
    MandatoryFieldMissingError,
    NoticePermissionError,
    ScopeBoundaryError,
    UnauthorizedHostelAccessError,
)


def validate_room_capacity(current_occupancy: int, room_capacity: int, adding: int = 1) -> None:
    """Enforces BR-HM-010:
    The system shall prevent room occupancy from exceeding defined room capacity.
    """
    if current_occupancy + adding > room_capacity:
        raise CapacityExceededError(
            f"Room capacity exceeded: current occupancy {current_occupancy} + {adding} "
            f"exceeds capacity {room_capacity}"
        )


def validate_fine_fields(
    student_user_id: int | None,
    amount: Decimal | float | int | None,
    reason: str | None,
    imposed_date: date | None,
) -> None:
    """Enforces BR-HM-025: Each fine record shall include at least the reason,
    amount, date, and affected student reference.
    """
    if not student_user_id:
        raise MandatoryFieldMissingError("Fine record must reference a student.")
    if amount is None or amount <= 0:
        raise MandatoryFieldMissingError("Fine record must specify a positive amount.")
    if not reason or not reason.strip():
        raise MandatoryFieldMissingError("Fine record must specify a valid reason.")
    if not imposed_date:
        raise MandatoryFieldMissingError("Fine record must specify an imposed date.")


def validate_complaint_data(category: str | None, description: str | None) -> None:
    """Enforces BR-HM-015 and BR-HM-016: Complaint core data capture and hostel-related scope."""
    if not category or not category.strip():
        raise MandatoryFieldMissingError("Complaint category is mandatory.")
    if not description or not description.strip():
        raise MandatoryFieldMissingError("Complaint description is mandatory.")

    valid_categories = {c.value for c in ComplaintCategory}
    if category.strip() not in valid_categories:
        raise ScopeBoundaryError(
            f"Complaint category '{category}' is outside HM hostel-related complaint scope."
        )


def validate_notice_publication(
    permitted_hostel_ids: Sequence[int],
    target_hostel_id: int | None,
    is_super_admin: bool = False,
) -> None:
    """Enforces BR-HM-029: Caretakers and Wardens may publish hostel notices and
    announcements only for hostels assigned to them in HM.
    """
    if is_super_admin:
        return
    if target_hostel_id is None:
        raise NoticePermissionError("Only Super Admin can publish global notices.")
    if target_hostel_id not in permitted_hostel_ids:
        raise NoticePermissionError(
            f"Hostel {target_hostel_id} is not within your assigned hostels."
        )


def validate_caretaker_access(
    caretaker_hostel_ids: Sequence[int],
    target_hostel_id: int,
    is_super_admin: bool = False,
) -> None:
    """Enforces BR-HM-035: Caretaker operations are supported within the assigned
    hostel context maintained in HM.
    """
    if is_super_admin:
        return
    if target_hostel_id not in caretaker_hostel_ids:
        raise UnauthorizedHostelAccessError(
            f"Operation denied: Hostel {target_hostel_id} is not in your assigned caretaker "
            "hostels."
        )


def validate_student_access(
    student_hostel_id: int | None,
    target_hostel_id: int,
) -> None:
    """Enforces BR-HM-002: Student access to hostel-specific data shall be based
    on the student hostel allocation.
    """
    if student_hostel_id != target_hostel_id:
        raise UnauthorizedHostelAccessError(
            f"Student access denied: Target hostel {target_hostel_id} does not match allocated "
            f"hostel {student_hostel_id}."
        )
