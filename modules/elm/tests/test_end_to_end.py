from decimal import Decimal
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from modules.elm.models import (
    AssignmentNotification,
    HierarchyConfiguration,
    HolidayCalendar,
    HolidayDate,
    LeaveApplication,
    LeavePolicy,
    LeaveUsage,
    SanctioningAuthorityRule,
)
from modules.elm.services import apply_leave, make_director_decision, review_leave

pytestmark = pytest.mark.django_db
BASE = "/api/v1/elm/applications/"


def submit(client, **overrides):
    data = {"category": "CL", "start_date": "2026-01-02", "end_date": "2026-01-02"}
    data.update(overrides)
    return client.post(BASE, data, format="json")


def act(client, application, path, **body):
    identifier = application["id"] if isinstance(application, dict) else application.pk
    return client.post(f"{BASE}{identifier}/{path}/", body, format="json")


def test_uc001_through_uc003_with_logged_in_users(elm_client, elm_people):
    applicant, head, substitute = elm_people[:3]
    response = submit(
        elm_client(applicant),
        applicant=head.pk,
        num_days=99,
        substitute=substitute.pk,
        first_half=True,
    )
    assert response.status_code == 201
    app = response.json()
    assert app["applicant"] == applicant.pk
    assert Decimal(app["num_days"]) == Decimal("0.5")
    assert app["state"] == "Awaiting Substitute Response"
    assert app["allowed_actions"] == []
    assert act(elm_client(head), app, "unit-head-review", decision="Approve").status_code == 403
    assert act(elm_client(substitute), app, "substitute-response", accept=True).status_code == 200
    response = act(elm_client(head), app, "unit-head-review", decision="Approve")
    assert response.status_code == 200
    assert response.json()["state"] == "Approved"
    assert LeaveUsage.objects.get(
        employee=applicant, category="CL", year=2026
    ).used_days == Decimal("0.5")
    assert list(
        AssignmentNotification.objects.filter(application_id=app["id"]).values_list(
            "recipient_id", flat=True
        )
    ) == [substitute.pk, head.pk]


@pytest.mark.parametrize("establishment", [False, True])
@pytest.mark.parametrize("recommendation", ["Recommended", "Not Recommended"])
@pytest.mark.parametrize("decision,expected", [("Approve", "Approved"), ("Reject", "Rejected")])
def test_uc003_uc004_uc005_higher_sanction_path(
    elm_client,
    elm_people,
    establishment,
    recommendation,
    decision,
    expected,
):
    applicant, head, _, authority, processor = elm_people[:5]
    HierarchyConfiguration.objects.create(
        establishment_configured=establishment,
        establishment_role="establishment",
        establishment_employee=processor,
    )
    SanctioningAuthorityRule.objects.create(category="EL", unit=applicant.unit, authority=authority)
    response = submit(
        elm_client(applicant),
        category="EL",
        start_date="2026-01-02",
        end_date="2026-01-05",
    )
    assert response.status_code == 201
    app = response.json()
    response = act(elm_client(head), app, "unit-head-review", decision=recommendation)
    assert response.status_code == 200
    assert response.json()["unit_head_recommendation"] == recommendation
    assert response.json()["state"] == (
        "Awaiting Establishment Routing" if establishment else "Awaiting Final Sanction Decision"
    )
    if establishment:
        assert AssignmentNotification.objects.filter(
            application_id=app["id"],
            recipient=processor,
            kind="establishment",
        ).exists()
        response = act(elm_client(processor, role="establishment"), app, "establishment-route")
        assert response.status_code == 200
        assert response.json()["state"] == "Awaiting Final Sanction Decision"
    assert (
        AssignmentNotification.objects.filter(
            application_id=app["id"],
            recipient=authority,
            kind="sanctioning_authority",
        ).count()
        == 1
    )
    response = act(elm_client(authority), app, "final-decision", decision=decision)
    assert response.status_code == 200
    assert response.json()["state"] == expected
    assert response.json()["allowed_actions"] == []
    if decision == "Approve":
        assert LeaveUsage.objects.get(
            employee=applicant, category="EL", year=2026
        ).used_days == Decimal("4")
    else:
        assert not LeaveUsage.objects.filter(employee=applicant).exists()
    assert act(elm_client(authority), app, "final-decision", decision=decision).status_code == 403


