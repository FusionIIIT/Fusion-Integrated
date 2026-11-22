from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.mms.domain.exceptions import GuardFailed
from modules.mms.models import (
    Announcement,
    Deregistration,
    Feedback,
    MonthlyBill,
    NotificationOutbox,
    RebateRequest,
    Registration,
    RegistrationWindow,
    RoleAssignment,
    SpecialFoodPolicy,
    SpecialFoodRequest,
    VacationResponse,
    VacationSurvey,
)
from modules.mms.selectors import scoping
from modules.mms.services import (
    announcement,
    billing,
    deregistration,
    feedback,
    menu,
    rebate,
    registration,
    reports,
    roles,
    special_food,
    survey,
)
from modules.mms.services.special_food import _decision_period_hours


@pytest.mark.django_db
def test_uc_001_alt_a1_role_assignment_keeps_one_active_role(mess_admin_actor):
    """test_id=UC-001-ALT-A1,FR-AFR-004,FR-AFR-097; source_id=MMS-UC-001 Alternative Flow A1; FR_source_ids=AFR-MMS-004,AFR-MMS-097"""
    now = timezone.now()
    current = roles.assign(mess_admin_actor, "caretaker", 201, now, now + timedelta(days=5))

    with pytest.raises(ConflictError):
        roles.assign(mess_admin_actor, "caretaker", 202, now + timedelta(days=1))

    current.refresh_from_db()
    assert current.is_active
    assert RoleAssignment.objects.filter(designation="caretaker", is_active=True).count() == 1


@pytest.mark.django_db
def test_uc_001_alt_a2_unavailable_employee_is_not_assigned(mess_admin_actor, stub_iam):
    """test_id=UC-001-ALT-A2,FR-AFR-099; source_id=MMS-UC-001 Alternative Flow A2; FR_source_ids=AFR-MMS-099"""
    stub_iam().employees = []

    roles.assign(mess_admin_actor, "caretaker", 999999, timezone.now())

    assert not RoleAssignment.objects.filter(employee_user_id=999999).exists()


@pytest.mark.django_db
def test_uc_002_alt_a1_invalid_registration_window_is_not_opened(caretaker_actor):
    """test_id=UC-002-ALT-A1; source_id=MMS-UC-002 Alternative Flow A1"""
    now = timezone.now()
    with pytest.raises(GuardFailed):
        registration.open_window(caretaker_actor, "2026-2027", now, now)

    assert RegistrationWindow.objects.count() == 0


@pytest.mark.django_db
def test_uc_003_alt_a1_registration_is_blocked_when_no_window_is_open(student_actor):
    """test_id=UC-003-ALT-A1; source_id=MMS-UC-003 Alternative Flow A1"""
    with pytest.raises(GuardFailed):
        registration.submit(student_actor)

    assert Registration.objects.count() == 0


@pytest.mark.skip(
    reason="NOT_AUTOMATED: the supplied registration model and service define no required detail fields, so an omitted required value cannot be constructed without inventing a contract."
)
def test_uc_003_alt_a2_missing_required_registration_details_are_not_automated():
    """test_id=UC-003-ALT-A2; source_id=MMS-UC-003 Alternative Flow A2"""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: MMS-UC-009 v1.4 explicitly leaves Mess Admin menu visibility unresolved because Problem Statement ??3.3.2, 3.2.1, and 3.3.11 conflict."
)
def test_uc_009_alt_a1_mess_admin_weekly_menu_visibility_is_not_automated():
    """test_id=UC-009-ALT-A1; source_id=MMS-UC-009 Alternative Flow A1"""


@pytest.mark.django_db
@pytest.mark.django_db
def test_uc_004_alt_a1_registration_decision_cannot_be_repeated(student_actor, caretaker_actor):
    """test_id=UC-004-ALT-A1; source_id=MMS-UC-004 Alternative Flow A1"""
    request = Registration.objects.create(
        user_id=student_actor.user_id,
        status="approved",
        decided_at=timezone.now(),
        decided_by_user_id=201,
    )

    with pytest.raises(NotFoundError):
        registration.decide(caretaker_actor, request.pk, approve=False)

    request.refresh_from_db()
    assert request.status == "approved"


