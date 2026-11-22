from types import SimpleNamespace

import pytest

from conftest import make_session
from core.api.exceptions import ConflictError, NotFoundError
from fusion_auth.principal import Principal
from modules.hr.domain import state_machine
from modules.hr.models import (
    Appraisal,
    Claim,
    EmployeeRecord,
    WorkflowRoute,
)
from modules.hr.registry import ROLE_GRANTS
from modules.hr.selectors.claims import visible_claims
from modules.hr.services import appraisals as appraisal_service
from modules.hr.services import claims as service
from modules.hr.services import configuration as configuration_service
from modules.hr.services import employees as employee_service

pytestmark = pytest.mark.django_db


def actor(user_id: int, *permissions: str) -> Principal:
    return Principal.from_session(
        make_session(
            user_id=user_id,
            kind="staff",
            permissions=permissions,
            modules=("hr",),
        )
    )


def test_approval_is_rejected_before_last_configured_authority():
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_claim(
            state_machine.PENDING_AUTHORITY,
            action="approve",
            authority_step=0,
            route_length=2,
        )


def test_appraisal_must_follow_reviewer_order_before_finalization():
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.review_appraisal(
            state_machine.PENDING_REVIEW,
            action="finalize",
            current_index=0,
            reviewer_count=2,
        )


def test_only_the_current_authority_can_decide_a_claim():
    route = WorkflowRoute.objects.create(
        employee_category="staff",
        request_type="cpda_advance",
        steps=[
            {"approver_user_id": 88, "authority_label": "First"},
            {"approver_user_id": 99, "authority_label": "Final"},
        ],
        updated_by_user_id=7,
    )
    claim = Claim.objects.create(
        employee_user_id=1001,
        employee_category="staff",
        request_type="cpda_advance",
        purpose="Research materials",
        amount="100.00",
        form_data={"purpose": "Research materials"},
        supporting_documents=[{"file_id": "file1", "url": "https://drive.google.com"}],
        status="pending_authority",
        current_authority_user_id=88,
        route_snapshot=route.steps,
        authority_step=0,
    )

    with pytest.raises(NotFoundError):
        service.decide_claim(
            actor=actor(77, "hr.claim.approve"),
            claim_id=claim.pk,
            action="forward",
        )

    updated = service.decide_claim(
        actor=actor(88, "hr.claim.approve"),
        claim_id=claim.pk,
        action="forward",
    )
    assert updated.status == "pending_next_authority"
    assert updated.current_authority_user_id == 99

    finalized = service.decide_claim(
        actor=actor(99, "hr.claim.approve"),
        claim_id=claim.pk,
        action="approve",
    )
    assert finalized.status == "approved"
    assert finalized.current_authority_user_id is None


def test_hr_api_requires_a_specific_permission(stub_iam):
    from rest_framework.test import APIClient

    stub_iam(make_session(user_id=1001, kind="staff", modules=("hr",), permissions=()))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")

    response = client.get("/api/v1/hr/employees/")

    assert response.status_code == 403


@pytest.mark.parametrize(
    "role",
    [
        "Director",
        "Accountant",
        "hr_officer",
    ],
)
def test_claim_visibility_is_limited_to_the_active_role_scope(role):
    claims = [
        Claim.objects.create(
            employee_user_id=1001,
            employee_category="staff",
            request_type="cpda_advance",
            status="pending_authority",
            amount="10.00",
            current_authority_user_id=88,
        ),
        Claim.objects.create(
            employee_user_id=1002,
            employee_category="staff",
            request_type="cpda_advance",
            status="pending_authority",
            amount="10.00",
            current_authority_user_id=99,
        ),
        Claim.objects.create(
            employee_user_id=1003,
            employee_category="staff",
            request_type="cpda_advance",
            status="approved",
            amount="10.00",
        ),
        Claim.objects.create(
            employee_user_id=1004,
            employee_category="staff",
            request_type="cpda_advance",
            status="financial_processing_recorded",
            amount="10.00",
        ),
    ]
    principal = actor(88, *ROLE_GRANTS[role])

    visible_ids = set(visible_claims(principal).values_list("pk", flat=True))
    if role == "Director":
        expected_ids = {
            claim.pk for claim in claims if claim.current_authority_user_id == principal.user_id
        }
    elif role == "Accountant":
        expected_ids = {
            claim.pk
            for claim in claims
            if claim.status in {"approved", "financial_processing_recorded"}
        }
    else:
        expected_ids = {claim.pk for claim in claims}

    assert visible_ids == expected_ids


