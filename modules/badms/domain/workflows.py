"""State machines and workflow transitions for BADMS.

Composite Workflows:
- CW-BA-01: Secure Archival Request Processing (BW-BA-01, BW-BA-02, BW-BA-03)
- CW-BA-02: Storage-Extension Request Processing (BW-BA-04, BW-BA-05)
- CW-BA-03: Data Restoration Processing (BW-BA-06, BW-BA-07)

Zero external framework dependencies. Pure Python.
"""

from typing import Optional, Set
from .rules import (
    CLASS_SENSITIVE,
    DomainValidationError,
)


# ---------------------------------------------------------------------------
# Workflow 1: CW-BA-01 Secure Archival States
# ---------------------------------------------------------------------------
ARCHIVAL_NOT_SUBMITTED = "NOT_SUBMITTED"
ARCHIVAL_SUBMITTED = "SUBMITTED"
ARCHIVAL_REJECTED = "REJECTED"
ARCHIVAL_HOD_APPROVED = "HOD_APPROVED"
ARCHIVAL_CLASSIFIED_NON_SENSITIVE = "CLASSIFIED_NON_SENSITIVE"
ARCHIVAL_CLASSIFIED_SENSITIVE = "CLASSIFIED_SENSITIVE"
ARCHIVAL_ENCRYPTED = "SENSITIVE_ARCHIVE_ENCRYPTED"
ARCHIVAL_SPECIAL = "SPECIAL_ARCHIVED"

ARCHIVAL_TERMINAL_STATES = {
    ARCHIVAL_REJECTED,
    ARCHIVAL_CLASSIFIED_NON_SENSITIVE,
    ARCHIVAL_ENCRYPTED,
    ARCHIVAL_SPECIAL,
}


class ArchivalWorkflowEngine:
    """State machine controller for CW-BA-01 Secure Archival Request Processing."""

    @staticmethod
    def transition_submit(current_state: str) -> str:
        """User submits request -> SUBMITTED.
        
        Ref: BA-UC-002, CW-BA-01 step 1.
        """
        if current_state and current_state != ARCHIVAL_NOT_SUBMITTED:
            raise DomainValidationError(
                f"Cannot submit archival request in state '{current_state}'. "
                f"Must be '{ARCHIVAL_NOT_SUBMITTED}'."
            )
        return ARCHIVAL_SUBMITTED

    @staticmethod
    def transition_hod_decision(current_state: str, approved: bool) -> str:
        """HoD reviews request -> HOD_APPROVED or REJECTED.
        
        Ref: BA-UC-003, BW-BA-01 (Reject), BW-BA-02/03 (Approve).
        """
        if current_state != ARCHIVAL_SUBMITTED:
            raise DomainValidationError(
                f"HoD can only decide requests in '{ARCHIVAL_SUBMITTED}' state, "
                f"current state is '{current_state}'."
            )
        return ARCHIVAL_HOD_APPROVED if approved else ARCHIVAL_REJECTED

    @staticmethod
    def transition_sysadmin_classification(current_state: str, authoritative_class: str) -> str:
        """SysAdmin assigns authoritative classification.
        
        If Sensitive -> CLASSIFIED_SENSITIVE (routed to IT Security).
        Otherwise -> CLASSIFIED_NON_SENSITIVE (policy applied).
        Ref: BA-UC-004, BW-BA-02 (Non-Sensitive), BW-BA-03 (Sensitive).
        """
        if current_state != ARCHIVAL_HOD_APPROVED:
            raise DomainValidationError(
                f"SysAdmin can only classify requests that have received HoD approval. "
                f"Current state is '{current_state}'."
            )
        if authoritative_class.strip().upper() == CLASS_SENSITIVE:
            return ARCHIVAL_CLASSIFIED_SENSITIVE
        return ARCHIVAL_CLASSIFIED_NON_SENSITIVE

    @staticmethod
    def transition_it_security_encryption(current_state: str) -> str:
        """IT Security configures AES-256 encryption -> SENSITIVE_ARCHIVE_ENCRYPTED.
        
        Ref: BA-UC-005, BW-BA-03 step 4.
        """
        if current_state != ARCHIVAL_CLASSIFIED_SENSITIVE:
            raise DomainValidationError(
                f"Encryption configuration requires request in '{ARCHIVAL_CLASSIFIED_SENSITIVE}' state. "
                f"Current state is '{current_state}'."
            )
        return ARCHIVAL_ENCRYPTED


