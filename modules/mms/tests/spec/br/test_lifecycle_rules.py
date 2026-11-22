from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.mms.domain import state_machine as sm
from modules.mms.domain.exceptions import GuardFailed, InvalidTransition
from modules.mms.models import (
    Deregistration,
    Feedback,
    MenuItem,
    MonthlyBill,
    NotificationOutbox,
    RebateRequest,
    Registration,
    RegistrationWindow,
    RoleAssignment,
    SpecialFoodCharge,
    SpecialFoodRequest,
    SpecialFoodTransition,
    VacationResponse,
    VacationSurvey,
)
from modules.mms.selectors import scoping
from modules.mms.services import (
    announcement,
    billing,
    deregistration,
    menu,
    rebate,
    registration,
    reports,
    roles,
    special_food,
    survey,
)


@pytest.mark.django_db
def test_br_003_one_active_caretaker(mess_admin_actor):
    """test_id=BR-003; source_id=BR-MMS-003 rule"""
    now = timezone.now()
    roles.assign(mess_admin_actor, "caretaker", 201, now)
    roles.assign(mess_admin_actor, "caretaker", 202, now + timedelta(days=1))

    assert RoleAssignment.objects.filter(designation="caretaker", is_active=True).count() == 1


@pytest.mark.django_db
def test_br_004_one_active_warden(mess_admin_actor):
    """test_id=BR-004; source_id=BR-MMS-004 rule"""
    now = timezone.now()
    roles.assign(mess_admin_actor, "warden", 301, now)
    roles.assign(mess_admin_actor, "warden", 302, now + timedelta(days=1))

    assert RoleAssignment.objects.filter(designation="warden", is_active=True).count() == 1


@pytest.mark.django_db
def test_br_006_midcycle_reassignment_takes_immediate_effect(mess_admin_actor):
    """test_id=BR-006,FR-AFR-004,FR-AFR-097,FR-CFR-002; source_id=BR-MMS-006 rule; FR_source_ids=AFR-MMS-004,AFR-MMS-097,CFR-MMS-002"""
    now = timezone.now()
    old = roles.assign(mess_admin_actor, "caretaker", 201, now - timedelta(days=4))
    current = roles.assign(mess_admin_actor, "caretaker", 202, now)

    old.refresh_from_db()
    assert not old.is_active
    assert current.is_active
    assert current.effective_from == now


@pytest.mark.django_db
def test_br_008_only_caretaker_opens_registration_window(caretaker_actor, student_actor):
    """test_id=BR-008; source_id=BR-MMS-008 rule"""
    now = timezone.now()
    window = registration.open_window(caretaker_actor, "cycle", now, now + timedelta(days=1))

    with pytest.raises(PermissionDeniedError):
        registration.open_window(student_actor, "other", now, now + timedelta(days=1))
    assert RegistrationWindow.objects.count() == 1
    assert window.is_open


@pytest.mark.django_db
def test_br_009_registration_requires_open_window(student_actor):
    """test_id=BR-009; source_id=BR-MMS-009 rule"""
    with pytest.raises(GuardFailed):
        registration.submit(student_actor)

    assert Registration.objects.count() == 0


@pytest.mark.django_db
def test_br_010_warden_cannot_decide_registration(warden_actor):
    """test_id=BR-010; source_id=BR-MMS-010 rule"""
    request = Registration.objects.create(user_id=101, status="pending")

    with pytest.raises(PermissionDeniedError):
        registration.decide(warden_actor, request.pk, approve=True)

    request.refresh_from_db()
    assert request.status == "pending"


@pytest.mark.django_db
def test_br_011_warden_can_view_student_requests_for_oversight(warden_actor):
    """test_id=BR-011; source_id=BR-MMS-011 rule"""
    request = Registration.objects.create(user_id=101, status="pending")

    assert scoping.registration_requests_for(warden_actor).filter(pk=request.pk).exists()


@pytest.mark.django_db
def test_br_012_registered_student_can_submit_deregistration(student_actor):
    """test_id=BR-012; source_id=BR-MMS-012 rule"""
    Registration.objects.create(user_id=student_actor.user_id, status="approved")

    request = deregistration.submit(student_actor)

    assert request.status == "pending"


@pytest.mark.django_db
def test_br_013_approved_deregistration_effective_next_day(student_actor, caretaker_actor):
    """test_id=BR-013,FR-AFR-018,FR-CFR-005; source_id=BR-MMS-013 rule; FR_source_ids=AFR-MMS-018,CFR-MMS-005"""
    request = deregistration.submit(student_actor)
    decided = deregistration.decide(caretaker_actor, request.pk, approve=True)

    assert decided.effective_date == timezone.localdate() + timedelta(days=1)
    assert decided.status == "approved_awaiting_effective_date"


