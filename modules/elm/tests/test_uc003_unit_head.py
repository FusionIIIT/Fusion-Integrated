from decimal import Decimal

import pytest

from modules.elm.models import LeaveUsage
from modules.elm.services import apply_leave, review_leave

pytestmark = pytest.mark.django_db


def test_row_8_cl_approve_deducts_half_day(elm_people):
    app = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        first_half=True,
    )
    review_leave(application=app, unit_head=elm_people[1], decision="Approve")
    assert LeaveUsage.objects.get(
        employee=elm_people[0], category="CL", year=2026
    ).used_days == Decimal("0.5")


def test_row_9_cl_rejected(elm_people):
    app = apply_leave(
        applicant=elm_people[0], category="CL", start_date="2026-01-01", end_date="2026-01-01"
    )
    assert (
        review_leave(application=app, unit_head=elm_people[1], decision="Reject").state
        == "Rejected"
    )


def test_row_11_higher_request_reaches_final_when_unconfigured(elm_people):
    app = apply_leave(
        applicant=elm_people[0], category="EL", start_date="2026-01-01", end_date="2026-01-01"
    )
    from modules.elm.models import SanctioningAuthorityRule

    SanctioningAuthorityRule.objects.create(category="EL", authority=elm_people[3])
    assert (
        review_leave(application=app, unit_head=elm_people[1], decision="Not Recommended").state
        == "Awaiting Final Sanction Decision"
    )


def test_row_10_configured_establishment_state(elm_people):
    from modules.elm.models import HierarchyConfiguration, SanctioningAuthorityRule

    HierarchyConfiguration.objects.create(
        establishment_configured=True, establishment_role="establishment"
    )
    SanctioningAuthorityRule.objects.create(category="EL", authority=elm_people[3])
    app = apply_leave(
        applicant=elm_people[0], category="EL", start_date="2026-01-01", end_date="2026-01-01"
    )
    assert (
        review_leave(application=app, unit_head=elm_people[1], decision="Recommended").state
        == "Awaiting Establishment Routing"
    )


def test_br017_not_recommended_is_not_rejected(elm_people):
    from modules.elm.models import SanctioningAuthorityRule

    SanctioningAuthorityRule.objects.create(category="EL", authority=elm_people[3])
    app = apply_leave(
        applicant=elm_people[0], category="EL", start_date="2026-01-01", end_date="2026-01-01"
    )
    result = review_leave(application=app, unit_head=elm_people[1], decision="Not Recommended")
    assert result.state != "Rejected"
