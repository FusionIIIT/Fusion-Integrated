from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import PermissionDeniedError
from modules.mms.models import (
    Announcement,
    Deregistration,
    Feedback,
    MenuItem,
    MonthlyBill,
    NotificationOutbox,
    RebateRequest,
    Registration,
    RegistrationWindow,
    RoleAssignment,
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

EXCEPTION_CASES = [
    pytest.param(
        f"UC-{n:03}-EXC",
        f"MMS-UC-{n:03} Exception Flow",
        id=f"UC-{n:03}-EXC__MMS-UC-{n:03}-Exception",
    )
    for n in range(1, 32)
]


@pytest.mark.django_db
@pytest.mark.parametrize(("test_id", "source_id"), EXCEPTION_CASES)
def test_exception_flow_refuses_invalid_or_unauthorized_action_without_state_change(
    test_id,
    source_id,
    student_actor,
    caretaker_actor,
    warden_actor,
    mess_admin_actor,
    monkeypatch,
):
    """The pytest case id contains each frozen test_id and source_id."""
    now = timezone.now()
    today = timezone.localdate()

    if test_id == "UC-001-EXC":
        count_before = RoleAssignment.objects.count()
        with pytest.raises(PermissionDeniedError):
            roles.assign(student_actor, "caretaker", 201, now)
        assert RoleAssignment.objects.count() == count_before
    elif test_id == "UC-002-EXC":
        count_before = RegistrationWindow.objects.count()
        with pytest.raises(PermissionDeniedError):
            registration.open_window(student_actor, "2026-2027", now, now + timedelta(days=1))
        assert RegistrationWindow.objects.count() == count_before
    elif test_id == "UC-003-EXC":
        student_actor.permissions.discard("mms.registration.create")
        with pytest.raises(PermissionDeniedError):
            registration.submit(student_actor)
        assert Registration.objects.count() == 0
    elif test_id == "UC-004-EXC":
        request = Registration.objects.create(user_id=101, status="pending")
        with pytest.raises(PermissionDeniedError):
            registration.decide(warden_actor, request.pk, approve=True)
        request.refresh_from_db()
        assert request.status == "pending"
    elif test_id == "UC-005-EXC":
        student_actor.permissions.discard("mms.deregistration.create")
        with pytest.raises(PermissionDeniedError):
            deregistration.submit(student_actor)
        assert Deregistration.objects.count() == 0
    elif test_id == "UC-006-EXC":
        request = Deregistration.objects.create(user_id=101, status="pending")
        with pytest.raises(PermissionDeniedError):
            deregistration.decide(student_actor, request.pk, approve=True)
        request.refresh_from_db()
        assert request.status == "pending"
    elif test_id == "UC-007-EXC":
        request = Registration.objects.create(user_id=101, status="pending")
        with pytest.raises(PermissionDeniedError):
            registration.decide(warden_actor, request.pk, approve=True)
        request.refresh_from_db()
        assert request.status == "pending"
    elif test_id == "UC-008-EXC":
        count_before = MenuItem.objects.count()
        with pytest.raises(PermissionDeniedError):
            menu.upsert_item(student_actor, today, "lunch", "Dal")
        assert MenuItem.objects.count() == count_before
    elif test_id == "UC-009-EXC":
        count_before = MenuItem.objects.count()
        with pytest.raises(PermissionDeniedError):
            menu.upsert_item(mess_admin_actor, today, "lunch", "Dal")
        assert MenuItem.objects.count() == count_before
    elif test_id == "UC-010-EXC":
        bill = MonthlyBill.objects.create(user_id=101, month=today.replace(day=1), state="generated")
        with pytest.raises(PermissionDeniedError):
            billing.finalize(student_actor, bill.pk)
        bill.refresh_from_db()
        assert bill.state == "generated"
    elif test_id == "UC-011-EXC":
        other_bill = MonthlyBill.objects.create(
            user_id=202, month=today.replace(day=1), state="published"
        )
        assert not scoping.monthly_bills_for(student_actor).filter(pk=other_bill.pk).exists()
    elif test_id == "UC-012-EXC":
        student_actor.permissions.discard("mms.feedback.create")
        with pytest.raises(PermissionDeniedError):
            feedback.submit(student_actor, "Valid feedback")
        assert Feedback.objects.count() == 0
    elif test_id == "UC-013-EXC":
        other_feedback = Feedback.objects.create(user_id=202, text="Private feedback")
        assert not scoping.feedback_for(student_actor).filter(pk=other_feedback.pk).exists()
    elif test_id == "UC-014-EXC":
        student_actor.permissions.discard("mms.rebate.create")
        count_before = RebateRequest.objects.count()
        with pytest.raises(PermissionDeniedError):
            rebate.submit(student_actor, "medical", "", today + timedelta(days=2), today + timedelta(days=5))
        assert RebateRequest.objects.count() == count_before
    elif test_id == "UC-015-EXC":
        request = RebateRequest.objects.create(
            user_id=101,
            reason="medical",
            start_date=today + timedelta(days=2),
            end_date=today + timedelta(days=5),
            status="pending",
        )
        with pytest.raises(PermissionDeniedError):
            rebate.decide(student_actor, request.pk, approve=True)
        request.refresh_from_db()
        assert request.status == "pending"
    elif test_id == "UC-016-EXC":
        count_before = VacationSurvey.objects.count()
        with pytest.raises(PermissionDeniedError):
            survey.create(student_actor, "Winter recess", now + timedelta(days=2))
        assert VacationSurvey.objects.count() == count_before
    elif test_id == "UC-017-EXC":
        student_actor.permissions.discard("mms.survey_response.create")
        open_survey = VacationSurvey.objects.create(
            vacation="Winter recess", response_deadline=now + timedelta(days=2), created_by_user_id=201
        )
        with pytest.raises(PermissionDeniedError):
            survey.respond(student_actor, open_survey.pk, "yes")
        assert not VacationResponse.objects.filter(survey=open_survey.pk).exists()
    elif test_id == "UC-018-EXC":
        other_response = VacationResponse.objects.create(
            survey=1, student_user_id=202, response="yes"
        )
        assert not scoping.vacation_responses_for(student_actor).filter(pk=other_response.pk).exists()
    elif test_id == "UC-019-EXC":
        student_actor.permissions.discard("mms.special_food.create")
        count_before = SpecialFoodRequest.objects.count()
        with pytest.raises(PermissionDeniedError):
            special_food.submit(student_actor, "Illness", today + timedelta(days=1))
        assert SpecialFoodRequest.objects.count() == count_before
    elif test_id == "UC-020-EXC":
        request = SpecialFoodRequest.objects.create(
            user_id=101,
            reason="Illness",
            requested_date=today + timedelta(days=1),
            status="requested",
            decision_due_at=now + timedelta(days=1),
        )
        with pytest.raises(PermissionDeniedError):
            special_food.decide(student_actor, request.pk, approve=True)
        request.refresh_from_db()
        assert request.status == "requested"
    elif test_id == "UC-021-EXC":
        student_actor.permissions.discard("mms.special_food.update")
        request = SpecialFoodRequest.objects.create(
            user_id=101,
            reason="Illness",
            requested_date=today + timedelta(days=1),
            status="approved",
            decided_at=now,
            decided_by_user_id=201,
        )
        with pytest.raises(PermissionDeniedError):
            special_food.fulfill(student_actor, request.pk, "served")
        request.refresh_from_db()
        assert request.status == "approved"
    elif test_id == "UC-022-EXC":
        count_before = Announcement.objects.count()
        with pytest.raises(PermissionDeniedError):
            announcement.publish(student_actor, "Title", "Body")
        assert Announcement.objects.count() == count_before
    elif test_id == "UC-023-EXC":
        count_before = Announcement.objects.count()
        list(scoping.announcements_for(student_actor))
        assert Announcement.objects.count() == count_before
    elif test_id == "UC-024-EXC":
        with pytest.raises(PermissionDeniedError):
            reports.get_supervisory_report(student_actor)
    elif test_id == "UC-025-EXC":
        with pytest.raises(PermissionDeniedError):
            reports.get_operational_report(warden_actor)
    elif test_id == "UC-026-EXC":
        other_request = Deregistration.objects.create(user_id=202, status="pending")
        assert not scoping.deregistration_requests_for(student_actor).filter(pk=other_request.pk).exists()
    elif test_id == "UC-027-EXC":
        request = Deregistration.objects.create(user_id=101, status="rejected")
        assert deregistration.activate_approved() == 0
        request.refresh_from_db()
        assert request.status == "rejected"
    elif test_id == "UC-028-EXC":
        Registration.objects.create(user_id=101, status="approved")
        opened = VacationSurvey.objects.create(
            vacation="Winter recess", response_deadline=now - timedelta(minutes=1), created_by_user_id=201
        )
        explicit = VacationResponse.objects.create(
            survey=opened.pk, student_user_id=101, response="no", responded_at=now - timedelta(hours=1)
        )
        survey.apply_default_no()
        explicit.refresh_from_db()
        assert explicit.response == "no"
    elif test_id == "UC-029-EXC":
        request = SpecialFoodRequest.objects.create(
            user_id=101,
            reason="Illness",
            requested_date=today + timedelta(days=1),
            status="approved",
            decision_due_at=now - timedelta(minutes=1),
            decided_at=now - timedelta(hours=1),
            decided_by_user_id=201,
        )
        assert special_food.default_reject_undecided() == 0
        request.refresh_from_db()
        assert request.status == "approved"
    elif test_id == "UC-030-EXC":
        from django.db import OperationalError

        source_registration = Registration.objects.create(user_id=101, status="approved")

        def fail_bill_write(**_kwargs):
            raise OperationalError("simulated database write failure")

        monkeypatch.setattr(MonthlyBill.objects, "create", fail_bill_write)
        with pytest.raises(OperationalError):
            billing.generate_monthly()

        source_registration.refresh_from_db()
        assert source_registration.status == "approved"
        assert MonthlyBill.objects.count() == 0
    elif test_id == "UC-031-EXC":
        pytest.skip(
            "NOT_AUTOMATED: external email-delivery failure behavior is outside MMS scope, "
            "and no email transport failure interface is available"
        )
    else:
        opened = VacationSurvey.objects.create(
            vacation="Winter recess", response_deadline=now + timedelta(days=2), created_by_user_id=201
        )
        assert survey.send_reminders() == 1
        opened.refresh_from_db()
        assert opened.is_open
        assert NotificationOutbox.objects.filter(topic="survey.reminder").exists()
