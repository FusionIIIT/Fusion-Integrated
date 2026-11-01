"""RSPC domain state machines — pure Python, no Django imports.

Covers all request types per the workflow specifications:
  BW-RSPC-01/02 Research Project Proposal
  BW-RSPC-03/04 Consultancy Project
  BW-RSPC-05/06 Staff Appointment
  BW-RSPC-07/08 Financial Request
  BW-RSPC-09/10 Procurement Request
  CW-RSPC-06/07 Progress Report / Project Closure

Each state machine is a tuple of Transition records.  A transition that is not
in the table is impossible to express, making illegal moves obvious at
authoring time rather than detectable only in production.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str) -> None:
        super().__init__(f"Cannot move from {frm!r} to {to!r}.")
        self.frm = frm
        self.to = to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str) -> None:
        super().__init__(
            f"A {actor_kind!r} may not move from {frm!r} to {to!r}.")
        self.actor_kind = actor_kind
        self.frm = frm
        self.to = to


class GuardFailed(Exception):
    def __init__(self, guard: str, message: str = "") -> None:
        super().__init__(message or f"Guard {guard!r} failed.")
        self.guard = guard


# ---------------------------------------------------------------------------
# Transition record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    guards: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Research Project Proposal States  (BW-RSPC-01, BW-RSPC-02)
# ---------------------------------------------------------------------------

class ProposalStatus:
    DRAFT              = "draft"
    SUBMITTED          = "submitted"
    HOD_REVIEW         = "hod_review"
    HOD_RECOMMENDED    = "hod_recommended"
    HOD_NOT_RECOMMENDED = "hod_not_recommended"
    ADMIN_VERIFIED     = "admin_verified"
    DEAN_APPROVED      = "dean_approved"
    DEAN_REJECTED      = "dean_rejected"
    FORWARDED_DIRECTOR = "forwarded_director"
    DIRECTOR_APPROVED  = "director_approved"
    DIRECTOR_REJECTED  = "director_rejected"


PROPOSAL_TERMINAL = frozenset({
    ProposalStatus.HOD_NOT_RECOMMENDED,
    ProposalStatus.DEAN_REJECTED,
    ProposalStatus.DIRECTOR_REJECTED,
    ProposalStatus.DEAN_APPROVED,
    ProposalStatus.DIRECTOR_APPROVED,
})

PROPOSAL_TRANSITIONS: tuple[Transition, ...] = (
    Transition(ProposalStatus.DRAFT, ProposalStatus.SUBMITTED,
               "rspc.proposal.create", ("mandatory_fields_present",)),
    Transition(ProposalStatus.SUBMITTED, ProposalStatus.HOD_REVIEW,
               "rspc.proposal.review_hod"),
    Transition(ProposalStatus.HOD_REVIEW, ProposalStatus.HOD_RECOMMENDED,
               "rspc.proposal.review_hod"),
    Transition(ProposalStatus.HOD_REVIEW, ProposalStatus.HOD_NOT_RECOMMENDED,
               "rspc.proposal.review_hod", ("has_remarks",)),
    Transition(ProposalStatus.HOD_RECOMMENDED, ProposalStatus.ADMIN_VERIFIED,
               "rspc.proposal.verify_admin", ("completeness_check",)),
    Transition(ProposalStatus.ADMIN_VERIFIED, ProposalStatus.DEAN_APPROVED,
               "rspc.proposal.decide_dean"),
    Transition(ProposalStatus.ADMIN_VERIFIED, ProposalStatus.DEAN_REJECTED,
               "rspc.proposal.decide_dean", ("has_remarks",)),
    Transition(ProposalStatus.ADMIN_VERIFIED, ProposalStatus.FORWARDED_DIRECTOR,
               "rspc.proposal.decide_dean"),
    Transition(ProposalStatus.FORWARDED_DIRECTOR, ProposalStatus.DIRECTOR_APPROVED,
               "rspc.proposal.decide_director"),
    Transition(ProposalStatus.FORWARDED_DIRECTOR, ProposalStatus.DIRECTOR_REJECTED,
               "rspc.proposal.decide_director", ("has_remarks",)),
)


# ---------------------------------------------------------------------------
# Consultancy Project States  (BW-RSPC-03, BW-RSPC-04, CW-RSPC-01/02)
# ---------------------------------------------------------------------------

class ConsultancyStatus:
    DRAFT              = "draft"
    SUBMITTED          = "submitted"
    HOD_REVIEW         = "hod_review"
    HOD_RECOMMENDED    = "hod_recommended"
    ADMIN_VERIFIED     = "admin_verified"
    DEAN_APPROVED      = "dean_approved"
    DEAN_REJECTED      = "dean_rejected"
    FORWARDED_DIRECTOR = "forwarded_director"
    DIRECTOR_APPROVED  = "director_approved"
    DIRECTOR_REJECTED  = "director_rejected"


CONSULTANCY_TERMINAL = frozenset({
    ConsultancyStatus.DEAN_APPROVED,
    ConsultancyStatus.DEAN_REJECTED,
    ConsultancyStatus.DIRECTOR_APPROVED,
    ConsultancyStatus.DIRECTOR_REJECTED,
})

CONSULTANCY_TRANSITIONS: tuple[Transition, ...] = (
    Transition(ConsultancyStatus.DRAFT, ConsultancyStatus.SUBMITTED,
               "rspc.consultancy.create", ("mandatory_fields_present",)),
    Transition(ConsultancyStatus.SUBMITTED, ConsultancyStatus.HOD_REVIEW,
               "rspc.consultancy.review_hod"),
    Transition(ConsultancyStatus.HOD_REVIEW, ConsultancyStatus.HOD_RECOMMENDED,
               "rspc.consultancy.review_hod"),
    Transition(ConsultancyStatus.HOD_RECOMMENDED, ConsultancyStatus.ADMIN_VERIFIED,
               "rspc.consultancy.verify_admin"),
    # Direct path without HoD when represented path skips HoD stage
    Transition(ConsultancyStatus.SUBMITTED, ConsultancyStatus.ADMIN_VERIFIED,
               "rspc.consultancy.verify_admin"),
    Transition(ConsultancyStatus.ADMIN_VERIFIED, ConsultancyStatus.DEAN_APPROVED,
               "rspc.consultancy.decide_dean"),
    Transition(ConsultancyStatus.ADMIN_VERIFIED, ConsultancyStatus.DEAN_REJECTED,
               "rspc.consultancy.decide_dean", ("has_remarks",)),
    Transition(ConsultancyStatus.ADMIN_VERIFIED, ConsultancyStatus.FORWARDED_DIRECTOR,
               "rspc.consultancy.decide_dean"),
    Transition(ConsultancyStatus.FORWARDED_DIRECTOR, ConsultancyStatus.DIRECTOR_APPROVED,
               "rspc.consultancy.decide_director"),
    Transition(ConsultancyStatus.FORWARDED_DIRECTOR, ConsultancyStatus.DIRECTOR_REJECTED,
               "rspc.consultancy.decide_director", ("has_remarks",)),
)


# ---------------------------------------------------------------------------
# Staff Appointment States  (BW-RSPC-05, BW-RSPC-06, CW-RSPC-03)
# ---------------------------------------------------------------------------

class AppointmentStatus:
    DRAFT                        = "draft"
    REQUESTED                    = "requested"
    ADMIN_VERIFIED               = "admin_verified"
    SELECTION_RECOMMENDATION     = "selection_recommendation_recorded"
    APPROVED                     = "approved"
    FORWARDED_DIRECTOR           = "forwarded_director"
    DIRECTOR_APPROVED            = "director_approved"
    REJECTED                     = "rejected"


APPOINTMENT_TERMINAL = frozenset({
    AppointmentStatus.APPROVED,
    AppointmentStatus.DIRECTOR_APPROVED,
    AppointmentStatus.REJECTED,
})

APPOINTMENT_TRANSITIONS: tuple[Transition, ...] = (
    Transition(AppointmentStatus.DRAFT, AppointmentStatus.REQUESTED,
               "rspc.appointment.create", ("mandatory_fields_present",)),
    Transition(AppointmentStatus.REQUESTED, AppointmentStatus.ADMIN_VERIFIED,
               "rspc.appointment.manage_admin"),
    Transition(AppointmentStatus.ADMIN_VERIFIED,
               AppointmentStatus.SELECTION_RECOMMENDATION,
               "rspc.appointment.recommend"),
    Transition(AppointmentStatus.SELECTION_RECOMMENDATION,
               AppointmentStatus.APPROVED,
               "rspc.appointment.decide_dean"),
    Transition(AppointmentStatus.SELECTION_RECOMMENDATION,
               AppointmentStatus.FORWARDED_DIRECTOR,
               "rspc.appointment.decide_dean"),
    Transition(AppointmentStatus.FORWARDED_DIRECTOR,
               AppointmentStatus.DIRECTOR_APPROVED,
               "rspc.appointment.decide_director"),
    Transition(AppointmentStatus.FORWARDED_DIRECTOR,
               AppointmentStatus.REJECTED,
               "rspc.appointment.decide_director", ("has_remarks",)),
)


# ---------------------------------------------------------------------------
# Financial / Fund Request States  (BW-RSPC-07, BW-RSPC-08, CW-RSPC-04)
# ---------------------------------------------------------------------------

class FinanceStatus:
    DRAFT              = "draft"
    SUBMITTED          = "submitted"
    VERIFIED           = "verified"
    APPROVED           = "approved"
    FORWARDED_DIRECTOR = "forwarded_director"
    DIRECTOR_APPROVED  = "director_approved"
    REJECTED           = "rejected"


FINANCE_TERMINAL = frozenset({
    FinanceStatus.APPROVED,
    FinanceStatus.DIRECTOR_APPROVED,
    FinanceStatus.REJECTED,
})

FINANCE_TRANSITIONS: tuple[Transition, ...] = (
    Transition(FinanceStatus.DRAFT, FinanceStatus.SUBMITTED,
               "rspc.finance.create", ("mandatory_fields_present",)),
    Transition(FinanceStatus.SUBMITTED, FinanceStatus.VERIFIED,
               "rspc.finance.verify_admin"),
    Transition(FinanceStatus.VERIFIED, FinanceStatus.APPROVED,
               "rspc.finance.decide_dean"),
    Transition(FinanceStatus.VERIFIED, FinanceStatus.REJECTED,
               "rspc.finance.decide_dean", ("has_remarks",)),
    Transition(FinanceStatus.VERIFIED, FinanceStatus.FORWARDED_DIRECTOR,
               "rspc.finance.decide_dean"),
    Transition(FinanceStatus.FORWARDED_DIRECTOR, FinanceStatus.DIRECTOR_APPROVED,
               "rspc.finance.decide_director"),
    Transition(FinanceStatus.FORWARDED_DIRECTOR, FinanceStatus.REJECTED,
               "rspc.finance.decide_director", ("has_remarks",)),
)


# ---------------------------------------------------------------------------
# Procurement Request States  (BW-RSPC-09, BW-RSPC-10, CW-RSPC-05)
# ---------------------------------------------------------------------------

class ProcurementStatus:
    DRAFT              = "draft"
    SUBMITTED          = "submitted"
    VERIFIED           = "verified"
    APPROVED           = "approved"
    FORWARDED_DIRECTOR = "forwarded_director"
    DIRECTOR_APPROVED  = "director_approved"
    REJECTED           = "rejected"


PROCUREMENT_TERMINAL = frozenset({
    ProcurementStatus.APPROVED,
    ProcurementStatus.DIRECTOR_APPROVED,
    ProcurementStatus.REJECTED,
})

PROCUREMENT_TRANSITIONS: tuple[Transition, ...] = (
    Transition(ProcurementStatus.DRAFT, ProcurementStatus.SUBMITTED,
               "rspc.procurement.create", ("mandatory_fields_present",)),
    Transition(ProcurementStatus.SUBMITTED, ProcurementStatus.VERIFIED,
               "rspc.procurement.verify_admin",
               ("budget_check",)),
    Transition(ProcurementStatus.VERIFIED, ProcurementStatus.APPROVED,
               "rspc.procurement.decide_dean"),
    Transition(ProcurementStatus.VERIFIED, ProcurementStatus.REJECTED,
               "rspc.procurement.decide_dean", ("has_remarks",)),
    Transition(ProcurementStatus.VERIFIED, ProcurementStatus.FORWARDED_DIRECTOR,
               "rspc.procurement.decide_dean"),
    Transition(ProcurementStatus.FORWARDED_DIRECTOR, ProcurementStatus.DIRECTOR_APPROVED,
               "rspc.procurement.decide_director"),
    Transition(ProcurementStatus.FORWARDED_DIRECTOR, ProcurementStatus.REJECTED,
               "rspc.procurement.decide_director", ("has_remarks",)),
)


# ---------------------------------------------------------------------------
# Progress Report States  (CW-RSPC-06)
# ---------------------------------------------------------------------------

class ProgressReportStatus:
    DRAFT     = "draft"
    SUBMITTED = "submitted"
    ACCEPTED  = "accepted"
    RETURNED  = "returned"


PROGRESS_REPORT_TERMINAL = frozenset({
    ProgressReportStatus.ACCEPTED,
})

PROGRESS_REPORT_TRANSITIONS: tuple[Transition, ...] = (
    Transition(ProgressReportStatus.DRAFT, ProgressReportStatus.SUBMITTED,
               "rspc.progress_report.submit", ("mandatory_fields_present",)),
    Transition(ProgressReportStatus.RETURNED, ProgressReportStatus.SUBMITTED,
               "rspc.progress_report.submit"),
    Transition(ProgressReportStatus.SUBMITTED, ProgressReportStatus.ACCEPTED,
               "rspc.progress_report.manage"),
    Transition(ProgressReportStatus.SUBMITTED, ProgressReportStatus.RETURNED,
               "rspc.progress_report.manage", ("has_remarks",)),
)


# ---------------------------------------------------------------------------
# Project Closure States  (CW-RSPC-07)
# ---------------------------------------------------------------------------

class ClosureStatus:
    DRAFT          = "draft"
    SUBMITTED      = "submitted"
    ADMIN_VERIFIED = "admin_verified"
    DEAN_APPROVED  = "dean_approved"
    DEAN_REJECTED  = "dean_rejected"


CLOSURE_TERMINAL = frozenset({
    ClosureStatus.DEAN_APPROVED,
    ClosureStatus.DEAN_REJECTED,
})

CLOSURE_TRANSITIONS: tuple[Transition, ...] = (
    Transition(ClosureStatus.DRAFT, ClosureStatus.SUBMITTED,
               "rspc.closure.submit", ("mandatory_fields_present",)),
    Transition(ClosureStatus.SUBMITTED, ClosureStatus.ADMIN_VERIFIED,
               "rspc.closure.verify_admin"),
    Transition(ClosureStatus.ADMIN_VERIFIED, ClosureStatus.DEAN_APPROVED,
               "rspc.closure.decide_dean"),
    Transition(ClosureStatus.ADMIN_VERIFIED, ClosureStatus.DEAN_REJECTED,
               "rspc.closure.decide_dean", ("has_remarks",)),
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _find_transition(
    transitions: tuple[Transition, ...], frm: str, to: str,
) -> Transition:
    matches = [t for t in transitions if t.frm == frm and t.to == to]
    if not matches:
        raise InvalidTransition(frm, to)
    return matches[0]


def validate_transition(
    transitions: tuple[Transition, ...],
    frm: str,
    to: str,
    permissions: set[str],
    context: dict | None = None,
) -> Transition:
    """Assert the move is legal, the caller has the right permission,
    and any guards pass.  Raises domain errors — no Django/DRF."""
    t = _find_transition(transitions, frm, to)

    if t.permission not in permissions:
        raise ActorNotAllowed("caller", frm, to)

    ctx = context or {}
    for guard in t.guards:
        if guard == "mandatory_fields_present":
            if not ctx.get("mandatory_fields_present", True):
                raise GuardFailed(guard, "All mandatory fields must be filled.")
        elif guard == "has_remarks":
            if not ctx.get("has_remarks", False):
                raise GuardFailed(guard,
                                  "Remarks are required for this decision.")
        elif guard == "completeness_check":
            if not ctx.get("completeness_check", True):
                raise GuardFailed(guard,
                                  "The request does not pass completeness check.")
        elif guard == "budget_check":
            if not ctx.get("budget_check", True):
                raise GuardFailed(guard,
                                  "Request exceeds the sanctioned project budget.")
    return t
