"""Reviewers and appraisal archives are verified and immutable."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.hreis.models import (
    AppraisalDetail,
    EmployeeServiceRecord,
    HRPolicyVersion,
    ServiceRecordRevision,
)
from modules.hreis.services import appraisals, records
from modules.hreis.services import requests as submissions
from modules.hreis.tests.actors import Principal

pytestmark = pytest.mark.django_db


def principal(user, role, permissions, kind="staff"):
    return Principal(
        user_id=user,
        username=f"user{user}",
        display_name="Person",
        kind=kind,
        active_role=role,
        roles=(role,),
        permissions=frozenset(permissions),
        modules=("hreis",),
    )


@pytest.fixture
def submitted(monkeypatch):
    EmployeeServiceRecord.objects.create(
        user_id=10,
        department="CSE",
        designation_snapshot="Professor",
        appointment_details={},
        service_history=[{"kind": "appointment"}],
        revision=0,
    )
    now = timezone.now()
    HRPolicyVersion.objects.create(
        family="appraisal",
        version=1,
        effective_from=now - timedelta(days=1),
        effective_until=now + timedelta(days=1),
        parameters={
            "submission_window": {
                "start": (now - timedelta(hours=2)).isoformat(),
                "end": (now + timedelta(hours=2)).isoformat(),
            },
            "routes": [
                {
                    "employee_kind": "faculty",
                    "department": "CSE",
                    "authorities": ["HOD (CSE)", "Registrar"],
                }
            ],
        },
        approved_by_user_id=99,
        approved_designation="hradmin",
    )
    monkeypatch.setattr(
        appraisals,
        "get_users",
        lambda ids: {i: SimpleNamespace(kind="faculty") for i in ids if i in {10, 201}},
    )
    return submissions.submit_appraisal(
        principal(10, "faculty", ("hreis.appraisal.create",), kind="faculty"),
        period_key="FY2026",
        submitted_form={"yearly_summary": "Teaching"},
        idempotency_key="appraisal-create",
    )


def test_reviewer_assignment_then_forward_then_final_archive(submitted):
    row = appraisals.assign_reviewers(
        principal(99, "hradmin", ("hreis.appraisal.assign",)),
        request_id=submitted.id,
        reviewer_user_ids=[201],
        idempotency_key="assign-reviewer",
    )
    # HR-AFR-013: HR Administrator explicitly assigned the verified reviewer.
    assert row.state == "pending_review"
    assert AppraisalDetail.objects.get(request=row).reviewer_user_ids == [201]
    hod = principal(201, "HOD (CSE)", ("hreis.appraisal.approve",), "faculty")
    with pytest.raises(ConflictError):
        appraisals.review_appraisal(
            hod,
            request_id=row.id,
            event="finalize",
            idempotency_key="early-finalize",
        )
    next_row = appraisals.review_appraisal(
        hod,
        request_id=row.id,
        event="forward",
        idempotency_key="forward-review",
    )
    assert next_row.state == "pending_next_appraisal_authority"
    registrar = principal(202, "Registrar", ("hreis.appraisal.approve",))
    final = appraisals.review_appraisal(
        registrar,
        request_id=row.id,
        event="finalize",
        idempotency_key="finalize-review",
    )
    assert final.state == "finalized"
    record = EmployeeServiceRecord.objects.get(user_id=10)
    assert record.revision == 1
    assert record.service_history[0] == {"kind": "appointment"}
    assert record.service_history[-1]["period_key"] == "FY2026"
    detail = AppraisalDetail.objects.get(request=row)
    assert detail.finalized_at is not None
    assert detail.archive_reference == f"hreis:service-record:{record.pk}:revision:1"
    assert ServiceRecordRevision.objects.get(record=record).snapshot["service_history"][-1][
        "submitted_form"
    ] == {"yearly_summary": "Teaching"}
    hr = principal(99, "hradmin", ("hreis.service_record.update",))
    with pytest.raises(ConflictError) as exc:
        records.update_record(
            hr,
            record_id=record.pk,
            expected_revision=1,
            fields={"service_history": [{"kind": "appointment"}]},
            idempotency_key="strip-final-archive",
        )
    assert exc.value.code == "appraisal_archive_immutable"
    # Normal HR history remains editable without changing archived appraisals.
    updated = records.update_record(
        hr,
        record_id=record.pk,
        expected_revision=1,
        fields={"service_history": [*record.service_history, {"kind": "training"}]},
        idempotency_key="append-normal-history",
    )
    assert updated.revision == 2
    assert updated.service_history[-2]["period_key"] == "FY2026"
    with pytest.raises(NotFoundError):
        appraisals.review_appraisal(
            registrar,
            request_id=row.id,
            event="finalize",
            idempotency_key="duplicate-finalize",
        )


def test_appraisal_owner_cannot_be_assigned_or_act_as_reviewer(submitted):
    administrator = principal(99, "hradmin", ("hreis.appraisal.assign",))
    with pytest.raises(BadRequestError) as exc:
        appraisals.assign_reviewers(
            administrator,
            request_id=submitted.id,
            reviewer_user_ids=[10],
            idempotency_key="self-reviewer-assignment",
        )
    assert exc.value.code == "invalid_reviewers"
    row = appraisals.assign_reviewers(
        administrator,
        request_id=submitted.id,
        reviewer_user_ids=[201],
        idempotency_key="valid-independent-reviewer",
    )
    owner_as_hod = principal(10, "HOD (CSE)", ("hreis.appraisal.approve",), "faculty")
    with pytest.raises(NotFoundError) as exc:
        appraisals.review_appraisal(
            owner_as_hod,
            request_id=row.id,
            event="forward",
            idempotency_key="self-appraisal-review",
        )
    assert exc.value.code == "appraisal_not_assigned"
    row.refresh_from_db()
    assert row.state == "pending_review"


def test_unknown_reviewers_and_unauthorized_role_are_refused(submitted):
    hr = principal(99, "hradmin", ("hreis.appraisal.assign",))
    with pytest.raises(ConflictError) as exc:
        appraisals.assign_reviewers(
            hr,
            request_id=submitted.id,
            reviewer_user_ids=[999],
            idempotency_key="unknown-reviewer",
        )
    assert exc.value.code == "reviewer_unknown"
    assert AppraisalDetail.objects.get(request=submitted).reviewer_user_ids == []


def test_three_stage_appraisal_can_forward_twice_then_finalize(monkeypatch):
    # HR-UC-008, BR-HR-014, BW-HR-05: repeated forward never loses the route.
    EmployeeServiceRecord.objects.create(
        user_id=10,
        department="CSE",
        designation_snapshot="Professor",
        appointment_details={},
        service_history=[],
    )
    now = timezone.now()
    HRPolicyVersion.objects.create(
        family="appraisal",
        version=1,
        effective_from=now - timedelta(days=1),
        effective_until=now + timedelta(days=1),
        parameters={
            "submission_window": {
                "start": (now - timedelta(hours=2)).isoformat(),
                "end": (now + timedelta(hours=2)).isoformat(),
            },
            "routes": [
                {
                    "employee_kind": "faculty",
                    "department": "CSE",
                    "authorities": ["HOD (CSE)", "Registrar", "Director"],
                }
            ],
        },
        approved_by_user_id=99,
        approved_designation="hradmin",
    )
    monkeypatch.setattr(
        appraisals,
        "get_users",
        lambda ids: {i: SimpleNamespace(kind="faculty") for i in ids if i in {10, 201}},
    )
    row = submissions.submit_appraisal(
        principal(10, "faculty", ("hreis.appraisal.create",), kind="faculty"),
        period_key="FY2027",
        submitted_form={"teaching": "verified"},
        idempotency_key="three-step-submit",
    )
    row = appraisals.assign_reviewers(
        principal(99, "hradmin", ("hreis.appraisal.assign",)),
        request_id=row.pk,
        reviewer_user_ids=[201],
        idempotency_key="three-step-assign",
    )
    for user, role, expected_step in [
        (201, "HOD (CSE)", 1),
        (202, "Registrar", 2),
    ]:
        row = appraisals.review_appraisal(
            principal(user, role, ("hreis.appraisal.approve",)),
            request_id=row.pk,
            event="forward",
            idempotency_key=f"three-step-forward-{expected_step}",
        )
        assert row.route_step == expected_step
        assert row.state == "pending_next_appraisal_authority"
    final = appraisals.review_appraisal(
        principal(203, "Director", ("hreis.appraisal.approve",)),
        request_id=row.pk,
        event="finalize",
        idempotency_key="three-step-final",
    )
    assert final.state == "finalized"
    assert (
        EmployeeServiceRecord.objects.get(user_id=10).service_history[-1]["period_key"] == "FY2027"
    )


def test_one_stage_appraisal_finalizes_without_unneeded_forward(monkeypatch):
    # BW-HR-04, HR-UC-008, HR-AFR-047, BR-HR-014:
    # a route whose only authority is the current assigned reviewer closes directly.
    EmployeeServiceRecord.objects.create(
        user_id=10,
        department="CSE",
        designation_snapshot="Professor",
        appointment_details={},
        service_history=[],
    )
    now = timezone.now()
    HRPolicyVersion.objects.create(
        family="appraisal",
        version=1,
        effective_from=now - timedelta(hours=1),
        effective_until=now + timedelta(days=1),
        parameters={
            "submission_window": {
                "start": (now - timedelta(minutes=10)).isoformat(),
                "end": (now + timedelta(hours=2)).isoformat(),
            },
            "routes": [
                {
                    "employee_kind": "faculty",
                    "department": "CSE",
                    "authorities": ["HOD (CSE)"],
                }
            ],
        },
        approved_by_user_id=99,
        approved_designation="hradmin",
    )
    monkeypatch.setattr(
        appraisals,
        "get_users",
        lambda ids: {i: SimpleNamespace(kind="faculty") for i in ids if i in {10, 201}},
    )
    submitted = submissions.submit_appraisal(
        principal(10, "faculty", ("hreis.appraisal.create",), kind="faculty"),
        period_key="FY2026",
        submitted_form={"research": "Approved publication list"},
        idempotency_key="direct-final-submit",
    )
    assigned = appraisals.assign_reviewers(
        principal(99, "hradmin", ("hreis.appraisal.assign",)),
        request_id=submitted.pk,
        reviewer_user_ids=[201],
        idempotency_key="direct-final-assign",
    )
    assert assigned.state == "pending_review" and assigned.route_step == 0
    closed = appraisals.review_appraisal(
        principal(201, "HOD (CSE)", ("hreis.appraisal.approve",), "faculty"),
        request_id=submitted.pk,
        event="finalize",
        idempotency_key="direct-final-finalize",
    )
    assert closed.state == "finalized" and closed.route_step == 0
    archived = EmployeeServiceRecord.objects.get(user_id=10).service_history[-1]
    assert archived["submitted_form"] == {"research": "Approved publication list"}
    assert AppraisalDetail.objects.get(request_id=submitted.pk).finalized_at is not None


def test_hr_administrator_cannot_assign_reviewers_to_own_appraisal():
    # BR-HR-013: even a multi-role HR administrator may not select the
    # people evaluating an appraisal they submitted in another acting role.
    from modules.hreis.models import HRRequest

    own = HRRequest.objects.create(user_id=99, family="appraisal", state="submitted")
    AppraisalDetail.objects.create(
        request=own,
        period_key="FY2026",
        employee_record=EmployeeServiceRecord.objects.create(
            user_id=99,
            department="CSE",
            designation_snapshot="Synthetic HR",
        ),
        submitted_form={"teaching": "self-submitted"},
        reviewer_user_ids=[],
    )
    with pytest.raises(NotFoundError) as error:
        appraisals.assign_reviewers(
            principal(99, "hradmin", ("hreis.appraisal.assign",)),
            request_id=own.pk,
            reviewer_user_ids=[201],
            idempotency_key="self-committee-selection",
        )
    assert error.value.code == "appraisal_not_assigned"
    assert own.appraisal.reviewer_user_ids == []
    assert not ServiceRecordRevision.objects.exists()
