TITLE: Add the missing transaction.atomic decorators and fix the apply-time substitute check
FORMAT: diff
EDIT: modules/leave/services/applications.py
READ: modules/leave/models.py
LIMIT: 600
POST: none
---
Two items from the 003c task were not applied. Fix only these, with SEARCH/REPLACE edits:

1. There is still no @transaction.atomic anywhere in the file, and select_for_update() raises TransactionManagementError outside a transaction. Add the line @transaction.atomic directly above each of these four lines:
def apply_leave(user_id: int, kind: str, data: dict) -> LeaveApplication:
def respond_to_substitute(actor_id: int, application_id: int, accept: bool) -> LeaveApplication:
def replace_substitute(actor_id: int, application_id: int, substitute_id: int) -> LeaveApplication:
def withdraw(actor_id: int, application_id: int) -> LeaveApplication:

2. In apply_leave, the substitute overlap check is still a loop over sub_apps wrapped in `try: ... except Exception: continue`, which swallows the LeaveError it raises, so a substitute who is on leave is accepted. Replace the `sub_apps = LeaveApplication.objects.filter(...)` query and the whole `for sub_app in sub_apps:` loop inside apply_leave with:
        if has_overlap(substitute_id, start_date, end_date, half_day):
            raise LeaveError("The substitute is on leave on these dates.")

Do not change anything else.
