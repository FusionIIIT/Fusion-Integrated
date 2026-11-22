from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.mms.models import (
    Announcement,
    Deregistration,
    Feedback,
    MenuItem,
    MonthlyBill,
    NotificationOutbox,
    Registration,
    RoleAssignment,
    SpecialFoodCharge,
    SpecialFoodPolicy,
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
    feedback,
    menu,
    rebate,
    registration,
    reports,
    roles,
    special_food,
    survey,
)


@pytest.mark.django_db
def test_uc_001_main_assign_caretaker_and_warden(mess_admin_actor):
    """test_id=UC-001-MAIN,FR-CFR-002,FR-AFR-002,FR-AFR-003,FR-AFR-005,FR-AFR-006,FR-AFR-096; source_id=MMS-UC-001 Main Flow; FR_source_ids=AFR-MMS-002,AFR-MMS-003,AFR-MMS-005,AFR-MMS-006,AFR-MMS-096,CFR-MMS-002"""
    now = timezone.now()
    caretaker = roles.assign(mess_admin_actor, "caretaker", 201, now, now + timedelta(days=30))
    warden = roles.assign(mess_admin_actor, "warden", 301, now, now + timedelta(days=30))

    assert set(RoleAssignment.objects.filter(is_active=True).values_list("designation", flat=True)) == {
        "caretaker",
        "warden",
    }
    assert caretaker.effective_until == now + timedelta(days=30)
    assert warden.effective_until == now + timedelta(days=30)


@pytest.mark.django_db
def test_uc_002_main_open_registration_window(caretaker_actor):
    """test_id=UC-002-MAIN,FR-CFR-004,FR-AFR-012; source_id=MMS-UC-002 Main Flow; FR_source_ids=AFR-MMS-012,CFR-MMS-004"""
    now = timezone.now()
    window = registration.open_window(caretaker_actor, "2026-2027", now, now + timedelta(days=3))

    assert window.is_open
    assert window.cycle_or_period == "2026-2027"


@pytest.mark.django_db
def test_uc_003_main_student_submits_registration(student_actor, caretaker_actor):
    """test_id=UC-003-MAIN,FR-AFR-013,FR-AFR-022,FR-CFR-004,FR-CFR-007; source_id=MMS-UC-003 Main Flow; FR_source_ids=AFR-MMS-013,AFR-MMS-022,CFR-MMS-004,CFR-MMS-007"""
    now = timezone.now()
    registration.open_window(caretaker_actor, "2026-2027", now - timedelta(days=1), now + timedelta(days=1))

    request = registration.submit(student_actor)

    assert request.status == "pending"
    assert NotificationOutbox.objects.filter(topic="registration.submitted", recipient_user_id=101).exists()


@pytest.mark.django_db
def test_uc_004_main_caretaker_approves_registration(student_actor, caretaker_actor):
    """test_id=UC-004-MAIN,FR-AFR-015,FR-AFR-023,FR-CFR-004,FR-CFR-007; source_id=MMS-UC-004 Main Flow; FR_source_ids=AFR-MMS-015,AFR-MMS-023,CFR-MMS-004,CFR-MMS-007"""
    now = timezone.now()
    registration.open_window(caretaker_actor, "2026-2027", now - timedelta(days=1), now + timedelta(days=1))
    request = registration.submit(student_actor)

    decided = registration.decide(caretaker_actor, request.pk, approve=True)

    assert decided.status == "approved"
    assert NotificationOutbox.objects.filter(topic="registration.decided", recipient_user_id=101).exists()


@pytest.mark.django_db
def test_uc_005_main_student_submits_deregistration(student_actor):
    """test_id=UC-005-MAIN,FR-CFR-005,FR-AFR-014,FR-AFR-022; source_id=MMS-UC-005 Main Flow; FR_source_ids=AFR-MMS-014,AFR-MMS-022,CFR-MMS-005"""
    Registration.objects.create(user_id=student_actor.user_id, status="approved")
    request = deregistration.submit(student_actor)

    assert request.status == "pending"
    assert NotificationOutbox.objects.filter(topic="deregistration.submitted", recipient_user_id=101).exists()


