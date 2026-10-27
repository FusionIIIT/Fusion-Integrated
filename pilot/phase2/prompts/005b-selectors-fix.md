Review of task 005. Fix only these, with SEARCH/REPLACE edits:

1. selectors.visible_application uses LeaveApplication.objects.get(id=application_id), which raises DoesNotExist (HTTP 500) for an unknown id. Use:
    app = LeaveApplication.objects.prefetch_related("actions").filter(id=application_id).first()
    if app is None:
        raise NotFoundError()

2. my_applications and inbox return applications whose serializer also lists their actions, which makes one extra query per row. Add .prefetch_related("actions") to both querysets, and order inbox by "created_at" (oldest first, so the longest-waiting request is on top).

3. In services/admin.py, LeaveBalance is imported but never used (ruff F401). Change the import line to `from modules.leave.models import ReportingLine`.

Do not change anything else.
