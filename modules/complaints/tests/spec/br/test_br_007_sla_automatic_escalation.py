"""BR-007 – Automatic SLA Breach Escalation.

Business Rule:
Automatic SLA escalation occurs only for overdue complaints not yet resolved
(Page 4 – Workflow BW-CMS-08).
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from modules.complaints import services
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_br_007_overdue_unresolved_complaint_is_escalated(complaint_factory):
    """Overdue complaint in submitted or in_progress status is automatically escalated."""
    now = timezone.now()
    past_deadline = now - timedelta(hours=2)

    c1 = complaint_factory(
        status="submitted",
        sla_deadline=past_deadline,
        is_escalated=False,
    )
    c2 = complaint_factory(
        status="in_progress",
        sla_deadline=past_deadline,
        is_escalated=False,
    )

    escalated_count = services.check_and_escalate_sla_breaches()
    assert escalated_count == 2

    c1.refresh_from_db()
    c2.refresh_from_db()

    assert c1.is_escalated is True
    assert c1.escalation_type == "automatic_sla"
    assert c2.is_escalated is True
    assert c2.escalation_type == "automatic_sla"

@pytest.mark.django_db
def test_br_007_overdue_resolved_or_closed_complaint_not_escalated(complaint_factory):
    """Overdue complaints that are already resolved or closed must NOT be escalated."""
    now = timezone.now()
    past_deadline = now - timedelta(hours=5)

    c_resolved = complaint_factory(
        status="resolved",
        sla_deadline=past_deadline,
        is_escalated=False,
    )
    c_closed = complaint_factory(
        status="closed",
        sla_deadline=past_deadline,
        is_escalated=False,
    )

    escalated_count = services.check_and_escalate_sla_breaches()
    assert escalated_count == 0

    c_resolved.refresh_from_db()
    c_closed.refresh_from_db()

    assert c_resolved.is_escalated is False
    assert c_closed.is_escalated is False

@pytest.mark.django_db
def test_br_007_not_overdue_complaint_not_escalated(complaint_factory):
    """Complaints with future SLA deadline are not escalated."""
    now = timezone.now()
    future_deadline = now + timedelta(hours=24)

    c = complaint_factory(
        status="submitted",
        sla_deadline=future_deadline,
        is_escalated=False,
    )

    escalated_count = services.check_and_escalate_sla_breaches()
    assert escalated_count == 0

    c.refresh_from_db()
    assert c.is_escalated is False
