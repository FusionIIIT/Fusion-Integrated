from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from modules.lms.domain.rules import nonempty, require_role
from modules.lms.models import Announcement
from modules.lms.selectors import scoping
from modules.lms.services.common import enforce_rules


@enforce_rules
@transaction.atomic
def post_announcement(scope, workspace_id, content):
    require_role(scope.role, ("FACULTY", "TA"))
    # Serialize with policy changes, so a revoke cannot race a TA post.
    workspace = get_object_or_404(scoping.workspaces(scope).select_for_update(), pk=workspace_id)
    now = timezone.now()
    policy = scoping.effective_policy(workspace.id, now)
    if scope.role == "TA" and not (policy and policy.can_ta_post_announcements):
        require_role(scope.role, ("FACULTY",))
    nonempty(content, "Announcement")
    return Announcement.objects.create(
        workspace=workspace, content=content, author_user_id=scope.user_id
    )
