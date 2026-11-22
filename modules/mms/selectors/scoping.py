"""Data scoping selectors for MMS queries."""
from __future__ import annotations
from django.db.models import QuerySet

from modules.mms.models import (
    MessRegistration,
    MessDeregistration,
    MessMenu,
    MessRebate,
    SpecialFoodRequest,
    MessBill,
    MessAnnouncement,
    MessFeedback,
    VacationFoodResponse,
)


def visible_registrations(actor) -> QuerySet[MessRegistration]:
    """Scoping for mess registrations. Admin is restricted (BR-MMS-005)."""
    if actor.has_permission("mms.registration.review") or actor.has_permission("mms.registration.view_oversight"):
        return MessRegistration.objects.all()
    if actor.has_permission("mms.registration.self"):
        return MessRegistration.objects.filter(user_id=actor.user_id)
    return MessRegistration.objects.none()


def visible_deregistrations(actor) -> QuerySet[MessDeregistration]:
    """Scoping for mess deregistrations."""
    if actor.has_permission("mms.deregistration.review") or actor.has_permission("mms.registration.view_oversight"):
        return MessDeregistration.objects.all()
    if actor.has_permission("mms.deregistration.self"):
        return MessDeregistration.objects.filter(user_id=actor.user_id)
    return MessDeregistration.objects.none()


def visible_rebates(actor) -> QuerySet[MessRebate]:
    """Scoping for mess rebates."""
    if actor.has_permission("mms.rebate.review") or actor.has_permission("mms.report.supervisory"):
        return MessRebate.objects.all()
    if actor.has_permission("mms.rebate.self"):
        return MessRebate.objects.filter(user_id=actor.user_id)
    return MessRebate.objects.none()


def visible_special_food_requests(actor) -> QuerySet[SpecialFoodRequest]:
    """Scoping for special food requests."""
    if actor.has_permission("mms.special_food.review") or actor.has_permission("mms.special_food.fulfill"):
        return SpecialFoodRequest.objects.all()
    if actor.has_permission("mms.special_food.self"):
        return SpecialFoodRequest.objects.filter(user_id=actor.user_id)
    return SpecialFoodRequest.objects.none()


def visible_bills(actor) -> QuerySet[MessBill]:
    """Scoping for monthly mess bills (BR-MMS-040)."""
    if actor.has_permission("mms.bill.manage"):
        return MessBill.objects.all()
    if actor.has_permission("mms.bill.view_self"):
        return MessBill.objects.filter(user_id=actor.user_id)
    return MessBill.objects.none()


def visible_feedback(actor) -> QuerySet[MessFeedback]:
    """Scoping for feedback entries (BR-MMS-020)."""
    if actor.has_permission("mms.feedback.view"):
        return MessFeedback.objects.all()
    if actor.has_permission("mms.feedback.submit"):
        return MessFeedback.objects.filter(user_id=actor.user_id)
    return MessFeedback.objects.none()


def visible_menus(actor) -> QuerySet[MessMenu]:
    """All roles with menu.view can view active weekly menus."""
    if actor.has_permission("mms.menu.view"):
        return MessMenu.objects.filter(is_active=True)
    return MessMenu.objects.none()


def visible_announcements(actor) -> QuerySet[MessAnnouncement]:
    """All roles with announcement.view can view active announcements."""
    if actor.has_permission("mms.announcement.view"):
        return MessAnnouncement.objects.filter(is_active=True)
    return MessAnnouncement.objects.none()


def visible_vacation_responses(actor, survey_id: int) -> QuerySet[VacationFoodResponse]:
    """Vacation survey responses visible to staff or student's own."""
    qs = VacationFoodResponse.objects.filter(survey_id=survey_id)
    if actor.has_permission("mms.vacation.manage") or actor.has_permission("mms.report.supervisory"):
        return qs
    if actor.has_permission("mms.vacation.respond"):
        return qs.filter(user_id=actor.user_id)
    return VacationFoodResponse.objects.none()
