"""Tests for role-scoped queryset narrowing in IWD."""

import pytest

from conftest import make_principal
from modules.iwd.models import Complaint
from modules.iwd.selectors.scoping import scope_complaints

pytestmark = pytest.mark.django_db


def test_scope_complaints_none_principal():
    """Verify None principal returns empty queryset."""
    Complaint.objects.create(requester_user_id=1, category="Civil", remarks="c1", location="L1")
    assert scope_complaints(None).count() == 0


def test_scope_complaints_regular_user_isolation():
    """Verify regular user sees only their own complaints."""
    c1 = Complaint.objects.create(
        requester_user_id=10, category="Civil", remarks="User 10", location="L1"
    )
    Complaint.objects.create(
        requester_user_id=20, category="Civil", remarks="User 20", location="L2"
    )

    p10 = make_principal(user_id=10, active_role="student")
    scoped = scope_complaints(p10)

    assert scoped.count() == 1
    assert scoped.first() == c1


def test_scope_complaints_assigned_engineer():
    """Verify engineer sees only complaints assigned to them."""
    c1 = Complaint.objects.create(
        requester_user_id=10,
        assigned_engineer_id=100,
        category="Civil",
        remarks="Assigned to 100",
        location="L1",
    )
    Complaint.objects.create(
        requester_user_id=10,
        assigned_engineer_id=200,
        category="Civil",
        remarks="Assigned to 200",
        location="L2",
    )

    p_eng = make_principal(user_id=100, active_role="iwd_engineer")
    scoped = scope_complaints(p_eng)

    assert scoped.count() == 1
    assert scoped.first() == c1


def test_scope_complaints_department_head_sees_all():
    """Verify department head has overarching visibility across complaints."""
    Complaint.objects.create(requester_user_id=1, category="Civil", remarks="C1", location="L1")
    Complaint.objects.create(
        requester_user_id=2, category="Electrical", remarks="C2", location="L2"
    )

    p_head = make_principal(user_id=50, active_role="iwd_department_head")
    scoped = scope_complaints(p_head)

    assert scoped.count() == 2
