"""Tests for FR-010: Automatic SLA breach check endpoint.

The view ``ComplaintSlaCheckView`` triggers two service functions:
``check_and_escalate_sla_breaches`` and ``check_and_send_sla_reminders``.
Both return the count of affected complaints. The exact HTTP status code is
implementation‑derived (normally ``200 OK``).
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
        """Fallback freeze_time implementation when freezegun is not installed.
        Parses an ISO datetime string and patches django.utils.timezone.now.
        Returns a frozen object with ``time_to_freeze`` attribute and ``move_to`` method.
        """
        fixed = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        class Frozen:
            time_to_freeze = fixed
            def move_to(self, new_time):
                self.time_to_freeze = new_time
        frozen = Frozen()
        with patch('django.utils.timezone.now', return_value=frozen.time_to_freeze):
            yield frozen


from modules.complaints.tests.spec.helpers import complaint_factory
from modules.complaints.services import complaints as complaint_services


@pytest.mark.django_db
def test_sla_breach_escalation(api_client, stub_iam, make_session, complaint_factory):
    """A complaint past its SLA deadline should be escalated automatically.

    The test creates a complaint with ``sla_deadline`` in the past, invokes the
    SLA check endpoint, and verifies that the escalation count is ``1`` and that
    the complaint's ``escalation_type`` is set to ``AUTOMATIC_SLA``.
    """
    # Freeze time to a known point so we can set a past deadline reliably.
    with freeze_time("2023-01-01T12:00:00Z") as frozen:
        # Create a complaint with a deadline 1 hour earlier.
        from datetime import timedelta
        past_deadline = frozen.time_to_freeze - timedelta(hours=1)
        complaint = complaint_factory(
            status="in_progress",
            sla_deadline=past_deadline,
        )

        # Session with permission to trigger the endpoint (module grant sufficient).
        make_session(
            user_id=2,
            permissions=["complaints.complaint.sla_check"],
            active_role="complaint_handler",
        )

        url = "/api/v1/complaints/sla-check/"
        response = api_client.post(url, {}, format="json")
        # Implementation‑derived status code.
        assert response.status_code == 200
        data = response.json()
        # The service returns the number of escalated complaints.
        assert data.get("escalated_count") == 1
        # Verify the complaint was escalated.
        complaint.refresh_from_db()
        assert complaint.escalation_type == "automatic"
        assert isinstance(data.get("reminders_sent"), int)

