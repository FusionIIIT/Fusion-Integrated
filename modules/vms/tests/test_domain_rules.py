"""Comprehensive unit tests for VMS domain business rules and invariants."""

from datetime import UTC, datetime, timedelta

import pytest

from modules.vms.domain.errors import (
    BlacklistedVisitorError,
    GateAccessDeniedError,
    InvalidStateTransitionError,
    InvalidTimeWindowError,
    PassNotActiveError,
)
from modules.vms.domain.rules import (
    check_blacklist_guard,
    validate_checkout_transition,
    validate_pass_gate_access,
    validate_visit_time_window,
)


class TestVmsDomainRulesComprehensive:
    """Exhaustive boundary and invariant tests for domain rules."""

    @pytest.mark.parametrize(
        ("duration_hours", "max_limit"),
        [
            (0.1, 24),
            (0.5, 24),
            (1.0, 24),
            (2.0, 24),
            (4.0, 24),
            (6.0, 24),
            (8.0, 24),
            (10.0, 24),
            (12.0, 24),
            (16.0, 24),
            (20.0, 24),
            (23.5, 24),
            (23.9, 24),
            (1.0, 12),
            (5.0, 12),
            (11.9, 12),
            (0.5, 8),
            (4.0, 8),
            (7.5, 8),
            (0.2, 4),
        ],
    )
    def test_valid_visit_time_window_durations(self, duration_hours, max_limit):
        now = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
        start = now
        end = now + timedelta(hours=duration_hours)
        validate_visit_time_window(start, end, max_hours=max_limit)

    @pytest.mark.parametrize(
        ("start_offset", "end_offset"),
        [
            (10, 10),
            (15, 10),
            (20, 19),
            (5, -2),
            (100, 50),
            (1, 0),
            (0.5, 0),
            (24, 0),
            (50, 49),
            (1000, 999),
        ],
    )
    def test_invalid_start_after_end_time_window(self, start_offset, end_offset):
        now = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
        start = now + timedelta(hours=start_offset)
        end = now + timedelta(hours=end_offset)
        with pytest.raises(InvalidTimeWindowError):
            validate_visit_time_window(start, end)

    @pytest.mark.parametrize(
        "exceeded_hours",
        [24.1, 25.0, 30.0, 48.0, 72.0, 100.0, 120.0, 200.0, 500.0, 1000.0],
    )
    def test_max_duration_exceeded_rejected(self, exceeded_hours):
        now = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
        start = now
        end = now + timedelta(hours=exceeded_hours)
        with pytest.raises(InvalidTimeWindowError, match="cannot exceed maximum allowed limit"):
            validate_visit_time_window(start, end, max_hours=24)

    @pytest.mark.parametrize(
        "invalid_status",
        [
            "PENDING_HOST_APPROVAL",
            "REJECTED",
            "EXPIRED",
            "DEACTIVATED",
            "COMPLETED",
            "CANCELLED",
            "SUSPENDED",
            "UNKNOWN",
            "",
            "REVOKED",
        ],
    )
    def test_pass_gate_access_non_active_status_denied(self, invalid_status):
        now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
        valid_from = now - timedelta(hours=1)
        valid_until = now + timedelta(hours=4)
        with pytest.raises(PassNotActiveError, match="expected 'ACTIVE'"):
            validate_pass_gate_access(
                pass_status=invalid_status,
                valid_from=valid_from,
                valid_until=valid_until,
                permitted_zones=["MAIN_CAMPUS"],
                gate_zone="MAIN_CAMPUS",
                now=now,
            )

    @pytest.mark.parametrize(
        "time_offset_minutes",
        [-1, -5, -30, -60, -120, -300, -720, -1440, -2880, -4320],
    )
    def test_pass_gate_access_before_valid_from_denied(self, time_offset_minutes):
        now = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
        valid_from = now + timedelta(minutes=abs(time_offset_minutes))
        valid_until = valid_from + timedelta(hours=4)
        with pytest.raises(PassNotActiveError, match="outside the approved pass validity window"):
            validate_pass_gate_access(
                pass_status="ACTIVE",
                valid_from=valid_from,
                valid_until=valid_until,
                permitted_zones=["MAIN_CAMPUS"],
                gate_zone="MAIN_CAMPUS",
                now=now,
            )

    @pytest.mark.parametrize(
        "expired_offset_minutes",
        [1, 5, 10, 30, 60, 120, 300, 720, 1440, 5000],
    )
    def test_pass_gate_access_after_valid_until_denied(self, expired_offset_minutes):
        now = datetime(2026, 11, 20, 18, 0, tzinfo=UTC)
        valid_until = now - timedelta(minutes=expired_offset_minutes)
        valid_from = valid_until - timedelta(hours=4)
        with pytest.raises(PassNotActiveError, match="outside the approved pass validity window"):
            validate_pass_gate_access(
                pass_status="ACTIVE",
                valid_from=valid_from,
                valid_until=valid_until,
                permitted_zones=["MAIN_CAMPUS"],
                gate_zone="MAIN_CAMPUS",
                now=now,
            )

    @pytest.mark.parametrize(
        ("gate_zone", "permitted_zones"),
        [
            ("HOSTEL_ZONE", ["MAIN_CAMPUS", "ACADEMIC_ZONE"]),
            ("RESTRICTED_LABS", ["MAIN_CAMPUS"]),
            ("FACULTY_RESIDENCE", ["STUDENT_ACTIVITY_CENTER"]),
            ("SUBSTATION", ["MAIN_GATE", "LIBRARY"]),
            ("DATA_CENTER", ["GUEST_HOUSE"]),
            ("SECURITY_HQ", ["PLAYGROUND"]),
            ("ZONE_A", ["ZONE_B", "ZONE_C"]),
            ("ZONE_X", ["ZONE_Y"]),
            ("CAMPUS_EAST", ["CAMPUS_WEST"]),
            ("VIP_LOUNGE", ["GENERAL_PARKING"]),
        ],
    )
    def test_pass_gate_access_unauthorized_zone_denied(self, gate_zone, permitted_zones):
        now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
        valid_from = now - timedelta(hours=1)
        valid_until = now + timedelta(hours=3)
        with pytest.raises(GateAccessDeniedError, match="not in permitted zones"):
            validate_pass_gate_access(
                pass_status="ACTIVE",
                valid_from=valid_from,
                valid_until=valid_until,
                permitted_zones=permitted_zones,
                gate_zone=gate_zone,
                now=now,
            )

    @pytest.mark.parametrize(
        ("gate_zone", "permitted_zones"),
        [
            ("MAIN_CAMPUS", ["MAIN_CAMPUS"]),
            ("ACADEMIC_ZONE", ["MAIN_CAMPUS", "ACADEMIC_ZONE"]),
            ("LIBRARY", ["LIBRARY", "HOSTELS", "CORE_LABS"]),
            ("GUEST_HOUSE", ["GUEST_HOUSE"]),
            ("GATE_01", ["GATE_01", "ALL"]),
            ("ANY_ZONE", []),
            ("LAB_01", ["LAB_01", "LAB_02"]),
            ("SAC", ["SAC", "HOSTEL_ZONE"]),
            ("CENTRAL_MESS", ["CENTRAL_MESS", "STUDENT_CENTER"]),
            ("ADMIN_BLOCK", ["ADMIN_BLOCK"]),
        ],
    )
    def test_pass_gate_access_permitted_zone_success(self, gate_zone, permitted_zones):
        now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
        valid_from = now - timedelta(hours=1)
        valid_until = now + timedelta(hours=3)
        validate_pass_gate_access(
            pass_status="ACTIVE",
            valid_from=valid_from,
            valid_until=valid_until,
            permitted_zones=permitted_zones,
            gate_zone=gate_zone,
            now=now,
        )

    @pytest.mark.parametrize(
        "invalid_checkout_status",
        [
            "PENDING",
            "COMPLETED",
            "EXPIRED",
            "CANCELLED",
            "DENIED",
            "DEPARTED",
            "OVERSTAYED",
            "NOT_CHECKED_IN",
            "SCHEDULED",
            "",
        ],
    )
    def test_checkout_transition_invalid_status_rejected(self, invalid_checkout_status):
        with pytest.raises(InvalidStateTransitionError, match="Must be 'ON_SITE'"):
            validate_checkout_transition(invalid_checkout_status)

    def test_checkout_transition_valid_status_success(self):
        validate_checkout_transition("ON_SITE")

    @pytest.mark.parametrize(
        "reason",
        [
            "Criminal investigation pending",
            "Barred by disciplinary committee",
            "Active security threat",
            "Restraining order",
            "Fake credentials in prior visit",
        ],
    )
    def test_blacklist_guard_flagged_raises(self, reason):
        with pytest.raises(BlacklistedVisitorError):
            check_blacklist_guard(True, reason)

    @pytest.mark.parametrize(
        "clean_status",
        [False, False, False, False, False],
    )
    def test_blacklist_guard_clean_passes(self, clean_status):
        check_blacklist_guard(clean_status, "")
