from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from conftest import make_session
from core.api.exceptions import BadRequestError, ConflictError
from fusion_auth.principal import Principal
from modules.elm.models import LeaveRequest, LeaveWorkflowAction
from modules.elm.services.routing import (
    ELMDependencyUnavailable,
    RouteStep,
    SubmissionRoute,
)
from modules.elm.services.submission import submit_leave_request

pytestmark = pytest.mark.django_db


class FakeRouteResolver:
    def __init__(self, *, requires_substitute=False, steps=None):
        self.requires_substitute = requires_substitute
        self.steps = steps

    def resolve_route(self, *, applicant, leave_type, start_date, end_date):
        steps = self.steps
        if steps is None:
            if leave_type in {"CL", "RH"}:
                steps = (RouteStep("UNIT_HEAD", 201),)
            else:
                steps = (
                    RouteStep("UNIT_HEAD", 201),
                    RouteStep("SANCTIONING_AUTHORITY", 202),
                )
        return SubmissionRoute(steps, requires_substitute=self.requires_substitute)


class FakeBalanceProvider:
    def __init__(self, balance=Decimal("12")):
        self.balance = balance
        self.reads = []

    def get_available_balance(self, *, user_id, leave_type):
        self.reads.append((user_id, leave_type))
        return self.balance


def _actor(*, user_id=101, kind="staff"):
    return Principal.from_session(
        make_session(
            user_id=user_id,
            kind=kind,
            roles=(kind,),
            active_role=kind,
            modules=("elm",),
            permissions=("elm.request.create", "elm.request.view_self"),
        )
    )


def _submit(actor=None, **kwargs):
    options = {
        "actor": actor or _actor(),
        "leave_type": "EL",
        "start_date": date(2025, 10, 3),
        "end_date": date(2025, 10, 6),
        "purpose": "Personal leave",
        "routing_resolver": FakeRouteResolver(),
        "balance_provider": FakeBalanceProvider(),
    }
    options.update(kwargs)
    return submit_leave_request(**options)


def test_supported_request_persists_actual_applicant_status_and_audit():
    provider = FakeBalanceProvider(Decimal("4"))
    request = _submit(balance_provider=provider)

    request.refresh_from_db()
    assert request.user_id == 101
    assert request.status == LeaveRequest.Status.PENDING_UNIT_HEAD
    assert request.chargeable_days == Decimal("4")
    assert request.submitted_at is not None
    assert list(request.approval_steps.values_list("role_code", flat=True)) == [
        "UNIT_HEAD",
        "SANCTIONING_AUTHORITY",
    ]
    action = request.workflow_actions.get()
    assert action.action == LeaveWorkflowAction.Action.SUBMITTED
    assert action.actor_user_id == 101
    assert provider.reads == [(101, "EL")]


def test_configured_establishment_route_keeps_the_optional_step_in_order():
    resolver = FakeRouteResolver(
        steps=(
            RouteStep("UNIT_HEAD", 201),
            RouteStep("ESTABLISHMENT", 202),
            RouteStep("SANCTIONING_AUTHORITY", 203),
        )
    )

    request = _submit(routing_resolver=resolver)

    assert request.status == LeaveRequest.Status.PENDING_UNIT_HEAD
    assert list(request.approval_steps.values_list("role_code", flat=True)) == [
        "UNIT_HEAD",
        "ESTABLISHMENT",
        "SANCTIONING_AUTHORITY",
    ]


def test_submission_does_not_post_or_reserve_balance():
    provider = FakeBalanceProvider()
    _submit(balance_provider=provider)

    assert provider.reads == [(101, "EL")]
    assert not hasattr(provider, "post_transaction")


@pytest.mark.parametrize(
    ("leave_type", "start_date", "end_date", "half_day"),
    [
        ("CL", date(2025, 10, 1), date(2025, 10, 1), None),
        ("CL", date(2025, 10, 1), date(2025, 10, 2), None),
        ("RH", date(2025, 10, 1), date(2025, 10, 1), None),
        ("SCL", date(2025, 10, 1), date(2025, 10, 1), None),
    ],
)
def test_unsupported_counting_rules_are_not_persisted(leave_type, start_date, end_date, half_day):
    with pytest.raises(ConflictError) as error:
        _submit(
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
        )
    assert error.value.code == "unsupported_leave_counting_rule"
    assert LeaveRequest.objects.count() == 0


def test_overlapping_pending_request_is_not_persisted():
    LeaveRequest.objects.create(
        user_id=101,
        leave_type="EL",
        start_date=date(2025, 10, 4),
        end_date=date(2025, 10, 4),
        purpose="Existing",
        status=LeaveRequest.Status.PENDING_UNIT_HEAD,
    )

    with pytest.raises(ConflictError) as error:
        _submit()

    assert error.value.code == "overlap"
    assert LeaveRequest.objects.count() == 1


