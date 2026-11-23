"""Every branch of the pure rules added with uploads, targeting and reporting; no database."""
import datetime

import pytest

from modules.gymkhana.domain.constants import MAX_UPLOAD_BYTES, POSTER_EXTENSIONS
from modules.gymkhana.domain.exceptions import DomainValidationError
from modules.gymkhana.domain.state_machines import (
    CLUB_TRANSITIONS,
    MEMBERSHIP_TRANSITIONS,
    POLL_TRANSITIONS,
    transition_club,
    transition_membership,
    transition_poll,
)
from modules.gymkhana.domain.validation import (
    validate_booking_times,
    validate_event_has_occurred,
    validate_file_present,
    validate_not_own_application,
    validate_poll_active,
    validate_target_groups,
    validate_upload,
)

NOW = datetime.datetime(2026, 12, 1, tzinfo=datetime.UTC)
SECOND = datetime.timedelta(seconds=1)


def test_br_gym_013_groups_are_normalised_and_deduplicated():
    groups = [(" ALL ", "All"), ("2024", " CSE "), ("2024", "CSE")]
    assert validate_target_groups(groups) == [("all", "all"), ("2024", "CSE")]


@pytest.mark.parametrize("groups", [
    [], [("24", "CSE")], [("2024x", "CSE")], [("", "CSE")], [("2024", "")],
    [("2024", "x" * 51)], [("2024\n", "")], [("all", "all"), ("bad", "CSE")],
])
def test_br_gym_013_an_unusable_group_is_refused(groups):
    with pytest.raises(DomainValidationError):
        validate_target_groups(groups)


def test_uc_gym_010_an_event_may_be_reported_from_the_moment_it_occurs():
    validate_event_has_occurred(NOW, NOW)
    with pytest.raises(DomainValidationError):
        validate_event_has_occurred(NOW + SECOND, NOW)


def test_br_gym_014_a_poll_closes_at_its_expiry():
    validate_poll_active(NOW + SECOND, NOW)
    with pytest.raises(DomainValidationError):
        validate_poll_active(NOW, NOW)


def test_br_gym_010_an_applicant_is_never_the_approver():
    validate_not_own_application(1, 2)
    with pytest.raises(DomainValidationError):
        validate_not_own_application(1, 1)


def test_br_gym_005_equal_times_are_not_a_range():
    ten = datetime.time(10)
    validate_booking_times(ten, datetime.time(10, 1))
    with pytest.raises(DomainValidationError):
        validate_booking_times(ten, ten)


def test_br_gym_018_019_a_missing_file_is_named():
    validate_file_present(True, "report_file")
    with pytest.raises(DomainValidationError, match="report_file"):
        validate_file_present(False, "report_file")


def test_a_file_at_the_size_limit_is_accepted_and_one_byte_more_is_not():
    ok = {"name": "a.PDF", "head": b"%PDF", "extensions": POSTER_EXTENSIONS}
    validate_upload(size=MAX_UPLOAD_BYTES, **ok)
    with pytest.raises(DomainValidationError, match="5 MB"):
        validate_upload(size=MAX_UPLOAD_BYTES + 1, **ok)


@pytest.mark.parametrize(("table", "move"), [
    (CLUB_TRANSITIONS, transition_club),
    (MEMBERSHIP_TRANSITIONS, transition_membership),
    (POLL_TRANSITIONS, transition_poll),
])
def test_every_transition_outside_its_table_is_refused(table, move):
    states = {"open", "confirmed", "active", "expired", "rejected"}
    events = {"CONFIRM", "APPROVE", "EXPIRE", "REJECT", "CANCEL"}
    actors = {"student_admin", "club_head", "system", "student", "faculty"}
    for key in ((s, e, a) for s in states for e in events for a in actors):
        if key in table:
            assert move(*key) == table[key]
        else:
            with pytest.raises(Exception, match="Cannot transition"):
                move(*key)