@pytest.mark.parametrize("decision,expected", [("Approve", "Approved"), ("Reject", "Rejected")])
@pytest.mark.parametrize("with_substitute", [False, True])
def test_rows_2_4_15_16_director_path(elm_client, elm_people, decision, expected, with_substitute):
    director, _, substitute = elm_people[:3]
    director.is_director = True
    director.save(update_fields=["is_director"])
    response = submit(
        elm_client(director), **({"substitute": substitute.pk} if with_substitute else {})
    )
    assert response.status_code == 201
    app = response.json()
    if with_substitute:
        response = act(elm_client(substitute), app, "substitute-response", accept=True)
        assert response.status_code == 200
        assert response.json()["state"] == "Awaiting Director Self-Sanction"
    else:
        assert app["state"] == "Awaiting Director Self-Sanction"
    assert (
        AssignmentNotification.objects.filter(
            application_id=app["id"],
            recipient=director,
            kind="director_self_sanction",
        ).count()
        == 1
    )
    response = act(elm_client(director), app, "director-decision", decision=decision)
    assert response.status_code == 200
    assert response.json()["state"] == expected
    if decision == "Approve":
        assert LeaveUsage.objects.get(employee=director, category="CL").used_days == Decimal("1")
    else:
        assert not LeaveUsage.objects.filter(employee=director).exists()


def test_uc002_decline_and_datetime(elm_client, elm_people):
    app = submit(elm_client(elm_people[0]), substitute=elm_people[2].pk).json()
    response = act(elm_client(elm_people[2]), app, "substitute-response", accept=False)
    assert response.status_code == 200
    assert response.json()["state"] == "Applicant Action Required"
    response_record = LeaveApplication.objects.get(pk=app["id"]).substitute_response
    assert response_record.response == "Declined"
    assert timezone.is_aware(response_record.responded_at)
    assert (
        act(elm_client(elm_people[1]), app, "unit-head-review", decision="Approve").status_code
        == 403
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"substitute": 999999},
        {"substitute": [1, 2]},
        {"substitute": "bad"},
        {"start_date": "bad"},
        {"start_date": None},
        {"category": "XYZ"},
        {"first_half": "invalid"},
        {"first_half": True, "second_half": True},
        {"first_half": True, "end_date": "2026-01-05"},
    ],
)
def test_uc001_malformed_input_returns_400(elm_client, elm_people, payload):
    assert submit(elm_client(elm_people[0]), **payload).status_code == 400
    assert not LeaveApplication.objects.exists()


@pytest.mark.parametrize("body", [{}, {"accept": "invalid"}, {"accept": None}])
def test_uc002_missing_or_invalid_response_is_not_a_decline(elm_client, elm_people, body):
    app = submit(elm_client(elm_people[0]), substitute=elm_people[2].pk).json()
    response = act(elm_client(elm_people[2]), app, "substitute-response", **body)
    assert response.status_code == 400
    assert LeaveApplication.objects.get(pk=app["id"]).state == "Awaiting Substitute Response"


@pytest.mark.parametrize(
    "path",
    [
        "substitute-response",
        "unit-head-review",
        "establishment-route",
        "final-decision",
        "director-decision",
    ],
)
def test_br036_unknown_or_hidden_action_is_404(elm_client, elm_people, path):
    app = submit(elm_client(elm_people[0])).json()
    client = elm_client(elm_people[5])
    assert client.post(f"{BASE}{app['id']}/{path}/", {}, format="json").status_code == 404
    assert client.post(f"{BASE}{uuid4()}/{path}/", {}, format="json").status_code == 404


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
@pytest.mark.parametrize("role", ["employee", "admin"])
def test_br034_no_mutation_for_any_role(elm_client, elm_people, role, method):
    app = submit(elm_client(elm_people[0])).json()
    before = LeaveApplication.objects.filter(pk=app["id"]).values().get()
    response = getattr(elm_client(elm_people[0], role=role), method)(
        f"{BASE}{app['id']}/",
        {"remarks": "modified"},
        format="json",
    )
    assert response.status_code == 405
    assert LeaveApplication.objects.filter(pk=app["id"]).values().get() == before


def test_br036_task_lists_and_allowed_actions(elm_client, elm_people):
    app = submit(elm_client(elm_people[0])).json()
    assert elm_client(elm_people[0]).get(BASE + "?task=unit-head").json()["results"] == []
    head_rows = elm_client(elm_people[1]).get(BASE + "?task=unit-head").json()["results"]
    assert [row["id"] for row in head_rows] == [app["id"]]
    assert head_rows[0]["allowed_actions"] == ["unit-head-review"]
    assert elm_client(elm_people[1]).get(BASE + "?task=mine").json()["results"] == []


