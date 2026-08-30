"""Policy and calendar maintenance, and leave that arrived on paper."""
from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain.categories import Category
from modules.leave.domain.counting import Half
from modules.leave.domain.state_machine import State
from modules.leave.models import (
    CategoryRule,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    LedgerEntry,
)
from modules.leave.selectors import balances
from modules.leave.selectors import policy as policy_selector
from modules.leave.services import administration
from modules.leave.tests import factories

pytestmark = pytest.mark.django_db

D = Decimal
ADMIN = 900
EMPLOYEE = 501


def _draft_policy(version="2027.1", effective_from=date(2027, 1, 1)) -> LeavePolicy:
    policy = LeavePolicy.objects.create(
        version=version, effective_from=effective_from, published=False
    )
    CategoryRule.objects.create(
        policy=policy, category=Category.CL.value, annual_credit=D(8), carries_forward=False
    )
    return policy


class TestPolicyPublication:
    def test_publishing_closes_the_version_it_supersedes(self):
        current = factories.make_policy()
        assert current.effective_to is None

        administration.publish_policy(policy=_draft_policy(), actor_user_id=ADMIN)

        current.refresh_from_db()
        assert current.effective_to == date(2027, 1, 1)

    def test_a_decision_taken_before_the_change_still_resolves_to_the_old_version(self):
        current = factories.make_policy()
        administration.publish_policy(policy=_draft_policy(), actor_user_id=ADMIN)

        assert policy_selector.effective_policy(date(2026, 6, 1)).pk == current.pk

    def test_a_version_with_no_rules_is_refused(self):
        empty = LeavePolicy.objects.create(
            version="2028.1", effective_from=date(2028, 1, 1), published=False
        )
        with pytest.raises(BadRequestError, match="no category rules"):
            administration.publish_policy(policy=empty, actor_user_id=ADMIN)

    def test_publishing_twice_is_refused(self):
        policy = _draft_policy()
        administration.publish_policy(policy=policy, actor_user_id=ADMIN)
        with pytest.raises(ConflictError, match="already published"):
            administration.publish_policy(policy=policy, actor_user_id=ADMIN)


class TestCalendarMaintenance:
    def test_a_published_calendar_cannot_be_edited(self):
        calendar = factories.make_calendar()
        with pytest.raises(ConflictError, match="cannot be edited"):
            administration.add_holiday(
                calendar=calendar, day=date(2026, 12, 25), name="Christmas"
            )

    def test_publishing_a_replacement_retires_the_earlier_one(self):
        first = factories.make_calendar()
        second = HolidayCalendar.objects.create(year=2026, version="2", published=False)
        Holiday.objects.create(calendar=second, day=date(2026, 8, 15), name="Independence Day")

        administration.publish_calendar(calendar=second, actor_user_id=ADMIN)

        first.refresh_from_db()
        assert first.published is False
        assert policy_selector.effective_calendar(2026).pk == second.pk

    def test_an_empty_calendar_is_refused(self):
        draft = HolidayCalendar.objects.create(year=2027, version="1", published=False)
        with pytest.raises(BadRequestError, match="unfinished"):
            administration.publish_calendar(calendar=draft, actor_user_id=ADMIN)

    def test_a_vacation_period_cannot_end_before_it_starts(self):
        draft = HolidayCalendar.objects.create(year=2027, version="1", published=False)
        with pytest.raises(BadRequestError, match="cannot end before"):
            administration.add_vacation_period(
                calendar=draft,
                name="Summer",
                starts_on=date(2027, 6, 30),
                ends_on=date(2027, 5, 15),
            )


class TestOfflineRecording:
    def test_it_lands_closed_and_charges_the_balance(self):
        factories.setup_all(EMPLOYEE)

        recorded = administration.record_offline(
            user_id=EMPLOYEE,
            category=Category.CL,
            starts_on=date(2026, 3, 2),
            ends_on=date(2026, 3, 4),
            reason="Sanctioned on file before the module went live",
            recorded_by_user_id=ADMIN,
        )

        assert recorded.state == State.CLOSED.value
        assert recorded.requested_days == recorded.actual_days == D(3)
        assert balances.balance_for(EMPLOYEE, 2026, Category.CL).available == D(5)

    def test_the_entry_names_who_recorded_it(self):
        factories.setup_all(EMPLOYEE)
        recorded = administration.record_offline(
            user_id=EMPLOYEE,
            category=Category.CL,
            starts_on=date(2026, 3, 2),
            ends_on=date(2026, 3, 2),
            reason="On file",
            recorded_by_user_id=ADMIN,
        )
        entry = LedgerEntry.objects.get(request_id=recorded.pk)
        assert entry.recorded_by_user_id == ADMIN

    def test_the_trail_shows_it_was_never_approved_here(self):
        factories.setup_all(EMPLOYEE)
        recorded = administration.record_offline(
            user_id=EMPLOYEE,
            category=Category.CL,
            starts_on=date(2026, 3, 2),
            ends_on=date(2026, 3, 2),
            reason="On file",
            recorded_by_user_id=ADMIN,
            note="Sanction letter 44/2026",
        )
        trail = list(recorded.transitions.all())
        assert [t.event for t in trail] == ["OFFLINE_RECORD"]
        assert trail[0].actor_user_id == ADMIN
        assert trail[0].remark == "Sanction letter 44/2026"

    def test_recording_the_same_period_twice_is_refused(self):
        factories.setup_all(EMPLOYEE)
        administration.record_offline(
            user_id=EMPLOYEE,
            category=Category.CL,
            starts_on=date(2026, 3, 2),
            ends_on=date(2026, 3, 4),
            reason="On file",
            recorded_by_user_id=ADMIN,
        )
        with pytest.raises(ConflictError, match="already on the record"):
            administration.record_offline(
                user_id=EMPLOYEE,
                category=Category.CL,
                starts_on=date(2026, 3, 2),
                ends_on=date(2026, 3, 4),
                reason="On file",
                recorded_by_user_id=ADMIN,
            )

    def test_an_employee_cannot_record_their_own(self):
        factories.setup_all(EMPLOYEE)
        with pytest.raises(BadRequestError, match="not by the employee"):
            administration.record_offline(
                user_id=EMPLOYEE,
                category=Category.CL,
                starts_on=date(2026, 3, 2),
                ends_on=date(2026, 3, 2),
                reason="On file",
                recorded_by_user_id=EMPLOYEE,
            )

    def test_a_half_day_is_refused_for_a_category_that_has_none(self):
        factories.setup_all(EMPLOYEE)
        with pytest.raises(BadRequestError, match="half day"):
            administration.record_offline(
                user_id=EMPLOYEE,
                category=Category.EL,
                starts_on=date(2026, 3, 2),
                ends_on=date(2026, 3, 2),
                reason="On file",
                recorded_by_user_id=ADMIN,
                half=Half.FIRST,
            )

    def test_it_is_charged_under_the_policy_in_force_on_the_day_taken(self):
        current, _ = factories.setup_all(EMPLOYEE)
        administration.publish_policy(policy=_draft_policy(), actor_user_id=ADMIN)

        recorded = administration.record_offline(
            user_id=EMPLOYEE,
            category=Category.CL,
            starts_on=date(2026, 3, 2),
            ends_on=date(2026, 3, 2),
            reason="On file",
            recorded_by_user_id=ADMIN,
        )
        assert recorded.policy_id == current.pk