@pytest.mark.django_db
def test_uc_006_main_caretaker_approves_deregistration(student_actor, caretaker_actor):
    """test_id=UC-006-MAIN,FR-AFR-016,FR-AFR-017,FR-AFR-018,FR-AFR-023,FR-CFR-005,FR-CFR-007; source_id=MMS-UC-006 Main Flow; FR_source_ids=AFR-MMS-016,AFR-MMS-017,AFR-MMS-018,AFR-MMS-023,CFR-MMS-005,CFR-MMS-007"""
    request = deregistration.submit(student_actor)

    decided = deregistration.decide(caretaker_actor, request.pk, approve=True)

    assert decided.status == "approved_awaiting_effective_date"
    assert decided.effective_date == timezone.localdate() + timedelta(days=1)


@pytest.mark.django_db
def test_uc_007_main_warden_can_view_requests_for_oversight(student_actor, warden_actor):
    """test_id=UC-007-MAIN,FR-CFR-006,FR-AFR-019; source_id=MMS-UC-007 Main Flow; FR_source_ids=AFR-MMS-019,CFR-MMS-006"""
    request = deregistration.submit(student_actor)

    visible_requests = scoping.deregistration_requests_for(warden_actor)

    assert visible_requests.filter(pk=request.pk).exists()
    assert request.status == "pending"


@pytest.mark.django_db
def test_uc_008_main_caretaker_publishes_weekly_menu(caretaker_actor):
    """test_id=UC-008-MAIN,FR-CFR-008,FR-AFR-029,FR-AFR-032; source_id=MMS-UC-008 Main Flow; FR_source_ids=AFR-MMS-029,AFR-MMS-032,CFR-MMS-008"""
    day = timezone.localdate() + timedelta(days=1)

    item = menu.upsert_item(caretaker_actor, day, "lunch", "Dal and rice")

    assert MenuItem.objects.get(pk=item.pk).item == "Dal and rice"
    assert NotificationOutbox.objects.filter(topic="menu.updated").exists()


@pytest.mark.django_db
def test_uc_009_main_student_views_weekly_menu(student_actor, caretaker_actor):
    """test_id=UC-009-MAIN; source_id=MMS-UC-009 Main Flow"""
    day = timezone.localdate() + timedelta(days=1)
    item = menu.upsert_item(caretaker_actor, day, "dinner", "Vegetable curry")

    assert list(menu.list_items(student_actor)) == [item]


@pytest.mark.django_db
def test_uc_010_main_caretaker_finalizes_and_publishes_monthly_bill(
    student_actor, caretaker_actor
):
    """test_id=UC-010-MAIN,FR-CFR-009,FR-AFR-037,FR-AFR-038,FR-AFR-039,FR-AFR-043; source_id=MMS-UC-010 Main Flow; FR_source_ids=AFR-MMS-037,AFR-MMS-038,AFR-MMS-039,AFR-MMS-043,CFR-MMS-009"""
    Registration.objects.create(user_id=student_actor.user_id, status="approved")
    assert billing.generate_monthly() == 1
    bill = MonthlyBill.objects.get(user_id=student_actor.user_id)

    billing.finalize(caretaker_actor, bill.pk)
    published = billing.publish(caretaker_actor, bill.pk)

    assert published.state == "published"
    assert scoping.monthly_bills_for(student_actor).filter(pk=bill.pk).exists()