@pytest.mark.django_db
def test_br_015_menu_update_enqueues_student_notification(caretaker_actor):
    """test_id=BR-015; source_id=BR-MMS-015 rule"""
    menu.upsert_item(caretaker_actor, timezone.localdate(), "breakfast", "Idli")

    notice = NotificationOutbox.objects.get(topic="menu.updated")
    assert notice.payload["audience"] == "students"


@pytest.mark.django_db
def test_br_016_bill_generation_uses_calendar_month(student_actor):
    """test_id=BR-016,FR-AFR-033,FR-CFR-009; source_id=BR-MMS-016 rule; FR_source_ids=AFR-MMS-033,CFR-MMS-009"""
    Registration.objects.create(user_id=student_actor.user_id, status="approved")

    assert billing.generate_monthly() == 1
    bill = MonthlyBill.objects.get(user_id=student_actor.user_id)
    assert bill.month == timezone.localdate().replace(day=1)


@pytest.mark.django_db
def test_br_018_bill_must_be_finalized_before_publication(caretaker_actor, student_actor):
    """test_id=BR-018; source_id=BR-MMS-018 rule"""
    bill = MonthlyBill.objects.create(
        user_id=student_actor.user_id,
        month=timezone.localdate().replace(day=1),
        state="generated",
    )

    with pytest.raises(NotFoundError):
        billing.publish(caretaker_actor, bill.pk)
    bill.refresh_from_db()
    assert bill.state == "generated"


@pytest.mark.django_db
def test_br_019_approved_rebate_reduces_monthly_bill(student_actor):
    """test_id=BR-019,FR-AFR-036,FR-AFR-059,FR-CFR-009,FR-CFR-012; source_id=BR-MMS-019 rule; FR_source_ids=AFR-MMS-036,AFR-MMS-059,CFR-MMS-009,CFR-MMS-012"""
    today = timezone.localdate()
    Registration.objects.create(user_id=student_actor.user_id, status="approved")
    RebateRequest.objects.create(
        user_id=student_actor.user_id,
        reason="medical",
        start_date=today.replace(day=1),
        end_date=today.replace(day=3),
        status="approved",
        approved_start_date=today.replace(day=1),
        approved_end_date=today.replace(day=3),
        decided_at=timezone.now(),
        decided_by_user_id=201,
    )

    assert billing.generate_monthly() == 1
    assert MonthlyBill.objects.get(user_id=student_actor.user_id).rebate_deductions > Decimal("0.00")


@pytest.mark.django_db
def test_br_020_feedback_visible_to_caretaker_and_warden(
    student_actor, caretaker_actor, warden_actor
):
    """test_id=BR-020,FR-AFR-045,FR-AFR-046,FR-CFR-010; source_id=BR-MMS-020 rule; FR_source_ids=AFR-MMS-045,AFR-MMS-046,CFR-MMS-010"""
    from modules.mms.services import feedback

    saved = feedback.submit(student_actor, "Dining area needs cleaning.")

    assert scoping.feedback_for(caretaker_actor).filter(pk=saved.pk).exists()
    assert scoping.feedback_for(warden_actor).filter(pk=saved.pk).exists()


@pytest.mark.django_db
def test_br_025_approved_rebate_uses_caretaker_modified_dates(student_actor, caretaker_actor):
    """test_id=BR-025,FR-AFR-056,FR-AFR-057,FR-CFR-012; source_id=BR-MMS-025 rule; FR_source_ids=AFR-MMS-056,AFR-MMS-057,CFR-MMS-012"""
    today = timezone.localdate()
    request = RebateRequest.objects.create(
        user_id=student_actor.user_id,
        reason="medical",
        start_date=today + timedelta(days=2),
        end_date=today + timedelta(days=5),
        status="pending",
    )
    approved_start, approved_end = today + timedelta(days=3), today + timedelta(days=6)

    decided = rebate.decide(
        caretaker_actor,
        request.pk,
        approve=True,
        approved_start_date=approved_start,
        approved_end_date=approved_end,
    )

    assert decided.approved_start_date == approved_start
    assert decided.approved_end_date == approved_end


