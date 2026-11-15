"""Business-rule decision, authorization, and threshold tests."""
from types import SimpleNamespace

import pytest

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.badms.domain import state_machine as sm


@pytest.mark.django_db
def test_br_001_only_authorized_actor_can_trigger_manual_backup(principal_factory):
    """BR-001 / BR-BA-001."""
    from modules.badms.services.operations import trigger_manual_backup

    with pytest.raises(PermissionDeniedError):
        trigger_manual_backup(actor=principal_factory(user_id=501))
    operation = trigger_manual_backup(
        actor=principal_factory(user_id=502, permissions={"badms.backup.trigger"})
    )
    assert operation.status == "success"


@pytest.mark.parametrize(
    "action,expected",
    [("approve", sm.ARCHIVAL_HOD_APPROVED), ("reject", sm.ARCHIVAL_HOD_REJECTED)],
)
def test_br_002_hod_decision_has_the_two_specified_outcomes(action, expected):
    """BR-002 / BR-BA-002 approve/reject outcomes."""
    assert sm.validate_hod_decision(action) == expected


@pytest.mark.django_db
def test_br_003_only_it_security_can_configure_encryption(principal_factory):
    """BR-003 / BR-BA-003."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import it_security_configure_encryption

    request = SecureArchivalRequest.objects.create(
        user_id=503, department="CSE", file_name="sensitive.bin", file_type="application/octet-stream",
        file_size_bytes=1, reason="Sensitive", authoritative_classification=sm.TIER_SENSITIVE,
        status=sm.ARCHIVAL_CLASSIFIED,
    )
    with pytest.raises(PermissionDeniedError):
        it_security_configure_encryption(actor=principal_factory(user_id=504), request_id=request.pk)


@pytest.mark.django_db
def test_br_004_only_authorized_sysadmin_can_set_authoritative_classification(principal_factory):
    """BR-004 / BR-BA-004."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import sysadmin_classify_archival

    request = SecureArchivalRequest.objects.create(
        user_id=505, department="CSE", file_name="item.txt", file_type="text/plain", file_size_bytes=1,
        reason="Classification", status=sm.ARCHIVAL_HOD_APPROVED,
    )
    with pytest.raises(PermissionDeniedError):
        sysadmin_classify_archival(
            actor=principal_factory(user_id=506), request_id=request.pk,
            authoritative_classification=sm.TIER_ROUTINE,
        )


@pytest.mark.django_db
def test_br_005_sensitive_restoration_waits_for_sysadmin_approval(principal_factory):
    """BR-005 / BR-BA-005."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import submit_restoration_request, sysadmin_review_restoration

    owner = principal_factory(user_id=507)
    archive = SecureArchivalRequest.objects.create(
        user_id=owner.user_id, department="CSE", file_name="sensitive.dat", file_type="application/octet-stream",
        file_size_bytes=2, reason="Sensitive", authoritative_classification=sm.TIER_SENSITIVE,
        status=sm.ARCHIVAL_COMPLETED,
    )
    restoration = submit_restoration_request(
        actor=owner, archival_request_id=archive.pk, reason="Restore sensitive data"
    )
    assert restoration.status == sm.RESTORATION_SUBMITTED
    with pytest.raises(PermissionDeniedError):
        sysadmin_review_restoration(actor=principal_factory(user_id=508), restoration_id=restoration.pk, action="approve")


@pytest.mark.django_db
def test_br_006_invalid_initial_classification_uses_specified_default(principal_factory):
    """BR-006 / BR-BA-006."""
    from modules.badms.services.operations import submit_archival_request

    request = submit_archival_request(
        actor=principal_factory(user_id=509), department="CSE", file_name="item", file_type="text/plain",
        file_size_bytes=1, reason="Default classification", initial_classification="unknown",
    )
    assert request.initial_classification == sm.TIER_ROUTINE


@pytest.mark.django_db
def test_br_007_sensitive_encryption_rejects_non_aes_256_algorithm(principal_factory):
    """BR-007 / BR-BA-007: sensitive data requires AES-256 at rest and in transit."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import it_security_configure_encryption

    request = SecureArchivalRequest.objects.create(
        user_id=510, department="CSE", file_name="sensitive.dat", file_type="application/octet-stream",
        file_size_bytes=2, reason="Sensitive", authoritative_classification=sm.TIER_SENSITIVE,
        status=sm.ARCHIVAL_CLASSIFIED,
    )
    with pytest.raises(BadRequestError):
        it_security_configure_encryption(
            actor=principal_factory(user_id=511, permissions={"badms.security.manage"}),
            request_id=request.pk, algorithm="DES",
        )


