TITLE: Rewrite models to the reviewed data model
FORMAT: whole
EDIT: modules/leave/models.py
READ: kit:phase2/DESIGN.md core/db/mixins.py
LIMIT: 1200
POST: none
---
Review findings on the Phase-1 modules/leave/models.py: the category field has max_length=2 but "SCL" and "COL" need 3; there is no workflow stage, no current assignee, no unit head / sanctioning authority on the request, no half-day field, no substitute consent state, and no reporting line, so requests cannot be routed to a specific approver.

Rewrite modules/leave/models.py so it matches the "models.py" section of DESIGN.md (read-only) exactly: the six TextChoices classes, ReportingLine, LeaveApplication, LeaveBalance (with the UniqueConstraint and the available property) and LeaveAction. Import TimeStampedModel and UserScopedModel from core.db.mixins (shown read-only); UserScopedModel already provides user_id. Use only django.db.models and decimal.Decimal. Give every model a short docstring and a __str__.

Write the whole file. Do not ask for more files.