@pytest.mark.django_db
def test_uc_005_alt_a1_unregistered_student_cannot_request_deregistration(student_actor):
    """test_id=UC-005-ALT-A1; source_id=MMS-UC-005 Alternative Flow A1"""
    with pytest.raises(ConflictError):
        deregistration.submit(student_actor)

    assert Deregistration.objects.count() == 0


@pytest.mark.django_db
def test_uc_006_alt_a1_deregistration_decision_cannot_be_repeated(
    student_actor, caretaker_actor
):
    """test_id=UC-006-ALT-A1; source_id=MMS-UC-006 Alternative Flow A1"""
    request = Deregistration.objects.create(
        user_id=student_actor.user_id,
        status="rejected",
        decided_at=timezone.now(),
        decided_by_user_id=caretaker_actor.user_id,
    )

    with pytest.raises(NotFoundError):
        deregistration.decide(caretaker_actor, request.pk, approve=True)

    request.refresh_from_db()
    assert request.status == "rejected"


@pytest.mark.django_db
def test_uc_007_alt_a1_warden_cannot_decide_registration(warden_actor, student_actor):
    """test_id=UC-007-ALT-A1,FR-AFR-020,FR-CFR-006; source_id=MMS-UC-007 Alternative Flow A1; FR_source_ids=AFR-MMS-020,CFR-MMS-006"""
    request = Registration.objects.create(user_id=student_actor.user_id, status="pending")

    with pytest.raises(PermissionDeniedError):
        registration.decide(warden_actor, request.pk, approve=True)

    request.refresh_from_db()
    assert request.status == "pending"


@pytest.mark.django_db
def test_uc_008_alt_a1_invalid_menu_structure_is_rejected(caretaker_actor):
    """test_id=UC-008-ALT-A1; source_id=MMS-UC-008 Alternative Flow A1"""
    with pytest.raises(ConflictError):
        menu.upsert_item(caretaker_actor, timezone.localdate(), "snack", "Fruit")

    from modules.mms.models import MenuItem

    assert MenuItem.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.django_db
def test_uc_010_alt_a1_generated_bill_is_not_published_before_finalization(
    caretaker_actor, student_actor
):
    """test_id=UC-010-ALT-A1; source_id=MMS-UC-010 Alternative Flow A1"""
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
def test_uc_011_alt_a1_no_bill_returns_empty_student_list(student_actor):
    """test_id=UC-011-ALT-A1; source_id=MMS-UC-011 Alternative Flow A1"""
    assert list(scoping.monthly_bills_for(student_actor)) == []


@pytest.mark.django_db
def test_uc_012_alt_a1_empty_feedback_is_rejected(student_actor):
    """test_id=UC-012-ALT-A1; source_id=MMS-UC-012 Alternative Flow A1"""
    with pytest.raises(ConflictError):
        feedback.submit(student_actor, "  ")

    assert Feedback.objects.count() == 0


@pytest.mark.django_db
def test_uc_013_alt_a1_no_feedback_returns_empty_list(caretaker_actor):
    """test_id=UC-013-ALT-A1; source_id=MMS-UC-013 Alternative Flow A1"""
    assert list(scoping.feedback_for(caretaker_actor)) == []


@pytest.mark.django_db
def test_uc_014_alt_a1_short_rebate_duration_is_rejected(student_actor):
    """test_id=UC-014-ALT-A1; source_id=MMS-UC-014 Alternative Flow A1"""
    today = timezone.localdate()
    with pytest.raises(ConflictError):
        rebate.submit(
            student_actor, "medical", "", today + timedelta(days=1), today + timedelta(days=3)
        )

    assert RebateRequest.objects.count() == 0


@pytest.mark.django_db
def test_uc_014_alt_a2_rebate_lead_time_under_one_day_is_rejected(student_actor):
    """test_id=UC-014-ALT-A2; source_id=MMS-UC-014 Alternative Flow A2"""
    today = timezone.localdate()
    with pytest.raises(ConflictError):
        rebate.submit(
            student_actor, "medical", "", today, today + timedelta(days=3)
        )

    assert RebateRequest.objects.count() == 0


