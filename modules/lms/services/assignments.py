from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404

from modules.lms.domain import rules
from modules.lms.models import Assignment, Grade, Submission
from modules.lms.selectors import scoping
from modules.lms.services.common import enforce_rules, faculty


@enforce_rules
@transaction.atomic
def save_assignment(scope, data, *, workspace_id=None, pk=None):
    faculty(scope)
    if pk is None:
        row = Assignment(
            workspace=scoping.workspace(scope, workspace_id), author_user_id=scope.user_id
        )
    else:
        row = get_object_or_404(scoping.assignments(scope).select_for_update(), pk=pk)
        old = {
            name: getattr(row, name) for name in ("submission_type", "due_at", "points_possible")
        }
        new = {**old, **data}
        submissions = Submission.objects.filter(assignment=row)
        rules.edit_assignment(
            old,
            new,
            has_submissions=submissions.exists(),
            has_grades=Grade.objects.filter(submission__assignment=row).exists(),
            last_submission_at=submissions.aggregate(Max("submitted_at"))["submitted_at__max"],
        )
    for field, value in data.items():
        setattr(row, field, value)
    rules.assignment(row.instructions, row.due_at, row.submission_type, row.points_possible)
    row.save()
    return row