@pytest.mark.django_db
def test_uc_011_main_student_views_own_published_bill(student_actor):
    """test_id=UC-011-MAIN,FR-AFR-009,FR-AFR-040,FR-AFR-041,FR-CFR-009; source_id=MMS-UC-011 Main Flow; FR_source_ids=AFR-MMS-009,AFR-MMS-040,AFR-MMS-041,CFR-MMS-009"""
    bill = MonthlyBill.objects.create(
        user_id=student_actor.user_id,
        month=timezone.localdate().replace(day=1),
        state="published",
        total=Decimal("75.00"),
    )

    assert list(scoping.monthly_bills_for(student_actor)) == [bill]


@pytest.mark.django_db
def test_uc_012_main_student_submits_feedback(student_actor):
    """test_id=UC-012-MAIN,FR-CFR-010,FR-AFR-044,FR-AFR-047; source_id=MMS-UC-012 Main Flow; FR_source_ids=AFR-MMS-044,AFR-MMS-047,CFR-MMS-010"""
    saved = feedback.submit(student_actor, "Please add more fruit.")

    assert saved.text == "Please add more fruit."
    assert Feedback.objects.filter(pk=saved.pk).exists()


@pytest.mark.django_db
def test_uc_013_main_caretaker_views_feedback(student_actor, caretaker_actor):
    """test_id=UC-013-MAIN; source_id=MMS-UC-013 Main Flow"""
    saved = feedback.submit(student_actor, "Please add more fruit.")

    assert scoping.feedback_for(caretaker_actor).filter(pk=saved.pk).exists()


@pytest.mark.django_db
def test_uc_014_main_student_submits_rebate(student_actor):
    """test_id=UC-014-MAIN,FR-CFR-011,FR-AFR-049,FR-AFR-050,FR-AFR-060; source_id=MMS-UC-014 Main Flow; FR_source_ids=AFR-MMS-049,AFR-MMS-050,AFR-MMS-060,CFR-MMS-011"""
    today = timezone.localdate()
    request = rebate.submit(
        student_actor, "medical", "", today + timedelta(days=1), today + timedelta(days=4)
    )

    assert request.status == "pending"
    assert NotificationOutbox.objects.filter(topic="rebate.submitted", recipient_user_id=101).exists()


@pytest.mark.django_db
def test_uc_015_main_caretaker_approves_rebate(student_actor, caretaker_actor):
    """test_id=UC-015-MAIN,FR-CFR-012,FR-AFR-055,FR-AFR-061; source_id=MMS-UC-015 Main Flow; FR_source_ids=AFR-MMS-055,AFR-MMS-061,CFR-MMS-012"""
    today = timezone.localdate()
    request = rebate.submit(
        student_actor, "medical", "", today + timedelta(days=2), today + timedelta(days=5)
    )

    decided = rebate.decide(caretaker_actor, request.pk, approve=True)

    assert decided.status == "approved"
    assert decided.approved_start_date == request.start_date
    assert NotificationOutbox.objects.filter(topic="rebate.decided", recipient_user_id=101).exists()


@pytest.mark.django_db
def test_uc_016_main_caretaker_creates_vacation_survey(caretaker_actor):
    """test_id=UC-016-MAIN,FR-CFR-013,FR-AFR-062,FR-AFR-065,FR-AFR-068; source_id=MMS-UC-016 Main Flow; FR_source_ids=AFR-MMS-062,AFR-MMS-065,AFR-MMS-068,CFR-MMS-013"""
    deadline = timezone.now() + timedelta(days=2)

    created = survey.create(caretaker_actor, "Winter recess", deadline)

    assert created.is_open
    assert NotificationOutbox.objects.filter(topic="survey.created").exists()


@pytest.mark.django_db
def test_uc_017_main_student_records_vacation_response(student_actor, caretaker_actor):
    """test_id=UC-017-MAIN,FR-CFR-014,FR-AFR-064; source_id=MMS-UC-017 Main Flow; FR_source_ids=AFR-MMS-064,CFR-MMS-014"""
    created = survey.create(caretaker_actor, "Winter recess", timezone.now() + timedelta(days=2))

    response = survey.respond(student_actor, created.pk, "yes")

    assert response.response == "yes"
    assert response.student_user_id == student_actor.user_id


