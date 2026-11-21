"""Unit tests for System Administrator domain state machines.

Pure Python tests: no DB, no network, runs in milliseconds.
Tests:
  - RoleStateMachine (CW-SA-02, BW-SA-03..05, UC-SA-010..011, UC-SA-028..029)
  - UserLifecycleStateMachine (CW-SA-03, BW-SA-06..08, UC-SA-005, UC-SA-015, UC-SA-018, UC-SA-031)
  - PurgeAuthorizationStateMachine (CW-SA-01, BW-SA-01..02, UC-SA-022..023)
"""
from datetime import date, datetime, timedelta
import pytest

from modules.system_admin.domain import (
    ArchivalEligibilityVerdict,
    InvalidStateTransitionError,
    PURGE_APPROVED,
    PURGE_COMPLETED,
    PURGE_NOT_REQUESTED,
    PURGE_PENDING_IT_HEAD,
    PURGE_REJECTED,
    ROLE_ACTIVE,
    ROLE_EXPIRED,
    ROLE_EXTENDED,
    ROLE_REVOKED,
    ROLE_SCHEDULED,
    ROLE_TERMINAL_STATES,
    RoleStateMachine,
    USER_ACTIVE,
    USER_ARCHIVED_PERMANENT,
    USER_ARCHIVED_REVERSIBLE,
    USER_DEACTIVATED,
    PurgeAuthorizationStateMachine,
    UserLifecycleStateMachine,
)


# =============================================================================
# A. Role State Machine Tests (CW-SA-02)
# =============================================================================

class TestRoleStateMachine:
    today = date(2026, 11, 2)
    past = date(2026, 11, 1)
    future = date(2026, 11, 5)

    def test_immediate_assignment_today_or_past(self):
        # BW-SA-03: Immediate activation if start_date <= today
        assert RoleStateMachine.validate_immediate_assignment(self.today, self.today) == ROLE_ACTIVE
        assert RoleStateMachine.validate_immediate_assignment(self.past, self.today) == ROLE_ACTIVE

    def test_immediate_assignment_future(self):
        # Future start date transitions to scheduled
        assert RoleStateMachine.validate_immediate_assignment(self.future, self.today) == ROLE_SCHEDULED

    def test_can_activate(self):
        # BW-SA-04 / UC-SA-028: Scheduled -> Active when start_date <= today
        assert RoleStateMachine.can_activate(ROLE_SCHEDULED, self.today, self.today) is True
        assert RoleStateMachine.can_activate(ROLE_SCHEDULED, self.past, self.today) is True
        assert RoleStateMachine.can_activate(ROLE_SCHEDULED, self.future, self.today) is False

        # Non-scheduled state cannot activate
        assert RoleStateMachine.can_activate(ROLE_ACTIVE, self.today, self.today) is False
        assert RoleStateMachine.can_activate(ROLE_REVOKED, self.today, self.today) is False

    def test_can_extend_active_and_extended(self):
        # BW-SA-05 / UC-SA-011: Active/Extended -> Extended if new_end_date > current_end_date
        current_end = date(2026, 11, 10)
        new_end = date(2026, 12, 1)
        same_end = date(2026, 11, 10)
        earlier_end = date(2026, 11, 5)

        assert RoleStateMachine.can_extend(ROLE_ACTIVE, current_end, new_end, self.today) is True
        assert RoleStateMachine.can_extend(ROLE_EXTENDED, current_end, new_end, self.today) is True

        # Cannot extend if new date <= current end date
        assert RoleStateMachine.can_extend(ROLE_ACTIVE, current_end, same_end, self.today) is False
        assert RoleStateMachine.can_extend(ROLE_ACTIVE, current_end, earlier_end, self.today) is False

    def test_cannot_extend_already_expired_role(self):
        # Cannot extend if today > current_end_date
        past_end = date(2026, 10, 31)
        new_end = date(2026, 12, 1)
        assert RoleStateMachine.can_extend(ROLE_ACTIVE, past_end, new_end, self.today) is False

    def test_cannot_extend_non_extensible_states(self):
        current_end = date(2026, 11, 10)
        new_end = date(2026, 12, 1)
        for state in [ROLE_SCHEDULED, ROLE_EXPIRED, ROLE_REVOKED]:
            assert RoleStateMachine.can_extend(state, current_end, new_end, self.today) is False

    def test_can_expire(self):
        # UC-SA-029: Active/Extended -> Expired when today >= end_date
        past_end = date(2026, 11, 1)
        future_end = date(2026, 11, 10)

        assert RoleStateMachine.can_expire(ROLE_ACTIVE, self.today, self.today) is True
        assert RoleStateMachine.can_expire(ROLE_ACTIVE, past_end, self.today) is True
        assert RoleStateMachine.can_expire(ROLE_EXTENDED, self.today, self.today) is True
        assert RoleStateMachine.can_expire(ROLE_ACTIVE, future_end, self.today) is False

        # Indefinite role (end_date=None) does not expire
        assert RoleStateMachine.can_expire(ROLE_ACTIVE, None, self.today) is False

        # States other than Active/Extended do not expire
        for state in [ROLE_SCHEDULED, ROLE_EXPIRED, ROLE_REVOKED]:
            assert RoleStateMachine.can_expire(state, past_end, self.today) is False

    def test_can_revoke(self):
        # UC-SA-010: Scheduled, Active, Extended can be revoked
        assert RoleStateMachine.can_revoke(ROLE_SCHEDULED) is True
        assert RoleStateMachine.can_revoke(ROLE_ACTIVE) is True
        assert RoleStateMachine.can_revoke(ROLE_EXTENDED) is True

        # Expired and Revoked (terminal) cannot be revoked
        assert RoleStateMachine.can_revoke(ROLE_EXPIRED) is False
        assert RoleStateMachine.can_revoke(ROLE_REVOKED) is False

    def test_terminal_states(self):
        assert ROLE_TERMINAL_STATES == frozenset({ROLE_EXPIRED, ROLE_REVOKED})


