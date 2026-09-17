"""Clocks start with a state, stop with it, and chase nobody once it moves on."""
from datetime import date, timedelta

import pytest
from django.utils import timezone

from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import Actor, Event, State
from modules.leave.models import LeaveRequest, SlaClock, SlaRule, SubstituteNomination
from modules.leave.services import sla
from modules.leave.services.workflow import apply_event
from modules.leave.tests import factories

pytestmark = pytest.mark.django_db

EMPLOYEE = 501
SUBSTITUTE = 502


@pytest.fixture
def policy():
    policy = factories.make_policy()
    factories.make_calendar()
    factories.make_authority(policy)
    for state, remind, escalate in (
        (State.AWAITING_SUBSTITUTE, 24, 48),
        (State.AWAITING_UNIT_HEAD, 48, 96),
        (State.AWAITING_FINAL_SANCTION, 48, 120),
    ):
        SlaRule.objects.create(
            policy_id=policy.pk, state=state.value,
            remind_after_hours=remind, escalate_after_hours=escalate,
        )
    return policy


def make_request(policy, state=State.DRAFT) -> LeaveRequest:
    return LeaveRequest.objects.create(
        user_id=EMPLOYEE, category=Category.CL.value, state=state.value,
        starts_on=date(2026, 3, 2), ends_on=date(2026, 3, 3), reason="Personal",
        requested_days=2, policy_id=policy.pk, unit="CSE",
    )


class TestTheClockFollowsTheState:
    def test_entering_a_controlled_state_starts_a_clock(self, policy):
        request = make_request(policy)
        SubstituteNomination.objects.create(
            request=request, substitute_user_id=SUBSTITUTE)

        apply_event(request, Event.SUBMIT, Actor.EMPLOYEE,
                    target=State.AWAITING_SUBSTITUTE)

        clock = SlaClock.objects.get(request=request, stopped_at__isnull=True)
        assert clock.state == State.AWAITING_SUBSTITUTE.value
        assert clock.escalate_at - clock.remind_at == timedelta(hours=24)

    def test_the_clock_names_the_substitute_being_waited_on(self, policy):
        request = make_request(policy)
        SubstituteNomination.objects.create(
            request=request, substitute_user_id=SUBSTITUTE)

        apply_event(request, Event.SUBMIT, Actor.EMPLOYEE,
                    target=State.AWAITING_SUBSTITUTE)

        assert SlaClock.objects.get(request=request).assigned_user_id == SUBSTITUTE

    def test_a_queue_state_names_no_individual(self, policy):
        request = make_request(policy)

        apply_event(request, Event.SUBMIT, Actor.EMPLOYEE,
                    target=State.AWAITING_UNIT_HEAD)

        # An office holds this, not a person; the queue is the assignment.
        assert SlaClock.objects.get(request=request).assigned_user_id is None

    def test_moving_on_stops_the_old_clock_and_starts_a_new_one(self, policy):
        request = make_request(policy)
        SubstituteNomination.objects.create(
            request=request, substitute_user_id=SUBSTITUTE)
        apply_event(request, Event.SUBMIT, Actor.EMPLOYEE,
                    target=State.AWAITING_SUBSTITUTE)

        apply_event(request, Event.SUBSTITUTE_ACCEPT, Actor.SUBSTITUTE)

        assert SlaClock.objects.filter(stopped_at__isnull=True).count() == 1
        assert SlaClock.objects.get(
            stopped_at__isnull=True).state == State.AWAITING_UNIT_HEAD.value

    def test_a_state_with_no_rule_is_not_chased(self, policy):
        SlaRule.objects.filter(state=State.AWAITING_UNIT_HEAD.value).delete()
        request = make_request(policy)

        apply_event(request, Event.SUBMIT, Actor.EMPLOYEE,
                    target=State.AWAITING_UNIT_HEAD)

        assert not SlaClock.objects.filter(stopped_at__isnull=True).exists()

    def test_a_decided_request_has_no_running_clock(self, policy):
        request = make_request(policy)
        apply_event(request, Event.SUBMIT, Actor.EMPLOYEE,
                    target=State.AWAITING_UNIT_HEAD)

        apply_event(request, Event.UNIT_HEAD_REJECT, Actor.UNIT_HEAD)

        assert not SlaClock.objects.filter(stopped_at__isnull=True).exists()


