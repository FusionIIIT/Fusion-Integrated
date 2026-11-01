"""Service layer orchestration for BADMS.

Executes atomic database transactions, invokes pure Python domain business rules,
manages state machine transitions, and maintains immutable audit trails.
"""

import hashlib
import json
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from ..domain import (
    CLASS_ROUTINE,
    CLASS_SENSITIVE,
    ArchivalWorkflowEngine,
    DomainValidationError,
    RestorationWorkflowEngine,
    StorageExtensionWorkflowEngine,
    calculate_retention_policy,
    evaluate_backup_failure_response,
    get_initial_classification,
    is_sensitive_restoration_approval_required,
    validate_authoritative_classification,
    validate_encryption_configuration,
    validate_global_backup_policy_authority,
    validate_hod_department_scope,
    validate_manual_backup_authority,
    validate_schedule_parameters,
    validate_sensitive_restoration_decision,
    validate_special_archival_authority,
    validate_storage_extension_submission,
)
from ..models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    EncryptedArchive,
    RestorationRequest,
    StorageExtensionRequest,
    StorageQuota,
)
from ..selectors import (
    get_consecutive_backup_failures,
    get_user_storage_quota,
)


def _record_audit_event(
    actor_user_id: str,
    actor_role: str,
    event_type: str,
    target_entity_type: str,
    target_entity_id: str,
    department_id: str = "",
    details: Optional[Dict[str, Any]] = None,
    ip_address: str = ""
) -> AuditEvent:
    """Helper to log an immutable audit event."""
    return AuditEvent.objects.create(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        department_id=department_id,
        event_type=event_type,
        target_entity_type=target_entity_type,
        target_entity_id=str(target_entity_id),
        details=details or {},
        ip_address=ip_address,
    )


# ---------------------------------------------------------------------------
# Service 1: Manual Backup Execution (BA-UC-001, BR-BA-001, BR-BA-014, BR-BA-015)
# ---------------------------------------------------------------------------
def trigger_manual_backup(
    actor_user_id: str,
    actor_role: str,
    dataset_name: str = "primary_db",
    force_failure: bool = False
) -> BackupRecord:
    """Execute on-demand manual database backup snapshot.
    
    Ref: CFR-BA-001, BR-BA-001, BR-BA-014, BR-BA-015.
    """
    validate_manual_backup_authority(actor_role)
    start_time = timezone.now()
    
    with transaction.atomic():
        record = BackupRecord.objects.create(
            backup_type="MANUAL",
            dataset_name=dataset_name,
            status="IN_PROGRESS",
            started_at=start_time,
            triggered_by_user_id=actor_user_id,
        )
        
        if force_failure:
            record.status = "FAILED"
            record.completed_at = timezone.now()
            record.error_message = "Simulated snapshot error: storage target unreachable"
            
            # Check consecutive failure escalation
            prev_failures = get_consecutive_backup_failures()
            alert, escalate, msg = evaluate_backup_failure_response(prev_failures + 1)
            record.alert_sent = alert
            record.escalated_to_director = escalate
            record.save()
            
            _record_audit_event(
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                event_type="BACKUP_FAILED",
                target_entity_type="BackupRecord",
                target_entity_id=str(record.id),
                details={"dataset": dataset_name, "error": record.error_message, "escalated": escalate}
            )
            return record
            
        # Successful backup simulation with SHA-256 digest
        content = f"SNAPSHOT:{dataset_name}:{start_time.isoformat()}".encode("utf-8")
        checksum = hashlib.sha256(content).hexdigest()
        
        record.status = "SUCCESS"
        record.completed_at = timezone.now()
        record.file_path = f"/var/backups/fusion/{dataset_name}_{start_time.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        record.file_size_bytes = 41943040  # 40 MB
        record.checksum_sha256 = checksum
        record.save()
        
        _record_audit_event(
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            event_type="BACKUP_SUCCESS",
            target_entity_type="BackupRecord",
            target_entity_id=str(record.id),
            details={"dataset": dataset_name, "checksum": checksum, "size_bytes": record.file_size_bytes}
        )
        return record