@pytest.mark.django_db
def test_br_008_classified_archival_gets_a_retention_deadline(principal_factory):
    """BR-008 / BR-BA-008; exact classification durations are outside this version's scope."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import sysadmin_classify_archival

    request = SecureArchivalRequest.objects.create(
        user_id=512, department="CSE", file_name="record.txt", file_type="text/plain", file_size_bytes=1,
        reason="Retention", status=sm.ARCHIVAL_HOD_APPROVED,
    )
    result = sysadmin_classify_archival(
        actor=principal_factory(user_id=513, permissions={"badms.archival.classify_authoritative"}),
        request_id=request.pk, authoritative_classification=sm.TIER_ROUTINE,
    )
    assert result.retention_until is not None


def test_br_009_a_second_pending_storage_extension_is_blocked():
    """BR-009 / BR-BA-009."""
    sm.validate_no_pending_extension(0)
    with pytest.raises(sm.RuleViolation) as error:
        sm.validate_no_pending_extension(1)
    assert error.value.rule_id == "BR-BA-009"


@pytest.mark.django_db
def test_br_010_hod_cannot_review_another_department_archival_request():
    """BR-010 / BR-BA-010 own-department decision scope."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import hod_review_archival

    request = SecureArchivalRequest.objects.create(
        user_id=514, department="EE", file_name="item.txt", file_type="text/plain", file_size_bytes=1,
        reason="Other department",
    )
    actor = SimpleNamespace(
        user_id=515, active_role="hod", department="CSE",
        has_permission=lambda code: code == "badms.department.review",
    )
    with pytest.raises(PermissionDeniedError):
        hod_review_archival(actor=actor, request_id=request.pk, action="approve")


@pytest.mark.django_db
def test_br_010_hod_cannot_review_another_department_storage_extension():
    """BR-010 / BR-BA-010 own-department scope for storage-extension decisions."""
    from modules.badms.models import StorageExtensionRequest
    from modules.badms.services.operations import hod_review_storage_extension

    request = StorageExtensionRequest.objects.create(
        user_id=524, department="EE", requested_additional_mb=256, reason="Other department"
    )
    actor = SimpleNamespace(
        user_id=525, active_role="hod", department="CSE",
        has_permission=lambda code: code == "badms.department.review",
    )
    with pytest.raises(PermissionDeniedError):
        hod_review_storage_extension(actor=actor, request_id=request.pk, action="approve")


def test_br_011_local_schedule_overrides_global_and_global_is_fallback():
    """BR-011 / BR-BA-011."""
    global_schedule = {"cron": "0 0 * * *"}
    local_schedule = {"cron": "0 3 * * *"}
    assert sm.calculate_effective_schedule("cse", {"cse": local_schedule}, global_schedule) == local_schedule
    assert sm.calculate_effective_schedule("ee", {"cse": local_schedule}, global_schedule) == global_schedule


@pytest.mark.django_db
def test_br_012_invalid_schedule_parameters_are_rejected(principal_factory):
    """BR-012 / BR-BA-012 malformed cron and invalid retention boundary."""
    from modules.badms.services.operations import configure_schedule

    with pytest.raises(BadRequestError):
        configure_schedule(
            actor=principal_factory(user_id=516, permissions={"badms.schedule.manage_local"}),
            scope="local", dataset_code="cse", cron_expression="not a cron", retention_days=-1,
        )