class TestProcessing:
    def _waiting(self, policy, hours: int) -> SlaClock:
        request = make_request(policy)
        apply_event(request, Event.SUBMIT, Actor.EMPLOYEE,
                    target=State.AWAITING_UNIT_HEAD)
        clock = SlaClock.objects.get(request=request)
        started = timezone.now() - timedelta(hours=hours)
        SlaClock.objects.filter(pk=clock.pk).update(
            started_at=started,
            remind_at=started + timedelta(hours=48),
            escalate_at=started + timedelta(hours=96),
        )
        clock.refresh_from_db()
        return clock

    def test_nothing_happens_before_the_threshold(self, policy):
        self._waiting(policy, hours=1)

        report = sla.process()

        assert (report.reminded, report.escalated) == (0, 0)

    def test_a_reminder_is_sent_once(self, policy):
        clock = self._waiting(policy, hours=50)

        first = sla.process()
        second = sla.process()

        assert (first.reminded, second.reminded) == (1, 0)
        clock.refresh_from_db()
        assert clock.reminded_at is not None

    def test_escalation_follows_when_it_keeps_waiting(self, policy):
        clock = self._waiting(policy, hours=100)

        report = sla.process()

        assert report.escalated == 1
        clock.refresh_from_db()
        assert clock.escalated_at is not None

    def test_a_task_no_longer_pending_is_not_chased(self, policy):
        clock = self._waiting(policy, hours=100)
        sla.stop(clock.request)

        report = sla.process()

        assert (report.reminded, report.escalated, report.still_open) == (0, 0, 0)

    def test_thresholds_come_from_the_policy_not_from_code(self, policy):
        SlaRule.objects.filter(state=State.AWAITING_UNIT_HEAD.value).update(
            remind_after_hours=1, escalate_after_hours=2)
        request = make_request(policy)

        apply_event(request, Event.SUBMIT, Actor.EMPLOYEE,
                    target=State.AWAITING_UNIT_HEAD)

        clock = SlaClock.objects.get(request=request)
        assert clock.remind_at - clock.started_at == timedelta(hours=1)


class TestASelfTransitionDoesNotResetTheClock:
    """BR-EL-032, BR-EL-033. Querying a resumption is not a fresh task."""

    def _awaiting_verification(self, policy):
        SlaRule.objects.get_or_create(
            policy_id=policy.pk,
            state=State.AWAITING_RESUMPTION_VERIFICATION.value,
            defaults={"remind_after_hours": 24, "escalate_after_hours": 48})
        request = make_request(policy)
        request.state = State.AWAITING_RESUMPTION_VERIFICATION.value
        request.save(update_fields=["state"])
        return sla.on_state_change(
            request, State.AWAITING_RESUMPTION_VERIFICATION)

    def test_the_original_clock_survives(self, policy):
        clock = self._awaiting_verification(policy)
        started = clock.started_at

        again = sla.on_state_change(
            clock.request,
            State.AWAITING_RESUMPTION_VERIFICATION,
            source=State.AWAITING_RESUMPTION_VERIFICATION)

        assert again.pk == clock.pk
        assert again.started_at == started

    def test_the_deadline_is_not_pushed_out(self, policy):
        clock = self._awaiting_verification(policy)
        escalate_at = clock.escalate_at

        sla.on_state_change(
            clock.request,
            State.AWAITING_RESUMPTION_VERIFICATION,
            source=State.AWAITING_RESUMPTION_VERIFICATION)

        clock.refresh_from_db()
        assert clock.escalate_at == escalate_at

    def test_only_one_clock_is_ever_running(self, policy):
        clock = self._awaiting_verification(policy)

        for _ in range(3):
            sla.on_state_change(
                clock.request,
                State.AWAITING_RESUMPTION_VERIFICATION,
                source=State.AWAITING_RESUMPTION_VERIFICATION)

        assert SlaClock.objects.filter(stopped_at__isnull=True).count() == 1

    def test_a_real_move_still_starts_a_new_one(self, policy):
        clock = self._awaiting_verification(policy)

        sla.on_state_change(clock.request, State.AWAITING_UNIT_HEAD,
                            source=State.AWAITING_RESUMPTION_VERIFICATION)

        clock.refresh_from_db()
        assert clock.stopped_at is not None
