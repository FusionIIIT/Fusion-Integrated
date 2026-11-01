"""Fixtures for the leave suite: a configured module, with no IAM anywhere."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import (
    AcademicVacationPeriod,
    HolidayCalendar,
    HolidayCalendarDay,
    LeaveHierarchyStep,
    LeavePolicy,
    SlaThreshold,
)

MODULE = "leave"


@pytest.fixture
def policy(db):
    return LeavePolicy.objects.create(
        is_active=True,
        entitlements={},
        substitute_required_categories=[],
        self_sanction_designation="Director",
    )


@pytest.fixture
def hierarchy(db):
    return [
        LeaveHierarchyStep.objects.create(sequence=10, kind="unit_head",
                                          designation="HOD (CSE)"),
        LeaveHierarchyStep.objects.create(sequence=20, kind="establishment",
                                          designation="Deputy Registrar (Estt.)"),
        LeaveHierarchyStep.objects.create(sequence=30, kind="final_authority",
                                          designation="Registrar"),
    ]


@pytest.fixture
def vacation(db):
    today = timezone.localdate()
    return AcademicVacationPeriod.objects.create(
        start_date=today + timedelta(days=10),
        end_date=today + timedelta(days=30), label="Winter vacation")


@pytest.fixture
def calendar(db):
    today = timezone.localdate()
    row = HolidayCalendar.objects.create(
        year=today.year, version=1, effective_from=today.replace(month=1, day=1),
        published_at=timezone.now())
    HolidayCalendarDay.objects.create(
        calendar=row, date=today + timedelta(days=3), kind="holiday",
        name="Institute holiday")
    HolidayCalendarDay.objects.create(
        calendar=row, date=today + timedelta(days=4), kind="restricted",
        name="Restricted holiday")
    return row


@pytest.fixture
def thresholds(db):
    return [
        SlaThreshold.objects.create(task_class="unit_head_review",
                                    reminder_hours=24, escalation_hours=48),
        SlaThreshold.objects.create(task_class="substitute_response",
                                    reminder_hours=24, escalation_hours=72),
    ]


@pytest.fixture
def configured(policy, hierarchy, vacation, calendar, thresholds):
    """Everything the module needs before a first request can be validated."""
    return policy


def leave_client(stub_iam, *, user_id=1001, permissions=(), kind="staff",
                 active_role="", roles=("staff",), modules=(MODULE,)):
    """A client authenticated as one principal; the two gates are set apart."""
    stub_iam(make_session(user_id=user_id, kind=kind, permissions=permissions,
                          modules=modules, roles=roles, active_role=active_role))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


EMPLOYEE_PERMISSIONS = (
    "leave.request.view", "leave.request.create", "leave.request.delete",
    "leave.cancellation.create", "leave.extension.create",
    "leave.resumption.create", "leave.substitute.review", "leave.balance.view",
    "leave.application.export", "leave.calendar.view",
)
UNIT_HEAD_PERMISSIONS = ("leave.request.view", "leave.request.review")
AUTHORITY_PERMISSIONS = ("leave.request.view", "leave.request.review",
                         "leave.request.approve", "leave.resumption.review")
ADMIN_PERMISSIONS = ("leave.request.view", "leave.record.view", "leave.record.update",
                     "leave.calendar.view", "leave.calendar.publish",
                     "leave.policy.update", "leave.threshold.update")


@pytest.fixture
def employee(stub_iam):
    def _make(user_id=1001, **kw):
        return leave_client(stub_iam, user_id=user_id,
                            permissions=EMPLOYEE_PERMISSIONS, **kw)

    return _make


@pytest.fixture
def unit_head(stub_iam):
    def _make(user_id=9001, **kw):
        return leave_client(stub_iam, user_id=user_id,
                            permissions=UNIT_HEAD_PERMISSIONS,
                            active_role="HOD (CSE)", **kw)

    return _make


@pytest.fixture
def authority(stub_iam):
    def _make(user_id=9002, **kw):
        return leave_client(stub_iam, user_id=user_id,
                            permissions=AUTHORITY_PERMISSIONS,
                            active_role="Registrar", **kw)

    return _make


@pytest.fixture
def establishment(stub_iam):
    def _make(user_id=9003, **kw):
        return leave_client(stub_iam, user_id=user_id,
                            permissions=("leave.request.view", "leave.request.review"),
                            active_role="Deputy Registrar (Estt.)", **kw)

    return _make


@pytest.fixture
def admin(stub_iam):
    def _make(user_id=9004, **kw):
        return leave_client(stub_iam, user_id=user_id, permissions=ADMIN_PERMISSIONS,
                            **kw)

    return _make
