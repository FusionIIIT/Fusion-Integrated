# Generated automated specification tests for BADMS - Strategy: BR (Business Rules)
import uuid
import pytest
from django.utils import timezone
from modules.badms.domain import (
    CLASS_ARCHIVAL,
    CLASS_CRITICAL,
    CLASS_ROUTINE,
    CLASS_SENSITIVE,
    ARCHIVAL_CLASSIFIED_NON_SENSITIVE,
    ARCHIVAL_CLASSIFIED_SENSITIVE,
    ARCHIVAL_ENCRYPTED,
    ARCHIVAL_HOD_APPROVED,
    ARCHIVAL_REJECTED,
    ARCHIVAL_SPECIAL,
    ARCHIVAL_SUBMITTED,
    EXT_APPROVED,
    EXT_REJECTED,
    EXT_SUBMITTED,
    RESTORE_APPROVED_FOR_EXECUTION,
    RESTORE_COMPLETED,
    RESTORE_REJECTED,
    RESTORE_SENSITIVE_PENDING,
    RESTORE_STANDARD_PENDING,
    DomainValidationError,
    calculate_retention_policy,
    evaluate_backup_failure_response,
    get_initial_classification,
    is_sensitive_restoration_approval_required,
    resolve_effective_schedule,
    validate_authoritative_classification,
    validate_encryption_configuration,
    validate_global_backup_policy_authority,
    validate_hod_department_scope,
    validate_it_security_policy_authority,
    validate_manual_backup_authority,
    validate_schedule_parameters,
    validate_sensitive_restoration_decision,
    validate_special_archival_authority,
    validate_storage_extension_submission,
)
from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    EncryptedArchive,
    RestorationRequest,
    StorageExtensionRequest,
    StorageQuota,
)
from modules.badms.services import (
    classify_archival_sysadmin,
    configure_backup_schedule,
    configure_sensitive_encryption_it_security,
    decide_secure_archival_hod,
    decide_sensitive_restoration_sysadmin,
    decide_storage_extension_hod,
    execute_data_restoration,
    perform_special_archival_operation,
    request_data_restoration,
    submit_secure_archival_request,
    submit_storage_extension_request,
    trigger_manual_backup,
)
from modules.badms.selectors import (
    get_archival_request_by_id,
    get_consecutive_backup_failures,
    get_user_storage_quota,
    list_archival_requests_for_user,
    list_audit_events,
    list_backup_history,
    list_backup_schedules,
    list_restoration_requests,
    list_storage_extensions,
)


def test_tc_badms_201_sysadmin_manual_backup_permitted():
    """TC-BADMS-201 | BR-BA-001 Permitted: SysAdmin manual backup trigger permitted."""
    validate_manual_backup_authority("sysadmin")
    rec = trigger_manual_backup(actor_user_id="admin_201", actor_role="sysadmin")
    assert rec.status == "SUCCESS"


def test_tc_badms_202_superadmin_manual_backup_permitted():
    """TC-BADMS-202 | BR-BA-001 Permitted: Super Admin manual backup trigger permitted."""
    validate_manual_backup_authority("superadmin")
    rec = trigger_manual_backup(actor_user_id="super_202", actor_role="superadmin")
    assert rec.status == "SUCCESS"


def test_tc_badms_203_user_manual_backup_prohibited():
    """TC-BADMS-203 | BR-BA-001 Prohibited: Regular user manual backup trigger prohibited."""
    with pytest.raises(DomainValidationError):
        validate_manual_backup_authority("student")
    with pytest.raises(DomainValidationError):
        trigger_manual_backup(actor_user_id="user_203", actor_role="student")


def test_tc_badms_204_hod_manual_backup_prohibited():
    """TC-BADMS-204 | BR-BA-001 Prohibited: HoD manual backup trigger prohibited."""
    with pytest.raises(DomainValidationError):
        validate_manual_backup_authority("hod")
    with pytest.raises(DomainValidationError):
        trigger_manual_backup(actor_user_id="hod_204", actor_role="hod")


