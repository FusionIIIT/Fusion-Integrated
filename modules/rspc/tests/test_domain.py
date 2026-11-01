"""Tests for RSPC domain state machines.

Pure Python, fast, zero DB interaction.
"""
import pytest

from modules.rspc.domain.state_machine import (
    ProposalStatus, ConsultancyStatus, AppointmentStatus,
    FinanceStatus, ProcurementStatus, ProgressReportStatus, ClosureStatus,
    PROPOSAL_TRANSITIONS, CONSULTANCY_TRANSITIONS, APPOINTMENT_TRANSITIONS,
    FINANCE_TRANSITIONS, PROCUREMENT_TRANSITIONS, PROGRESS_REPORT_TRANSITIONS,
    CLOSURE_TRANSITIONS,
    PROPOSAL_TERMINAL, CONSULTANCY_TERMINAL, APPOINTMENT_TERMINAL,
    FINANCE_TERMINAL, PROCUREMENT_TERMINAL, PROGRESS_REPORT_TERMINAL,
    CLOSURE_TERMINAL,
    validate_transition,
    InvalidTransition, ActorNotAllowed, GuardFailed,
)


# ---------------------------------------------------------------------------
# Research Project Proposal
# ---------------------------------------------------------------------------

def test_proposal_draft_to_submitted_success():
    t = validate_transition(
        PROPOSAL_TRANSITIONS,
        ProposalStatus.DRAFT,
        ProposalStatus.SUBMITTED,
        permissions={"rspc.proposal.create"},
        context={"mandatory_fields_present": True},
    )
    assert t.to == ProposalStatus.SUBMITTED


def test_proposal_draft_to_submitted_guard_failed():
    with pytest.raises(GuardFailed) as exc:
        validate_transition(
            PROPOSAL_TRANSITIONS,
            ProposalStatus.DRAFT,
            ProposalStatus.SUBMITTED,
            permissions={"rspc.proposal.create"},
            context={"mandatory_fields_present": False},
        )
    assert "mandatory" in str(exc.value).lower()


def test_proposal_invalid_transition():
    with pytest.raises(InvalidTransition):
        validate_transition(
            PROPOSAL_TRANSITIONS,
            ProposalStatus.DRAFT,
            ProposalStatus.DEAN_APPROVED,
            permissions={"*"},
        )


def test_proposal_permission_denied():
    with pytest.raises(ActorNotAllowed):
        validate_transition(
            PROPOSAL_TRANSITIONS,
            ProposalStatus.DRAFT,
            ProposalStatus.SUBMITTED,
            permissions={"rspc.other.permission"},
        )


def test_proposal_hod_review_flow():
    # Recommend
    t1 = validate_transition(
        PROPOSAL_TRANSITIONS,
        ProposalStatus.HOD_REVIEW,
        ProposalStatus.HOD_RECOMMENDED,
        permissions={"rspc.proposal.review_hod"},
    )
    assert t1.to == ProposalStatus.HOD_RECOMMENDED

    # Not recommend requires remarks guard
    with pytest.raises(GuardFailed):
        validate_transition(
            PROPOSAL_TRANSITIONS,
            ProposalStatus.HOD_REVIEW,
            ProposalStatus.HOD_NOT_RECOMMENDED,
            permissions={"rspc.proposal.review_hod"},
            context={"has_remarks": False},
        )


# ---------------------------------------------------------------------------
# Consultancy Project
# ---------------------------------------------------------------------------

def test_consultancy_flow():
    # Draft -> Submitted
    t = validate_transition(
        CONSULTANCY_TRANSITIONS,
        ConsultancyStatus.DRAFT,
        ConsultancyStatus.SUBMITTED,
        permissions={"rspc.consultancy.create"},
        context={"mandatory_fields_present": True},
    )
    assert t.to == ConsultancyStatus.SUBMITTED

    # Direct to Admin Verified (skipping HoD if configured)
    t2 = validate_transition(
        CONSULTANCY_TRANSITIONS,
        ConsultancyStatus.SUBMITTED,
        ConsultancyStatus.ADMIN_VERIFIED,
        permissions={"rspc.consultancy.verify_admin"},
    )
    assert t2.to == ConsultancyStatus.ADMIN_VERIFIED


# ---------------------------------------------------------------------------
# Staff Appointment
# ---------------------------------------------------------------------------

def test_appointment_lifecycle():
    t = validate_transition(
        APPOINTMENT_TRANSITIONS,
        AppointmentStatus.DRAFT,
        AppointmentStatus.REQUESTED,
        permissions={"rspc.appointment.create"},
        context={"mandatory_fields_present": True},
    )
    assert t.to == AppointmentStatus.REQUESTED


# ---------------------------------------------------------------------------
# Financial and Procurement Requests
# ---------------------------------------------------------------------------

def test_financial_flow():
    t = validate_transition(
        FINANCE_TRANSITIONS,
        FinanceStatus.DRAFT,
        FinanceStatus.SUBMITTED,
        permissions={"rspc.finance.create"},
        context={"mandatory_fields_present": True},
    )
    assert t.to == FinanceStatus.SUBMITTED


def test_procurement_budget_guard():
    with pytest.raises(GuardFailed):
        validate_transition(
            PROCUREMENT_TRANSITIONS,
            ProcurementStatus.SUBMITTED,
            ProcurementStatus.VERIFIED,
            permissions={"rspc.procurement.verify_admin"},
            context={"budget_check": False},
        )


# ---------------------------------------------------------------------------
# Progress Report and Closure
# ---------------------------------------------------------------------------

def test_progress_report_return_flow():
    t = validate_transition(
        PROGRESS_REPORT_TRANSITIONS,
        ProgressReportStatus.SUBMITTED,
        ProgressReportStatus.RETURNED,
        permissions={"rspc.progress_report.manage"},
        context={"has_remarks": True},
    )
    assert t.to == ProgressReportStatus.RETURNED


def test_closure_flow():
    t = validate_transition(
        CLOSURE_TRANSITIONS,
        ClosureStatus.DRAFT,
        ClosureStatus.SUBMITTED,
        permissions={"rspc.closure.submit"},
        context={"mandatory_fields_present": True},
    )
    assert t.to == ClosureStatus.SUBMITTED