@pytest.mark.django_db
def test_uc_014_alt_a3_overlapping_rebate_is_rejected(student_actor):
    """test_id=UC-014-ALT-A3; source_id=MMS-UC-014 Alternative Flow A3"""
    today = timezone.localdate()
    RebateRequest.objects.create(
        user_id=student_actor.user_id,
        reason="medical",
        start_date=today + timedelta(days=2),
        end_date=today + timedelta(days=5),
        status="pending",
    )
    with pytest.raises(ConflictError):
        rebate.submit(
            student_actor,
            "family_function",
            "",
            today + timedelta(days=4),
            today + timedelta(days=7),
        )

    assert RebateRequest.objects.count() == 1


@pytest.mark.django_db
def test_uc_015_alt_a1_rebate_decision_cannot_be_repeated(student_actor, caretaker_actor):
    """test_id=UC-015-ALT-A1; source_id=MMS-UC-015 Alternative Flow A1"""
    request = RebateRequest.objects.create(
        user_id=student_actor.user_id,
        reason="medical",
        start_date=timezone.localdate() + timedelta(days=2),
        end_date=timezone.localdate() + timedelta(days=5),
        status="approved",
        decided_at=timezone.now(),
        decided_by_user_id=caretaker_actor.user_id,
    )

    with pytest.raises(NotFoundError):
        rebate.decide(caretaker_actor, request.pk, approve=False)

    request.refresh_from_db()
    assert request.status == "approved"


@pytest.mark.django_db
def test_uc_016_alt_a1_missing_survey_deadline_does_not_create_survey(caretaker_actor):
    """test_id=UC-016-ALT-A1; source_id=MMS-UC-016 Alternative Flow A1"""
    with pytest.raises(ConflictError):
        survey.create(caretaker_actor, "Winter recess", None)

    assert VacationSurvey.objects.count() == 0


@pytest.mark.django_db
def test_uc_016_alt_a2_creation_does_not_invent_reminder_schedule(caretaker_actor):
    """test_id=UC-016-ALT-A2; source_id=MMS-UC-016 Alternative Flow A2"""
    survey.create(caretaker_actor, "Winter recess", timezone.now() + timedelta(days=2))

    assert not NotificationOutbox.objects.filter(topic="survey.reminder").exists()


@pytest.mark.django_db
def test_uc_017_alt_a1_closed_survey_blocks_response(student_actor):
    """test_id=UC-017-ALT-A1; source_id=MMS-UC-017 Alternative Flow A1"""
    closed_survey = VacationSurvey.objects.create(
        vacation="Winter recess",
        response_deadline=timezone.now() - timedelta(minutes=1),
        is_open=False,
        created_by_user_id=201,
    )

    with pytest.raises(NotFoundError):
        survey.respond(student_actor, closed_survey.pk, "yes")

    assert not VacationResponse.objects.filter(survey=closed_survey.pk).exists()

    # The same alternative flow also covers an open survey when the Student
    # is not currently registered. This fixture has no approved Registration.
    open_survey = VacationSurvey.objects.create(
        vacation="Summer recess",
        response_deadline=timezone.now() + timedelta(days=1),
        is_open=True,
        created_by_user_id=201,
    )
    with pytest.raises((ConflictError, NotFoundError, PermissionDeniedError)):
        survey.respond(student_actor, open_survey.pk, "yes")

    assert not VacationResponse.objects.filter(survey=open_survey.pk).exists()


@pytest.mark.django_db
def test_uc_018_alt_a1_no_survey_responses_returns_empty_summary(caretaker_actor):
    """test_id=UC-018-ALT-A1; source_id=MMS-UC-018 Alternative Flow A1"""
    created = VacationSurvey.objects.create(
        vacation="Winter recess",
        response_deadline=timezone.now() + timedelta(days=2),
        created_by_user_id=201,
    )

    assert list(scoping.vacation_responses_for(caretaker_actor).filter(survey=created.pk)) == []