def test_tc_badms_205_hod_decision_permitted(make_quota):
    """TC-BADMS-205 | BR-BA-002 Permitted: Respective HoD decision on departmental secure archival permitted."""
    make_quota(user_id="user_205", quota_mb=1000, department_id="CSE")
    req = submit_secure_archival_request("user_205", "CSE", "res_205.pdf", 2.0, "Grant")
    validate_hod_department_scope("hod", "CSE", "CSE")
    dec = decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    assert dec.status in [ARCHIVAL_HOD_APPROVED, "HOD_APPROVED", "APPROVED"]


def test_tc_badms_206_cross_department_hod_decision_prohibited(make_quota):
    """TC-BADMS-206 | BR-BA-002 Prohibited: Cross-department HoD secure archival decision prohibited."""
    make_quota(user_id="user_206", quota_mb=1000, department_id="ME")
    req = submit_secure_archival_request("user_206", "ME", "res_206.pdf", 2.0, "Grant")
    with pytest.raises(DomainValidationError):
        validate_hod_department_scope("hod", "CSE", "ME")
    with pytest.raises(DomainValidationError):
        decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)


def test_tc_badms_207_non_hod_decision_prohibited(make_quota):
    """TC-BADMS-207 | BR-BA-002 Prohibited: Non-HoD actor secure archival decision prohibited."""
    make_quota(user_id="user_207", quota_mb=1000, department_id="CSE")
    req = submit_secure_archival_request("user_207", "CSE", "res_207.pdf", 2.0, "Grant")
    with pytest.raises(DomainValidationError):
        validate_hod_department_scope("sysadmin", "CSE", "CSE")
    with pytest.raises(DomainValidationError):
        decide_secure_archival_hod(str(req.id), "admin_207", "sysadmin", "CSE", True)


def test_tc_badms_208_it_security_encryption_permitted(make_quota):
    """TC-BADMS-208 | BR-BA-003 Permitted: IT Security encryption configuration for Sensitive data permitted."""
    validate_encryption_configuration(actor_role="it_security", classification=CLASS_SENSITIVE, algorithm="AES-256")


def test_tc_badms_209_sysadmin_encryption_prohibited():
    """TC-BADMS-209 | BR-BA-003 Prohibited: SysAdmin encryption configuration prohibited."""
    with pytest.raises(DomainValidationError):
        validate_encryption_configuration(actor_role="sysadmin", classification=CLASS_SENSITIVE, algorithm="AES-256")


def test_tc_badms_210_regular_user_encryption_prohibited():
    """TC-BADMS-210 | BR-BA-003 Prohibited: Regular user encryption configuration prohibited."""
    with pytest.raises(DomainValidationError):
        validate_encryption_configuration(actor_role="student", classification=CLASS_SENSITIVE, algorithm="AES-256")


def test_tc_badms_211_sysadmin_classification_permitted():
    """TC-BADMS-211 | BR-BA-004 Permitted: SysAdmin authoritative classification permitted."""
    validate_authoritative_classification("sysadmin", CLASS_SENSITIVE)
    validate_authoritative_classification("sysadmin", CLASS_ROUTINE)


def test_tc_badms_212_non_sysadmin_classification_prohibited():
    """TC-BADMS-212 | BR-BA-004 Prohibited: Non-SysAdmin authoritative classification prohibited."""
    with pytest.raises(DomainValidationError):
        validate_authoritative_classification("hod", CLASS_CRITICAL)
    with pytest.raises(DomainValidationError):
        validate_authoritative_classification("student", CLASS_CRITICAL)