@pytest.mark.django_db
def test_br_029_undecided_special_food_request_defaults_to_rejected(student_actor):
    """test_id=BR-029,FR-AFR-073,FR-CFR-016; source_id=BR-MMS-029 rule; FR_source_ids=AFR-MMS-073,CFR-MMS-016"""
    request = SpecialFoodRequest.objects.create(
        user_id=student_actor.user_id,
        reason="Illness",
        requested_date=timezone.localdate() + timedelta(days=1),
        status="requested",
        decision_due_at=timezone.now() - timedelta(minutes=1),
    )

    assert special_food.default_reject_undecided() == 1
    request.refresh_from_db()
    assert request.status == "rejected"
    assert SpecialFoodTransition.objects.filter(request=request.pk, to_status="rejected_default").exists()


@pytest.mark.django_db
def test_br_030_approved_special_food_is_added_as_bill_charge(student_actor, caretaker_actor):
    """test_id=BR-030,FR-AFR-077,FR-CFR-017; source_id=BR-MMS-030 rule; FR_source_ids=AFR-MMS-077,CFR-MMS-017"""
    request = SpecialFoodRequest.objects.create(
        user_id=student_actor.user_id,
        reason="Illness",
        requested_date=timezone.localdate() + timedelta(days=1),
        status="requested",
        decision_due_at=timezone.now() + timedelta(days=1),
    )

    approved = special_food.decide(caretaker_actor, request.pk, approve=True)

    charge = SpecialFoodCharge.objects.get(request=request.pk)
    assert approved.status == "approved"
    assert charge.amount > Decimal("0.00")


@pytest.mark.django_db
def test_br_031_served_and_cancelled_require_approved_source_state():
    """test_id=BR-031,BR-031-BOUNDARY,FR-AFR-078,FR-AFR-079,FR-CFR-017; source_id=BR-MMS-031 rule; FR_source_ids=AFR-MMS-078,AFR-MMS-079,CFR-MMS-017"""
    with pytest.raises(InvalidTransition):
        sm.resolve("requested", "served", sm.CARETAKER)
    assert sm.resolve("approved", "served", sm.CARETAKER).to == "served"
    assert sm.resolve("approved", "cancelled", sm.CARETAKER).to == "cancelled"


@pytest.mark.django_db
def test_br_032_caretaker_and_warden_may_publish_announcements(caretaker_actor, warden_actor):
    """test_id=BR-032,FR-AFR-081,FR-AFR-082,FR-CFR-018; source_id=BR-MMS-032 rule; FR_source_ids=AFR-MMS-081,AFR-MMS-082,CFR-MMS-018"""
    first = announcement.publish(caretaker_actor, "Menu", "Dinner at 7.")
    second = announcement.publish(warden_actor, "Meeting", "Friday at 4.")

    assert first.publisher_user_id == caretaker_actor.user_id
    assert second.publisher_user_id == warden_actor.user_id


@pytest.mark.django_db
def test_br_034_reports_are_role_scoped(caretaker_actor, warden_actor):
    """test_id=BR-034,FR-AFR-092; source_id=BR-MMS-034 rule; FR_source_ids=AFR-MMS-092"""
    assert "pending_registrations" in reports.get_operational_report(caretaker_actor)
    assert "total_billed_amount" in reports.get_supervisory_report(warden_actor)
    with pytest.raises(PermissionDeniedError):
        reports.get_supervisory_report(caretaker_actor)
    with pytest.raises(PermissionDeniedError):
        reports.get_operational_report(warden_actor)


@pytest.mark.django_db
def test_br_039_only_caretaker_may_manage_menu(student_actor):
    """test_id=BR-039; source_id=BR-MMS-039 rule"""
    with pytest.raises(PermissionDeniedError):
        menu.upsert_item(student_actor, timezone.localdate(), "lunch", "Rice")
    assert MenuItem.objects.count() == 0


@pytest.mark.django_db
def test_br_040_students_only_view_own_published_bills(student_actor):
    """test_id=BR-040; source_id=BR-MMS-040 rule"""
    own = MonthlyBill.objects.create(
        user_id=student_actor.user_id,
        month=timezone.localdate().replace(day=1),
        state="published",
    )
    other = MonthlyBill.objects.create(
        user_id=202,
        month=timezone.localdate().replace(day=1),
        state="published",
    )

    visible = scoping.monthly_bills_for(student_actor)
    assert visible.filter(pk=own.pk).exists()
    assert not visible.filter(pk=other.pk).exists()


