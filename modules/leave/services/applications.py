from django.db import transaction
from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.leave.domain.categories import is_eligible_for_category, CL, RH, SCL, EL, VL, COL
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.state_machine import validate_transition
from modules.leave.models import LeaveApplication, LeaveBalance, LeaveActionHistory, SubstituteRequest, HolidayCalendar, VacationPeriod
from modules.leave.selectors.applications import get_active_overlapping_leaves, get_application_by_id
from modules.leave.selectors.balances import get_or_create_balance
from modules.leave.services.notifications import enqueue as enqueue_notification

@transaction.atomic
def apply_for_leave(user_id: int, category: str, start_date: datetime.date, end_date: datetime.date, purpose: str, half_day_type: str = "full", substitute_user_id: int | None = None, responsibilities: str = "", is_station_leave: bool = False, station_departure_date: datetime.date | None = None, station_arrival_date: datetime.date | None = None, station_destination: str = "", address_during_leave: str = "", is_faculty: bool = False, is_director: bool = False, unit_head_user_id: int | None = None, establishment_user_id: int | None = None, sanctioning_authority_user_id: int | None = None) -> LeaveApplication:
    if not is_eligible_for_category(user_id, category):
        raise BadRequestError("User is not eligible for the selected leave category.")
    
    if category == VL:
        active_periods = VacationPeriod.objects.filter(start_date__lte=start_date, end_date__gte=end_date)
        if not active_periods.exists():
            raise BadRequestError("Vacation period not found for the given dates.")
    
    overlapping_leaves = get_active_overlapping_leaves(user_id, start_date, end_date)
    if overlapping_leaves.exists():
        if category != CL or any(leave.category != CL for leave in overlapping_leaves) or any(leave.start_date != start_date for leave in overlapping_leaves):
            raise ConflictError("Overlapping leaves found. Only CL leaves can overlap with existing leaves on the same date.")
    
    days = calculate_leave_days(start_date, end_date, half_day_type)
    balance = get_or_create_balance(user_id, category)
    if balance.days < days:
        raise BadRequestError("Insufficient leave balance.")
    
    if is_station_leave and not station_destination:
        raise BadRequestError("Station destination is required for station leave.")
    
    if substitute_user_id == user_id:
        raise BadRequestError("Cannot nominate self as substitute.")
    
    initial_status = "substitute_pending" if substitute_user_id else ("approved" if is_director else "under_review")
    
    application = LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        purpose=purpose,
        half_day_type=half_day_type,
        days=days,
        status=initial_status,
        substitute_user_id=substitute_user_id,
        responsibilities=responsibilities,
        is_station_leave=is_station_leave,
        station_departure_date=station_departure_date,
        station_arrival_date=station_arrival_date,
        station_destination=station_destination,
        address_during_leave=address_during_leave,
        is_faculty=is_faculty,
        is_director=is_director,
        unit_head_user_id=unit_head_user_id,
        establishment_user_id=establishment_user_id,
        sanctioning_authority_user_id=sanctioning_authority_user_id
    )
    
    if substitute_user_id:
        SubstituteRequest.objects.create(application=application, user_id=substitute_user_id)
    
    LeaveActionHistory.objects.create(
        application=application,
        action="applied",
        performed_by=user_id,
        reason=purpose
    )
    
    enqueue_notification(user_id, "leave_application_applied", {"application_id": application.id})
    
    return application

@transaction.atomic
def withdraw_application(user_id: int, application_id: int, reason: str = "") -> LeaveApplication:
    application = get_application_by_id(application_id)
    if application.status not in ["under_review", "substitute_pending"]:
        raise BadRequestError("Cannot withdraw a leave application that is already finalized.")
    
    validate_transition(application.status, "withdrawn")
    
    application.status = "withdrawn"
    application.save()
    
    LeaveActionHistory.objects.create(
        application=application,
        action="withdrawn",
        performed_by=user_id,
        reason=reason
    )
    
    enqueue_notification(user_id, "leave_application_withdrawn", {"application_id": application.id})
    
    return application

@transaction.atomic
def request_cancellation(user_id: int, application_id: int, reason: str) -> LeaveApplication:
    application = get_application_by_id(application_id)
    if application.status != "approved" or application.start_date < datetime.date.today():
        raise BadRequestError("Cannot cancel a leave application that is not approved or has already started.")
    
    validate_transition(application.status, "cancel_requested")
    
    application.status = "cancel_requested"
    application.save()
    
    LeaveActionHistory.objects.create(
        application=application,
        action="cancellation_requested",
        performed_by=user_id,
        reason=reason
    )
    
    enqueue_notification(user_id, "leave_application_cancellation_requested", {"application_id": application.id})
    
    return application

@transaction.atomic
def request_extension(user_id: int, application_id: int, start_date: datetime.date, end_date: datetime.date, purpose: str, substitute_user_id: int | None = None, responsibilities: str = "", is_faculty: bool = False) -> LeaveApplication:
    if not application_id:
        raise BadRequestError("Parent leave ID is required for extension.")
    
    parent_leave = get_application_by_id(application_id)
    if parent_leave.status != "approved" or start_date != parent_leave.end_date + timedelta(days=1):
        raise BadRequestError("Invalid extension request. Parent leave must be approved and the new start date must be the day after the parent leave ends.")
    
    category = parent_leave.category
    days = calculate_leave_days(start_date, end_date)
    balance = get_or_create_balance(user_id, category)
    if balance.days < days:
        raise BadRequestError("Insufficient leave balance for extension.")
    
    new_application = LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        purpose=purpose,
        half_day_type="full",
        days=days,
        status="under_review",
        parent_leave=parent_leave
    )
    
    LeaveActionHistory.objects.create(
        application=new_application,
        action="extension_requested",
        performed_by=user_id,
        reason=purpose
    )
    
    enqueue_notification(user_id, "leave_application_extension_requested", {"application_id": new_application.id})
    
    return new_application

@transaction.atomic
def maintain_finalized_record(admin_user_id: int, application_id: int, reason: str, changes: dict) -> LeaveApplication:
    application = get_application_by_id(application_id)
    if application.status != "finalized":
        raise BadRequestError("Cannot modify a leave application that is not finalized.")
    
    for field, value in changes.items():
        setattr(application, field, value)
    
    application.save()
    
    LeaveActionHistory.objects.create(
        application=application,
        action="record_maintained",
        performed_by=admin_user_id,
        reason=reason
    )
    
    enqueue_notification(admin_user_id, "leave_application_record_maintained", {"application_id": application.id})
    
    return application