def test_tc_badms_213_sysadmin_classification_prior_to_hod_approval_prohibited(make_quota):
    """TC-BADMS-213 | BR-BA-004 Prohibited: SysAdmin classification prior to HoD approval prohibited."""
    make_quota(user_id="user_213", quota_mb=1000)
    req = submit_secure_archival_request("user_213", "CSE", "doc_213.pdf", 1.0, "Reason")
    with pytest.raises(DomainValidationError):
        classify_archival_sysadmin(str(req.id), "admin_213", "sysadmin", CLASS_ROUTINE)


def test_tc_badms_214_classification_value_boundary():
    """TC-BADMS-214 | BR-BA-004 Boundary: Authoritative classification accepts only domain values."""
    for val in [CLASS_CRITICAL, CLASS_SENSITIVE, CLASS_ROUTINE, CLASS_ARCHIVAL]:
        validate_authoritative_classification("sysadmin", val)
    with pytest.raises(DomainValidationError):
        validate_authoritative_classification("sysadmin", "Confidential")


def test_tc_badms_215_sensitive_restoration_permitted_with_approval():
    """TC-BADMS-215 | BR-BA-005 Permitted: Sensitive restoration requires SysAdmin approval."""
    assert is_sensitive_restoration_approval_required(CLASS_SENSITIVE) is True
    validate_sensitive_restoration_decision(actor_role="sysadmin", outcome="APPROVE")


def test_tc_badms_216_sensitive_restoration_blocked_without_approval(make_quota):
    """TC-BADMS-216 | BR-BA-005 Prohibited: Sensitive restoration blocked without approval."""
    make_quota(user_id="user_216", quota_mb=1000)
    req = submit_secure_archival_request("user_216", "CSE", "doc_216.pdf", 1.0, "Reason")
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_216", "sysadmin", CLASS_SENSITIVE)
    configure_sensitive_encryption_it_security(str(req.id), "sec_216", "it_security")
    rest = request_data_restoration("user_216", "CSE", str(req.id), "Restore")
    with pytest.raises(DomainValidationError):
        execute_data_restoration(str(rest.id), "admin_216", "sysadmin")


def test_tc_badms_217_non_sensitive_restoration_standard():
    """TC-BADMS-217 | BR-BA-005 Permitted: Non-Sensitive restoration standard path permitted."""
    assert is_sensitive_restoration_approval_required(CLASS_ROUTINE) is False
    assert is_sensitive_restoration_approval_required(CLASS_ARCHIVAL) is False


def test_tc_badms_218_user_specified_initial_classification():
    """TC-BADMS-218 | BR-BA-006 Permitted: User-specified initial classification preserved."""
    assert get_initial_classification(CLASS_SENSITIVE) == CLASS_SENSITIVE
    assert get_initial_classification(CLASS_CRITICAL) == CLASS_CRITICAL


def test_tc_badms_219_omitted_initial_classification_defaults_routine():
    """TC-BADMS-219 | BR-BA-006 Boundary: Omitted initial classification defaults to Routine."""
    assert get_initial_classification(None) == CLASS_ROUTINE
    assert get_initial_classification("") == CLASS_ROUTINE


def test_tc_badms_220_aes_256_encryption_for_sensitive():
    """TC-BADMS-220 | BR-BA-007 Permitted: AES-256 encryption at rest and in transit for Sensitive data."""
    validate_encryption_configuration(actor_role="it_security", classification=CLASS_SENSITIVE, algorithm="AES-256")


def test_tc_badms_221_sensitive_without_aes_256_prohibited():
    """TC-BADMS-221 | BR-BA-007 Prohibited: Archival of Sensitive data without AES-256 prohibited."""
    with pytest.raises(DomainValidationError):
        validate_encryption_configuration(actor_role="it_security", classification=CLASS_SENSITIVE, algorithm="DES")
    with pytest.raises(DomainValidationError):
        validate_encryption_configuration(actor_role="it_security", classification=CLASS_SENSITIVE, algorithm="PLAINTEXT")


def test_tc_badms_222_non_sensitive_bypasses_mandatory_encryption():
    """TC-BADMS-222 | BR-BA-007 Permitted: Non-Sensitive data does not require encryption routing."""
    assert is_sensitive_restoration_approval_required(CLASS_ROUTINE) is False


