"""Actual query scoping for each IAM acting-role context."""

import pytest

from fusion_auth.principal import Principal
from modules.hreis.models import (
    ApprovalRouteStep,
    AuditEvent,
    EmployeeServiceRecord,
    HRRequest,
    Notification,
)
from modules.hreis.selectors import scoping

pytestmark = pytest.mark.django_db


def _actor(user_id: int, role: str, *permissions: str, modules=("hreis",)) -> Principal:
    return Principal(
        user_id=user_id,
        username=f"user{user_id}",
        display_name="Synthetic",
        kind="faculty",
        active_role=role,
        roles=(role,),
        permissions=frozenset(permissions),
        modules=modules,
    )


@pytest.fixture
def two_records():
    return [
        EmployeeServiceRecord.objects.create(
            user_id=i,
            appointment_details={},
            department="CSE",
            designation_snapshot="Assistant Professor",
        )
        for i in (10, 20)
    ]


@pytest.fixture
def assigned_requests():
    first = HRRequest.objects.create(
        user_id=10,
        family="leave",
        state="pending_authority",
        route_step=0,
    )
    second = HRRequest.objects.create(
        user_id=20,
        family="ltc",
        state="pending_authority",
        route_step=1,
    )
    third = HRRequest.objects.create(
        user_id=20,
        family="leave",
        state="approved",
        route_step=0,
    )
    ApprovalRouteStep.objects.create(
        request=first,
        position=0,
        designation="HOD (CSE)",
        policy_version_label="leave-1",
    )
    ApprovalRouteStep.objects.create(
        request=second,
        position=0,
        designation="HOD (CSE)",
        policy_version_label="ltc-1",
    )
    ApprovalRouteStep.objects.create(
        request=second,
        position=1,
        designation="Director",
        policy_version_label="ltc-1",
    )
    ApprovalRouteStep.objects.create(
        request=third,
        position=0,
        designation="HOD (CSE)",
        policy_version_label="leave-1",
    )
    return first, second, third


def test_employee_only_sees_own_record_even_with_view_permission(two_records):
    actor = _actor(10, "faculty", scoping.P_RECORD_VIEW)
    assert list(scoping.service_records_for(actor)) == [two_records[0]]
    assert not scoping.service_records_for(actor).filter(user_id=20).exists()
    with pytest.raises(EmployeeServiceRecord.DoesNotExist):
        scoping.service_records_for(actor).get(pk=two_records[1].pk)


def test_hradmin_may_read_authorized_employee_records(two_records):
    actor = _actor(99, "hradmin", scoping.P_RECORD_VIEW)
    assert scoping.service_records_for(actor).count() == 2


def test_hod_cannot_read_other_service_records_and_permissions_do_not_stack(two_records):
    actor = _actor(10, "HOD (CSE)", scoping.P_RECORD_VIEW)
    assert list(scoping.service_records_for(actor)) == [two_records[0]]
    assert not scoping.service_records_for(actor).filter(user_id=20).exists()
    actor = _actor(10, "faculty", scoping.P_RECORD_VIEW)
    assert scoping.service_records_for(actor).count() == 1


def test_module_grant_and_permission_are_both_required(two_records):
    # HR-AFR-001, HR-AFR-094, HR-AFR-100, BR-HR-002:
    # neither active-role nor module permission can be inferred.
    missing_module = _actor(10, "faculty", scoping.P_RECORD_VIEW, modules=())
    missing_permission = _actor(10, "faculty")
    assert not scoping.service_records_for(missing_module).exists()
    assert not scoping.service_records_for(missing_permission).exists()
    assert not scoping.service_records_for(None).exists()


def test_request_owner_and_hradmin_scoping(assigned_requests):
    # HR-AFR-004, HR-AFR-099, BR-HR-030: no cross-employee queue disclosure.
    first, second, third = assigned_requests
    owner = _actor(20, "faculty", scoping.P_REQUEST_VIEW)
    assert set(scoping.requests_for(owner).values_list("pk", flat=True)) == {
        second.pk,
        third.pk,
    }
    assert not scoping.requests_for(_actor(99, "hradmin", scoping.P_REQUEST_VIEW)).exists()
    with pytest.raises(HRRequest.DoesNotExist):
        scoping.requests_for(owner).get(pk=first.pk)