# ---------------------------------------------------------------------------
# Workflow 2: CW-BA-02 Storage-Extension Request States
# ---------------------------------------------------------------------------
EXT_NOT_SUBMITTED = "NOT_SUBMITTED"
EXT_SUBMITTED = "SUBMITTED"
EXT_APPROVED = "APPROVED"
EXT_REJECTED = "REJECTED"

EXT_TERMINAL_STATES = {EXT_APPROVED, EXT_REJECTED}


class StorageExtensionWorkflowEngine:
    """State machine controller for CW-BA-02 Storage-Extension Request Processing."""

    @staticmethod
    def transition_submit(current_state: str) -> str:
        """User submits storage extension request -> SUBMITTED.
        
        Ref: BA-UC-007, CW-BA-02 step 1.
        """
        if current_state and current_state != EXT_NOT_SUBMITTED:
            raise DomainValidationError(
                f"Cannot submit storage extension request in state '{current_state}'. "
                f"Must be '{EXT_NOT_SUBMITTED}'."
            )
        return EXT_SUBMITTED

    @staticmethod
    def transition_hod_decision(current_state: str, approved: bool) -> str:
        """HoD reviews storage extension -> APPROVED or REJECTED.
        
        Ref: BA-UC-008, BW-BA-04 (Reject), BW-BA-05 (Approve).
        """
        if current_state != EXT_SUBMITTED:
            raise DomainValidationError(
                f"HoD can only decide storage extension requests in '{EXT_SUBMITTED}' state, "
                f"current state is '{current_state}'."
            )
        return EXT_APPROVED if approved else EXT_REJECTED


# ---------------------------------------------------------------------------
# Workflow 3: CW-BA-03 Data Restoration States
# ---------------------------------------------------------------------------
RESTORE_NOT_REQUESTED = "NOT_REQUESTED"
RESTORE_STANDARD_PENDING = "STANDARD_PENDING"
RESTORE_SENSITIVE_PENDING = "SENSITIVE_PENDING_APPROVAL"
RESTORE_APPROVED_FOR_EXECUTION = "APPROVED_FOR_RESTORATION"
RESTORE_REJECTED = "REJECTED"
RESTORE_COMPLETED = "RESTORED"

RESTORE_TERMINAL_STATES = {RESTORE_REJECTED, RESTORE_COMPLETED}


class RestorationWorkflowEngine:
    """State machine controller for CW-BA-03 Data Restoration Processing."""

    @staticmethod
    def transition_request(current_state: str, is_sensitive: bool) -> str:
        """User requests restoration -> STANDARD_PENDING or SENSITIVE_PENDING_APPROVAL.
        
        Ref: BA-UC-016, BW-BA-06 (Standard), BW-BA-07 (Sensitive).
        """
        if current_state and current_state != RESTORE_NOT_REQUESTED:
            raise DomainValidationError(
                f"Cannot request restoration in state '{current_state}'. "
                f"Must be '{RESTORE_NOT_REQUESTED}'."
            )
        return RESTORE_SENSITIVE_PENDING if is_sensitive else RESTORE_STANDARD_PENDING

    @staticmethod
    def transition_sysadmin_approval(current_state: str, approved: bool) -> str:
        """SysAdmin reviews sensitive restoration -> APPROVED_FOR_RESTORATION or REJECTED.
        
        Ref: BA-UC-017, BW-BA-07 steps 2-3.
        """
        if current_state != RESTORE_SENSITIVE_PENDING:
            raise DomainValidationError(
                f"SysAdmin approval is required only for requests in '{RESTORE_SENSITIVE_PENDING}' state. "
                f"Current state is '{current_state}'."
            )
        return RESTORE_APPROVED_FOR_EXECUTION if approved else RESTORE_REJECTED

    @staticmethod
    def transition_execution(current_state: str) -> str:
        """SysAdmin executes technical restoration -> RESTORED.
        
        Ref: BA-UC-018, BW-BA-06 step 3, BW-BA-07 step 4.
        """
        allowed_states = {RESTORE_STANDARD_PENDING, RESTORE_APPROVED_FOR_EXECUTION}
        if current_state not in allowed_states:
            raise DomainValidationError(
                f"Restoration execution requires state to be one of {allowed_states}. "
                f"Current state is '{current_state}'."
            )
        return RESTORE_COMPLETED