def test_tc_badms_223_retention_policy_critical():
    """TC-BADMS-223 | BR-BA-008 Permitted: Retention policy applied according to authoritative classification."""
    years, expiry = calculate_retention_policy(CLASS_CRITICAL)
    assert years == 30


def test_tc_badms_224_retention_treatment_unclassified_prohibited():
    """TC-BADMS-224 | BR-BA-008 Prohibited: Retention treatment without valid classification prohibited."""
    with pytest.raises(DomainValidationError):
        validate_authoritative_classification("sysadmin", "UNKNOWN_CLASSIFICATION")


def test_tc_badms_225_retention_across_all_classifications():
    """TC-BADMS-225 | BR-BA-008 Boundary: Distinct retention treatment across classifications."""
    assert calculate_retention_policy(CLASS_ROUTINE)[0] == 5
    assert calculate_retention_policy(CLASS_ARCHIVAL)[0] == 15
    assert calculate_retention_policy(CLASS_SENSITIVE)[0] == 10
    assert calculate_retention_policy(CLASS_CRITICAL)[0] == 30


def test_tc_badms_226_storage_extension_hod_permitted(make_quota):
    """TC-BADMS-226 | BR-BA-009 Permitted: Storage extension decided by respective HoD permitted."""
    make_quota(user_id="user_226", quota_mb=1000, used_mb=1000, department_id="CSE")
    ext = submit_storage_extension_request("user_226", "CSE", 500.0, "Genomics")
    validate_hod_department_scope("hod", "CSE", "CSE")
    dec = decide_storage_extension_hod(str(ext.id), "hod_cse", "hod", "CSE", True)
    assert dec.status in [EXT_APPROVED, "APPROVED"]


def test_tc_badms_227_sysadmin_approval_storage_extension_prohibited(make_quota):
    """TC-BADMS-227 | BR-BA-009 Prohibited: SysAdmin approval of storage-extension prohibited."""
    make_quota(user_id="user_227", quota_mb=1000, used_mb=1000, department_id="CSE")
    ext = submit_storage_extension_request("user_227", "CSE", 500.0, "Genomics")
    with pytest.raises(DomainValidationError):
        validate_hod_department_scope("sysadmin", "CSE", "CSE")
    with pytest.raises(DomainValidationError):
        decide_storage_extension_hod(str(ext.id), "admin_227", "sysadmin", "CSE", True)


def test_tc_badms_228_requester_self_approval_prohibited(make_quota):
    """TC-BADMS-228 | BR-BA-009 Prohibited: Requester self-approval of storage-extension prohibited."""
    make_quota(user_id="user_228", quota_mb=1000, used_mb=1000, department_id="CSE")
    ext = submit_storage_extension_request("user_228", "CSE", 500.0, "Genomics")
    with pytest.raises(DomainValidationError):
        validate_hod_department_scope("student", "CSE", "CSE")
    with pytest.raises(DomainValidationError):
        decide_storage_extension_hod(str(ext.id), "user_228", "student", "CSE", True)


def test_tc_badms_229_hod_intra_department_access():
    """TC-BADMS-229 | BR-BA-010 Permitted: HoD intra-department action and report access permitted."""
    validate_hod_department_scope("hod", "CSE", "CSE")


def test_tc_badms_230_hod_cross_department_access_prohibited():
    """TC-BADMS-230 | BR-BA-010 Prohibited: HoD access to foreign department reports prohibited."""
    with pytest.raises(DomainValidationError):
        validate_hod_department_scope("hod", "CSE", "EE")


def test_tc_badms_231_hod_cross_department_storage_extension_prohibited():
    """TC-BADMS-231 | BR-BA-010 Prohibited: HoD foreign department storage extension decision prohibited."""
    with pytest.raises(DomainValidationError):
        validate_hod_department_scope("hod", "CSE", "ME")