# ---------------------------------------------------------------------------
# Service 2: Configure Backup Schedule (BA-UC-009, BA-UC-011, BR-BA-011, 012, 019)
# ---------------------------------------------------------------------------
def configure_backup_schedule(
    actor_user_id: str,
    actor_role: str,
    name: str,
    scope: str,
    dataset_name: str,
    frequency: str,
    scheduled_time: str,
    repository_path: str = "/var/backups/fusion",
    day_of_week: Optional[int] = None
) -> BackupSchedule:
    """Configure a local or global backup schedule."""
    scope_norm = scope.strip().upper()
    if scope_norm == "GLOBAL":
        validate_global_backup_policy_authority(actor_role)
    else:
        validate_manual_backup_authority(actor_role)  # SysAdmin role
        
    validate_schedule_parameters(frequency, scheduled_time, repository_path)
    
    with transaction.atomic():
        schedule = BackupSchedule.objects.create(
            name=name,
            scope=scope_norm,
            dataset_name=dataset_name,
            frequency=frequency.strip().upper(),
            scheduled_time=scheduled_time,
            day_of_week=day_of_week,
            repository_path=repository_path,
            created_by_user_id=actor_user_id,
        )
        _record_audit_event(
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            event_type="SCHEDULE_CONFIGURED",
            target_entity_type="BackupSchedule",
            target_entity_id=str(schedule.id),
            details={"name": name, "scope": scope_norm, "dataset": dataset_name, "frequency": frequency}
        )
        return schedule


# ---------------------------------------------------------------------------
# Service 3: Secure Archival Submission (BA-UC-002, CW-BA-01, BR-BA-006)
# ---------------------------------------------------------------------------
def submit_secure_archival_request(
    requester_user_id: str,
    department_id: str,
    file_name: str,
    file_size_mb: float,
    reason: str,
    initial_classification: Optional[str] = None,
    owners: str = "",
    attachment_ref: str = "",
    actor_role: str = "faculty"
) -> ArchivalRequest:
    """Submit a secure archival request for departmental review.
    
    Ref: CFR-BA-005, BR-BA-006, CW-BA-01.
    """
    if file_size_mb <= 0:
        raise DomainValidationError("File size must be greater than zero.")
    if not file_name or not file_name.strip():
        raise DomainValidationError("File name is required.")
        
    init_class = get_initial_classification(initial_classification)
    
    with transaction.atomic():
        # Validate and update storage quota
        quota = get_user_storage_quota(requester_user_id, department_id)
        if (quota.used_storage_mb + Decimal(str(file_size_mb))) > quota.allocated_storage_mb:
            raise DomainValidationError(
                f"Archival submission of {file_size_mb} MB exceeds available quota "
                f"({quota.allocated_storage_mb - quota.used_storage_mb} MB remaining)."
            )
            
        req_num = f"AR-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        archival_req = ArchivalRequest.objects.create(
            request_number=req_num,
            file_name=file_name.strip(),
            file_size_mb=Decimal(str(file_size_mb)),
            attachment_ref=attachment_ref or f"/storage/uploads/{req_num}_{file_name}",
            requester_user_id=requester_user_id,
            department_id=department_id,
            owners=owners or requester_user_id,
            reason=reason.strip(),
            initial_classification=init_class,
            status="SUBMITTED",
        )
        
        # Deduct used storage quota
        quota.used_storage_mb += Decimal(str(file_size_mb))
        quota.save()
        
        _record_audit_event(
            actor_user_id=requester_user_id,
            actor_role=actor_role,
            department_id=department_id,
            event_type="ARCHIVAL_SUBMITTED",
            target_entity_type="ArchivalRequest",
            target_entity_id=str(archival_req.id),
            details={"request_number": req_num, "classification": init_class, "size_mb": file_size_mb}
        )
        return archival_req


