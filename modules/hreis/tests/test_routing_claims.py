"""Spec-grounded routing and claims rules; institutional policy is an input."""

from decimal import Decimal

import pytest

from modules.hreis.domain import claims, routing
from modules.hreis.domain import workflow as wf


@pytest.fixture
def route():
    return routing.ApprovalRoute(
        family=wf.LEAVE,
        employee_kind="faculty",
        department="CSE",
        version="policy-1",
        authorities=("HOD (CSE)", "Director"),
    )


def test_explicit_route_resolves_and_advances_one_step(route):
    p = {(route.family, route.employee_kind, route.department): route}
    assert routing.choose_route(wf.LEAVE, "faculty", "CSE", p) == route
    assert routing.current_authority(route, 0) == "HOD (CSE)"
    assert routing.forward_step(route, 0, "HOD (CSE)") == 1
    assert routing.current_authority(route, 1) == "Director"


def test_missing_route_is_never_inferred_from_department_or_kind(route):
    with pytest.raises(routing.RouteError) as exc:
        routing.choose_route(wf.LEAVE, "faculty", "CSE", {})
    assert exc.value.code == "policy_unavailable"
    with pytest.raises(routing.RouteError) as exc:
        routing.choose_route(wf.LTC, "faculty", "CSE", {(wf.LEAVE, "faculty", "CSE"): route})
    assert exc.value.code == "policy_unavailable"


def test_policy_mismatch_refused(route):
    with pytest.raises(routing.RouteError) as exc:
        routing.choose_route(wf.CPDA, "staff", "CSE", {(wf.CPDA, "staff", "CSE"): route})
    assert exc.value.code == "mismatched_policy"


@pytest.mark.parametrize(
    "family,kind,department",
    [
        ("payroll", "faculty", "CSE"),
        (wf.LEAVE, "student", "CSE"),
        (wf.LEAVE, "staff", ""),
        (wf.LEAVE, "staff", None),
    ],
)
def test_invalid_policy_scope_fails_closed(family, kind, department):
    with pytest.raises(routing.RouteError):
        routing.choose_route(family, kind, department, {})


@pytest.mark.parametrize(
    "authorities,code",
    [
        ((), "empty_route"),
        (("HOD (CSE)", "Accountant"), "unknown_authority"),
        (("HOD (CSE)", "HOD (CSE)"), "duplicate_authority"),
    ],
)
def test_rejects_unknown_duplicate_or_empty_route(route, authorities, code):
    bad = routing.ApprovalRoute(
        route.family, route.employee_kind, route.department, route.version, authorities
    )
    with pytest.raises(routing.RouteError) as exc:
        routing.validate_route(bad)
    assert exc.value.code == code


def test_actor_cannot_skip_a_step_or_forward_beyond_last(route):
    with pytest.raises(routing.RouteError) as exc:
        routing.forward_step(route, 0, "Director")
    assert exc.value.code == "wrong_authority"
    with pytest.raises(routing.RouteError) as exc:
        routing.forward_step(route, 1, "Director")
    assert exc.value.code == "no_next_authority"
    with pytest.raises(routing.RouteError) as exc:
        routing.current_authority(route, 2)
    assert exc.value.code == "invalid_step"


@pytest.mark.parametrize("subtype", ["advance", "reimbursement"])
def test_ltc_prescribed_forms_and_cpda_required_fields(subtype):
    assert claims.validate_ltc(subtype, "ltc-form-1").subtype == subtype
    assert claims.validate_cpda(
        subtype, "Research travel", Decimal("100.50"), ["document-1"]
    ).amount == Decimal("100.50")


@pytest.mark.parametrize("subtype", ["payment", "", None])
def test_claims_reject_unspecified_subtypes(subtype):
    with pytest.raises(claims.InvalidClaim) as exc:
        claims.validate_ltc(subtype, "form")
    assert exc.value.code == "unsupported_subtype"
    with pytest.raises(claims.InvalidClaim):
        claims.validate_cpda(subtype, "Purpose", Decimal("2"), ["doc"])


@pytest.mark.parametrize("form", ["", " ", None])
def test_ltc_requires_actual_prescribed_form(form):
    with pytest.raises(claims.InvalidClaim) as exc:
        claims.validate_ltc("advance", form)
    assert exc.value.code == "missing_form"


@pytest.mark.parametrize("purpose", ["", "  ", None])
def test_cpda_requires_purpose(purpose):
    with pytest.raises(claims.InvalidClaim) as exc:
        claims.validate_cpda("advance", purpose, Decimal("100"), ["doc"])
    assert exc.value.code == "missing_purpose"


@pytest.mark.parametrize(
    "amount",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        "10",
        10.0,
    ],
)
def test_cpda_amount_is_positive_finite_decimal(amount):
    with pytest.raises(claims.InvalidClaim) as exc:
        claims.validate_cpda("advance", "Purpose", amount, ["doc"])
    assert exc.value.code == "invalid_amount"


@pytest.mark.parametrize(
    "documents",
    [
        [],
        None,
        "",
        [" "],
        ["okay", ""],
    ],
)
def test_cpda_requires_document_references(documents):
    with pytest.raises(claims.InvalidClaim) as exc:
        claims.validate_cpda("advance", "Purpose", Decimal("100"), documents)
    assert exc.value.code == "missing_documents"


def test_financial_recording_requires_approval_and_verified_correctness():
    with pytest.raises(claims.InvalidClaim) as exc:
        claims.validate_financial_recording(claim_approved=False, correctness_verified=True)
    assert exc.value.code == "not_approved"
    with pytest.raises(claims.InvalidClaim) as exc:
        claims.validate_financial_recording(claim_approved=True, correctness_verified=None)
    assert exc.value.code == "policy_unavailable"
    with pytest.raises(claims.InvalidClaim) as exc:
        claims.validate_financial_recording(claim_approved=True, correctness_verified=False)
    assert exc.value.code == "incorrect_claim"
    assert (
        claims.validate_financial_recording(claim_approved=True, correctness_verified=True) is None
    )


def test_non_teaching_staff_route_uses_registrar_only_from_explicit_policy():
    # HR-AFR-007, HR-AFR-009, BR-HR-009: no staff authority is guessed.
    registrar_route = routing.ApprovalRoute(
        family=wf.LEAVE,
        employee_kind="staff",
        department="Administration",
        version="staff-leave-policy-1",
        authorities=("Registrar",),
    )
    routes = {(wf.LEAVE, "staff", "Administration"): registrar_route}
    selected = routing.choose_route(wf.LEAVE, "staff", "Administration", routes)
    assert routing.current_authority(selected, 0) == "Registrar"
    routing.require_current_authority(selected, 0, "Registrar")
    with pytest.raises(routing.RouteError):
        routing.require_current_authority(selected, 0, "HOD (CSE)")
    with pytest.raises(routing.RouteError):
        routing.choose_route(wf.LEAVE, "faculty", "Administration", routes)