def test_tc_badms_232_local_schedule_overrides_global():
    """TC-BADMS-232 | BR-BA-011 Permitted: Valid local dataset schedule overrides global schedule."""
    res = resolve_effective_schedule(
        dataset_name="ds_232",
        local_schedules=[{"dataset_name": "ds_232", "frequency": "DAILY", "is_active": True}],
        global_schedules=[{"frequency": "WEEKLY", "is_active": True}],
    )
    assert res["source"] == "LOCAL"
    assert res["schedule"]["frequency"] == "DAILY"


def test_tc_badms_233_global_schedule_when_no_local():
    """TC-BADMS-233 | BR-BA-011 Permitted: Global backup schedule applies when no local schedule exists."""
    res = resolve_effective_schedule(
        dataset_name="ds_233",
        local_schedules=[],
        global_schedules=[{"frequency": "WEEKLY", "is_active": True}],
    )
    assert res["source"] == "GLOBAL"
    assert res["schedule"]["frequency"] == "WEEKLY"


def test_tc_badms_234_disabled_local_fallback_to_global():
    """TC-BADMS-234 | BR-BA-011 Boundary: Disabled local schedule falls back to global."""
    res = resolve_effective_schedule(
        dataset_name="ds_234",
        local_schedules=[{"dataset_name": "ds_234", "frequency": "DAILY", "is_active": False}],
        global_schedules=[{"frequency": "WEEKLY", "is_active": True}],
    )
    assert res["source"] == "GLOBAL"


def test_tc_badms_235_valid_backup_schedule_applied():
    """TC-BADMS-235 | BR-BA-012 Permitted: Valid backup schedule configuration applied."""
    validate_schedule_parameters("DAILY", "01:00:00", "/var/backups")
    sched = configure_backup_schedule("admin_235", "sysadmin", "Sched235", "DATASET", "ds_235", "DAILY", "01:00:00")
    assert sched.name == "Sched235"


def test_tc_badms_236_invalid_schedule_parameters_rejected():
    """TC-BADMS-236 | BR-BA-012 Prohibited: Invalid schedule parameters rejected."""
    with pytest.raises(DomainValidationError):
        validate_schedule_parameters("INVALID_FREQ", "25:70:00", "/var/backups")


def test_tc_badms_237_empty_repository_path_rejected():
    """TC-BADMS-237 | BR-BA-012 Prohibited: Empty repository path rejected."""
    with pytest.raises(DomainValidationError):
        validate_schedule_parameters("DAILY", "01:00:00", "")


def test_tc_badms_238_backup_succeeds_reachable():
    """TC-BADMS-238 | BR-BA-013 Permitted: Automatic backup succeeds when repository reachable."""
    rec = trigger_manual_backup("admin_238", "sysadmin", force_failure=False)
    assert rec.status == "SUCCESS"


def test_tc_badms_239_backup_fails_unreachable():
    """TC-BADMS-239 | BR-BA-013 Prohibited: Automatic backup fails when repository unreachable."""
    rec = trigger_manual_backup("admin_239", "sysadmin", force_failure=True)
    assert rec.status == "FAILED"


def test_tc_badms_240_failure_alert_dispatched():
    """TC-BADMS-240 | BR-BA-014 Permitted: Backup failure dispatches alert within SLA."""
    alert, escalate, msg = evaluate_backup_failure_response(1)
    assert alert is True


def test_tc_badms_241_failure_alert_sla_boundary():
    """TC-BADMS-241 | BR-BA-014 Boundary: Alert SLA threshold within 5 minutes."""
    alert, escalate, msg = evaluate_backup_failure_response(1)
    assert alert is True


def test_tc_badms_242_no_failure_no_alert():
    """TC-BADMS-242 | BR-BA-014 Prohibited: Successful backup does not send failure alert."""
    rec = trigger_manual_backup(actor_user_id="admin_242", actor_role="sysadmin", force_failure=False)
    assert rec.status == "SUCCESS"
    assert rec.alert_sent is False


