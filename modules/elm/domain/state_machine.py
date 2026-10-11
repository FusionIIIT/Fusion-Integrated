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
    SUBMITTED = "submitted"      # routed; awaiting substitute consent or decision
    APPROVED = "approved"        # final, balance deducted
    REJECTED = "rejected"        # final
    WITHDRAWN = "withdrawn"      # applicant pulled it before a final decision
    CANCELLED = "cancelled"      # approved leave reversed before it began

    @property
    def is_final(self) -> bool:
        return self in (LeaveStatus.APPROVED, LeaveStatus.REJECTED,
                        LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED)


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
    Transition(None, LeaveStatus.SUBMITTED,
               permission="elm.application.create"),
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.APPROVED,
               permission="elm.application.decide"),
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED,
               permission="elm.application.decide"),
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.WITHDRAWN,
               permission="elm.application.withdraw"),
    Transition(LeaveStatus.APPROVED, LeaveStatus.CANCELLED,
               permission="elm.application.cancel"),
)

TERMINAL = {LeaveStatus.REJECTED, LeaveStatus.WITHDRAWN, LeaveStatus.CANCELLED}


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
