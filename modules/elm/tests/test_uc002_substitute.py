import pytest
from django.core.exceptions import ValidationError

from modules.elm.services import apply_leave, respond_to_substitute, review_leave

pytestmark = pytest.mark.django_db


def test_row_4_substitute_accept(elm_people):
    app = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        substitute=elm_people[2],
    )
    result = respond_to_substitute(application=app, substitute=elm_people[2], accepted=True)
    assert result.state == "Awaiting Unit Head Review"


def test_row_6_substitute_decline(elm_people):
    app = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        substitute=elm_people[2],
    )
    assert (
        respond_to_substitute(application=app, substitute=elm_people[2], accepted=False).state
        == "Applicant Action Required"
    )


def test_br015_unit_head_cannot_act_before_accept(elm_people):
    app = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        substitute=elm_people[2],
    )
    with pytest.raises(ValidationError):
        review_leave(application=app, unit_head=elm_people[1], decision="Approve")


def test_row_5_non_director_accepts_to_unit_head(elm_people):
    app = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        substitute=elm_people[2],
    )
    assert (
        respond_to_substitute(application=app, substitute=elm_people[2], accepted=True).state
        == "Awaiting Unit Head Review"
    )
