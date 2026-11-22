from collections.abc import Mapping

TRANSITIONS: Mapping[tuple[str, str, str], str] = {
    ("archive", "submitted", "approve"): "approved",
    ("archive", "submitted", "reject"): "rejected",
    ("archive", "submitted", "special_archive"): "classified",
    ("archive", "approved", "classify_non_sensitive"): "classified",
    ("archive", "approved", "classify_sensitive"): "security_review",
    ("archive", "security_review", "encryption_configured"): "ready_to_archive",
    ("archive", "classified", "archive_succeeded"): "archived",
    ("archive", "ready_to_archive", "archive_succeeded"): "archived",
    ("archive", "classified", "archive_failed"): "failed",
    ("archive", "ready_to_archive", "archive_failed"): "failed",
    ("restore", "submitted_sensitive", "approve"): "approved",
    ("restore", "submitted_sensitive", "reject"): "rejected",
    ("restore", "submitted_standard", "execute"): "restoring",
    ("restore", "approved", "execute"): "restoring",
    ("restore", "restoring", "succeeded"): "restored",
    ("restore", "restoring", "failed"): "failed",
    ("storage_extension", "submitted", "approve"): "approved",
    ("storage_extension", "submitted", "reject"): "rejected",
    ("backup", "queued", "start"): "running",
    ("backup", "running", "succeed"): "succeeded",
    ("backup", "running", "fail"): "failed",
}

ACTORS: Mapping[tuple[str, str], frozenset[str]] = {
    ("archive", "approve"): frozenset({"hod"}),
    ("archive", "reject"): frozenset({"hod"}),
    ("archive", "special_archive"): frozenset({"super_admin"}),
    ("archive", "classify_non_sensitive"): frozenset({"sysadmin"}),
    ("archive", "classify_sensitive"): frozenset({"sysadmin"}),
    ("archive", "encryption_configured"): frozenset({"it_security"}),
    ("archive", "archive_succeeded"): frozenset({"system"}),
    ("archive", "archive_failed"): frozenset({"system"}),
    ("restore", "approve"): frozenset({"sysadmin"}),
    ("restore", "reject"): frozenset({"sysadmin"}),
    ("restore", "execute"): frozenset({"requester", "sysadmin", "system"}),
    ("restore", "succeeded"): frozenset({"system"}),
    ("restore", "failed"): frozenset({"system"}),
    ("storage_extension", "approve"): frozenset({"hod"}),
    ("storage_extension", "reject"): frozenset({"hod"}),
    ("backup", "start"): frozenset({"system"}),
    ("backup", "succeed"): frozenset({"system"}),
    ("backup", "fail"): frozenset({"system"}),
}


class InvalidTransition(ValueError):
    pass


def transition(aggregate: str, state: str, event: str, actor: str) -> str:
    allowed_actors = ACTORS.get((aggregate, event), frozenset())
    target = TRANSITIONS.get((aggregate, state, event))
    if target is None or actor not in allowed_actors:
        raise InvalidTransition(
            f"{actor!r} cannot apply {event!r} to {aggregate} in {state}.")
    return target
