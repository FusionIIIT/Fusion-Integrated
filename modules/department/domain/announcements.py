def is_complete(title: str, body: str, target_roles: list[str]) -> bool:
    """Checks if an announcement is complete based on title, body, and target roles."""
    if not title or not body:
        return False
    valid_roles = {"student", "faculty"}
    if not target_roles:
        return False
    return all(role in valid_roles for role in target_roles)

def is_relevant(
    target_roles: list[str],
    target_programme: str | None,
    target_batch_year: int | None,
    viewer_kind: str,
    viewer_programme: str | None,
    viewer_batch_year: int | None,
) -> bool:
    """Checks if an announcement is relevant to the viewer based on roles and attributes."""
    if viewer_kind not in target_roles:
        return False

    if viewer_kind == "faculty":
        return True

    # Student logic
    if viewer_kind == "student":
        if target_programme and target_programme != viewer_programme:
            return False
        if target_batch_year is not None and target_batch_year != viewer_batch_year:
            return False
        return True

    return False
