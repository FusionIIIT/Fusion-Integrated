ROLE_NAMES = {
    "student": {"student", "ug_student", "pg_student"},
    "faculty": {"faculty", "course faculty"},
    "ta": {"ta", "teaching assistant"},
    "observer": {"observer"},
}


def active_course_role(role, active_role):
    return (active_role or "").casefold() in ROLE_NAMES.get(role, set())


def publication_state(release_at, now):
    return "scheduled" if release_at and release_at > now else "published"
