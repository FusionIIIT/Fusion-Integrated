REQUISITION_PENDING = "pending_approval"
REQUISITION_DRAFT = "draft"
REQUISITION_APPROVED = "approved"
REQUISITION_REJECTED = "rejected"
REQUISITION_FULFILLED = "fulfilled"
REQUISITION_TERMINAL = frozenset({REQUISITION_REJECTED, REQUISITION_FULFILLED})

REQUISITION_TRANSITIONS = (
    (REQUISITION_DRAFT, "submit", "Compounder", REQUISITION_PENDING),
    (REQUISITION_PENDING, "approve", "Registrar", REQUISITION_APPROVED),
    (REQUISITION_PENDING, "reject", "Registrar", REQUISITION_REJECTED),
    (REQUISITION_APPROVED, "fulfill", "Compounder", REQUISITION_FULFILLED),
)


def requisition_transition(state: str, event: str, actor: str) -> str:
    for source, action, role, target in REQUISITION_TRANSITIONS:
        if (source, action) == (state, event):
            if actor != role:
                raise PermissionError("This action is reserved for the assigned office role.")
            return target
    raise LookupError("The requisition is closed or the requested action is not available.")
