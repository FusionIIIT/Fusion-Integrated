"""Pure Python rules for clubs (BW-GYM-03) and membership (BW-GYM-01). No Django."""
OPEN = "open"
CONFIRMED = "confirmed"
CATEGORIES = ("Technical", "Sports", "Cultural")


class RuleViolation(Exception):
    pass


def check_category(category):
    if category not in CATEGORIES:
        raise RuleViolation("BR-GYM-003: category must be Technical, Sports or Cultural.")


def check_leaders(coordinator_id, co_coordinator_id, councillor_id, kinds):
    """`kinds` maps user id -> directory kind ("student", "faculty", ...)."""
    if coordinator_id == co_coordinator_id:
        raise RuleViolation("BR-GYM-001: coordinator and co-coordinator must differ.")
    if kinds.get(coordinator_id) != "student" or kinds.get(co_coordinator_id) != "student":
        raise RuleViolation("BR-GYM-001: club leaders must be students.")
    if kinds.get(councillor_id) != "faculty":
        raise RuleViolation("BR-GYM-002: the councillor must be a faculty member.")


def check_open(status):
    if status != OPEN:
        raise RuleViolation("BR-GYM-004: only an open request can be confirmed.")


def check_can_apply(club_status, already_applied):
    if club_status != CONFIRMED:
        raise RuleViolation("BR-GYM-007: you can only apply to a confirmed club.")
    if already_applied:
        raise RuleViolation("BR-GYM-009: you have already applied to this club.")


def check_club_head(user_id, coordinator_id, co_coordinator_id):
    if user_id not in (coordinator_id, co_coordinator_id):
        raise RuleViolation("BR-GYM-010: only this club's coordinator or co-coordinator can.")