@pytest.mark.django_db
def test_br_005_mess_admin_cannot_read_operational_student_records(
    mess_admin_actor, student_actor
):
    """test_id=BR-005,FR-CFR-003,FR-AFR-007; source_id=BR-MMS-005 rule; FR_source_ids=AFR-MMS-007,CFR-MMS-003"""
    Registration.objects.create(user_id=student_actor.user_id, status="pending")
    Deregistration.objects.create(user_id=student_actor.user_id, status="pending")
    RebateRequest.objects.create(
        user_id=student_actor.user_id,
        reason="medical",
        start_date=timezone.localdate() + timedelta(days=2),
        end_date=timezone.localdate() + timedelta(days=5),
        status="pending",
    )
    SpecialFoodRequest.objects.create(
        user_id=student_actor.user_id,
        reason="Illness",
        requested_date=timezone.localdate() + timedelta(days=2),
        status="requested",
    )
    MonthlyBill.objects.create(
        user_id=student_actor.user_id,
        month=timezone.localdate().replace(day=1),
        state="published",
    )
    Feedback.objects.create(user_id=student_actor.user_id, text="Please clean the hall.")

    assert not scoping.registration_requests_for(mess_admin_actor).exists()
    assert not scoping.deregistration_requests_for(mess_admin_actor).exists()
    assert not scoping.rebate_requests_for(mess_admin_actor).exists()
    assert not scoping.special_food_requests_for(mess_admin_actor).exists()
    assert not scoping.monthly_bills_for(mess_admin_actor).exists()
    assert not scoping.feedback_for(mess_admin_actor).exists()


@pytest.mark.django_db
def test_br_007_pending_work_remains_visible_after_caretaker_handoff(
    mess_admin_actor, caretaker_actor
):
    """test_id=BR-007,FR-AFR-098,FR-CFR-002; source_id=BR-MMS-007 rule; FR_source_ids=AFR-MMS-098,CFR-MMS-002"""
    now = timezone.now()
    roles.assign(mess_admin_actor, "caretaker", caretaker_actor.user_id, now)
    request = Registration.objects.create(user_id=101, status="pending")
    roles.assign(mess_admin_actor, "caretaker", 202, now + timedelta(minutes=1))
    new_caretaker = replace(caretaker_actor, user_id=202)

    assert scoping.registration_requests_for(new_caretaker).filter(pk=request.pk).exists()


@pytest.mark.django_db
def test_br_017_bill_includes_approved_special_food_charge(student_actor):
    """test_id=BR-017,FR-AFR-035,FR-CFR-009; source_id=BR-MMS-017 rule; FR_source_ids=AFR-MMS-035,CFR-MMS-009"""
    month = timezone.localdate().replace(day=1)
    Registration.objects.create(user_id=student_actor.user_id, status="approved")
    SpecialFoodCharge.objects.create(
        request=1,
        student_user_id=student_actor.user_id,
        month=month,
        amount=Decimal("125.00"),
    )

    assert billing.generate_monthly() == 1
    bill = MonthlyBill.objects.get(user_id=student_actor.user_id)
    assert bill.special_meal_charges == Decimal("125.00")
    assert bill.total == bill.served_day_charges + bill.special_meal_charges - bill.rebate_deductions


@pytest.mark.django_db
def test_br_026_survey_creation_emits_notification(caretaker_actor, student_actor):
    """test_id=BR-026,FR-AFR-063,FR-CFR-013; source_id=BR-MMS-026 rule; FR_source_ids=AFR-MMS-063,CFR-MMS-013"""
    created = survey.create(caretaker_actor, "Winter recess", timezone.now() + timedelta(days=2))

    notice = NotificationOutbox.objects.get(topic="survey.created")
    assert notice.payload["survey_id"] == created.pk
    assert notice.payload["audience"] == "students"

    with pytest.raises((ConflictError, NotFoundError, PermissionDeniedError)):
        survey.respond(student_actor, created.pk, "yes")
    assert not VacationResponse.objects.filter(survey=created.pk).exists()


@pytest.mark.django_db
def test_br_027_default_no_only_changes_registered_nonresponders():
    """test_id=BR-027,FR-AFR-066,FR-CFR-014; source_id=BR-MMS-027 rule; FR_source_ids=AFR-MMS-066,CFR-MMS-014"""
    Registration.objects.create(user_id=101, status="approved")
    Registration.objects.create(user_id=102, status="approved")
    Registration.objects.create(user_id=103, status="pending")
    created = VacationSurvey.objects.create(
        vacation="Winter recess",
        response_deadline=timezone.now() - timedelta(minutes=1),
        created_by_user_id=201,
    )
    VacationResponse.objects.create(
        survey=created.pk,
        student_user_id=101,
        response="yes",
        responded_at=created.response_deadline - timedelta(hours=1),
    )

    assert survey.apply_default_no() == 1
    assert VacationResponse.objects.get(survey=created.pk, student_user_id=101).response == "yes"
    assert VacationResponse.objects.get(survey=created.pk, student_user_id=102).response == "default_no"
    assert not VacationResponse.objects.filter(survey=created.pk, student_user_id=103).exists()
    assert survey.apply_default_no() == 0