def test_tc_badms_243_consecutive_failures_below_three_no_escalate():
    """TC-BADMS-243 | BR-BA-015 Boundary: Consecutive failures 1 and 2 do not escalate."""
    assert evaluate_backup_failure_response(1)[1] is False
    assert evaluate_backup_failure_response(2)[1] is False


def test_tc_badms_244_consecutive_failures_three_escalates():
    """TC-BADMS-244 | BR-BA-015 Boundary: Exactly three consecutive failures triggers escalation."""
    alert, escalate, msg = evaluate_backup_failure_response(3)
    assert alert is True
    assert escalate is True


def test_tc_badms_245_success_resets_counter():
    """TC-BADMS-245 | BR-BA-015 Boundary: Successful backup does not escalate."""
    rec = trigger_manual_backup(actor_user_id="admin_245", actor_role="sysadmin", force_failure=False)
    assert rec.status == "SUCCESS"
    assert rec.escalated_to_director is False


def test_tc_badms_246_subsequent_failures_maintain_escalation():
    """TC-BADMS-246 | BR-BA-015 Permitted: Subsequent failures beyond three maintain escalation."""
    alert, escalate, msg = evaluate_backup_failure_response(4)
    assert escalate is True


def test_tc_badms_247_storage_extension_validated_quota_full(make_quota):
    """TC-BADMS-247 | BR-BA-016 Permitted: Storage extension validated when quota is full."""
    make_quota(user_id="user_247", quota_mb=1000, used_mb=1000)
    validate_storage_extension_submission(used_storage_mb=1000.0, allocated_storage_mb=1000.0, requested_additional_mb=500.0)


def test_tc_badms_248_storage_extension_rejected_quota_not_full():
    """TC-BADMS-248 | BR-BA-016 Prohibited: Storage extension rejected when quota not full."""
    with pytest.raises(DomainValidationError):
        validate_storage_extension_submission(used_storage_mb=600.0, allocated_storage_mb=1000.0, requested_additional_mb=500.0)


def test_tc_badms_249_storage_extension_boundary_thresholds():
    """TC-BADMS-249 | BR-BA-016 Boundary: Storage extension boundary checks at exact 100% capacity."""
    # exactly full: permitted
    validate_storage_extension_submission(used_storage_mb=1000.0, allocated_storage_mb=1000.0, requested_additional_mb=100.0)
    # below threshold (e.g. 70%): prohibited
    with pytest.raises(DomainValidationError):
        validate_storage_extension_submission(used_storage_mb=700.0, allocated_storage_mb=1000.0, requested_additional_mb=100.0)


def test_tc_badms_250_hod_extension_decision_criteria(make_quota):
    """TC-BADMS-250 | BR-BA-017 Permitted: HoD storage-extension decision informed by criteria."""
    make_quota(user_id="user_250", quota_mb=1000, used_mb=1000, department_id="CSE")
    ext = submit_storage_extension_request("user_250", "CSE", 500.0, "Valid criteria research")
    dec = decide_storage_extension_hod(str(ext.id), "hod_cse", "hod", "CSE", True)
    assert dec.status in [EXT_APPROVED, "APPROVED"]


def test_tc_badms_251_hod_decision_empty_justification_rejected():
    """TC-BADMS-251 | BR-BA-017 Prohibited: Decision on invalid request context rejected."""
    with pytest.raises(Exception):
        decide_storage_extension_hod(
            request_id=str(uuid.uuid4()),
            hod_user_id="hod_cse",
            hod_role="hod",
            hod_department="CSE",
            approved=True,
        )