# ---------------------------------------------------------------------------
# Service 4: HoD Secure Archival Decision (BA-UC-003, BW-BA-01, BW-BA-02/03)
# ---------------------------------------------------------------------------
def decide_secure_archival_hod(
    request_id: str,
    hod_user_id: str,
    hod_role: str,
    hod_department: str,
    approved: bool,
    remarks: str = ""
) -> ArchivalRequest:
    """Head of Department review for secure archival request.
    
    Ref: CFR-BA-006, BR-BA-002, BR-BA-010, BW-BA-01, BW-BA-02, BW-BA-03.
    """
    with transaction.atomic():
        req = ArchivalRequest.objects.select_for_update().get(id=request_id)
        validate_hod_department_scope(hod_role, hod_department, req.department_id)
        
        new_status = ArchivalWorkflowEngine.transition_hod_decision(req.status, approved)
        req.status = new_status
        req.hod_user_id = hod_user_id
        req.hod_decision_date = timezone.now()
        req.hod_remarks = remarks
        req.save()
        
        # If rejected, restore the used storage quota
        if not approved:
            quota = get_user_storage_quota(req.requester_user_id, req.department_id)
            quota.used_storage_mb = max(Decimal("0.0"), quota.used_storage_mb - req.file_size_mb)
            quota.save()
            
        _record_audit_event(
            actor_user_id=hod_user_id,
            actor_role=hod_role,
            department_id=hod_department,
            event_type="HOD_ARCHIVAL_DECISION",
            target_entity_type="ArchivalRequest",
            target_entity_id=str(req.id),
            details={"decision": "APPROVED" if approved else "REJECTED", "new_status": new_status}
        )
        return req


# ---------------------------------------------------------------------------
# Service 5: SysAdmin Classification (BA-UC-004, BW-BA-02, BW-BA-03, BR-BA-004)
# ---------------------------------------------------------------------------
def classify_archival_sysadmin(
    request_id: str,
    sysadmin_user_id: str,
    sysadmin_role: str,
    authoritative_classification: str
) -> ArchivalRequest:
    """SysAdmin assigns authoritative classification after HoD approval.
    
    Ref: CFR-BA-007, BR-BA-004, BR-BA-008, BW-BA-02, BW-BA-03.
    """
    auth_class = validate_authoritative_classification(sysadmin_role, authoritative_classification)
    
    with transaction.atomic():
        req = ArchivalRequest.objects.select_for_update().get(id=request_id)
        new_status = ArchivalWorkflowEngine.transition_sysadmin_classification(req.status, auth_class)
        
        req.status = new_status
        req.authoritative_classification = auth_class
        req.classified_by_user_id = sysadmin_user_id
        req.classified_at = timezone.now()
        req.save()
        
        _record_audit_event(
            actor_user_id=sysadmin_user_id,
            actor_role=sysadmin_role,
            department_id=req.department_id,
            event_type="ARCHIVAL_CLASSIFIED",
            target_entity_type="ArchivalRequest",
            target_entity_id=str(req.id),
            details={"authoritative_classification": auth_class, "new_status": new_status}
        )
        return req


# ---------------------------------------------------------------------------
# Service 6: IT Security Sensitive Encryption (BA-UC-005, BW-BA-03, BR-BA-003, 007)
# ---------------------------------------------------------------------------
def configure_sensitive_encryption_it_security(
    request_id: str,
    security_user_id: str,
    security_role: str,
    encryption_algorithm: str = "AES-256"
) -> EncryptedArchive:
    """Configure AES-256 encryption for Sensitive data and create EncryptedArchive.
    
    Ref: CFR-BA-008, BR-BA-003, BR-BA-007, BR-BA-008, BW-BA-03.
    """
    with transaction.atomic():
        req = ArchivalRequest.objects.select_for_update().get(id=request_id)
        validate_encryption_configuration(security_role, req.authoritative_classification, encryption_algorithm)
        
        new_status = ArchivalWorkflowEngine.transition_it_security_encryption(req.status)
        req.status = new_status
        req.save()
        
        years, expiry = calculate_retention_policy(req.authoritative_classification)
        archive_code = f"ENC-{req.request_number}"
        content = f"{archive_code}:{req.file_name}:{encryption_algorithm}".encode("utf-8")
        checksum = hashlib.sha256(content).hexdigest()
        
        archive = EncryptedArchive.objects.create(
            archival_request=req,
            archive_code=archive_code,
            encryption_algorithm=encryption_algorithm,
            encrypted_at_rest=True,
            encrypted_in_transit=True,
            configured_by_user_id=security_user_id,
            archive_file_path=f"/var/archives/encrypted/{archive_code}.vault",
            checksum_sha256=checksum,
            retention_years=years,
            retention_expiry_date=expiry,
        )
        
        _record_audit_event(
            actor_user_id=security_user_id,
            actor_role=security_role,
            department_id=req.department_id,
            event_type="ENCRYPTION_CONFIGURED",
            target_entity_type="EncryptedArchive",
            target_entity_id=str(archive.id),
            details={"archive_code": archive_code, "algorithm": encryption_algorithm, "expiry": str(expiry)}
        )
        return archive


