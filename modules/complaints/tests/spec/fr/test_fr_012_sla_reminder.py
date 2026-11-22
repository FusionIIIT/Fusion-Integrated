"""Tests for FR-012: 75 % SLA reminder emission.

The specification mentions a reminder when 75 % of the SLA interval has
elapsed. The implementation provides ``check_and_send_sla_reminders`` which
sets the ``sla_reminder_sent`` flag on qualifying complaints. No external
notification channel is defined, so the test validates the flag and that the
function returns the correct count.
"""

import pytest
try:
    from freezegun import freeze_time
except ImportError:
    from contextlib import contextmanager
    from datetime import datetime, timezone
    from unittest.mock import patch

    @contextmanager
    def freeze_time(time_str):
        """Fallback freeze_time implementation when freezegun is unavailable.
        Parses an ISO datetime string and patches django.utils.timezone.now.
        Returns an object with `time_to_freeze` attribute and `move_to` method.
        """
        fixed = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        class Frozen:
            time_to_freeze = fixed
            def move_to(self, new_time):
                self.time_to_freeze = new_time
        frozen = Frozen()
        with patch('django.utils.timezone.now', return_value=frozen.time_to_freeze):
            yield frozen
from datetime import timedelta

from modules.complaints.tests.spec.helpers import complaint_factory
from modules.complaints.services import complaints as complaint_services


@pytest.mark.django_db
def test_sla_75_percent_reminder(api_client, stub_iam, make_session, complaint_factory):
    """A complaint with 75 % of its SLA elapsed should have ``sla_reminder_sent``
    set to ``True`` after invoking the reminder service.
    """
    # Freeze time to a known point.
    with freeze_time("2023-01-01T12:00:00Z") as frozen:
        # Create a complaint with a deadline 4 hours ahead (total duration 4h).
        total_duration = timedelta(hours=4)
        deadline = frozen.time_to_freeze + total_duration
        # Advance the frozen time to 75% of the duration (3 hours later).
        frozen.move_to(frozen.time_to_freeze + timedelta(hours=3))
        complaint = complaint_factory(
            status="in_progress",
            sla_deadline=deadline,
            sla_reminder_sent=False,
        )

        # Session with permission to trigger reminder endpoint (module grant is enough).
        make_session(
            user_id=2,
            permissions=["complaints.complaint.sla_check"],
            active_role="complaint_handler",
        )

        # Directly call the service function to avoid relying on the view.
        reminder_count = complaint_services.check_and_send_sla_reminders()
        assert reminder_count == 1
        complaint.refresh_from_db()
        assert complaint.sla_reminder_sent is True

