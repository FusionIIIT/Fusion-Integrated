"""Comprehensive state machine and workflow tests for BADMS.

Covers all 7 basis workflows and 3 composite workflows:
- BW-BA-01, BW-BA-02, BW-BA-03, CW-BA-01 (Secure Archival)
- BW-BA-04, BW-BA-05, CW-BA-02 (Storage Extension)
- BW-BA-06, BW-BA-07, CW-BA-03 (Restoration)
"""

import pytest

from modules.badms.domain.entities import (
    ActorRole,
    ArchivalStatus,
    RestorationStatus,
    StorageExtensionStatus,
)
from modules.badms.domain.errors import ActorNotAllowed, InvalidTransition
from modules.badms.domain.state_machines import (
    resolve_archival_transition,
    resolve_extension_transition,
    resolve_restoration_transition,
)

# ==============================================================================
# Archival Workflows (CW-BA-01, BW-BA-01..03)
# ==============================================================================


def test_bw_ba_01_archival_hod_rejection():
    # Step 1: User submits
    t1 = resolve_archival_transition(
        ArchivalStatus.NOT_SUBMITTED.value,
        ArchivalStatus.SUBMITTED.value,
        ActorRole.USER,
    )
    assert t1.to == ArchivalStatus.SUBMITTED.value

    # Step 2: HoD rejects
    t2 = resolve_archival_transition(
        ArchivalStatus.SUBMITTED.value,
        ArchivalStatus.REJECTED.value,
        ActorRole.HOD,
    )
    assert t2.to == ArchivalStatus.REJECTED.value

    # Disallowed actor on reject
    with pytest.raises(ActorNotAllowed):
        resolve_archival_transition(
            ArchivalStatus.SUBMITTED.value,
            ArchivalStatus.REJECTED.value,
            ActorRole.USER,
        )


def test_bw_ba_02_archival_approved_non_sensitive():
    # Step 1: Submit
    resolve_archival_transition(
        ArchivalStatus.NOT_SUBMITTED.value,
        ArchivalStatus.SUBMITTED.value,
        ActorRole.USER,
    )
    # Step 2: HoD approves
    resolve_archival_transition(
        ArchivalStatus.SUBMITTED.value,
        ArchivalStatus.HOD_APPROVED.value,
        ActorRole.HOD,
    )
    # Step 3: SysAdmin classifies as Non-Sensitive
    t3 = resolve_archival_transition(
        ArchivalStatus.HOD_APPROVED.value,
        ArchivalStatus.CLASSIFIED_NON_SENSITIVE.value,
        ActorRole.SYSADMIN,
    )
    assert t3.to == ArchivalStatus.CLASSIFIED_NON_SENSITIVE.value


def test_bw_ba_03_archival_approved_sensitive_encryption():
    # Step 1: Submit
    resolve_archival_transition(
        ArchivalStatus.NOT_SUBMITTED.value,
        ArchivalStatus.SUBMITTED.value,
        ActorRole.USER,
    )
    # Step 2: HoD approves
    resolve_archival_transition(
        ArchivalStatus.SUBMITTED.value,
        ArchivalStatus.HOD_APPROVED.value,
        ActorRole.HOD,
    )
    # Step 3: SysAdmin classifies as Sensitive
    t3 = resolve_archival_transition(
        ArchivalStatus.HOD_APPROVED.value,
        ArchivalStatus.CLASSIFIED_SENSITIVE.value,
        ActorRole.SYSADMIN,
    )
    assert t3.to == ArchivalStatus.CLASSIFIED_SENSITIVE.value

    # Step 4: IT Security configures encryption
    t4 = resolve_archival_transition(
        ArchivalStatus.CLASSIFIED_SENSITIVE.value,
        ArchivalStatus.SENSITIVE_ARCHIVE_ENCRYPTED.value,
        ActorRole.IT_SECURITY,
    )
    assert t4.to == ArchivalStatus.SENSITIVE_ARCHIVE_ENCRYPTED.value

    # Unauthorized role cannot encrypt
    with pytest.raises(ActorNotAllowed):
        resolve_archival_transition(
            ArchivalStatus.CLASSIFIED_SENSITIVE.value,
            ArchivalStatus.SENSITIVE_ARCHIVE_ENCRYPTED.value,
            ActorRole.SYSADMIN,
        )