@pytest.mark.django_db
def test_uc_018_main_caretaker_views_vacation_response_summary(student_actor, caretaker_actor):
    """test_id=UC-018-MAIN,FR-AFR-067,FR-CFR-014; source_id=MMS-UC-018 Main Flow; FR_source_ids=AFR-MMS-067,CFR-MMS-014"""
    created = survey.create(caretaker_actor, "Winter recess", timezone.now() + timedelta(days=2))
    survey.respond(student_actor, created.pk, "no")

    summary_rows = scoping.vacation_responses_for(caretaker_actor).filter(survey=created.pk)

    assert list(summary_rows.values_list("response", flat=True)) == ["no"]


@pytest.mark.django_db
def test_uc_019_main_student_submits_special_food_request(student_actor):
    """test_id=UC-019-MAIN,FR-CFR-015,FR-AFR-070,FR-AFR-075; source_id=MMS-UC-019 Main Flow; FR_source_ids=AFR-MMS-070,AFR-MMS-075,CFR-MMS-015"""
    today = timezone.localdate()
    SpecialFoodPolicy.objects.create(decision_period_hours=24, effective_from=today - timedelta(days=1))

    request = special_food.submit(student_actor, "Illness", today + timedelta(days=1))

    assert request.status == "requested"
    assert NotificationOutbox.objects.filter(
        topic="special_food.submitted", recipient_user_id=student_actor.user_id
    ).exists()


@pytest.mark.django_db
def test_uc_020_main_caretaker_approves_special_food_request(student_actor, caretaker_actor):
    """test_id=UC-020-MAIN,FR-CFR-016,FR-AFR-072,FR-AFR-076; source_id=MMS-UC-020 Main Flow; FR_source_ids=AFR-MMS-072,AFR-MMS-076,CFR-MMS-016"""
    today = timezone.localdate()
    SpecialFoodPolicy.objects.create(decision_period_hours=24, effective_from=today - timedelta(days=1))
    request = special_food.submit(student_actor, "Illness", today + timedelta(days=1))

    decided = special_food.decide(caretaker_actor, request.pk, approve=True)

    assert decided.status == "approved"
    assert SpecialFoodCharge.objects.filter(request=request.pk).exists()
    assert NotificationOutbox.objects.filter(topic="special_food.decided").exists()


@pytest.mark.django_db
def test_uc_021_main_caretaker_marks_approved_request_served(student_actor, caretaker_actor):
    """test_id=UC-021-MAIN,FR-CFR-017,FR-AFR-080; source_id=MMS-UC-021 Main Flow; FR_source_ids=AFR-MMS-080,CFR-MMS-017"""
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

    served = special_food.fulfill(caretaker_actor, request.pk, "served")

    assert served.status == "served"
    assert SpecialFoodTransition.objects.filter(request=request.pk, to_status="served").exists()


@pytest.mark.django_db
def test_uc_022_main_authorized_actor_publishes_announcement(caretaker_actor):
    """test_id=UC-022-MAIN,FR-CFR-018,FR-AFR-081,FR-AFR-083; source_id=MMS-UC-022 Main Flow; FR_source_ids=AFR-MMS-081,AFR-MMS-083,CFR-MMS-018"""
    published = announcement.publish(caretaker_actor, "Dining hall hours", "Dinner closes at 8 PM.")

    assert Announcement.objects.get(pk=published.pk).published_at is not None
    assert NotificationOutbox.objects.filter(topic="announcement.published").exists()


@pytest.mark.django_db
def test_uc_023_main_student_views_announcement_history(student_actor, caretaker_actor):
    """test_id=UC-023-MAIN,FR-AFR-010,FR-AFR-084,FR-CFR-018; source_id=MMS-UC-023 Main Flow; FR_source_ids=AFR-MMS-010,AFR-MMS-084,CFR-MMS-018"""
    published = announcement.publish(caretaker_actor, "Dining hall hours", "Dinner closes at 8 PM.")

    assert scoping.announcements_for(student_actor).filter(pk=published.pk).exists()


