from django.db.models import Q

from fusion_auth.client import get_client
from modules.department.models import Announcement


def _matches_target(field, value):
    unrestricted = Q(**{field: []})
    if value is None or value == "":
        return unrestricted
    return unrestricted | Q(**{f"{field}__contains": [value]})


def visible_announcements(principal):
    """Apply BR-DEPT-002 using live IAM membership and the current acting role."""
    viewer = get_client().get_users([principal.user_id]).get(principal.user_id)
    if viewer is None or not viewer.is_active or not viewer.department.strip():
        return Announcement.objects.none()
    return Announcement.objects.filter(
        _matches_target("target_roles", principal.active_role or principal.kind),
        _matches_target("target_programmes", viewer.programme),
        _matches_target("target_batch_years", viewer.batch_year),
        department=viewer.department,
        is_active=True,
    )
