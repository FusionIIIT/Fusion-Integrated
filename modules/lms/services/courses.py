from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.academics import contracts as academics
from modules.lms.domain.rules import active_course_role, publication_state
from modules.lms.models import Announcement, Assignment, GradeAudit, Material, Submission, Workspace


def require(actor, permission):
    if actor is None or not actor.has_module("lms") or not actor.has_permission(permission):
        raise PermissionDeniedError()


def contexts(actor):
    require(actor, "lms.course.view")
    return [
        row
        for row in academics.get_course_contexts([actor.user_id]).get(actor.user_id, [])
        if active_course_role(row["role"], actor.active_role)
    ]


def workspace_context(actor, workspace_id, allowed=None, permission="lms.course.view"):
    require(actor, permission)
    workspace = Workspace.objects.filter(pk=workspace_id).first()
    if workspace is None:
        raise NotFoundError()
    context = next(
        (
            row
            for row in contexts(actor)
            if (row["course_id"], row["year"], row["semester_type"])
            == (workspace.course_id, workspace.year, workspace.semester_type)
        ),
        None,
    )
    if context is None:
        raise NotFoundError()
    if allowed and context["role"] not in allowed:
        raise PermissionDeniedError("Your course role cannot perform this action.")
    return workspace, context


@transaction.atomic
def open_courses(actor):
    output = []
    for context in contexts(actor):
        row, _ = Workspace.objects.get_or_create(
            course_id=context["course_id"],
            year=context["year"],
            semester_type=context["semester_type"],
        )
        output.append({**context, "id": row.pk})
    return output


@transaction.atomic
def save_content(actor, workspace_id, kind, data, item_id=None):
    definitions = {
        "details": (Workspace, "lms.course.manage", ("faculty",)),
        "material": (Material, "lms.material.manage", ("faculty",)),
        "assignment": (Assignment, "lms.assignment.manage", ("faculty",)),
        "announcement": (Announcement, "lms.announcement.create", ("faculty", "ta")),
    }
    if kind not in definitions:
        raise NotFoundError()
    model, permission, roles = definitions[kind]
    workspace, context = workspace_context(actor, workspace_id, roles, permission)
    if (
        kind == "announcement"
        and context["role"] == "ta"
        and context.get("may_announce") is not True
    ):
        raise PermissionDeniedError("Faculty authorization for TA announcements is required.")
    if kind == "details":
        obj = Workspace.objects.select_for_update().get(pk=workspace.pk)
    elif item_id:
        obj = model.objects.select_for_update().filter(pk=item_id, workspace=workspace).first()
        if obj is None:
            raise NotFoundError()
    else:
        obj = model(workspace=workspace)
    if kind == "assignment" and obj.pk and obj.state != "draft":
        raise ConflictError("Only draft assignments can be edited in the supplied baseline.")
    publish = data.pop("publish", False)
    permitted = {
        "details": ("syllabus", "schedule"),
        "material": ("title", "section", "kind", "text", "link", "file", "release_at"),
        "assignment": (
            "title",
            "instructions",
            "submission_type",
            "points_possible",
            "due_at",
            "release_at",
            "file",
        ),
        "announcement": ("title", "body"),
    }[kind]
    for key in permitted:
        if key in data:
            setattr(obj, key, data[key])
    if kind == "material":
        obj.state = publication_state(obj.release_at, timezone.now()) if publish else "draft"
    if kind == "announcement":
        obj.author_id = actor.user_id
    obj.full_clean()
    obj.save()
    return obj


@transaction.atomic
def publish_assignment(actor, workspace_id, item_id):
    workspace_context(actor, workspace_id, ("faculty",), "lms.assignment.manage")
    row = (
        Assignment.objects.select_for_update().filter(pk=item_id, workspace_id=workspace_id).first()
    )
    if row is None:
        raise NotFoundError()
    if row.state != "draft":
        raise ConflictError("The assignment is already published.")
    row.state = publication_state(row.release_at, timezone.now())
    row.full_clean()
    row.save()
    return row


@transaction.atomic
def submit(actor, workspace_id, item_id, data):
    workspace_context(actor, workspace_id, ("student",), "lms.submission.create")
    row = (
        Assignment.objects.select_for_update().filter(pk=item_id, workspace_id=workspace_id).first()
    )
    if row is None:
        raise NotFoundError()
    if row.state != "published" or (row.release_at and row.release_at > timezone.now()):
        raise ConflictError("The assignment is not available.")
    if timezone.now() >= row.due_at:
        raise DomainError(
            "Late-submission policy is unresolved (ISS-LMS-001).", code="late_policy_unresolved"
        )
    if Submission.objects.filter(assignment=row, student_id=actor.user_id).exists():
        raise ConflictError(
            "Resubmission policy is unresolved (ISS-LMS-005).",
            code="resubmission_policy_unresolved",
        )
    value = data.get(row.submission_type)
    if not value:
        raise DomainError("Provide the configured submission type: " + row.submission_type)
    return Submission.objects.create(
        assignment=row, student_id=actor.user_id, **{row.submission_type: value}
    )


@transaction.atomic
def grade(actor, workspace_id, item_id, data, release=False):
    workspace_context(
        actor,
        workspace_id,
        ("faculty",) if release else ("faculty", "ta"),
        "lms.grade.publish" if release else "lms.submission.review",
    )
    row = (
        Submission.objects.select_for_update()
        .filter(pk=item_id, assignment__workspace_id=workspace_id)
        .select_related("assignment")
        .first()
    )
    if row is None:
        raise NotFoundError()
    if row.revision != data["revision"]:
        raise ConflictError("This submission changed. Refresh before saving.")
    before = {"points": str(row.points), "feedback": row.feedback, "released": row.released}
    if release:
        if row.points is None:
            raise ConflictError("Grade the submission before releasing it.")
        row.released = True
    else:
        if row.released:
            raise DomainError("Post-release grade-change policy is unresolved (ISS-LMS-006).")
        if not 0 <= data["points"] <= row.assignment.points_possible:
            raise DomainError("Points must be within the assignment maximum.")
        row.points, row.feedback = data["points"], data["feedback"]
        row.grader_id, row.graded_at = actor.user_id, timezone.now()
    row.revision += 1
    row.save()
    GradeAudit.objects.create(
        submission=row,
        actor_id=actor.user_id,
        old_values=before,
        new_values={"points": str(row.points), "feedback": row.feedback, "released": row.released},
    )
    return row


def release_due():
    now = timezone.now()
    return sum(
        model.objects.filter(state="scheduled", release_at__lte=now).update(state="published")
        for model in (Material, Assignment)
    )
