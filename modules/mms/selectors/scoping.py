"""MMS visibility rules — every read starts here (BR-MMS-005/011/034/040/042).

A foreign id yields 404, never 403: a row you may not see is treated as if it
does not exist. Scoping decides the rows; permissions decide the verb.
"""

from __future__ import annotations

from django.db.models import QuerySet

from modules.mms.models import (
    Announcement,
    Deregistration,
    Feedback,
    MenuItem,
    MonthlyBill,
    NotificationOutbox,
    RebateRequest,
    Registration,
    RoleAssignment,
    SpecialFoodRequest,
    VacationResponse,
    VacationSurvey,
)

P_VIEW_ALL = "mms.menu.view"  # any MMS actor may view shared reference data


def _own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def _kind(actor) -> str | None:
    return getattr(actor, "kind", None)


def is_caretaker(actor) -> bool:
    return _has(actor, "mms.registration.review")


def is_warden(actor) -> bool:
    return _has(actor, "mms.report.supervisory")


def is_mess_admin(actor) -> bool:
    return _has(actor, "mms.role.assign")


def role_assignments() -> QuerySet[RoleAssignment]:
    return RoleAssignment.objects.all()


def active_caretaker() -> QuerySet[RoleAssignment]:
    """The currently active Mess Caretaker (exactly one, BR-MMS-003)."""
    return RoleAssignment.objects.filter(designation="caretaker", is_active=True)


def active_warden() -> QuerySet[RoleAssignment]:
    """The currently active Mess Warden (exactly one, BR-MMS-004)."""
    return RoleAssignment.objects.filter(designation="warden", is_active=True)


# -- Special food ---------------------------------------------------------
def special_food_requests_for(actor) -> QuerySet[SpecialFoodRequest]:
    base = SpecialFoodRequest.objects.all()
    if is_caretaker(actor) or is_mess_admin(actor):
        # Caretaker decides all pending requests (BR-MMS-010); Mess Admin may
        # not touch operational data, so this is read-only scope only via the
        # caretaker permission held in tests.
        return base
    own = _own_id(actor)
    if own is None:
        return base.none()
    return base.filter(user_id=own)


def special_food_request_for(actor, pk: int) -> QuerySet[SpecialFoodRequest]:
    qs = special_food_requests_for(actor)
    return qs.filter(pk=pk)


# -- Rebate ---------------------------------------------------------------
def rebate_requests_for(actor) -> QuerySet[RebateRequest]:
    base = RebateRequest.objects.all()
    if is_caretaker(actor):
        return base
    own = _own_id(actor)
    if own is None:
        return base.none()
    return base.filter(user_id=own)


# -- Registration / deregistration ----------------------------------------
def registration_requests_for(actor) -> QuerySet[Registration]:
    base = Registration.objects.all()
    if is_caretaker(actor):
        return base
    own = _own_id(actor)
    if own is None:
        return base.none()
    return base.filter(user_id=own)


def deregistration_requests_for(actor) -> QuerySet[Deregistration]:
    base = Deregistration.objects.all()
    if is_caretaker(actor):
        return base
    own = _own_id(actor)
    if own is None:
        return base.none()
    return base.filter(user_id=own)


# -- Menu -----------------------------------------------------------------
def menu_items_for(actor) -> QuerySet[MenuItem]:
    # Students, Caretaker and Warden may view (BR-MMS-038); Mess Admin access
    # is unresolved — not granted here pending a ruling.
    if _kind(actor) in ("student", "faculty", "staff") or is_caretaker(actor) or is_warden(actor):
        return MenuItem.objects.all()
    return MenuItem.objects.none()


# -- Billing --------------------------------------------------------------
def monthly_bills_for(actor) -> QuerySet[MonthlyBill]:
    # Students view only their own published bills (BR-MMS-040); Caretaker
    # views all for review/finalize/publish.
    base = MonthlyBill.objects.all()
    if is_caretaker(actor):
        return base
    own = _own_id(actor)
    if own is None:
        return base.none()
    return base.filter(user_id=own, state="published")


# -- Feedback -------------------------------------------------------------
def feedback_for(actor) -> QuerySet[Feedback]:
    base = Feedback.objects.all()
    if is_caretaker(actor) or is_warden(actor):
        return base
    own = _own_id(actor)
    if own is None:
        return base.none()
    return base.filter(user_id=own)


# -- Announcements --------------------------------------------------------
def announcements_for(actor) -> QuerySet[Announcement]:
    # All MMS actors may view announcement history per access rights (BR-MMS-033).
    return Announcement.objects.all()


# -- Vacation -------------------------------------------------------------
def vacation_surveys_for(actor) -> QuerySet[VacationSurvey]:
    return VacationSurvey.objects.all()


def vacation_responses_for(actor) -> QuerySet[VacationResponse]:
    base = VacationResponse.objects.all()
    if is_caretaker(actor):
        return base
    own = _own_id(actor)
    if own is None:
        return base.none()
    return base.filter(student_user_id=own)


# -- Reports --------------------------------------------------------------
def supervisory_reports_for(actor) -> QuerySet[MonthlyBill]:
    # Warden: supervisory reports (registered lists etc.) — scoped here as
    # bill-derived aggregates; Caretaker: operational reports.
    if is_warden(actor):
        return MonthlyBill.objects.all()
    if is_caretaker(actor):
        return MonthlyBill.objects.all()
    return MonthlyBill.objects.none()


# -- Notifications --------------------------------------------------------
def notification_outbox_for(actor) -> QuerySet[NotificationOutbox]:
    # Outbox is operational; caretaker/warden may inspect it.
    if is_caretaker(actor) or is_warden(actor):
        return NotificationOutbox.objects.all()
    return NotificationOutbox.objects.none()