# =============================================================================
# B. User Lifecycle State Machine Tests (CW-SA-03)
# =============================================================================

class TestUserLifecycleStateMachine:
    def test_can_deactivate(self):
        assert UserLifecycleStateMachine.can_deactivate(USER_ACTIVE) is True
        assert UserLifecycleStateMachine.can_deactivate(USER_DEACTIVATED) is False
        assert UserLifecycleStateMachine.can_deactivate(USER_ARCHIVED_REVERSIBLE) is False
        assert UserLifecycleStateMachine.can_deactivate(USER_ARCHIVED_PERMANENT) is False

    def test_can_reactivate(self):
        # BW-SA-06 / UC-SA-005: Deactivated -> Active
        assert UserLifecycleStateMachine.can_reactivate(USER_DEACTIVATED) is True
        assert UserLifecycleStateMachine.can_reactivate(USER_ACTIVE) is False
        assert UserLifecycleStateMachine.can_reactivate(USER_ARCHIVED_REVERSIBLE) is False
        assert UserLifecycleStateMachine.can_reactivate(USER_ARCHIVED_PERMANENT) is False

    def test_can_archive(self):
        # UC-SA-015: Deactivated -> Archived Reversible if eligibility verdict is True
        eligible_verdict = ArchivalEligibilityVerdict(is_eligible=True)
        ineligible_verdict = ArchivalEligibilityVerdict(is_eligible=False, reason="Pending tasks")

        assert UserLifecycleStateMachine.can_archive(USER_DEACTIVATED, eligible_verdict) is True
        assert UserLifecycleStateMachine.can_archive(USER_DEACTIVATED, ineligible_verdict) is False

        # Active or already archived cannot transition to archived
        assert UserLifecycleStateMachine.can_archive(USER_ACTIVE, eligible_verdict) is False
        assert UserLifecycleStateMachine.can_archive(USER_ARCHIVED_REVERSIBLE, eligible_verdict) is False

    def test_can_restore_from_archive(self):
        # BW-SA-07 / UC-SA-018: Restorable only within reversible window (BR-SA-005)
        now = datetime(2026, 11, 2, 12, 0, 0)
        window_open = now + timedelta(days=5)
        window_expired = now - timedelta(days=1)

        # In window
        assert UserLifecycleStateMachine.can_restore_from_archive(
            USER_ARCHIVED_REVERSIBLE, window_open, now
        ) is True
        # Exact boundary
        assert UserLifecycleStateMachine.can_restore_from_archive(
            USER_ARCHIVED_REVERSIBLE, now, now
        ) is True
        # Window expired
        assert UserLifecycleStateMachine.can_restore_from_archive(
            USER_ARCHIVED_REVERSIBLE, window_expired, now
        ) is False

        # Other states cannot be restored from archive
        assert UserLifecycleStateMachine.can_restore_from_archive(
            USER_DEACTIVATED, window_open, now
        ) is False
        assert UserLifecycleStateMachine.can_restore_from_archive(
            USER_ARCHIVED_PERMANENT, window_open, now
        ) is False

    def test_can_finalize_permanent(self):
        # BW-SA-08 / UC-SA-031 / ISS-SA-004: Reversible -> Permanent once window expires
        now = datetime(2026, 11, 2, 12, 0, 0)
        window_open = now + timedelta(days=5)
        window_expired = now - timedelta(days=1)

        assert UserLifecycleStateMachine.can_finalize_permanent(
            USER_ARCHIVED_REVERSIBLE, window_expired, now
        ) is True
        # Still in window -> cannot finalize
        assert UserLifecycleStateMachine.can_finalize_permanent(
            USER_ARCHIVED_REVERSIBLE, window_open, now
        ) is False
        assert UserLifecycleStateMachine.can_finalize_permanent(
            USER_ARCHIVED_REVERSIBLE, now, now
        ) is False

        # Other states cannot finalize
        assert UserLifecycleStateMachine.can_finalize_permanent(
            USER_ACTIVE, window_expired, now
        ) is False
        assert UserLifecycleStateMachine.can_finalize_permanent(
            USER_DEACTIVATED, window_expired, now
        ) is False


