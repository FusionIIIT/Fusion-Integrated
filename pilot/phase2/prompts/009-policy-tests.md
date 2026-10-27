Phase 1 shipped no tests for the leave module. Write pytest unit tests for modules/leave/domain/policy.py (read-only). They are plain test functions: no Django, no database, no classes, no fixtures.

modules/leave/tests/__init__.py is an empty file.

modules/leave/tests/test_policy.py starts with exactly:

from datetime import date
from decimal import Decimal

import pytest

from modules.leave.domain import policy

FRI = date(2026, 11, 6)   # a Friday
MON = date(2026, 11, 9)   # the following Monday

Write one small test per rule, named after the business rule it checks:
- entitlement: CL for "staff" is Decimal("8"); EL for "faculty" is None (BR-EL-005); VL for "staff" is None (BR-EL-006); VL for "faculty" is Decimal("60"); any kind other than "faculty", for example "employee", is treated as staff (EL gives Decimal("30")).
- count_days: CL from FRI to MON is Decimal("2") because weekends are not counted; EL from FRI to MON is Decimal("4") because EL counts calendar days (BR-EL-011); CL on MON alone with half_day "first" is Decimal("0.5") (BR-EL-010); half_day "first" on EL raises policy.PolicyError; half_day "first" on a two-day CL raises policy.PolicyError; end before start raises policy.PolicyError.
- overlaps (BR-EL-012): FRI..FRI and MON..MON with no half days do not overlap; FRI..MON and MON..MON overlap; MON first half and MON second half do not overlap; MON first half and MON first half overlap.
- unit_head_is_final (BR-EL-016/017): True for "CL" and "RH", False for "EL".

Use pytest.raises(policy.PolicyError) for the error cases. Write both files in full. Do not ask for more files.
