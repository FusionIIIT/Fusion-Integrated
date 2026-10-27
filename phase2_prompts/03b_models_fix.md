# Task: fix 5 defects in modules/leave/models.py (output the COMPLETE file; change nothing else)

`manage.py check` fails with:
  File "modules/leave/models.py", line 172, in Meta
    CheckConstraint(F('balance_days') >= 0, name="leave_balance_not_negative"),
TypeError: '>=' not supported between instances of 'F' and 'int'

Fix exactly these:
1. LeaveBalance: replace that constraint with
   `models.CheckConstraint(condition=models.Q(balance_days__gte=0), name="leave_balance_not_negative")`.
2. LeaveApplication constraints: use the keyword `condition=` (NOT `check=`, which is deprecated in Django 5.2) in both CheckConstraints.
3. The half-day constraint is wrong: `half_day` is a CharField whose "no half day" value is the empty string, not NULL. It must read
   `condition=models.Q(half_day="") | models.Q(start_date=models.F("end_date"))`.
4. LeaveCategory.Meta: remove the redundant `unique_together = (('code',),)` (keep db_table only).
5. LeaveApplicationTransition docstring mentions "PC-BR-008" which belongs to another module. Change it to: "Append-only audit of every status change (CFR-EL-016.4)."
Also remove trailing whitespace on blank lines and keep every line at most 100 characters (wrap the long `__str__` and the RECOMMENDATION_CHOICES /
SUBSTITUTE_RESPONSE_CHOICES lists). Import order: `from django.db import models`, blank line, `from core.db.mixins import ...`
(no separate `from django.db.models import CheckConstraint, F` import: use `models.CheckConstraint` and `models.F`).
No explanations, no placeholders, no TODOs.