@pytest.mark.django_db
def test_uc_019_alt_a1_special_food_request_without_lead_time_is_rejected(student_actor):
    """test_id=UC-019-ALT-A1; source_id=MMS-UC-019 Alternative Flow A1"""
    today = timezone.localdate()
    SpecialFoodPolicy.objects.create(decision_period_hours=24, effective_from=today - timedelta(days=1))

    with pytest.raises(ConflictError):
        special_food.submit(student_actor, "Illness", today)

    assert SpecialFoodRequest.objects.count() == 0


@pytest.mark.django_db
def test_uc_020_alt_a1_special_food_decision_cannot_be_repeated(
    student_actor, caretaker_actor
):
    """test_id=UC-020-ALT-A1; source_id=MMS-UC-020 Alternative Flow A1"""
    now = timezone.now()
    request = SpecialFoodRequest.objects.create(
        user_id=student_actor.user_id,
        reason="Illness",
        requested_date=timezone.localdate() + timedelta(days=1),
        status="approved",
        decision_due_at=now + timedelta(days=1),
        decided_at=now,
        decided_by_user_id=caretaker_actor.user_id,
    )

    with pytest.raises(NotFoundError):
        special_food.decide(caretaker_actor, request.pk, approve=False)

    request.refresh_from_db()
    assert request.status == "approved"


@pytest.mark.django_db
def test_uc_020_alt_a2_decision_period_uses_institution_policy():
    """test_id=UC-020-ALT-A2; source_id=MMS-UC-020 Alternative Flow A2"""
    SpecialFoodPolicy.objects.create(
        decision_period_hours=24,
        effective_from=timezone.localdate() - timedelta(days=1),
    )

    assert _decision_period_hours() == 24


@pytest.mark.django_db
def test_uc_021_alt_a1_nonapproved_special_food_cannot_be_fulfilled(
    student_actor, caretaker_actor
):
    """test_id=UC-021-ALT-A1; source_id=MMS-UC-021 Alternative Flow A1"""
    request = SpecialFoodRequest.objects.create(
        user_id=student_actor.user_id,
        reason="Illness",
        requested_date=timezone.localdate() + timedelta(days=1),
        status="requested",
    )

    with pytest.raises(NotFoundError):
        special_food.fulfill(caretaker_actor, request.pk, "served")

    request.refresh_from_db()
    assert request.status == "requested"


@pytest.mark.django_db
def test_uc_022_alt_a1_student_cannot_publish_announcement(student_actor):
    """test_id=UC-022-ALT-A1; source_id=MMS-UC-022 Alternative Flow A1"""
    with pytest.raises(PermissionDeniedError):
        announcement.publish(student_actor, "Dining hall hours", "Dinner closes at 8 PM.")

    assert Announcement.objects.count() == 0


@pytest.mark.django_db
def test_uc_023_alt_a1_empty_announcement_history_is_empty(student_actor):
    """test_id=UC-023-ALT-A1; source_id=MMS-UC-023 Alternative Flow A1"""
    assert list(scoping.announcements_for(student_actor)) == []


@pytest.mark.django_db
def test_uc_024_alt_a1_supervisory_report_with_no_data_is_empty(warden_actor):
    """test_id=UC-024-ALT-A1; source_id=MMS-UC-024 Alternative Flow A1"""
    result = reports.get_supervisory_report(warden_actor)

    assert result["total_billed_amount"] == 0
    assert result["feedback_count"] == 0


@pytest.mark.django_db
def test_uc_025_alt_a1_operational_report_with_no_data_is_empty(caretaker_actor):
    """test_id=UC-025-ALT-A1; source_id=MMS-UC-025 Alternative Flow A1"""
    result = reports.get_operational_report(caretaker_actor)

    assert result["total_registered_students"] == 0
    assert result["pending_registrations"] == 0


@pytest.mark.django_db
def test_uc_026_alt_a1_no_requests_returns_empty_student_history(student_actor):
    """test_id=UC-026-ALT-A1; source_id=MMS-UC-026 Alternative Flow A1"""
    assert list(scoping.deregistration_requests_for(student_actor)) == []