def test_missing_production_router_fails_closed_without_persisting():
    from django.test import override_settings

    with (
        override_settings(ELM_SUBMISSION_ROUTING_RESOLVER=None),
        pytest.raises(ELMDependencyUnavailable) as error,
    ):
        submit_leave_request(
            actor=_actor(),
            leave_type="EL",
            start_date=date(2025, 10, 3),
            end_date=date(2025, 10, 6),
            purpose="Personal leave",
            balance_provider=FakeBalanceProvider(),
        )

    assert error.value.status_code == 503
    assert LeaveRequest.objects.count() == 0


def test_insufficient_balance_fails_without_persisting():
    with pytest.raises(ConflictError) as error:
        _submit(balance_provider=FakeBalanceProvider(Decimal("3.99")))

    assert error.value.code == "insufficient_balance"
    assert LeaveRequest.objects.count() == 0


def test_vl_requires_faculty_and_calendar_validation():
    with pytest.raises(ConflictError) as error:
        _submit(
            actor=_actor(kind="staff"),
            leave_type="VL",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 1),
        )
    assert error.value.code == "category_ineligible"
    assert LeaveRequest.objects.count() == 0


def test_vl_requires_an_authoritative_academic_calendar():
    with pytest.raises(ELMDependencyUnavailable) as error:
        _submit(
            actor=_actor(kind="faculty"),
            leave_type="VL",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 1),
        )
    assert error.value.status_code == 503
    assert LeaveRequest.objects.count() == 0


def test_route_that_requires_substitute_rejects_missing_nominee():
    resolver = FakeRouteResolver(requires_substitute=True)

    with pytest.raises(BadRequestError) as error:
        _submit(routing_resolver=resolver)

    assert error.value.code == "substitute_required"
    assert LeaveRequest.objects.count() == 0


def test_required_substitute_is_validated_and_waits_for_consent(monkeypatch):
    monkeypatch.setattr(
        "modules.elm.services.submission.directory.get_users",
        lambda ids: {303: SimpleNamespace(kind="staff")},
    )
    resolver = FakeRouteResolver(requires_substitute=True)

    request = _submit(routing_resolver=resolver, substitute_user_id=303)

    assert request.status == LeaveRequest.Status.PENDING_SUBSTITUTE
    assignment = request.substitute_assignments.get()
    assert assignment.nominee_user_id == 303
    assert assignment.status == "PENDING"


def test_optional_nominee_does_not_override_resolved_route():
    with pytest.raises(BadRequestError) as error:
        _submit(substitute_user_id=303)

    assert error.value.code == "substitute_not_required"
    assert LeaveRequest.objects.count() == 0


def test_invalid_route_shape_fails_closed_without_persisting():
    resolver = FakeRouteResolver(
        steps=(
            RouteStep("UNIT_HEAD", 201),
            RouteStep("SANCTIONING_AUTHORITY", 202),
        )
    )

    with pytest.raises(ELMDependencyUnavailable):
        _submit(
            leave_type="CL",
            start_date=date(2025, 10, 3),
            end_date=date(2025, 10, 3),
            half_day="FIRST",
            routing_resolver=resolver,
        )

    assert LeaveRequest.objects.count() == 0


@pytest.mark.parametrize(
    "steps",
    (
        (
            RouteStep("UNIT_HEAD", 201),
            RouteStep("SANCTIONING_AUTHORITY", 202),
            RouteStep("SANCTIONING_AUTHORITY", 203),
        ),
        (
            RouteStep("UNIT_HEAD", 201),
            RouteStep("ESTABLISHMENT", 202),
            RouteStep("ESTABLISHMENT", 203),
            RouteStep("SANCTIONING_AUTHORITY", 204),
        ),
    ),
)
def test_ambiguous_or_duplicate_route_steps_fail_closed_without_persisting(steps):
    with pytest.raises(ELMDependencyUnavailable):
        _submit(routing_resolver=FakeRouteResolver(steps=steps))

    assert LeaveRequest.objects.count() == 0


def test_director_self_sanction_must_be_assigned_to_the_applicant():
    resolver = FakeRouteResolver(steps=(RouteStep("DIRECTOR_SELF_SANCTION", 202),))

    with pytest.raises(ELMDependencyUnavailable):
        _submit(routing_resolver=resolver)

    assert LeaveRequest.objects.count() == 0


def test_director_applicant_route_starts_at_self_sanction():
    director = Principal.from_session(
        make_session(
            user_id=101,
            kind="staff",
            roles=("staff", "director"),
            active_role="director",
            modules=("elm",),
            permissions=("elm.request.create", "elm.request.view_self"),
        )
    )
    resolver = FakeRouteResolver(steps=(RouteStep("DIRECTOR_SELF_SANCTION", 101),))

    request = _submit(actor=director, routing_resolver=resolver)

    assert request.status == LeaveRequest.Status.PENDING_DIRECTOR_SANCTION
    assert list(request.approval_steps.values_list("role_code", "assigned_user_id")) == [
        ("DIRECTOR_SELF_SANCTION", 101)
    ]


def test_route_steps_must_use_the_immutable_route_tuple_contract():
    with pytest.raises(ELMDependencyUnavailable):
        _submit(routing_resolver=FakeRouteResolver(steps=[RouteStep("UNIT_HEAD", 201)]))

    assert LeaveRequest.objects.count() == 0
