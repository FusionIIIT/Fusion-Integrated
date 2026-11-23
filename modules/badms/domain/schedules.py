import re

CRON_REGEX = (
    r"^(\*|[0-9,\-\*/]+)\s+(\*|[0-9,\-\*/]+)\s+(\*|[0-9,\-\*/]+)\s+"
    r"(\*|[0-9,\-\*/]+)\s+(\*|[0-9,\-\*/]+)$"
)


class InvalidScheduleParametersError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class ScheduleConflictError(Exception):
    """Raised when an active backup schedule already exists for the dataset and scope."""

    def __init__(self, message: str = "A conflicting backup schedule already exists."):
        super().__init__(message)


def validate_schedule_conflict(has_conflict: bool, dataset_name: str, scope_type: str) -> None:
    if has_conflict:
        raise ScheduleConflictError(
            f"An active backup schedule already exists for dataset '{dataset_name}' "
            f"with scope '{scope_type}'. "
            "Update the existing schedule or deactivate it before creating a new one."
        )


def validate_cron_expression(expression: str) -> None:
    parts = expression.strip().split()
    if len(parts) != 5 or not re.match(CRON_REGEX, expression.strip()):
        raise InvalidScheduleParametersError(
            "Schedule cron expression must have 5 standard whitespace-separated fields. "
            "Please provide a valid 5-part cron pattern such as '0 2 * * *'."
        )


def resolve_effective_schedule(
    local_schedule: dict | None, global_schedule: dict | None
) -> dict | None:
    if local_schedule and local_schedule.get("is_active"):
        return local_schedule
    if global_schedule and global_schedule.get("is_active"):
        return global_schedule
    return None