@pytest.mark.parametrize("category,used", [("CL", "8"), ("RH", "2")])
def test_br010_rh_and_cl_approval_posts_usage(elm_client, elm_people, category, used):
    if category == "RH":
        calendar = HolidayCalendar.objects.create(name="RH", year=2026, is_published=True)
        HolidayDate.objects.create(calendar=calendar, date="2026-01-02", is_restricted_holiday=True)
    response = submit(elm_client(elm_people[0]), category=category)
    assert response.status_code == 201
    response = act(
        elm_client(elm_people[1]), response.json(), "unit-head-review", decision="Approve"
    )
    assert response.status_code == 200
    assert LeaveUsage.objects.get(employee=elm_people[0], category=category).used_days == Decimal(
        "1"
    )


def test_br030_policy_limit_changes_immediately(elm_people):
    policy = LeavePolicy.objects.create(name="Current", cl_days=0)
    with pytest.raises(ValidationError, match="entitlement"):
        apply_leave(
            applicant=elm_people[0], category="CL", start_date="2026-01-02", end_date="2026-01-02"
        )
    policy.cl_days = 8
    policy.save(update_fields=["cl_days"])
    assert apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-02",
        end_date="2026-01-02",
    ).pk


def test_br031_replacement_calendar_supersedes_previous(elm_people):
    previous = HolidayCalendar.objects.create(name="Old", year=2026, is_published=True)
    HolidayDate.objects.create(calendar=previous, date="2026-01-02", is_restricted_holiday=True)
    replacement = HolidayCalendar.objects.create(name="New", year=2026, is_published=False)
    HolidayDate.objects.create(calendar=replacement, date="2026-01-05", is_restricted_holiday=True)
    app = apply_leave(
        applicant=elm_people[0],
        category="RH",
        start_date="2026-01-02",
        end_date="2026-01-02",
    )
    assert app.category == "RH"
    replacement.is_published = True
    replacement.save(update_fields=["is_published"])
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[1], category="RH", start_date="2026-01-02", end_date="2026-01-02"
        )
    assert (
        apply_leave(
            applicant=elm_people[1],
            category="RH",
            start_date="2026-01-05",
            end_date="2026-01-05",
        ).category
        == "RH"
    )


def test_br019_routing_resolves_current_authority(elm_client, elm_people):
    hierarchy = HierarchyConfiguration.objects.create(
        establishment_configured=True,
        establishment_role="establishment",
    )
    rule = SanctioningAuthorityRule.objects.create(category="EL", authority=elm_people[3])
    app = submit(elm_client(elm_people[0]), category="EL").json()
    assert (
        act(elm_client(elm_people[1]), app, "unit-head-review", decision="Recommended").status_code
        == 200
    )
    rule.authority = elm_people[5]
    rule.save(update_fields=["authority"])
    result = act(
        elm_client(elm_people[4], role=hierarchy.establishment_role), app, "establishment-route"
    )
    assert result.status_code == 200
    assert result.json()["sanctioning_authority"] == elm_people[5].pk


def test_br019_applicant_specific_authority(elm_people):
    SanctioningAuthorityRule.objects.create(category="EL", authority=elm_people[3])
    SanctioningAuthorityRule.objects.create(
        applicant=elm_people[0],
        category="EL",
        unit=elm_people[0].unit,
        authority=elm_people[5],
    )
    app = apply_leave(
        applicant=elm_people[0], category="EL", start_date="2026-01-02", end_date="2026-01-02"
    )
    review_leave(application=app, unit_head=elm_people[1], decision="Recommended")
    assert app.sanctioning_authority == elm_people[5]


def test_deciding_with_stale_object_cannot_double_deduct(elm_people):
    director = elm_people[0]
    director.is_director = True
    director.save(update_fields=["is_director"])
    app = apply_leave(
        applicant=director, category="CL", start_date="2026-01-02", end_date="2026-01-02"
    )
    stale = LeaveApplication.objects.get(pk=app.pk)
    make_director_decision(application=app, actor=director, decision="Approve")
    with pytest.raises(ValidationError):
        make_director_decision(application=stale, actor=director, decision="Approve")
    assert LeaveUsage.objects.get(employee=director, category="CL").used_days == Decimal("1")


def test_br036_module_grant_required_on_every_view(elm_client, elm_people):
    client = elm_client(elm_people[0], modules=())
    for path in ["applications", "colleagues", "policies", "holidays"]:
        assert client.get(f"/api/v1/elm/{path}/").status_code == 403


def test_br036_unknown_employee_is_403(elm_client, elm_people):
    person = elm_people[5]
    person.user = None
    person.save(update_fields=["user"])
    assert elm_client(person).get(BASE).status_code == 403
