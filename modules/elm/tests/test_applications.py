"""Submitting and deciding, through the service choke point (Steps 5.2, 5.7).

Every positive case here has a negative twin: a refusal asserted only by
code, so a message rewrite cannot make a test pass for the wrong reason.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.models import LeaveApplication, LeaveBalanceEntry
from modules.elm.selectors import queries
from modules.elm.services import applications as service
from modules.elm.tests.support import APPROVER_PERMS, principal

pytestmark = pytest.mark.django_db

EMPLOYEE = 1001
APPROVER_ID = 2002


def employee(**kw):
    return principal(user_id=EMPLOYEE, **kw)


def approver(**kw):
    return principal(user_id=APPROVER_ID, permissions=APPROVER_PERMS,
                     kind="faculty", roles=("Leave Approver",),
                     active_role="Leave Approver", **kw)


class TestSubmission:

    def test_a_plain_request_is_recorded_with_its_frozen_days(self, make_type,
                                                              next_monday):
        leave_type = make_type()
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday + timedelta(days=1),
            reason="Family function")
        assert application.status == "pending"
        assert application.days == Decimal(2)
        assert application.events.count() == 1
        assert application.events.first().to_status == "pending"

    def test_the_first_submission_grants_the_annual_entitlement(self, make_type,
                                                                next_monday):
        leave_type = make_type()
        service.submit_application(actor=employee(), leave_type_id=leave_type.pk,
                                   start_date=next_monday, end_date=next_monday)
        assert queries.available_days(EMPLOYEE, "CL", next_monday.year) == Decimal("8.0")

    def test_a_reason_required_type_refuses_a_blank_reason(self, make_type,
                                                           next_monday):
        leave_type = make_type(code="EL", name="Earned Leave",
                               requires_reason=True, allows_half_day=False)
        with pytest.raises(ConflictError) as err:
            service.submit_application(actor=employee(),
                                       leave_type_id=leave_type.pk,
                                       start_date=next_monday,
                                       end_date=next_monday)
        assert err.value.code == "reason_required"
        assert not LeaveApplication.objects.exists()

    def test_an_overlapping_request_is_refused(self, make_type, next_monday):
        leave_type = make_type()
        service.submit_application(actor=employee(), leave_type_id=leave_type.pk,
                                   start_date=next_monday,
                                   end_date=next_monday + timedelta(days=1))
        with pytest.raises(ConflictError) as err:
            service.submit_application(
                actor=employee(), leave_type_id=leave_type.pk,
                start_date=next_monday + timedelta(days=1),
                end_date=next_monday + timedelta(days=2))
        assert err.value.code == "overlapping_leave"
        assert LeaveApplication.objects.count() == 1

    def test_an_unknown_type_is_a_404_style_refusal(self, next_monday):
        with pytest.raises(NotFoundError):
            service.submit_application(actor=employee(), leave_type_id=9999,
                                       start_date=next_monday,
                                       end_date=next_monday)

    def test_a_second_active_request_starting_the_same_day_cannot_exist(
            self, make_type, next_monday):
        leave_type = make_type()
        LeaveApplication.objects.create(user_id=EMPLOYEE, leave_type=leave_type,
                                        start_date=next_monday,
                                        end_date=next_monday, days=1)
        with transaction.atomic(), pytest.raises(IntegrityError):
            LeaveApplication.objects.create(user_id=EMPLOYEE,
                                            leave_type=leave_type,
                                            start_date=next_monday,
                                            end_date=next_monday, days=1)


class TestDecision:

    def test_an_approver_approves_and_the_ledger_is_debited(self, make_type,
                                                            next_monday):
        leave_type = make_type()
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday)
        decided = service.transition(actor=approver(),
                                     application_id=application.pk,
                                     to_status="approved", note="Approved")
        assert decided.status == "approved"
        assert decided.decided_by_user_id == APPROVER_ID
        debit = LeaveBalanceEntry.objects.get(application=application,
                                              kind="debit")
        assert debit.days == Decimal("-1.0")
        assert queries.available_days(EMPLOYEE, "CL", next_monday.year) == Decimal("7.0")

    def test_an_approver_cannot_approve_their_own_request(self, make_type,
                                                          next_monday):
        leave_type = make_type()
        application = LeaveApplication.objects.create(
            user_id=APPROVER_ID, leave_type=leave_type, start_date=next_monday,
            end_date=next_monday, days=1)
        with pytest.raises(PermissionDeniedError) as err:
            service.transition(actor=approver(), application_id=application.pk,
                               to_status="approved")
        assert err.value.code == "self_approval_denied"

    def test_a_request_with_no_balance_is_refused(self, make_type, next_monday):
        leave_type = make_type(code="COL", name="Compensatory Off",
                               entitlement="0.0", allows_half_day=False,
                               requires_reason=True)
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday, reason="Worked Sunday")
        with pytest.raises(ConflictError) as err:
            service.transition(actor=approver(), application_id=application.pk,
                               to_status="approved")
        assert err.value.code == "insufficient_balance"
        assert not LeaveBalanceEntry.objects.filter(kind="debit").exists()

    def test_a_rejection_without_a_note_is_refused(self, make_type, next_monday):
        leave_type = make_type()
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday)
        with pytest.raises(ConflictError) as err:
            service.transition(actor=approver(), application_id=application.pk,
                               to_status="rejected", note="  ")
        assert err.value.code == "decision_note_required"

    def test_a_rejection_with_a_note_records_it(self, make_type, next_monday):
        leave_type = make_type()
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday)
        decided = service.transition(actor=approver(),
                                     application_id=application.pk,
                                     to_status="rejected",
                                     note="Team is short-staffed that week.")
        assert decided.status == "rejected"
        assert decided.decision_note == "Team is short-staffed that week."

    def test_an_employee_cannot_approve(self, make_type, next_monday):
        leave_type = make_type()
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday)
        with pytest.raises(PermissionDeniedError) as err:
            service.transition(actor=employee(), application_id=application.pk,
                               to_status="approved")
        assert err.value.code == "actor_not_allowed"


class TestWithdrawalAndCancellation:

    def test_the_owner_withdraws_a_pending_request(self, make_type, next_monday):
        leave_type = make_type()
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday)
        withdrawn = service.transition(actor=employee(),
                                       application_id=application.pk,
                                       to_status="withdrawn")
        assert withdrawn.status == "withdrawn"
        assert not LeaveBalanceEntry.objects.filter(kind="debit").exists()

    def test_an_approver_cannot_withdraw_someone_elses_request(self, make_type,
                                                               next_monday):
        leave_type = make_type()
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday)
        with pytest.raises(PermissionDeniedError) as err:
            service.transition(actor=approver(), application_id=application.pk,
                               to_status="withdrawn")
        assert err.value.code == "actor_not_allowed"

    def test_cancelling_an_approved_request_restores_the_balance(self, make_type,
                                                                 next_monday):
        leave_type = make_type()
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday)
        service.transition(actor=approver(), application_id=application.pk,
                           to_status="approved", note="Approved")
        after_approval = queries.available_days(EMPLOYEE, "CL", next_monday.year)

        cancelled = service.transition(actor=employee(),
                                       application_id=application.pk,
                                       to_status="cancelled")
        assert cancelled.status == "cancelled"
        restored = queries.available_days(EMPLOYEE, "CL", next_monday.year)
        assert restored - after_approval == Decimal("1.0")
        assert LeaveBalanceEntry.objects.get(application=application,
                                             kind="reversal").days == Decimal("1.0")

    def test_a_finished_leave_cannot_be_cancelled(self, make_type, next_monday):
        leave_type = make_type()
        today = timezone.localdate()
        finished = LeaveApplication.objects.create(
            user_id=EMPLOYEE, leave_type=leave_type,
            start_date=today - timedelta(days=10), end_date=today - timedelta(days=9),
            days=2, status="approved")
        with pytest.raises(ConflictError) as err:
            service.transition(actor=employee(), application_id=finished.pk,
                               to_status="cancelled")
        assert err.value.code == "leave_finished"

    def test_a_terminal_request_cannot_move_again(self, make_type, next_monday):
        leave_type = make_type()
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday)
        service.transition(actor=employee(), application_id=application.pk,
                           to_status="withdrawn")
        with pytest.raises(ConflictError) as err:
            service.transition(actor=employee(), application_id=application.pk,
                               to_status="cancelled")
        assert err.value.code == "invalid_transition"

    def test_an_unknown_target_status_is_refused(self, make_type, next_monday):
        leave_type = make_type()
        application = service.submit_application(
            actor=employee(), leave_type_id=leave_type.pk,
            start_date=next_monday, end_date=next_monday)
        with pytest.raises(BadRequestError) as err:
            service.transition(actor=employee(), application_id=application.pk,
                               to_status="vanished")
        assert err.value.code == "unknown_status"
