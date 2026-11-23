from django.db.models import OuterRef, Prefetch, Subquery
from django.utils import timezone

from fusion_auth.client import get_client
from modules.lms.models import CoursePolicyVersion, MaterialSection
from modules.lms.selectors import scoping


def course_data(rows, scope):
    rows = list(rows)
    if not rows:
        return []
    offerings = get_client().get_course_offerings([row.external_offering_key for row in rows])
    by_key = {row["offering_key"]: row for row in offerings}
    users = get_client().get_users(
        {
            uid
            for item in offerings
            for uid in (*item.get("instructor_user_ids", []), *item.get("ta_user_ids", []))
        }
    )
    return [
        {
            "id": row.id,
            "external_offering_key": row.external_offering_key,
            "course_code": by_key.get(row.external_offering_key, {}).get("course_code", ""),
            "course_name": by_key.get(row.external_offering_key, {}).get("course_name", ""),
            "working_year": by_key.get(row.external_offering_key, {}).get("working_year"),
            "session": by_key.get(row.external_offering_key, {}).get("session"),
            "syllabus": row.syllabus if scope.role == "FACULTY" or row.details_published_at else "",
            "schedule": row.schedule if scope.role == "FACULTY" or row.details_published_at else "",
            "details_published_at": row.details_published_at,
            "acting_course_role": scope.role,
            "can_post_announcements": scope.role == "FACULTY"
            or (scope.role == "TA" and row.ta_posts),
            "sections": row.materialsection_set.all(),
            "staff": [
                {
                    "user_id": uid,
                    "display_name": users[uid].display_name,
                    "email": users[uid].email,
                    "course_role": role,
                }
                for role, field in (("FACULTY", "instructor_user_ids"), ("TA", "ta_user_ids"))
                for uid in by_key.get(row.external_offering_key, {}).get(field, [])
                if uid in users
            ],
        }
        for row in rows
    ]


def course_rows(scope):
    policy = CoursePolicyVersion.objects.filter(
        workspace_id=OuterRef("pk"),
        effective_from__lte=timezone.now(),
    ).order_by("-effective_from", "-version")
    return (
        scoping.workspaces(scope)
        .annotate(
            ta_posts=Subquery(
                policy.values("can_ta_post_announcements")[:1],
            )
        )
        .prefetch_related(
            Prefetch(
                "materialsection_set", queryset=MaterialSection.objects.order_by("order", "id")
            )
        )
    )
