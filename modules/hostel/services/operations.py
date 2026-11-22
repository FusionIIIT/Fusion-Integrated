"""Services for hostel operations.
Includes leave, complaint, attendance, fine, and notice management.
"""
from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.hostel.domain.policies import (
    PolicyViolationError,
    validate_fine_amount,
    validate_notice_topic,
)
from modules.hostel.domain.state_machines import (
    InvalidTransitionError,
    apply_complaint_transition,
    apply_leave_transition,
)
from modules.hostel.models import (
    Hostel,
    HostelComplaint,
    HostelFine,
    HostelNotice,
    LeaveRequest,
    StudentAttendance,
)

# Declared permissions enforced in services and endpoints
PERM_ATTENDANCE_VIEW = "hostel.attendance.view"
PERM_COMPLAINT_CREATE = "hostel.complaint.create"
PERM_FINE_CREATE = "hostel.fine.create"
PERM_INVENTORY_MANAGE = "hostel.inventory.manage"
PERM_LEAVE_CREATE = "hostel.leave.create"
PERM_NOTICE_PUBLISH = "hostel.notice.publish"
PERM_REPORT_VIEW = "hostel.report.view"
PERM_SECURITY_MANAGE = "hostel.security.manage"


@transaction.atomic
def submit_leave_request(
    user_id: int, hostel_id: int, start_date, end_date, reason: str
) -> LeaveRequest:
    try:
        hostel = Hostel.objects.get(id=hostel_id, is_active=True)
    except Hostel.DoesNotExist as err:
        raise NotFoundError(
            "The requested hostel does not exist or is inactive.",
            code="hostel_not_found",
        ) from err

    return LeaveRequest.objects.create(
        user_id=user_id,
        hostel=hostel,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status="PENDING",
    )


@transaction.atomic
def process_leave_decision(
    leave_id: int, event: str, role: str, action_by_user_id: int, remarks: str = ""
) -> LeaveRequest:
    try:
        leave = LeaveRequest.objects.select_for_update().get(id=leave_id)
    except LeaveRequest.DoesNotExist as err:
        raise NotFoundError("Leave request not found.", code="leave_not_found") from err

    try:
        new_state = apply_leave_transition(leave.status, event, role)
    except InvalidTransitionError as err:
        raise ConflictError(str(err), code="invalid_transition") from err

    leave.status = new_state
    leave.action_by_user_id = action_by_user_id
    leave.action_remarks = remarks
    leave.save()
    return leave


@transaction.atomic
def submit_complaint(
    user_id: int, hostel_id: int, category: str, title: str, description: str
) -> HostelComplaint:
    try:
        hostel = Hostel.objects.get(id=hostel_id, is_active=True)
    except Hostel.DoesNotExist as err:
        raise NotFoundError("Hostel not found.", code="hostel_not_found") from err

    return HostelComplaint.objects.create(
        user_id=user_id,
        hostel=hostel,
        category=category,
        title=title,
        description=description,
        status="LOGGED",
    )


@transaction.atomic
def process_complaint_decision(
    complaint_id: int, event: str, role: str, remarks: str = ""
) -> HostelComplaint:
    try:
        complaint = HostelComplaint.objects.select_for_update().get(id=complaint_id)
    except HostelComplaint.DoesNotExist as err:
        raise NotFoundError("Complaint not found.", code="complaint_not_found") from err

    try:
        new_state = apply_complaint_transition(complaint.status, event, role)
    except InvalidTransitionError as err:
        raise ConflictError(str(err), code="invalid_transition") from err

    complaint.status = new_state
    if remarks:
        complaint.resolution_remarks = remarks
    complaint.save()
    return complaint


@transaction.atomic
def record_student_attendance(
    user_id: int, hostel_id: int, date, status: str, marked_by_user_id: int
) -> StudentAttendance:
    attendance, _ = StudentAttendance.objects.update_or_create(
        user_id=user_id,
        date=date,
        defaults={
            "hostel_id": hostel_id,
            "status": status,
            "marked_by_user_id": marked_by_user_id,
        },
    )
    return attendance


@transaction.atomic
def impose_fine(
    user_id: int, hostel_id: int, amount: float, reason: str, imposed_by_user_id: int
) -> HostelFine:
    try:
        validate_fine_amount(amount)
    except PolicyViolationError as err:
        raise BadRequestError(str(err), code="invalid_fine_amount") from err

    return HostelFine.objects.create(
        user_id=user_id,
        hostel_id=hostel_id,
        amount=amount,
        reason=reason,
        status="IMPOSED",
        imposed_by_user_id=imposed_by_user_id,
    )


@transaction.atomic
def publish_notice(
    hostel_id: int,
    title: str,
    body: str,
    topic: str,
    published_by_user_id: int,
    published_by_role: str,
) -> HostelNotice:
    try:
        validate_notice_topic(topic)
    except PolicyViolationError as err:
        raise BadRequestError(str(err), code="invalid_topic") from err

    return HostelNotice.objects.create(
        hostel_id=hostel_id,
        title=title,
        body=body,
        topic=topic,
        published_by_user_id=published_by_user_id,
        published_by_role=published_by_role,
    )
