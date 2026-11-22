from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404
from django.utils import timezone

from modules.lms.domain.rules import nonempty
from modules.lms.models import CoursePolicyVersion, MaterialSection
from modules.lms.selectors import scoping
from modules.lms.services.common import enforce_rules, faculty


@enforce_rules
@transaction.atomic
def update_details(scope, pk, data):
    faculty(scope)
    row = get_object_or_404(scoping.workspaces(scope).select_for_update(), pk=pk)
    for field, value in data.items():
        setattr(row, field, value)
    row.details_published_at = timezone.now()
    row.created_by_user_id = scope.user_id
    row.save()
    return row


@enforce_rules
@transaction.atomic
def set_policy(scope, pk, data):
    faculty(scope)
    row = get_object_or_404(scoping.workspaces(scope).select_for_update(), pk=pk)
    version = (
        CoursePolicyVersion.objects.filter(workspace=row).aggregate(Max("version"))["version__max"]
        or 0
    ) + 1
    return CoursePolicyVersion.objects.create(
        workspace=row,
        version=version,
        effective_from=timezone.now(),
        author_user_id=scope.user_id,
        can_ta_post_announcements=data["can_ta_post_announcements"],
    )


@enforce_rules
@transaction.atomic
def save_section(scope, data, *, workspace_id=None, pk=None):
    faculty(scope)
    if pk is None:
        row = MaterialSection(workspace=scoping.workspace(scope, workspace_id))
    else:
        row = get_object_or_404(scoping.sections(scope).select_for_update(), pk=pk)
    for field, value in data.items():
        setattr(row, field, value)
    nonempty(row.label, "Section label")
    row.save()
    return row