def test_approver_cannot_approve_their_own_claim():
    claim = Claim.objects.create(
        employee_user_id=88,
        employee_category="staff",
        request_type="cpda_advance",
        amount="10.00",
        status="pending_authority",
        current_authority_user_id=88,
        route_snapshot=[{"approver_user_id": 88}],
    )

    with pytest.raises(NotFoundError):
        service.decide_claim(
            actor=actor(88, "hr.claim.approve"),
            claim_id=claim.pk,
            action="approve",
        )

    claim.refresh_from_db()
    assert claim.status == "pending_authority"


def test_employee_cannot_be_assigned_to_review_their_own_appraisal():
    appraisal = Appraisal.objects.create(
        employee_user_id=88,
        period="2026",
        form_data={"summary": "work"},
    )

    with pytest.raises(ConflictError) as error:
        appraisal_service.assign_reviewers(
            actor=actor(7, "hr.appraisal.assign"),
            appraisal_id=appraisal.pk,
            reviewer_user_ids=[88],
        )

    assert error.value.code == "self_review_not_allowed"


def test_employee_cannot_review_their_own_appraisal():
    appraisal = Appraisal.objects.create(
        employee_user_id=88,
        period="2026",
        form_data={"summary": "work"},
        status="pending_review",
        reviewer_user_ids=[88],
        current_reviewer_user_id=88,
    )

    with pytest.raises(NotFoundError):
        appraisal_service.review_appraisal(
            actor=actor(88, "hr.appraisal.review"),
            appraisal_id=appraisal.pk,
            action="finalize",
        )

    appraisal.refresh_from_db()
    assert appraisal.status == "pending_review"


def test_finalized_appraisal_is_archived_in_employee_service_history():
    EmployeeRecord.objects.create(
        user_id=88,
        employee_category="staff",
        department="Research",
        designation="Faculty",
        created_by_user_id=7,
        updated_by_user_id=7,
    )
    appraisal = Appraisal.objects.create(
        employee_user_id=88,
        period="2026",
        form_data={"summary": "work"},
        status="pending_review",
        reviewer_user_ids=[99],
        current_reviewer_user_id=99,
    )

    updated = appraisal_service.review_appraisal(
        actor=actor(99, "hr.appraisal.review"),
        appraisal_id=appraisal.pk,
        action="finalize",
    )

    record = EmployeeRecord.objects.get(user_id=88)
    assert updated.status == "closed"
    assert record.service_history == [
        {
            "record_type": "appraisal_archive",
            "appraisal_id": appraisal.pk,
            "period": "2026",
            "finalized_at": updated.finalized_at.isoformat(),
        }
    ]


def test_finalized_appraisal_archive_cannot_be_removed_from_service_history():
    EmployeeRecord.objects.create(
        user_id=88,
        employee_category="staff",
        department="Research",
        designation="Faculty",
        service_history=[
            {
                "record_type": "appraisal_archive",
                "appraisal_id": 1,
                "period": "2026",
                "finalized_at": "2026-01-01T00:00:00+00:00",
            }
        ],
        created_by_user_id=7,
        updated_by_user_id=7,
    )

    with pytest.raises(ConflictError) as error:
        employee_service.update_employee_record(
            actor=actor(7, "hr.employee.update"),
            user_id=88,
            changes={"service_history": []},
        )

    assert error.value.code == "appraisal_archive_immutable"


def test_workflow_route_rejects_inactive_approver(monkeypatch):
    monkeypatch.setattr(
        configuration_service.directory,
        "get_users",
        lambda user_ids: {99: SimpleNamespace(kind="staff")},
    )
    monkeypatch.setattr(
        configuration_service.directory,
        "held_employee_ids",
        set,
    )

    with pytest.raises(ConflictError) as error:
        configuration_service.save_workflow_route(
            actor=actor(7, "hr.workflow.manage"),
            employee_category="staff",
            request_type="cpda_advance",
            steps=[{"approver_user_id": 99, "authority_label": "Registrar"}],
        )

    assert error.value.code == "invalid_workflow_approver"
