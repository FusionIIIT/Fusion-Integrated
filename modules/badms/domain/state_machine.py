from dataclasses import dataclass

# Archival Request States (CW-BA-01, BW-BA-01, BW-BA-02, BW-BA-03)
ARCHIVAL_SUBMITTED = "submitted"
ARCHIVAL_REJECTED = "rejected"
ARCHIVAL_HOD_APPROVED = "hod_approved"
ARCHIVAL_CLASSIFIED_NON_SENSITIVE = "classified_non_sensitive"
ARCHIVAL_CLASSIFIED_SENSITIVE = "classified_sensitive"
ARCHIVAL_SENSITIVE_ENCRYPTED = "sensitive_archive_encrypted"
ARCHIVAL_SPECIAL_ARCHIVED = "special_archived"

ARCHIVAL_TERMINAL_STATES = frozenset(
    {
        ARCHIVAL_REJECTED,
        ARCHIVAL_CLASSIFIED_NON_SENSITIVE,
        ARCHIVAL_SENSITIVE_ENCRYPTED,
        ARCHIVAL_SPECIAL_ARCHIVED,
    }
)

# Storage Extension Request States (CW-BA-02, BW-BA-04, BW-BA-05)
STORAGE_SUBMITTED = "submitted"
STORAGE_APPROVED = "approved"
STORAGE_REJECTED = "rejected"

STORAGE_TERMINAL_STATES = frozenset({STORAGE_APPROVED, STORAGE_REJECTED})

# Restoration Request States (CW-BA-03, BW-BA-06, BW-BA-07)
RESTORATION_REQUESTED_STANDARD = "requested_standard"
RESTORATION_SENSITIVE_PENDING = "sensitive_pending_approval"
RESTORATION_APPROVED = "approved"
RESTORATION_REJECTED = "rejected"
RESTORATION_RESTORED = "restored"

RESTORATION_TERMINAL_STATES = frozenset({RESTORATION_REJECTED, RESTORATION_RESTORED})


class InvalidStateTransitionError(Exception):
    def __init__(self, workflow: str, current_state: str, event: str):
        super().__init__(
            f"Invalid transition {event!r} from state {current_state!r} in {workflow}. "
            "Please verify the current record status before retrying."
        )
        self.workflow = workflow
        self.current_state = current_state
        self.event = event


class UnauthorizedTransitionActorError(Exception):
    def __init__(self, actor_role: str, event: str):
        super().__init__(
            f"Actor with role {actor_role!r} is not authorized to trigger {event!r}. "
            "Please switch to an authorized role or request approval from the designated owner."
        )
        self.actor_role = actor_role
        self.event = event


@dataclass(frozen=True)
class StateTransition:
    source_state: str
    event: str
    actor_role: str
    target_state: str


# (source_state, event, actor_role) -> target_state
ARCHIVAL_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("none", "submit", "user"): ARCHIVAL_SUBMITTED,
    (ARCHIVAL_SUBMITTED, "reject", "hod"): ARCHIVAL_REJECTED,
    (ARCHIVAL_SUBMITTED, "approve", "hod"): ARCHIVAL_HOD_APPROVED,
    (
        ARCHIVAL_HOD_APPROVED,
        "classify_non_sensitive",
        "sysadmin",
    ): ARCHIVAL_CLASSIFIED_NON_SENSITIVE,
    (ARCHIVAL_HOD_APPROVED, "classify_sensitive", "sysadmin"): ARCHIVAL_CLASSIFIED_SENSITIVE,
    (
        ARCHIVAL_CLASSIFIED_SENSITIVE,
        "encrypt_and_create",
        "it_security",
    ): ARCHIVAL_SENSITIVE_ENCRYPTED,
    ("none", "special_archive", "super_admin"): ARCHIVAL_SPECIAL_ARCHIVED,
}

STORAGE_EXTENSION_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("none", "submit", "user"): STORAGE_SUBMITTED,
    (STORAGE_SUBMITTED, "reject", "hod"): STORAGE_REJECTED,
    (STORAGE_SUBMITTED, "approve", "hod"): STORAGE_APPROVED,
}

RESTORATION_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("none", "request_non_sensitive", "user"): RESTORATION_REQUESTED_STANDARD,
    ("none", "request_sensitive", "user"): RESTORATION_SENSITIVE_PENDING,
    (RESTORATION_SENSITIVE_PENDING, "reject", "sysadmin"): RESTORATION_REJECTED,
    (RESTORATION_SENSITIVE_PENDING, "approve", "sysadmin"): RESTORATION_APPROVED,
    (RESTORATION_REQUESTED_STANDARD, "execute", "sysadmin"): RESTORATION_RESTORED,
    (RESTORATION_APPROVED, "execute", "sysadmin"): RESTORATION_RESTORED,
}


def transition_archival(current_state: str, event: str, actor_role: str) -> str:
    key = (current_state, event, actor_role)
    if key in ARCHIVAL_TRANSITIONS:
        return ARCHIVAL_TRANSITIONS[key]
    for (src, ev, _) in ARCHIVAL_TRANSITIONS:
        if src == current_state and ev == event:
            raise UnauthorizedTransitionActorError(actor_role, event)
    raise InvalidStateTransitionError("archival", current_state, event)


def transition_storage_extension(current_state: str, event: str, actor_role: str) -> str:
    key = (current_state, event, actor_role)
    if key in STORAGE_EXTENSION_TRANSITIONS:
        return STORAGE_EXTENSION_TRANSITIONS[key]
    for (src, ev, _) in STORAGE_EXTENSION_TRANSITIONS:
        if src == current_state and ev == event:
            raise UnauthorizedTransitionActorError(actor_role, event)
    raise InvalidStateTransitionError("storage_extension", current_state, event)


def transition_restoration(current_state: str, event: str, actor_role: str) -> str:
    key = (current_state, event, actor_role)
    if key in RESTORATION_TRANSITIONS:
        return RESTORATION_TRANSITIONS[key]
    for (src, ev, _) in RESTORATION_TRANSITIONS:
        if src == current_state and ev == event:
            raise UnauthorizedTransitionActorError(actor_role, event)
    raise InvalidStateTransitionError("restoration", current_state, event)