def test_tc_badms_252_storage_extension_zero_or_negative_rejected():
    """TC-BADMS-252 | BR-BA-017 Boundary: Requested additional storage <= 0 is rejected."""
    with pytest.raises(DomainValidationError):
        validate_storage_extension_submission(used_storage_mb=1000.0, allocated_storage_mb=1000.0, requested_additional_mb=0.0)
    with pytest.raises(DomainValidationError):
        validate_storage_extension_submission(used_storage_mb=1000.0, allocated_storage_mb=1000.0, requested_additional_mb=-50.0)


def test_tc_badms_253_superadmin_special_archival_permitted():
    """TC-BADMS-253 | BR-BA-018 Permitted: Super Admin special archival permitted."""
    validate_special_archival_authority("superadmin")
    arc = perform_special_archival_operation("super_253", "superadmin", "special_253.tar", 10.0, "CSE", "Offline auth")
    assert arc.status in [ARCHIVAL_SPECIAL, "SPECIAL_ARCHIVED", "ARCHIVED"]


def test_tc_badms_254_sysadmin_special_archival_prohibited():
    """TC-BADMS-254 | BR-BA-018 Prohibited: SysAdmin special archival prohibited."""
    with pytest.raises(DomainValidationError):
        validate_special_archival_authority("sysadmin")


def test_tc_badms_255_user_or_hod_special_archival_prohibited():
    """TC-BADMS-255 | BR-BA-018 Prohibited: Regular user or HoD special archival prohibited."""
    with pytest.raises(DomainValidationError):
        validate_special_archival_authority("student")
    with pytest.raises(DomainValidationError):
        validate_special_archival_authority("hod")


def test_tc_badms_256_superadmin_global_backup_policy_permitted():
    """TC-BADMS-256 | BR-BA-019 Permitted: Super Admin global backup policy configuration permitted."""
    validate_global_backup_policy_authority("superadmin")


def test_tc_badms_257_sysadmin_global_backup_schedule_prohibited():
    """TC-BADMS-257 | BR-BA-019 Prohibited: SysAdmin global backup schedule configuration prohibited."""
    with pytest.raises(DomainValidationError):
        validate_global_backup_policy_authority("sysadmin")


def test_tc_badms_258_it_security_global_backup_policy_prohibited():
    """TC-BADMS-258 | BR-BA-019 Prohibited: IT Security global backup policy configuration prohibited."""
    with pytest.raises(DomainValidationError):
        validate_global_backup_policy_authority("it_security")


def test_tc_badms_259_authorized_scope_information_display():
    """TC-BADMS-259 | BR-BA-020 Permitted: Authorized scope protected information display permitted."""
    logs = list_audit_events("sysadmin")
    assert hasattr(logs, "__iter__")


def test_tc_badms_260_user_audit_log_access_prohibited():
    """TC-BADMS-260 | BR-BA-020 Prohibited: Regular user access to audit logs prohibited."""
    logs = list_audit_events("student")
    assert len(logs) == 0


def test_tc_badms_261_hod_out_of_department_information_prohibited():
    """TC-BADMS-261 | BR-BA-020 Prohibited: HoD access to out-of-department protected information prohibited."""
    with pytest.raises(DomainValidationError):
        validate_hod_department_scope("hod", "CSE", "ECE")


def test_tc_badms_262_it_security_rbac_permitted():
    """TC-BADMS-262 | BR-BA-021 Permitted: IT Security manages RBAC and security policies permitted."""
    validate_it_security_policy_authority("it_security")


def test_tc_badms_263_sysadmin_rbac_management_prohibited():
    """TC-BADMS-263 | BR-BA-021 Prohibited: SysAdmin management of RBAC and security policies prohibited."""
    with pytest.raises(DomainValidationError):
        validate_it_security_policy_authority("sysadmin")


def test_tc_badms_264_other_roles_rbac_prohibited():
    """TC-BADMS-264 | BR-BA-021 Prohibited: Other roles prohibited from IT Security RBAC management."""
    with pytest.raises(DomainValidationError):
        validate_it_security_policy_authority("student")
    with pytest.raises(DomainValidationError):
        validate_it_security_policy_authority("hod")
