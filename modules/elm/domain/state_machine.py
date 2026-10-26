"""Leave request lifecycle.

A declarative transition table, not if-chains: an illegal transition is
impossible to express, and each row names the permission that authorises it so
the permission manifest can prove the permission is actually enforced
(module-authoring-guide step 3).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LeaveStatus(StrEnum):
    SUBMITTED = "submitted"                    # awaiting substitute consent or decision
    FORWARDED = "forwarded"                    # recommended by Unit Head; awaiting sanction
    APPROVED = "approved"                      # final, balance deducted
    REJECTED = "rejected"                      # final
    WITHDRAWN = "withdrawn"                    # applicant pulled it before a final decision
    CANCELLATION_REQUESTED = "cancel_req"      # cancellation requested before start
    CANCELLED = "cancelled"                    # approved leave reversed and balance restored
    RESUMPTION_REQUESTED = "res_req"           # employee returned and submitted resumption
    RESUMED = "resumed"                        # resumption reviewed and synchronized

    @property
    def is_final(self) -> bool:
        return self in (LeaveStatus.APPROVED, LeaveStatus.REJECTED,
                        LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED,
                        LeaveStatus.RESUMED)


class SubstituteStatus(StrEnum):
    NONE = "none"                # no substitute required
    PENDING = "pending"          # nominated, awaiting consent
    ACCEPTED = "accepted"
    DECLINED = "declined"


@dataclass(frozen=True)
class Transition:
    frm: LeaveStatus | None
    to: LeaveStatus
    permission: str


TRANSITIONS: tuple[Transition, ...] = (
    # Creation
    Transition(None, LeaveStatus.SUBMITTED,
               permission="elm.application.create"),
    # Direct decision (CL/RH at Unit Head, or Director self-sanction)
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.APPROVED,
               permission="elm.application.decide"),
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED,
               permission="elm.application.decide"),
    # Unit Head recommendation for higher-sanction categories (SCL, EL, COL, VL)
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.FORWARDED,
               permission="elm.application.recommend"),
    # Higher sanction decision
    Transition(LeaveStatus.FORWARDED, LeaveStatus.APPROVED,
               permission="elm.application.decide"),
    Transition(LeaveStatus.FORWARDED, LeaveStatus.REJECTED,
               permission="elm.application.decide"),
    # Immediate withdrawal at any point before final approval
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.WITHDRAWN,
               permission="elm.application.withdraw"),
    Transition(LeaveStatus.FORWARDED, LeaveStatus.WITHDRAWN,
               permission="elm.application.withdraw"),
    # Pre-start cancellation workflow
    Transition(LeaveStatus.APPROVED, LeaveStatus.CANCELLATION_REQUESTED,
               permission="elm.application.cancel"),
    Transition(LeaveStatus.CANCELLATION_REQUESTED, LeaveStatus.CANCELLED,
               permission="elm.application.decide"),
    Transition(LeaveStatus.CANCELLATION_REQUESTED, LeaveStatus.APPROVED,
               permission="elm.application.decide"),
    # Resumption workflow
    Transition(LeaveStatus.APPROVED, LeaveStatus.RESUMPTION_REQUESTED,
               permission="elm.application.resume"),
    Transition(LeaveStatus.RESUMPTION_REQUESTED, LeaveStatus.RESUMED,
               permission="elm.application.decide"),
)

TERMINAL = {LeaveStatus.REJECTED, LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED, LeaveStatus.RESUMED}


def transition_for(frm: LeaveStatus | None, to: LeaveStatus) -> Transition:
    for t in TRANSITIONS:
        if t.frm == frm and t.to == to:
            return t
    raise InvalidTransition(frm, to)


class InvalidTransition(Exception):
    def __init__(self, frm, to):
        self.frm = frm
        self.to = to
        super().__init__(f"Cannot move leave from {frm} to {to}.")