@pytest.mark.django_db
def test_uc_026_alt_a2_student_cannot_see_other_student_request(student_actor):
    """test_id=UC-026-ALT-A2,FR-AFR-011,FR-AFR-021; source_id=MMS-UC-026 Alternative Flow A2; FR_source_ids=AFR-MMS-011,AFR-MMS-021"""
    other_request = Deregistration.objects.create(user_id=202, status="pending")

    assert not scoping.deregistration_requests_for(student_actor).filter(pk=other_request.pk).exists()


@pytest.mark.django_db
def test_uc_027_alt_a1_already_changed_deregistration_is_not_activated(student_actor):
    """test_id=UC-027-ALT-A1; source_id=MMS-UC-027 Alternative Flow A1"""
    request = Deregistration.objects.create(user_id=student_actor.user_id, status="rejected")

    assert deregistration.activate_approved() == 0
    request.refresh_from_db()
    assert request.status == "rejected"


@pytest.mark.django_db
def test_uc_028_alt_a1_explicit_vacation_response_is_unchanged(student_actor):
    """test_id=UC-028-ALT-A1; source_id=MMS-UC-028 Alternative Flow A1"""
    Registration.objects.create(user_id=student_actor.user_id, status="approved")
    created = VacationSurvey.objects.create(
        vacation="Winter recess",
        response_deadline=timezone.now() - timedelta(minutes=1),
        created_by_user_id=201,
    )
    response = VacationResponse.objects.create(
        survey=created.pk,
        student_user_id=student_actor.user_id,
        response="yes",
        responded_at=created.response_deadline - timedelta(hours=1),
    )

    survey.apply_default_no()

    response.refresh_from_db()
    assert response.response == "yes"


@pytest.mark.django_db
def test_uc_028_alt_a2_no_registered_students_creates_no_default_rows():
    """test_id=UC-028-ALT-A2; source_id=MMS-UC-028 Alternative Flow A2"""
    created = VacationSurvey.objects.create(
        vacation="Winter recess",
        response_deadline=timezone.now() - timedelta(minutes=1),
        created_by_user_id=201,
    )

    assert survey.apply_default_no() == 1
    assert VacationResponse.objects.filter(survey=created.pk).count() == 0


@pytest.mark.django_db
def test_uc_029_alt_a1_already_decided_special_food_is_not_default_rejected(
    student_actor, caretaker_actor
):
    """test_id=UC-029-ALT-A1; source_id=MMS-UC-029 Alternative Flow A1"""
    request = SpecialFoodRequest.objects.create(
        user_id=student_actor.user_id,
        reason="Illness",
        requested_date=timezone.localdate() + timedelta(days=1),
        status="approved",
        decision_due_at=timezone.now() - timedelta(minutes=1),
        decided_at=timezone.now() - timedelta(hours=1),
        decided_by_user_id=caretaker_actor.user_id,
    )

    assert special_food.default_reject_undecided() == 0
    request.refresh_from_db()
    assert request.status == "approved"


@pytest.mark.django_db
def test_uc_030_alt_a1_no_registered_students_means_no_bill_is_generated():
    """test_id=UC-030-ALT-A1; source_id=MMS-UC-030 Alternative Flow A1"""
    assert billing.generate_monthly() == 0
    assert MonthlyBill.objects.count() == 0


@pytest.mark.django_db
def test_uc_031_alt_a1_closed_survey_gets_no_reminder(caretaker_actor):
    """test_id=UC-031-ALT-A1,FR-AFR-069,FR-CFR-013; source_id=MMS-UC-031 Alternative Flow A1; FR_source_ids=AFR-MMS-069,CFR-MMS-013"""
    created = survey.create(caretaker_actor, "Winter recess", timezone.now() + timedelta(days=2))
    created.is_open = False
    created.save(update_fields=["is_open", "updated_at"])

    assert survey.send_reminders() == 0
    assert not NotificationOutbox.objects.filter(topic="survey.reminder").exists()
