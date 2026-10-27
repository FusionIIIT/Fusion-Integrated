TITLE: Fix imports, transactions and apply_leave creation found in review of 003b
FORMAT: diff
EDIT: modules/leave/services/applications.py
READ: modules/leave/models.py modules/leave/domain/policy.py
LIMIT: 900
POST: none
---
Review of modules/leave/services/applications.py after task 003b. The structure is now right, but these defects remain. Fix only these, with SEARCH/REPLACE edits:

1. The file uses Decimal, date and Optional without importing them, so importing the module raises NameError. Add at the very top, before `from django.db import transaction`:
from datetime import date
from decimal import Decimal
from typing import Optional

2. `transaction` is imported but never used, and select_for_update() raises TransactionManagementError outside a transaction. Put the decorator @transaction.atomic on the line above each of: def apply_leave, def respond_to_substitute, def replace_substitute, def withdraw.

3. In apply_leave, `app, created = LeaveApplication.objects.create(...)` fails because create() returns one object, not a tuple; the days value is never saved; ReportingLine.objects.get() is called six times and raises DoesNotExist (HTTP 500) instead of LeaveError; and route_to_approver(app) is called even when a substitute was nominated, which overwrites the SUBSTITUTE stage. Replace everything in apply_leave from the line `    # 5. Handle substitute logic (BR-EL-014)` down to and including the line `    route_to_approver(app)` with code that does, in this order:
   a. if substitute_id is not None: raise LeaveError("Substitute cannot be the applicant.") when substitute_id == user_id; raise LeaveError("The substitute is on leave on these dates.") when has_overlap(substitute_id, start_date, end_date, half_day) is True. No try/except.
   b. line = ReportingLine.objects.filter(user_id=user_id).first(); if line is None: raise LeaveError("No reporting line configured.")
   c. app = LeaveApplication.objects.create(user_id=user_id, kind=RequestKind.LEAVE, category=category, start_date=start_date, end_date=end_date, half_day=half_day, days=days, purpose=purpose, station_leave=station_leave, station_address=station_address, substitute_id=substitute_id, unit_head_id=line.unit_head_id, establishment_id=line.establishment_id, sanctioning_authority_id=line.sanctioning_authority_id, status=Status.PENDING)
   d. if substitute_id is not None: set app.stage = Stage.SUBSTITUTE, app.assignee_id = substitute_id, app.substitute_status = SubstituteStatus.PENDING and call app.save(); else: set app.substitute_status = SubstituteStatus.NOT_REQUIRED and call route_to_approver(app).

Do not change anything else.
