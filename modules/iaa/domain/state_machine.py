"""Pure Python state machines for IAA workflows CW-IAA-01 through CW-IAA-04."""


class InvalidStateTransitionError(Exception):
    def __init__(self, current_state: str, event: str, actor_role: str):
        message = (
            f"Invalid transition: Cannot perform event '{event}' on record in "
            f"state '{current_state}' as actor '{actor_role}'."
        )
        super().__init__(message)
        self.current_state = current_state
        self.event = event
        self.actor_role = actor_role


EXPENSE_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("draft", "submit", "basic_user"): "submitted",
    ("submitted", "raise_query", "finance_staff"): "query_raised",
    ("query_raised", "respond_query", "basic_user"): "query_responded",
    ("query_responded", "validate", "finance_staff"): "finance_validated",
    ("submitted", "validate", "finance_staff"): "finance_validated",
    ("finance_validated", "approve_level", "approving_authority"): "approval_pending",
    ("finance_validated", "approve_final", "approving_authority"): "approved",
    ("finance_validated", "reject", "approving_authority"): "rejected",
    ("finance_validated", "timeout_escalate", "system"): "escalated",
    ("approval_pending", "approve_level", "approving_authority"): "approval_pending",
    ("approval_pending", "approve_final", "approving_authority"): "approved",
    ("approval_pending", "reject", "approving_authority"): "rejected",
    ("approval_pending", "timeout_escalate", "system"): "escalated",
    ("escalated", "approve_level", "approving_authority"): "approval_pending",
    ("escalated", "approve_final", "approving_authority"): "approved",
    ("escalated", "reject", "approving_authority"): "rejected",
    ("approved", "record", "finance_staff"): "recorded",
}

TA_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("not_submitted", "submit", "basic_user"): "submitted",
    ("submitted", "raise_query", "finance_staff"): "query_raised",
    ("query_raised", "respond_query", "basic_user"): "query_responded",
    ("submitted", "verify_standard", "finance_staff"): "verified",
    ("query_responded", "verify_standard", "finance_staff"): "verified",
    ("submitted", "verify_high_value", "finance_staff"): "approval_pending",
    ("query_responded", "verify_high_value", "finance_staff"): "approval_pending",
    ("submitted", "reject", "finance_staff"): "rejected",
    ("query_responded", "reject", "finance_staff"): "rejected",
    ("approval_pending", "approve_level", "approving_authority"): "approval_pending",
    ("approval_pending", "approve_final", "approving_authority"): "approved",
    ("approval_pending", "reject", "approving_authority"): "rejected",
    ("approval_pending", "timeout_escalate", "system"): "escalated",
    ("escalated", "approve_final", "approving_authority"): "approved",
    ("escalated", "reject", "approving_authority"): "rejected",
    ("verified", "record", "finance_staff"): "recorded",
    ("approved", "record", "finance_staff"): "recorded",
}

ANOMALY_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("none", "flag_manual", "finance_or_auditor"): "open",
    ("none", "flag_automatic", "system"): "open",
    ("open", "resolve", "resolver"): "resolved",
    ("open", "escalate", "resolver"): "escalated",
    ("escalated", "resolve", "resolver"): "resolved",
}

AUDIT_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("none", "create", "auditor"): "open",
    ("open", "respond", "basic_user"): "responded",
    ("responded", "close", "auditor"): "closed",
    ("responded", "reject_response", "auditor"): "open",
}


def transition_expense_request(current_state: str, event: str, actor_role: str) -> str:
    key = (current_state, event, actor_role)
    if key not in EXPENSE_TRANSITIONS:
        raise InvalidStateTransitionError(current_state, event, actor_role)
    return EXPENSE_TRANSITIONS[key]


def transition_ta_claim(current_state: str, event: str, actor_role: str) -> str:
    key = (current_state, event, actor_role)
    if key not in TA_TRANSITIONS:
        raise InvalidStateTransitionError(current_state, event, actor_role)
    return TA_TRANSITIONS[key]


def transition_anomaly(current_state: str, event: str, actor_role: str) -> str:
    key = (current_state, event, actor_role)
    if key not in ANOMALY_TRANSITIONS:
        raise InvalidStateTransitionError(current_state, event, actor_role)
    return ANOMALY_TRANSITIONS[key]


def transition_audit_observation(current_state: str, event: str, actor_role: str) -> str:
    key = (current_state, event, actor_role)
    if key not in AUDIT_TRANSITIONS:
        raise InvalidStateTransitionError(current_state, event, actor_role)
    return AUDIT_TRANSITIONS[key]
