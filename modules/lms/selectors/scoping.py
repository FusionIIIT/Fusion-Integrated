"""Every lookup begins with live IAM association scoping for the acting role."""

from dataclasses import dataclass

from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.api.exceptions import PermissionDeniedError
from fusion_auth.client import get_client
from modules.lms.models import (
    Announcement,
    Assignment,
    CoursePolicyVersion,
    CourseWorkspace,
    Grade,
    Material,
    MaterialSection,
    Submission,
)

ROLE_MAP = {"student": "STUDENT", "faculty": "FACULTY", "lms_ta": "TA", "lms_observer": "OBSERVER"}


@dataclass(frozen=True)
class AccessScope:
    user_id: int
    role: str
    offering_keys: tuple[str, ...]


def resolve_scope(principal):
    role = ROLE_MAP.get(principal.active_role)
    if role is None:
        raise PermissionDeniedError("Select a supported LMS acting role.")
    rows = get_client().get_course_associations([principal.user_id], course_role=role)
    return AccessScope(
        principal.user_id,
        role,
        tuple(
            {
                row["offering_key"]
                for row in rows
                if row["user_id"] == principal.user_id and row["course_role"] == role
            }
        ),
    )


def workspaces(scope):
    return CourseWorkspace.objects.filter(external_offering_key__in=scope.offering_keys)


def workspace(scope, pk):
    return get_object_or_404(workspaces(scope), pk=pk)


def sections(scope):
    return MaterialSection.objects.filter(workspace__in=workspaces(scope))


def materials(scope):
    rows = Material.objects.filter(workspace__in=workspaces(scope))
    if scope.role != "FACULTY":
        rows = rows.filter(state="PUBLISHED", published_at__lte=timezone.now())
    return rows.select_related("stored_file", "section")


def assignments(scope):
    if scope.role == "OBSERVER":
        raise PermissionDeniedError()
    rows = Assignment.objects.filter(workspace__in=workspaces(scope))
    if scope.role != "FACULTY":
        rows = rows.filter(state="AVAILABLE", published_at__lte=timezone.now())
    return rows


def announcements(scope):
    return Announcement.objects.filter(workspace__in=workspaces(scope))


def submissions(scope):
    if scope.role == "OBSERVER":
        raise PermissionDeniedError()
    rows = Submission.objects.filter(assignment__in=assignments(scope))
    if scope.role == "STUDENT":
        rows = rows.filter(user_id=scope.user_id)
    return rows.select_related("stored_file", "assignment", "grade")


def grades(scope):
    rows = Grade.objects.filter(submission__in=submissions(scope))
    if scope.role == "STUDENT":
        rows = rows.filter(state="RELEASED")
    return rows.select_related("submission__assignment")


def effective_policy(workspace_id, now=None):
    return (
        CoursePolicyVersion.objects.filter(
            workspace_id=workspace_id,
            effective_from__lte=now or timezone.now(),
        )
        .order_by("-effective_from", "-version")
        .first()
    )
