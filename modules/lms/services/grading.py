from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from modules.lms.domain import rules
from modules.lms.domain.state_machine import GRADE_TRANSITIONS, transition
from modules.lms.models import Grade, GradeAuditLog
from modules.lms.selectors import scoping
from modules.lms.services.common import enforce_rules


@enforce_rules
@transaction.atomic
def save_grade(scope, submission_id, data=None, *, release=False):
    rules.require_role(scope.role, ("FACULTY",) if release else ("FACULTY", "TA"))
    target = get_object_or_404(scoping.submissions(scope), pk=submission_id)
    # All assignment edit/submit/grade operations take the assignment lock first.
    get_object_or_404(scoping.assignments(scope).select_for_update(), pk=target.assignment_id)
    target = get_object_or_404(
        scoping.submissions(scope).select_for_update(of=("self",)), pk=target.pk
    )
    grade = Grade.objects.filter(submission=target).select_for_update().first()
    old = {
        "points": grade.points if grade else None,
        "feedback": grade.feedback if grade else "",
        "state": grade.state if grade else "ABSENT",
    }
    if old["state"] == "RELEASED":
        rules.require_role(scope.role, ("FACULTY",))
    new_state = transition(
        GRADE_TRANSITIONS, old["state"], "release" if release else "save", scope.role
    )
    now = timezone.now()
    if grade is None:
        grade = Grade(submission=target)
    if not release:
        rules.points(data["points"])
        grade.points, grade.feedback = data["points"], data.get("feedback", "")
        grade.grader_user_id, grade.graded_at = scope.user_id, now
    else:
        grade.released_by_user_id, grade.released_at = scope.user_id, now
    grade.state = new_state
    grade.save()
    GradeAuditLog.objects.create(
        submission=target,
        actor_user_id=scope.user_id,
        operation="RELEASE" if release else "SAVE",
        old_points=old["points"],
        new_points=grade.points,
        old_feedback=old["feedback"],
        new_feedback=grade.feedback,
        old_state=old["state"],
        new_state=grade.state,
        changed_at=now,
    )
    return grade


@enforce_rules
def release_grade(scope, submission_id):
    rules.require_role(scope.role, ("FACULTY",))
    return save_grade(scope, submission_id, release=True)