@pytest.mark.django_db
def test_uc_024_main_warden_gets_supervisory_report(warden_actor):
    """test_id=UC-024-MAIN,FR-CFR-019; source_id=MMS-UC-024 Main Flow; FR_source_ids=CFR-MMS-019"""
    report = reports.get_supervisory_report(warden_actor, period="2026-11")

    assert report["period"] == "2026-11"
    assert "total_billed_amount" in report


@pytest.mark.django_db
def test_uc_025_main_caretaker_gets_operational_report(caretaker_actor):
    """test_id=UC-025-MAIN,FR-CFR-020; source_id=MMS-UC-025 Main Flow; FR_source_ids=CFR-MMS-020"""
    report = reports.get_operational_report(caretaker_actor, period="2026-11")

    assert report["period"] == "2026-11"
    assert "pending_registrations" in report


@pytest.mark.django_db
def test_uc_026_main_student_views_own_request_history(student_actor):
    """test_id=UC-026-MAIN,FR-CFR-007,FR-AFR-011,FR-AFR-021; source_id=MMS-UC-026 Main Flow; FR_source_ids=AFR-MMS-011,AFR-MMS-021,CFR-MMS-007"""
    request = Deregistration.objects.create(user_id=student_actor.user_id, status="pending")

    assert scoping.deregistration_requests_for(student_actor).filter(pk=request.pk).exists()


@pytest.mark.django_db
def test_uc_027_main_due_deregistration_becomes_effective(student_actor):
    """test_id=UC-027-MAIN; source_id=MMS-UC-027 Main Flow"""
    request = Deregistration.objects.create(
        user_id=student_actor.user_id,
        status="approved_awaiting_effective_date",
        effective_date=timezone.localdate(),
        decided_at=timezone.now(),
        decided_by_user_id=201,
    )

    assert deregistration.activate_approved() == 1
    request.refresh_from_db()
    assert request.status == "student_deregistered"


@pytest.mark.django_db
def test_uc_028_main_deadline_applies_default_no(student_actor):
    """test_id=UC-028-MAIN; source_id=MMS-UC-028 Main Flow"""
    Registration.objects.create(user_id=student_actor.user_id, status="approved")
    created = VacationSurvey.objects.create(
        vacation="Winter recess",
        response_deadline=timezone.now() - timedelta(minutes=1),
        created_by_user_id=201,
    )

    assert survey.apply_default_no() == 1
    assert VacationResponse.objects.get(survey=created.pk, student_user_id=101).response == "default_no"


@pytest.mark.django_db
def test_uc_029_main_expired_special_food_request_is_default_rejected(student_actor):
    """test_id=UC-029-MAIN; source_id=MMS-UC-029 Main Flow"""
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
def test_uc_030_main_system_generates_monthly_bills(student_actor):
    """test_id=UC-030-MAIN; source_id=MMS-UC-030 Main Flow"""
    Registration.objects.create(user_id=student_actor.user_id, status="approved")

    assert billing.generate_monthly() == 1
    bill = MonthlyBill.objects.get(user_id=student_actor.user_id)
    assert bill.month == timezone.localdate().replace(day=1)
    assert bill.state == "generated"


@pytest.mark.django_db
def test_uc_031_main_system_sends_survey_reminder(caretaker_actor):
    """test_id=UC-031-MAIN; source_id=MMS-UC-031 Main Flow"""
    created = survey.create(caretaker_actor, "Winter recess", timezone.now() + timedelta(days=2))

    assert survey.send_reminders() == 1
    assert NotificationOutbox.objects.filter(
        topic="survey.reminder", payload__survey_id=created.pk
    ).exists()
