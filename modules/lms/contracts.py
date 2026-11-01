from collections.abc import Sequence

from modules.lms.models import Workspace


def get_workspace_summaries(course_ids: Sequence[int]) -> dict[int, list[dict]]:
    result = {}
    for row in Workspace.objects.filter(course_id__in=course_ids):
        result.setdefault(row.course_id, []).append(
            {"id": row.pk, "year": row.year, "semester_type": row.semester_type}
        )
    return result