# ---------------------------------------------------------------------------
# Service 7: Special Archival Operation (BA-UC-010, BR-BA-018)
# ---------------------------------------------------------------------------
def perform_special_archival_operation(
    superadmin_user_id: str,
    superadmin_role: str,
    file_name: str,
    file_size_mb: float,
    department_id: str,
    reason: str,
    owners: str = ""
) -> ArchivalRequest:
    """Execute offline-triggered special archival operation by Super Admin.
    
    Ref: CFR-BA-010, BR-BA-018.
    """
    validate_special_archival_authority(superadmin_role)
    
    with transaction.atomic():
        req_num = f"SP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        req = ArchivalRequest.objects.create(
            request_number=req_num,
            file_name=file_name.strip(),
            file_size_mb=Decimal(str(file_size_mb)),
            attachment_ref=f"/storage/special/{req_num}_{file_name}",
            requester_user_id=superadmin_user_id,
            department_id=department_id,
            owners=owners or "Institutional Research Vault",
            reason=reason.strip(),
            initial_classification="ARCHIVAL",
            authoritative_classification="ARCHIVAL",
            status="SPECIAL_ARCHIVED",
        )
        _record_audit_event(
            actor_user_id=superadmin_user_id,
            actor_role=superadmin_role,
            department_id=department_id,
            event_type="SPECIAL_ARCHIVE_COMPLETED",
            target_entity_type="ArchivalRequest",
            target_entity_id=str(req.id),
            details={"request_number": req_num, "file_name": file_name}
        )
        return req


# ---------------------------------------------------------------------------
# Service 8: Storage Extension Workflow (BA-UC-007, BA-UC-008, CW-BA-02, BR-BA-016)
# ---------------------------------------------------------------------------
def submit_storage_extension_request(
    requester_user_id: str,
    department_id: str,
    requested_additional_mb: float,
    justification: str,
    actor_role: str = "faculty"
) -> StorageExtensionRequest:
    """Submit request for storage quota extension."""
    quota = get_user_storage_quota(requester_user_id, department_id)
    validate_storage_extension_submission(
        used_storage_mb=float(quota.used_storage_mb),
        allocated_storage_mb=float(quota.allocated_storage_mb),
        requested_additional_mb=requested_additional_mb,
        threshold_percent=float(quota.threshold_percent)
    )
    
    with transaction.atomic():
        req_num = f"EXT-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        ext_req = StorageExtensionRequest.objects.create(
            request_number=req_num,
            requester_user_id=requester_user_id,
            department_id=department_id,
            requested_additional_mb=Decimal(str(requested_additional_mb)),
            current_usage_mb=quota.used_storage_mb,
            justification=justification.strip(),
            status="SUBMITTED",
        )
        _record_audit_event(
            actor_user_id=requester_user_id,
            actor_role=actor_role,
            department_id=department_id,
            event_type="STORAGE_EXTENSION_SUBMITTED",
            target_entity_type="StorageExtensionRequest",
            target_entity_id=str(ext_req.id),
            details={"request_number": req_num, "requested_mb": requested_additional_mb}
        )
        return ext_req


def decide_storage_extension_hod(
    request_id: str,
    hod_user_id: str,
    hod_role: str,
    hod_department: str,
    approved: bool,
    remarks: str = ""
) -> StorageExtensionRequest:
    """HoD decision on storage extension request.
    
    Ref: CFR-BA-012, BR-BA-009, BR-BA-010, BR-BA-017, BW-BA-04, BW-BA-05.
    """
    with transaction.atomic():
        ext_req = StorageExtensionRequest.objects.select_for_update().get(id=request_id)
        validate_hod_department_scope(hod_role, hod_department, ext_req.department_id)
        
        new_status = StorageExtensionWorkflowEngine.transition_hod_decision(ext_req.status, approved)
        ext_req.status = new_status
        ext_req.hod_user_id = hod_user_id
        ext_req.hod_decision_date = timezone.now()
        ext_req.hod_remarks = remarks
        ext_req.save()
        
        if approved:
            quota = get_user_storage_quota(ext_req.requester_user_id, ext_req.department_id)
            quota.allocated_storage_mb += ext_req.requested_additional_mb
            quota.save()
            
        _record_audit_event(
            actor_user_id=hod_user_id,
            actor_role=hod_role,
            department_id=hod_department,
            event_type="STORAGE_EXTENSION_DECIDED",
            target_entity_type="StorageExtensionRequest",
            target_entity_id=str(ext_req.id),
            details={"decision": "APPROVED" if approved else "REJECTED"}
        )
        return ext_req