@pytest.mark.django_db
def test_br_033_published_announcement_is_available_in_history(
    student_actor, caretaker_actor, warden_actor
):
    """test_id=BR-033,FR-AFR-085,FR-CFR-018; source_id=BR-MMS-033 rule; FR_source_ids=AFR-MMS-085,CFR-MMS-018"""
    published = announcement.publish(caretaker_actor, "Dining hall hours", "Dinner ends at 8 PM.")

    for actor in (student_actor, caretaker_actor, warden_actor):
        assert scoping.announcements_for(actor).filter(pk=published.pk).exists()
    assert scoping.announcements_for(student_actor).count() == 1


@pytest.mark.django_db
def test_br_038_weekly_menu_is_visible_to_student_caretaker_and_warden(
    student_actor, caretaker_actor, warden_actor
):
    """test_id=BR-038,FR-AFR-026,FR-AFR-027,FR-CFR-008; source_id=BR-MMS-038 rule; FR_source_ids=AFR-MMS-026,AFR-MMS-027,CFR-MMS-008"""
    created = menu.upsert_item(caretaker_actor, timezone.localdate(), "dinner", "Dal and rice")

    for actor in (student_actor, caretaker_actor, warden_actor):
        assert menu.list_items(actor).filter(pk=created.pk).exists()


@pytest.mark.django_db
def test_br_042_students_see_only_their_own_request_rows(student_actor):
    """test_id=BR-042,FR-AFR-058,FR-AFR-074; source_id=BR-MMS-042 rule; FR_source_ids=AFR-MMS-058,AFR-MMS-074"""
    own_registration = Registration.objects.create(user_id=101, status="pending")
    other_registration = Registration.objects.create(user_id=102, status="pending")
    own_deregistration = Deregistration.objects.create(user_id=101, status="pending")
    other_deregistration = Deregistration.objects.create(user_id=102, status="pending")
    own_rebate = RebateRequest.objects.create(
        user_id=101,
        reason="medical",
        start_date=timezone.localdate() + timedelta(days=2),
        end_date=timezone.localdate() + timedelta(days=5),
        status="pending",
    )
    other_rebate = RebateRequest.objects.create(
        user_id=102,
        reason="medical",
        start_date=timezone.localdate() + timedelta(days=2),
        end_date=timezone.localdate() + timedelta(days=5),
        status="pending",
    )

    for selector, own, other in (
        (scoping.registration_requests_for, own_registration, other_registration),
        (scoping.deregistration_requests_for, own_deregistration, other_deregistration),
        (scoping.rebate_requests_for, own_rebate, other_rebate),
    ):
        visible = selector(student_actor)
        assert visible.filter(pk=own.pk).exists()
        assert not visible.filter(pk=other.pk).exists()


def test_br_001_routes_stay_within_mess_management_scope():
    """test_id=BR-001,FR-CFR-001,FR-CFR-021,FR-AFR-001,FR-AFR-093; source_id=BR-MMS-001 rule; FR_source_ids=AFR-MMS-001,AFR-MMS-093,CFR-MMS-001,CFR-MMS-021"""
    from modules.mms.api.urls import urlpatterns

    out_of_scope = ("payment", "accounting", "payroll", "procurement", "inventory")
    exposed = [str(pattern.pattern).lower() for pattern in urlpatterns]
    assert not any(term in path for path in exposed for term in out_of_scope)


@pytest.mark.django_db
def test_br_002_unavailable_employee_identity_is_not_assigned(
    mess_admin_actor, stub_iam
):
    """test_id=BR-002,FR-AFR-099,FR-CFR-002; source_id=BR-MMS-002 rule; FR_source_ids=AFR-MMS-099,CFR-MMS-002"""
    stub_iam().employees = []
    now = timezone.now()

    roles.assign(mess_admin_actor, "caretaker", 999999, now)

    assert not RoleAssignment.objects.filter(employee_user_id=999999).exists()


@pytest.mark.django_db
def test_br_035_read_only_report_does_not_trigger_notification(caretaker_actor):
    """test_id=BR-035,FR-CFR-022; source_id=BR-MMS-035 rule; FR_source_ids=CFR-MMS-022"""
    reports.get_operational_report(caretaker_actor)

    assert not NotificationOutbox.objects.exists()


@pytest.mark.skip(
    reason="NOT_AUTOMATED: no authoritative external institution-policy provider is present to supply or verify policy inputs."
)
def test_br_036_institutional_policy_inputs_are_not_automated():
    """test_id=BR-036; source_id=BR-MMS-036 rule"""
