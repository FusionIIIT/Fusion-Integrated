TITLE: Add selectors and admin services (reporting lines, balances)
FORMAT: whole
EDIT: modules/leave/selectors.py modules/leave/services/admin.py
READ: kit:phase2/DESIGN.md modules/leave/models.py modules/leave/domain/policy.py modules/leave/services/applications.py
LIMIT: 1200
POST: none
---
Review findings: Phase-1 had no read layer, so list endpoints returned every user's applications, and there was no way to configure who a person's Unit Head or Sanctioning Authority is (EL-UC-014), so nothing could be routed.

Create two files.

modules/leave/selectors.py (reads only, no writes):
- def my_applications(user_id: int) -> QuerySet  (that user's applications, newest first, prefetch "actions")
- def inbox(user_id: int) -> QuerySet  (PENDING applications whose assignee_id == user_id)
- def visible_application(user_id: int, application_id: int) -> LeaveApplication  (only if the user is the owner, the assignee or the substitute; otherwise raise NotFoundError from core.api.exceptions; selectors must not import services, which sit above them)
- def get_reporting_line(user_id: int) -> ReportingLine | None

modules/leave/services/admin.py (writes, transaction.atomic):
- def set_reporting_line(user_id: int, unit_head_id: int, establishment_id: int | None, sanctioning_authority_id: int | None) -> ReportingLine  (update_or_create by user_id; raise LeaveError if unit_head_id is missing)
- def ensure_balances(user_id: int, kind: str, year: int) -> list  (for every category in policy.CATEGORIES that policy.entitlement allows for this kind, call get_balance from modules.leave.services.applications; return the balances ordered by category)

Write both files in full. Do not ask for more files.

Use exactly these imports. They are the only names you need, and every one of them exists; do not import anything else (task 003 failed because it imported functions that do not exist):

selectors.py:
from django.db.models import Q, QuerySet

from core.api.exceptions import NotFoundError
from modules.leave.models import LeaveApplication, ReportingLine, Status

services/admin.py:
from django.db import transaction

from modules.leave.domain import policy
from modules.leave.models import LeaveBalance, ReportingLine
from modules.leave.services.applications import LeaveError, get_balance
