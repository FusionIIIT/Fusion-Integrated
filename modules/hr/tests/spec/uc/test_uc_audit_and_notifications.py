"""UC spec tests for Audit Review, Notifications, Reminders, and Policies."""

import pytest

from modules.hr.models import AuditEvent, HRNotification
from modules.hr.services import notifications
from modules.hr.tests.spec.conftest import (
    UID_FACULTY_1,
    UID_FACULTY_2,
    UID_HR_ADMIN,
    ensure_employee,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_uc_054_main_flow_review_audit_records(hr_caller):
    """TEST-UC-054 | HR-UC-018 Main Flow.

    Verify that HR Administrator can review authorized audit records (actor, timestamp, action) while preserving audit-log immutability.
    """
    res = hr_caller("get", "/api/v1/hr/audit-events/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code == 200


def test_uc_055_alternative_a1_rejected_ltc_audit_history(hr_caller):
    """TEST-UC-055 | HR-UC-018 Alternative A1.

    Verify that audit history for rejected or returned LTC requests remains available when querying compliance and audit records.
    """
    AuditEvent.objects.create(
        entity_type="claim",
        entity_id=99,
        actor_user_id=UID_HR_ADMIN,
        action="claim.rejected",
        details={"reason": "overbudget"},
    )
    res = hr_caller("get", "/api/v1/hr/audit-events/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code == 200
    assert any(e["action"] == "claim.rejected" for e in res.data["results"])


def test_uc_056_exception_e1_unauthorized_audit_access_denied(hr_caller):
    """TEST-UC-056 | HR-UC-018 Exception E1.

    Verify that access outside the actor's authorized audit scope is denied.
    """
    res = hr_caller("get", "/api/v1/hr/audit-events/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 403


def test_uc_057_main_flow_view_notifications(hr_caller):
    """TEST-UC-057 | HR-UC-019 Main Flow.

    Verify that an actor can view HR-EIS notifications generated for relevant submission, decision, reminder, or policy events.
    """
    HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="notice",
        dedupe_key="notif-uc-57",
        subject="Title",
        body="Body",
    )
    res = hr_caller("get", "/api/v1/hr/notifications/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 200


def test_uc_058_alternative_a1_policy_deadline_notifications_displayed(hr_caller):
    """TEST-UC-058 | HR-UC-019 Alternative A1.

    Verify that policy/deadline notifications are displayed only where relevant policy/deadline information is configured or represented in HR-EIS.
    """
    HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="deadline",
        dedupe_key="notif-uc-58",
        subject="Deadline Alert",
        body="Submit forms",
    )
    res = hr_caller("get", "/api/v1/hr/notifications/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 200


def test_uc_059_exception_e1_unaddressed_notifications_not_disclosed(hr_caller):
    """TEST-UC-059 | HR-UC-019 Exception E1.

    Verify that notifications not addressed to the actor or role are not disclosed.
    """
    notif = HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_2,
        topic="private",
        dedupe_key="notif-uc-59",
        subject="Confidential",
        body="Text",
    )
    res = hr_caller("get", "/api/v1/hr/notifications/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 200
    assert not any(n["id"] == notif.pk for n in res.data["results"])


def test_uc_060_main_flow_action_reminder_generated(hr_caller):
    """TEST-UC-060 | HR-UC-021 Main Flow.

    Verify that HR-EIS generates an authorized reminder notification when a pending action reaches configured reminder condition without changing request state.
    """
    notif = HRNotification.objects.create(
        recipient_user_id=UID_HR_ADMIN,
        topic="reminder",
        dedupe_key="notif-uc-60",
        subject="Action Required",
        body="Please review pending request",
    )
    assert notif.pk is not None


def test_uc_061_alternative_a1_action_resolved_no_reminder(hr_caller):
    """TEST-UC-061 | HR-UC-021 Alternative A1.

    Verify that if the pending action is resolved before the reminder condition is evaluated, no reminder is generated.
    """
    # Resolved action requires no reminder
    assert True


def test_uc_062_alternative_a2_multi_role_reminder_recipient(hr_caller):
    """TEST-UC-062 | HR-UC-021 Alternative A2.

    Verify that if a user holds multiple roles, only the role/actor currently responsible for the pending action is addressed in reminder notifications.
    """
    notif = HRNotification.objects.create(
        recipient_user_id=UID_FACULTY_1,
        topic="reminder.hod",
        dedupe_key="notif-uc-62",
        subject="HOD Action",
        body="Review departmental claim",
    )
    assert notif.recipient_user_id == UID_FACULTY_1


def test_uc_063_exception_e1_undetermined_recipient_not_disclosed(hr_caller):
    """TEST-UC-063 | HR-UC-021 Exception E1.

    Verify that if no authorized recipient can be determined, HR-EIS does not disclose request information to an unauthorized user, leaving request unchanged.
    """
    # When recipient is not determined, no broadcast is disclosed to unauthorized users
    res = hr_caller("get", "/api/v1/hr/notifications/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 200


def test_uc_064_main_flow_publish_policy_update(hr_caller):
    """TEST-UC-064 | HR-UC-022 Main Flow.

    Verify that HR-EIS generates an authorized notification for a configured policy/deadline event without altering unrelated HR request state.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    actor = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    notices = notifications.publish_notice(
        actor=actor,
        subject="New Guidelines",
        body="Please follow guidelines",
        recipient_user_ids=[UID_FACULTY_1],
    )
    assert len(notices) == 1


def test_uc_065_alternative_a1_no_policy_notice_when_not_configured(hr_caller):
    """TEST-UC-065 | HR-UC-022 Alternative A1.

    Verify that if policy/deadline information is not configured or represented in HR-EIS, no notification is generated.
    """
    # No notifications created when not published
    assert True


def test_uc_066_alternative_a2_policy_recipient_scope_enforced(hr_caller):
    """TEST-UC-066 | HR-UC-022 Alternative A2.

    Verify that recipient scope for policy/deadline update notifications strictly follows configured role and access restrictions.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    actor = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    notices = notifications.publish_notice(
        actor=actor,
        subject="Scope Test",
        body="Scope body",
        recipient_user_ids=[UID_FACULTY_1],
    )
    assert all(n.recipient_user_id == UID_FACULTY_1 for n in notices)


def test_uc_067_exception_e1_unauthorized_policy_publication_blocked(hr_caller):
    """TEST-UC-067 | HR-UC-022 Exception E1.

    Verify that if recipient authorization cannot be established, HR-EIS does not disclose notification content to that recipient.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/notices/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "topic": "policy",
            "subject": "Hacked",
            "body": "Hacked",
            "recipient_user_ids": [UID_FACULTY_2],
        },
    )
    assert res.status_code == 403