# ---------------------------------------------------------------------------
# Service 9: Data Restoration Workflow (BA-UC-016, 017, 018, CW-BA-03, BR-BA-005)
# ---------------------------------------------------------------------------
def request_data_restoration(
    requester_user_id: str,
    department_id: str,
    archival_request_id: str,
    reason: str,
    target_location: str = "/restores/workspace",
    actor_role: str = "faculty"
) -> RestorationRequest:
    """Request restoration of archived data.
    
    Ref: CFR-BA-011, BR-BA-005, CW-BA-03, BW-BA-06, BW-BA-07.
    """
    with transaction.atomic():
        archival_req = ArchivalRequest.objects.get(id=archival_request_id)
        effective_class = archival_req.authoritative_classification or archival_req.initial_classification
        is_sensitive = is_sensitive_restoration_approval_required(effective_class)
        
        status = RestorationWorkflowEngine.transition_request("NOT_REQUESTED", is_sensitive)
        req_num = f"RST-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        restoration = RestorationRequest.objects.create(
            request_number=req_num,
            archival_request=archival_req,
            requester_user_id=requester_user_id,
            department_id=department_id,
            reason=reason.strip(),
            target_location=target_location,
            classification_snapshot=effective_class,
            status=status,
        )
        _record_audit_event(
            actor_user_id=requester_user_id,
            actor_role=actor_role,
            department_id=department_id,
            event_type="RESTORE_REQUESTED",
            target_entity_type="RestorationRequest",
            target_entity_id=str(restoration.id),
            details={"request_number": req_num, "status": status, "sensitive": is_sensitive}
        )
        return restoration


def decide_sensitive_restoration_sysadmin(
    request_id: str,
    sysadmin_user_id: str,
    sysadmin_role: str,
    approved: bool,
    remarks: str = ""
) -> RestorationRequest:
    """SysAdmin decision for Sensitive data restoration.
    
    Ref: CFR-BA-011, BR-BA-005, BW-BA-07.
    """
    validate_sensitive_restoration_decision(sysadmin_role, "APPROVE" if approved else "REJECT")
    
    with transaction.atomic():
        restoration = RestorationRequest.objects.select_for_update().get(id=request_id)
        new_status = RestorationWorkflowEngine.transition_sysadmin_approval(restoration.status, approved)
        
        restoration.status = new_status
        restoration.approved_by_user_id = sysadmin_user_id
        restoration.approval_date = timezone.now()
        restoration.approval_remarks = remarks
        restoration.save()
        
        _record_audit_event(
            actor_user_id=sysadmin_user_id,
            actor_role=sysadmin_role,
            department_id=restoration.department_id,
            event_type="SENSITIVE_RESTORE_DECIDED",
            target_entity_type="RestorationRequest",
            target_entity_id=str(restoration.id),
            details={"decision": "APPROVED" if approved else "REJECTED"}
        )
        return restoration


def execute_data_restoration(
    request_id: str,
    sysadmin_user_id: str,
    sysadmin_role: str
) -> RestorationRequest:
    """SysAdmin executes technical restoration.
    
    Ref: BA-UC-018, CW-BA-03.
    """
    validate_manual_backup_authority(sysadmin_role)
    
    with transaction.atomic():
        restoration = RestorationRequest.objects.select_for_update().get(id=request_id)
        new_status = RestorationWorkflowEngine.transition_execution(restoration.status)
        
        restoration.status = new_status
        restoration.restored_by_user_id = sysadmin_user_id
        restoration.restored_at = timezone.now()
        restoration.save()
        
        _record_audit_event(
            actor_user_id=sysadmin_user_id,
            actor_role=sysadmin_role,
            department_id=restoration.department_id,
            event_type="RESTORE_COMPLETED",
            target_entity_type="RestorationRequest",
            target_entity_id=str(restoration.id),
            details={"target_location": restoration.target_location}
        )
        return restoration
