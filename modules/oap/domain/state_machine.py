"""OAP State Machines.

Pure Python module implementing authoritative state transitions for all 6 procedures:
- Leave Application (BW-OAP-01, BW-OAP-02, CW-OAP-01)
- Bonafide Certificate (BW-OAP-03, BW-OAP-04, CW-OAP-02)
- No-Dues Clearance (BW-OAP-05, BW-OAP-06, CW-OAP-03)
- Assistantship Claim (BW-OAP-07, BW-OAP-08, CW-OAP-04)
- Graduate Seminar (BW-OAP-09)

Enforces guards, business rules, and legal transitions.
"""

from typing import Mapping

from modules.oap.domain import constants as c


class InvalidStateTransitionError(Exception):
    """Raised when an illegal workflow state transition is attempted."""
    pass


class LeaveStateMachine:
    @staticmethod
    def initial_state() -> str:
        return c.LEAVE_SUBMITTED

    @staticmethod
    def transition_decision(current_state: str, decision: str) -> str:
        if current_state != c.LEAVE_SUBMITTED:
            raise InvalidStateTransitionError(
                f"Cannot decide leave in state '{current_state}'. Expected '{c.LEAVE_SUBMITTED}'."
            )
        decision_lower = decision.strip().lower()
        if decision_lower == "approve" or decision_lower == "approved":
            return c.LEAVE_APPROVED
        elif decision_lower == "reject" or decision_lower == "rejected":
            return c.LEAVE_REJECTED
        else:
            raise InvalidStateTransitionError(f"Invalid leave decision: '{decision}'.")


class BonafideStateMachine:
    @staticmethod
    def initial_state() -> str:
        return c.BONAFIDE_SUBMITTED

    @staticmethod
    def transition_decision(current_state: str, decision: str) -> str:
        if current_state != c.BONAFIDE_SUBMITTED:
            raise InvalidStateTransitionError(
                f"Cannot decide bonafide in state '{current_state}'. Expected '{c.BONAFIDE_SUBMITTED}'."
            )
        decision_lower = decision.strip().lower()
        if decision_lower in ("approve", "approved"):
            return c.BONAFIDE_APPROVED
        elif decision_lower in ("reject", "rejected"):
            return c.BONAFIDE_REJECTED
        else:
            raise InvalidStateTransitionError(f"Invalid bonafide decision: '{decision}'.")


class NoDuesStateMachine:
    @staticmethod
    def initial_state() -> str:
        return c.NODUES_VERIFICATION_IN_PROGRESS

    @staticmethod
    def compute_request_state(domain_statuses: Mapping[str, str]) -> str:
        """Determines the consolidated request state from the 7 mandatory authority statuses.
        
        Follows OA-BR-31, OA-BR-32, OA-BR-33.
        """
        # If any mandatory domain is not recorded or is pending
        for domain in c.MANDATORY_NO_DUES_DOMAINS:
            status = domain_statuses.get(domain, c.CLEARANCE_PENDING)
            if status == c.CLEARANCE_PENDING:
                return c.NODUES_VERIFICATION_IN_PROGRESS

        # All 7 verifications recorded
        any_dues_outstanding = any(
            domain_statuses.get(domain) == c.CLEARANCE_DUES_OUTSTANDING
            for domain in c.MANDATORY_NO_DUES_DOMAINS
        )
        if any_dues_outstanding:
            return c.NODUES_COMPLETE_DUES_OUTSTANDING

        return c.NODUES_COMPLETE_ALL_CLEAR

    @staticmethod
    def finalize(current_state: str) -> str:
        """Academic Administrator finalizes no-dues clearance.
        
        OA-BR-33: Guard requires all seven mandatory authority results to be clear.
        """
        if current_state != c.NODUES_COMPLETE_ALL_CLEAR:
            raise InvalidStateTransitionError(
                f"Cannot finalize no-dues in state '{current_state}'. "
                f"Requires '{c.NODUES_COMPLETE_ALL_CLEAR}' (OA-BR-33)."
            )
        return c.NODUES_FINALIZED


class AssistantshipStateMachine:
    @staticmethod
    def initial_state() -> str:
        return c.ASSISTANTSHIP_AWAITING_DUAL_SUPERVISOR

    @staticmethod
    def compute_supervisor_verification_state(thesis_verified: bool, ta_verified: bool) -> str:
        """State transition for dual supervisor verification (OA-BR-42, OA-BR-52)."""
        if thesis_verified and ta_verified:
            return c.ASSISTANTSHIP_AWAITING_DEPT_REVIEW
        if thesis_verified or ta_verified:
            return c.ASSISTANTSHIP_AWAITING_OTHER_SUPERVISOR
        return c.ASSISTANTSHIP_AWAITING_DUAL_SUPERVISOR

    @staticmethod
    def forward_to_hod(current_state: str) -> str:
        """Department Administrator reviews and forwards to HoD (OA-BR-43)."""
        if current_state != c.ASSISTANTSHIP_AWAITING_DEPT_REVIEW:
            raise InvalidStateTransitionError(
                f"Cannot forward claim to HoD in state '{current_state}'. "
                f"Requires '{c.ASSISTANTSHIP_AWAITING_DEPT_REVIEW}' (OA-BR-43)."
            )
        return c.ASSISTANTSHIP_AWAITING_HOD_DECISION

    @staticmethod
    def decide_hod(current_state: str, decision: str) -> str:
        """HoD approves or rejects the assistantship claim (OA-BR-44)."""
        if current_state != c.ASSISTANTSHIP_AWAITING_HOD_DECISION:
            raise InvalidStateTransitionError(
                f"Cannot record HoD decision in state '{current_state}'. "
                f"Requires '{c.ASSISTANTSHIP_AWAITING_HOD_DECISION}' (OA-BR-44)."
            )
        decision_lower = decision.strip().lower()
        if decision_lower in ("approve", "approved"):
            return c.ASSISTANTSHIP_APPROVED_AWAITING_STIPEND
        elif decision_lower in ("reject", "rejected"):
            return c.ASSISTANTSHIP_REJECTED
        else:
            raise InvalidStateTransitionError(f"Invalid HoD decision: '{decision}'.")

    @staticmethod
    def process_stipend(current_state: str) -> str:
        """Academic Administrator processes stipend disbursement (OA-BR-45)."""
        if current_state != c.ASSISTANTSHIP_APPROVED_AWAITING_STIPEND:
            raise InvalidStateTransitionError(
                f"Cannot process stipend disbursement in state '{current_state}'. "
                f"Requires '{c.ASSISTANTSHIP_APPROVED_AWAITING_STIPEND}' (OA-BR-45)."
            )
        return c.ASSISTANTSHIP_STIPEND_PROCESSED


class SeminarStateMachine:
    @staticmethod
    def initial_state() -> str:
        return c.SEMINAR_AWAITING_SCHEDULING

    @staticmethod
    def schedule(current_state: str) -> str:
        """Department Administrator schedules the graduate seminar (OA-BR-62)."""
        if current_state != c.SEMINAR_AWAITING_SCHEDULING:
            raise InvalidStateTransitionError(
                f"Cannot schedule seminar in state '{current_state}'. "
                f"Requires '{c.SEMINAR_AWAITING_SCHEDULING}' (OA-BR-62)."
            )
        return c.SEMINAR_SCHEDULED