def test_cw_ba_01_invalid_archival_skips():
    # Direct skip from Submitted to Encrypted must fail
    with pytest.raises(InvalidTransition):
        resolve_archival_transition(
            ArchivalStatus.SUBMITTED.value,
            ArchivalStatus.SENSITIVE_ARCHIVE_ENCRYPTED.value,
            ActorRole.IT_SECURITY,
        )

    # Reclassifying a rejected request must fail
    with pytest.raises(InvalidTransition):
        resolve_archival_transition(
            ArchivalStatus.REJECTED.value,
            ArchivalStatus.HOD_APPROVED.value,
            ActorRole.HOD,
        )


# ==============================================================================
# Storage Extension Workflows (CW-BA-02, BW-BA-04..05)
# ==============================================================================


def test_bw_ba_04_storage_extension_rejected():
    # Submit
    resolve_extension_transition(
        StorageExtensionStatus.NOT_SUBMITTED.value,
        StorageExtensionStatus.SUBMITTED.value,
        ActorRole.USER,
    )
    # Reject
    t = resolve_extension_transition(
        StorageExtensionStatus.SUBMITTED.value,
        StorageExtensionStatus.REJECTED.value,
        ActorRole.HOD,
    )
    assert t.to == StorageExtensionStatus.REJECTED.value


def test_bw_ba_05_storage_extension_approved():
    # Submit
    resolve_extension_transition(
        StorageExtensionStatus.NOT_SUBMITTED.value,
        StorageExtensionStatus.SUBMITTED.value,
        ActorRole.USER,
    )
    # Approve
    t = resolve_extension_transition(
        StorageExtensionStatus.SUBMITTED.value,
        StorageExtensionStatus.APPROVED.value,
        ActorRole.HOD,
    )
    assert t.to == StorageExtensionStatus.APPROVED.value


def test_cw_ba_02_invalid_extension_transitions():
    # Moving from approved to rejected is invalid
    with pytest.raises(InvalidTransition):
        resolve_extension_transition(
            StorageExtensionStatus.APPROVED.value,
            StorageExtensionStatus.REJECTED.value,
            ActorRole.HOD,
        )


# ==============================================================================
# Restoration Workflows (CW-BA-03, BW-BA-06..07)
# ==============================================================================


def test_bw_ba_06_restoration_standard_path():
    # Intake non-sensitive
    t1 = resolve_restoration_transition(
        RestorationStatus.NOT_REQUESTED.value,
        RestorationStatus.REQUESTED_STANDARD.value,
        ActorRole.USER,
    )
    assert t1.to == RestorationStatus.REQUESTED_STANDARD.value

    # SysAdmin technical execution
    t2 = resolve_restoration_transition(
        RestorationStatus.REQUESTED_STANDARD.value,
        RestorationStatus.RESTORED.value,
        ActorRole.SYSADMIN,
    )
    assert t2.to == RestorationStatus.RESTORED.value


def test_bw_ba_07_restoration_sensitive_sysadmin_approval():
    # Intake sensitive
    t1 = resolve_restoration_transition(
        RestorationStatus.NOT_REQUESTED.value,
        RestorationStatus.PENDING_APPROVAL.value,
        ActorRole.USER,
    )
    assert t1.to == RestorationStatus.PENDING_APPROVAL.value

    # SysAdmin Rejection path
    t_rej = resolve_restoration_transition(
        RestorationStatus.PENDING_APPROVAL.value,
        RestorationStatus.REJECTED.value,
        ActorRole.SYSADMIN,
    )
    assert t_rej.to == RestorationStatus.REJECTED.value

    # SysAdmin Approval path
    t_appr = resolve_restoration_transition(
        RestorationStatus.PENDING_APPROVAL.value,
        RestorationStatus.APPROVED.value,
        ActorRole.SYSADMIN,
    )
    assert t_appr.to == RestorationStatus.APPROVED.value

    # Technical Execution
    t_exec = resolve_restoration_transition(
        RestorationStatus.APPROVED.value,
        RestorationStatus.RESTORED.value,
        ActorRole.SYSADMIN,
    )
    assert t_exec.to == RestorationStatus.RESTORED.value


def test_cw_ba_03_invalid_restoration_transitions():
    # Direct execution of unapproved sensitive restoration fails
    with pytest.raises(InvalidTransition):
        resolve_restoration_transition(
            RestorationStatus.PENDING_APPROVAL.value,
            RestorationStatus.RESTORED.value,
            ActorRole.SYSADMIN,
        )
