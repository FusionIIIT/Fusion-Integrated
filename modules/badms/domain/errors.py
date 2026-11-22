"""Pure domain exceptions for BADMS.

No HTTP status codes or Django references are permitted here.
"""


class BadmsDomainError(Exception):
    """Base exception for all BADMS domain rule and transition violations."""


class InvalidTransition(BadmsDomainError):
    def __init__(self, entity_name: str, frm: str, to: str):
        super().__init__(f"Cannot move {entity_name} from {frm!r} to {to!r}.")
        self.entity_name = entity_name
        self.frm = frm
        self.to = to


class ActorNotAllowed(BadmsDomainError):
    def __init__(self, actor_role: str, action: str):
        super().__init__(f"Actor role {actor_role!r} is not permitted to perform {action!r}.")
        self.actor_role = actor_role
        self.action = action


class GuardFailed(BadmsDomainError):
    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard {guard!r} failed.")
        self.guard = guard


class RuleViolation(BadmsDomainError):
    def __init__(self, rule_id: str, message: str):
        super().__init__(f"[{rule_id}] {message}")
        self.rule_id = rule_id
        self.message = message


class DepartmentScopeViolation(BadmsDomainError):
    def __init__(self, actor_dept_id: int, target_dept_id: int):
        super().__init__(
            f"Department scope violation: actor department ({actor_dept_id}) "
            f"does not match target ({target_dept_id})."
        )
        self.actor_dept_id = actor_dept_id
        self.target_dept_id = target_dept_id


class QuotaExceededError(BadmsDomainError):
    def __init__(self, requested_bytes: int, available_bytes: int):
        super().__init__(
            f"Quota exceeded: requested {requested_bytes} bytes "
            f"exceeds available {available_bytes} bytes."
        )
        self.requested_bytes = requested_bytes
        self.available_bytes = available_bytes


class StorageNotFullError(BadmsDomainError):
    def __init__(self, current_usage: int, quota: int):
        super().__init__(
            f"Cannot request storage extension: current usage ({current_usage}) "
            f"is below quota ({quota})."
        )
        self.current_usage = current_usage
        self.quota = quota


class RepositoryUnreachableError(BadmsDomainError):
    def __init__(self, repository_path: str):
        super().__init__(f"Target repository {repository_path!r} is unreachable.")
        self.repository_path = repository_path