def test_approver_sees_only_current_step_and_authorized_family(assigned_requests):
    # HR-AFR-006, HR-AFR-008, HR-AFR-009, HR-AFR-074,
    # BR-HR-009: current step and permitted family both constrain reads.
    first, second, _third = assigned_requests
    hod = _actor(88, "HOD (CSE)", scoping.P_REQUEST_VIEW, "hreis.leave.approve")
    director = _actor(77, "Director", scoping.P_REQUEST_VIEW, "hreis.claim.approve")
    assert list(scoping.requests_for(hod).values_list("pk", flat=True)) == [first.pk]
    assert list(scoping.requests_for(director).values_list("pk", flat=True)) == [second.pk]
    no_family_grant = _actor(88, "HOD (CSE)", scoping.P_REQUEST_VIEW)
    assert not scoping.requests_for(no_family_grant).exists()
    assert not scoping.requests_for(
        _actor(88, "Registrar", scoping.P_REQUEST_VIEW, "hreis.leave.approve")
    ).exists()


def test_authority_queue_excludes_approvers_own_requests(assigned_requests):
    own_request, _other, _closed = assigned_requests
    owner_as_hod = _actor(
        10, "HOD (CSE)", scoping.P_REQUEST_VIEW, "hreis.leave.approve"
    )
    assert not scoping.requests_for(owner_as_hod).filter(pk=own_request.pk).exists()


def test_notification_scope_is_always_personal_even_for_hradmin():
    a = Notification.objects.create(
        recipient_user_id=10,
        event_key="notif-10",
        title="Notice",
        message="One",
    )
    Notification.objects.create(
        recipient_user_id=20,
        event_key="notif-20",
        title="Notice",
        message="Two",
    )
    hr_actor = _actor(10, "hradmin", scoping.P_NOTIFICATION_VIEW)
    assert list(scoping.notifications_for(hr_actor)) == [a]
    assert not scoping.notifications_for(_actor(10, "hradmin", modules=())).exists()


def test_audit_scoping_is_hradmin_only():
    # HR-AFR-088, HR-AFR-089, BR-HR-026: compliance audit remains HR-only.
    event = AuditEvent.objects.create(
        event_key="audit-1",
        actor_user_id=10,
        subject_user_id=20,
        action="update",
        resource_kind="service_record",
        resource_id=1,
    )
    assert list(scoping.audit_events_for(_actor(99, "hradmin", scoping.P_AUDIT_VIEW))) == [event]
    assert not scoping.audit_events_for(_actor(10, "faculty", scoping.P_AUDIT_VIEW)).exists()


def test_hradmin_queue_limited_to_verification_and_unassigned_appraisals():
    # HR-CFR-001, BR-HR-030: no global disclosure of medical/leave requests.
    own_leave = HRRequest.objects.create(
        user_id=10, family="leave", state="pending_authority"
    )
    verification = HRRequest.objects.create(
        user_id=20, family="ltc", state="awaiting_hr_verification"
    )
    appraisal = HRRequest.objects.create(
        user_id=20, family="appraisal", state="submitted"
    )
    approved = HRRequest.objects.create(
        user_id=20, family="cpda", state="approved"
    )
    hr = _actor(99, "hradmin", scoping.P_REQUEST_VIEW)
    assert set(scoping.requests_for(hr).values_list("pk", flat=True)) == {
        verification.pk, appraisal.pk
    }
    assert not scoping.requests_for(hr).filter(pk__in=[own_leave.pk, approved.pk]).exists()


def test_authorities_and_accountant_may_read_only_own_service_record(two_records):
    # HR-UC-001: the current designation must not erase personal read access.
    for role in ("Registrar", "HOD (CSE)", "Accounts Admin"):
        person = _actor(10, role, scoping.P_RECORD_VIEW)
        assert list(scoping.service_records_for(person)) == [two_records[0]]
        assert not scoping.service_records_for(person).filter(user_id=20).exists()