@pytest.mark.skip(reason="NOT_AUTOMATED: no scheduled backup/repository execution interface is implemented")
def test_br_013_scheduled_backup_requires_reachable_repository():
    """BR-013 / BR-BA-013."""
    raise AssertionError("NOT_AUTOMATED: no scheduled backup/repository execution interface is implemented")


@pytest.mark.skip(reason="NOT_AUTOMATED: no backup failure alert adapter exists to exercise the five-minute SLA")
def test_br_014_failed_backup_alert_is_sent_within_five_minutes():
    """BR-014 / BR-BA-014."""
    raise AssertionError("NOT_AUTOMATED: no backup failure alert adapter exists")


@pytest.mark.parametrize("count,expected", [(2, False), (3, True), (4, True)])
def test_br_015_repeated_failure_escalation_boundary(count, expected):
    """BR-015 / BR-BA-015 threshold sides."""
    assert sm.check_repeated_failure_escalation(count) is expected


@pytest.mark.parametrize("used,allowed", [(99, False), (100, True), (101, True)])
def test_br_016_storage_extension_requires_full_quota(used, allowed):
    """BR-016 / BR-BA-016 below/equal/above quota outcomes."""
    if allowed:
        sm.validate_storage_quota_threshold(used, 100)
    else:
        with pytest.raises(sm.RuleViolation):
            sm.validate_storage_quota_threshold(used, 100)


@pytest.mark.skip(reason="NOT_AUTOMATED: decision criteria are not captured as structured service inputs")
def test_br_017_storage_decision_uses_infrastructure_policy_and_justification():
    """BR-017 / BR-BA-017."""
    raise AssertionError("NOT_AUTOMATED: no structured criteria input exists")


@pytest.mark.django_db
def test_br_018_special_archival_is_limited_to_super_admin(principal_factory):
    """BR-018 / BR-BA-018."""
    from modules.badms.services.operations import super_admin_special_archival

    args = {
        "department": "CSE", "file_name": "special.tar", "file_type": "application/x-tar",
        "file_size_bytes": 8, "reason": "Offline authority request",
    }
    with pytest.raises(PermissionDeniedError):
        super_admin_special_archival(actor=principal_factory(user_id=517), **args)
    request = super_admin_special_archival(
        actor=principal_factory(user_id=518, permissions={"badms.archival.special"}), **args
    )
    assert request.is_special
    assert request.status == sm.ARCHIVAL_SPECIAL_EXECUTED


@pytest.mark.django_db
def test_br_019_global_schedule_requires_super_admin_permission(principal_factory):
    """BR-019 / BR-BA-019."""
    from modules.badms.services.operations import configure_schedule

    args = {"scope": "global", "dataset_code": "all", "cron_expression": "0 1 * * *", "retention_days": 10}
    with pytest.raises(PermissionDeniedError):
        configure_schedule(actor=principal_factory(user_id=519), **args)
    schedule = configure_schedule(
        actor=principal_factory(user_id=520, permissions={"badms.schedule.manage_global"}), **args
    )
    assert schedule.scope == "global"


@pytest.mark.django_db
def test_br_020_hod_sees_only_requests_in_their_department(principal_factory):
    """BR-020 / BR-BA-020 protected-information scope."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.selectors.scoping import visible_archival_requests

    SecureArchivalRequest.objects.create(
        user_id=521, department="CSE", file_name="cse.txt", file_type="text/plain", file_size_bytes=1,
        reason="CSE request",
    )
    SecureArchivalRequest.objects.create(
        user_id=522, department="EE", file_name="ee.txt", file_type="text/plain", file_size_bytes=1,
        reason="EE request",
    )
    hod = principal_factory(user_id=523, permissions={"badms.department.review"})
    visible = visible_archival_requests(hod)
    assert visible.count() == 0


@pytest.mark.skip(reason="NOT_AUTOMATED: RBAC/security-policy management endpoints are not implemented in BADMS")
def test_br_021_only_it_security_can_manage_rbac_and_security_policies():
    """BR-021 / BR-BA-021."""
    raise AssertionError("NOT_AUTOMATED: no RBAC/security-policy management interface exists")
