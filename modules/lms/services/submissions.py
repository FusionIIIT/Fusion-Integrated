from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.api.exceptions import ConflictError
from core.files.writers import discard_upload, write_upload
from modules.lms.domain import rules
from modules.lms.models import StoredFile, Submission
from modules.lms.selectors import scoping
from modules.lms.services.common import enforce_rules


@enforce_rules
def create_submission(scope, assignment_id, data):
    rules.require_role(scope.role, ("STUDENT",))
    stored = None
    try:
        with transaction.atomic():
            assignment = get_object_or_404(
                scoping.assignments(scope).select_for_update(),
                pk=assignment_id,
            )
            now = timezone.now()
            if Submission.objects.filter(assignment=assignment, user_id=scope.user_id).exists():
                _duplicate()
            rules.submission(assignment.submission_type, data["kind"], now, assignment.due_at)
            upload = data.get("file")
            rules.payload(data["kind"], data.get("text", ""), data.get("url", ""), bool(upload))
            file_row = None
            if upload:
                stored = write_upload(upload, profile="submission", namespace="lms")
                file_row = StoredFile.objects.create(
                    workspace_id=assignment.workspace_id,
                    owner_user_id=scope.user_id,
                    **stored,
                )
            return Submission.objects.create(
                assignment=assignment,
                user_id=scope.user_id,
                kind=data["kind"],
                text=data.get("text", ""),
                url=data.get("url", ""),
                stored_file=file_row,
                submitted_at=now,
            )
    except Exception as exc:
        if stored:
            discard_upload(stored["storage_key"])
        if isinstance(exc, IntegrityError) and (
            getattr(getattr(exc, "__cause__", None), "diag", None) is not None
            and exc.__cause__.diag.constraint_name == "lms_submission_assignment_user_uniq"
        ):
            raise ConflictError(
                "A successful submission already exists.", code="SUBMISSION_ALREADY_EXISTS"
            ) from exc
        raise


def _duplicate():
    raise ConflictError("A successful submission already exists.", code="SUBMISSION_ALREADY_EXISTS")
