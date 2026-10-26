"""A short set that holds up the rules most likely to go wrong."""
import datetime as dt
from decimal import Decimal

import pytest

from core.api.exceptions import PermissionDeniedError
from modules.elm.domain import calculation
from modules.elm.domain import leave_types as lt
from modules.elm.models import LeaveBalance
from modules.elm.services import applications, decisions
from modules.elm.services.common import RuleBroken
from modules.elm.tests.support import (
    EMPLOYEE,
    ESTABLISHMENT,
    ESTABLISHMENT_PERMS,
    OTHER_UNIT_HEAD,
    SANCTION_PERMS,
    SANCTIONER,
    UNIT_HEAD,
    UNIT_HEAD_PERMS,
    acting,
    request,
)

D = dt.date
FRI, NEXT_MON = D(2026, 3, 6), D(2026, 3, 9)
pytestmark = pytest.mark.django_db


def apply(*args, **kwargs):
    return applications.submit(acting(EMPLOYEE), request(*args, **kwargs))


def used(leave_type="CL"):
    return LeaveBalance.objects.get(user_id=EMPLOYEE, year=2026, leave_type=leave_type).used


def test_weekends_count_for_el_but_not_for_cl():
    """BR-EL-011."""
    assert calculation.leave_days(lt.CL, FRI, NEXT_MON, lt.NO_HALF) == Decimal(2)
    assert calculation.leave_days(lt.EL, FRI, NEXT_MON, lt.NO_HALF) == Decimal(4)


def test_overlapping_leave_is_refused():
    """BR-EL-012."""
    apply(start=D(2026, 3, 2), end=D(2026, 3, 4))
    with pytest.raises(RuleBroken) as caught:
        apply(start=D(2026, 3, 4), end=D(2026, 3, 5))
    assert caught.value.details == [{"rule": "BR-EL-012"}]


def test_unit_head_approval_deducts_and_stays_in_the_unit():
    """BR-EL-016: final for CL, and only for their own unit."""
    app = apply(end=D(2026, 3, 4))
    with pytest.raises(PermissionDeniedError):
        decisions.unit_head_decide(
            acting(OTHER_UNIT_HEAD, UNIT_HEAD_PERMS), app.pk, decision="approve")
    done = decisions.unit_head_decide(acting(UNIT_HEAD, UNIT_HEAD_PERMS), app.pk, decision="approve")
    assert done.status == "APPROVED"
    assert used() == Decimal(3)


def test_approval_that_would_overdraw_is_a_rule_error_not_a_crash():
    app = apply(end=D(2026, 3, 4))
    LeaveBalance.objects.filter(user_id=EMPLOYEE, leave_type="CL").update(used=7)
    with pytest.raises(RuleBroken):
        decisions.unit_head_decide(acting(UNIT_HEAD, UNIT_HEAD_PERMS), app.pk, decision="approve")
    assert used() == Decimal(7)


def test_scl_goes_through_recommendation_routing_and_the_authority():
    """BR-EL-004, 017, 018, 019."""
    app = apply("SCL", D(2026, 3, 2), D(2026, 3, 4))
    with pytest.raises(RuleBroken):
        decisions.unit_head_decide(acting(UNIT_HEAD, UNIT_HEAD_PERMS), app.pk, decision="approve")
    decisions.unit_head_decide(acting(UNIT_HEAD, UNIT_HEAD_PERMS), app.pk, decision="recommend")
    decisions.establishment_route(acting(ESTABLISHMENT, ESTABLISHMENT_PERMS), app.pk)
    sanctioner = acting(SANCTIONER, SANCTION_PERMS)
    with pytest.raises(RuleBroken):
        decisions.final_decide(sanctioner, app.pk, approve=True)
    done = decisions.final_decide(
        sanctioner, app.pk, approve=True, special_purpose_admissible=True)
    assert done.status == "APPROVED"
    assert used("SCL") == Decimal(3)
