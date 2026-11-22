from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone

from core.files.writers import check_private_upload_root
from fusion_auth.client import IamUnavailable, get_client
from modules.lms.models import CoursePolicyVersion, CourseWorkspace


@transaction.atomic
def sync_workspaces():
    offerings = get_client().get_course_offerings()
    created = 0
    for offering in offerings:
        workspace, added = CourseWorkspace.objects.get_or_create(
            external_offering_key=offering["offering_key"],
            defaults={"syllabus": offering.get("syllabus", "") or ""},
        )
        created += added
        if not CoursePolicyVersion.objects.filter(workspace=workspace).exists():
            CoursePolicyVersion.objects.get_or_create(
                workspace=workspace,
                version=1,
                defaults={"effective_from": timezone.now()},
            )
    return created


def unmet_prerequisites():
    missing = [str(error.msg) for error in check_private_upload_root()]
    try:
        offerings = get_client().get_course_offerings()
        keys = set(CourseWorkspace.objects.values_list("external_offering_key", flat=True))
        if any(row["offering_key"] not in keys for row in offerings):
            missing.append("Run manage.py sync_lms_workspaces after the IAM catalogue sync.")
        if CourseWorkspace.objects.exclude(
            id__in=CoursePolicyVersion.objects.values("workspace_id")
        ).exists():
            missing.append(
                "Run manage.py sync_lms_workspaces to seed safe default course policies."
            )
    except IamUnavailable:
        missing.append(
            "Start the pinned IAM service and configure its service token and course routes."
        )
    except (OperationalError, ProgrammingError):
        missing.append("Run manage.py migrate before LMS setup.")
    return missing
