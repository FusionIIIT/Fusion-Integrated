"""Approval-path resolution (BR-EL-019, BR-EL-020, BR-EL-030).

Pure lookups over published HierarchyRule rows. Callers pass the applicant's unit and
kind (from modules.directory.contracts); nothing here talks to IAM.
"""
from modules.elm.models import HierarchyRule, PublishState

Stage = HierarchyRule.Stage


class RoutingError(Exception):
    pass


def _score(rule: HierarchyRule, unit: str, kind: str, leave_type: str) -> int | None:
    """None if the rule does not apply; otherwise how specific it is.
    Unit outranks leave type, which outranks employee kind."""
    score = 0
    for wanted, actual, weight in (
        (rule.unit, unit, 4),
        (rule.leave_type, leave_type, 2),
        (rule.applicant_kind, kind, 1),
    ):
        if wanted:
            if wanted != actual:
                return None
            score += weight
    return score


def approver_for(stage: str, *, applicant_id: int, unit: str = "", kind: str = "",
                 leave_type: str = "") -> int:
    """Most specific published rule for this stage. A rule naming the applicant
    as the approver is skipped, so nobody sanctions their own leave
    (the Director case is handled separately by is_director)."""
    best = None
    rules = (HierarchyRule.objects
             .filter(status=PublishState.PUBLISHED, stage=stage)
             .exclude(approver_id=applicant_id)
             .order_by("id"))
    for rule in rules:
        score = _score(rule, unit, kind, leave_type)
        if score is not None and (best is None or score > best[0]):
            best = (score, rule.approver_id)
    if best is None:
        raise RoutingError(f"No published '{stage}' rule applies to this request.")
    return best[1]


def establishment_configured(*, applicant_id: int, unit: str = "", kind: str = "",
                             leave_type: str = "") -> bool:
    """WF-EL-01 steps 10/11: is an Establishment step in this path?"""
    try:
        approver_for(Stage.ESTABLISHMENT, applicant_id=applicant_id, unit=unit,
                     kind=kind, leave_type=leave_type)
    except RoutingError:
        return False
    return True


def is_director(user_id: int) -> bool:
    """BR-EL-020: the Director is whoever a published DIRECTOR rule names."""
    return HierarchyRule.objects.filter(
        status=PublishState.PUBLISHED, stage=Stage.DIRECTOR, approver_id=user_id
    ).exists()
