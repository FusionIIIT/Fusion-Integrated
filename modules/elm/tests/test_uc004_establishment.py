import pytest
from django.core.exceptions import ValidationError

from modules.elm.models import HierarchyConfiguration, SanctioningAuthorityRule
from modules.elm.services import apply_leave, review_leave, route_establishment

pytestmark = pytest.mark.django_db


def test_row_12_only_establishment_role_routes(elm_people):
    HierarchyConfiguration.objects.create(
        establishment_configured=True, establishment_role="establishment"
    )
    SanctioningAuthorityRule.objects.create(category="EL", authority=elm_people[3])
    app = apply_leave(
        applicant=elm_people[0], category="EL", start_date="2026-01-01", end_date="2026-01-01"
    )
    review_leave(application=app, unit_head=elm_people[1], decision="Recommended")
    assert (
        route_establishment(application=app, role="establishment").state
        == "Awaiting Final Sanction Decision"
    )


def test_wrong_establishment_role_refused(elm_people):
    HierarchyConfiguration.objects.create(
        establishment_configured=True, establishment_role="establishment"
    )
    with pytest.raises(ValidationError):
        route_establishment(
            application=apply_leave(
                applicant=elm_people[0],
                category="EL",
                start_date="2026-01-01",
                end_date="2026-01-01",
            ),
            role="employee",
        )


def test_cl_cannot_enter_establishment_route(elm_people):
    HierarchyConfiguration.objects.create(
        establishment_configured=True, establishment_role="establishment"
    )
    app = apply_leave(
        applicant=elm_people[0], category="CL", start_date="2026-01-01", end_date="2026-01-01"
    )
    with pytest.raises(ValidationError):
        route_establishment(application=app, role="establishment")