# =============================================================================
# C. Purge Authorization State Machine Tests (CW-SA-01)
# =============================================================================

class TestPurgeAuthorizationStateMachine:
    def test_can_request_purge(self):
        # UC-SA-022 / BR-SA-021: Super Admin requests purge after retention period
        assert PurgeAuthorizationStateMachine.can_request_purge(retention_expired=True) is True
        assert PurgeAuthorizationStateMachine.can_request_purge(retention_expired=False) is False

    def test_transition_on_decision_approved(self):
        # BW-SA-01 / UC-SA-023: IT Head approves
        next_state = PurgeAuthorizationStateMachine.transition_on_decision(
            PURGE_PENDING_IT_HEAD, it_head_approved=True
        )
        assert next_state == PURGE_APPROVED

    def test_transition_on_decision_rejected(self):
        # BW-SA-02 / UC-SA-023: IT Head rejects
        next_state = PurgeAuthorizationStateMachine.transition_on_decision(
            PURGE_PENDING_IT_HEAD, it_head_approved=False
        )
        assert next_state == PURGE_REJECTED

    def test_transition_on_decision_invalid_state_raises(self):
        # Calling decision on non-pending state raises InvalidStateTransitionError
        for invalid_state in [PURGE_NOT_REQUESTED, PURGE_APPROVED, PURGE_REJECTED, PURGE_COMPLETED]:
            with pytest.raises(InvalidStateTransitionError) as exc_info:
                PurgeAuthorizationStateMachine.transition_on_decision(
                    invalid_state, it_head_approved=True
                )
            assert exc_info.value.code == "invalid_state_transition"
            assert exc_info.value.from_state == invalid_state
