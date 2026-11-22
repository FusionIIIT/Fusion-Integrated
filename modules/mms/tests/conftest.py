"""Test fixtures for MMS module tests."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest


@dataclass
class MockPrincipal:
    user_id: int
    kind: str
    permissions: set[str] = field(default_factory=set)

    def has_permission(self, code: str) -> bool:
        return code in self.permissions


@pytest.fixture
def student_actor():
    return MockPrincipal(
        user_id=101,
        kind="student",
        permissions={
            "mms.registration.create",
            "mms.deregistration.create",
            "mms.menu.view",
            "mms.billing.view_self",
            "mms.rebate.create",
            "mms.survey_response.create",
            "mms.special_food.create",
            "mms.announcement.view",
            "mms.feedback.create",
            "mms.request.view_self",
        },
    )


@pytest.fixture
def caretaker_actor():
    return MockPrincipal(
        user_id=201,
        kind="staff",
        permissions={
            "mms.registration.window.manage",
            "mms.registration.review",
            "mms.deregistration.review",
            "mms.menu.view",
            "mms.menu.manage",
            "mms.billing.review",
            "mms.billing.approve",
            "mms.billing.publish",
            "mms.rebate.review",
            "mms.rebate.update",
            "mms.survey.create",
            "mms.survey.view_summary",
            "mms.special_food.review",
            "mms.special_food.update",
            "mms.announcement.publish",
            "mms.announcement.view",
            "mms.feedback.view",
            "mms.report.operational",
            "mms.request.view_self",
        },
    )


@pytest.fixture
def warden_actor():
    return MockPrincipal(
        user_id=301,
        kind="faculty",
        permissions={
            "mms.menu.view",
            "mms.billing.view_self",
            "mms.survey.view_summary",
            "mms.announcement.publish",
            "mms.announcement.view",
            "mms.feedback.view",
            "mms.report.supervisory",
            "mms.request.view_self",
        },
    )


@pytest.fixture
def mess_admin_actor():
    return MockPrincipal(
        user_id=401,
        kind="staff",
        permissions={
            "mms.role.assign",
        },
    )
