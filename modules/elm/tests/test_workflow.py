from datetime import date

import pytest

from conftest import make_session
from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.principal import Principal
from modules.elm.models import (
    LeaveApprovalStep,
    LeaveRequest,
    LeaveWorkflowAction,
    SubstituteAssignment,
)
from modules.elm.services.routing import ELMDependencyUnavailable
from modules.elm.services.workflow import (
    decide_leave_request,
    nominate_replacement_substitute,
    respond_to_substitute_assignment,
    withdraw_leave_request,
)

pytestmark = pytest.mark.django_db


def _actor(user_id):
    return Principal.from_session(
        make_session(
            user_id=user_id,
            kind="staff",
            active_role="staff",
            roles=("staff",),
            modules=("elm",),
            permissions=("elm.request.create", "elm.request.withdraw"),
        )
    )


def _request(
    *, user_id=101, status=LeaveRequest.Status.PENDING_UNIT_HEAD, leave_type="EL", with_steps=True
):
    row = LeaveRequest.objects.create(
        user_id=user_id,
        leave_type=leave_type,
        start_date=date(2025, 10, 1),
        end_date=date(2025, 10, 1),
        purpose="Personal leave",
        chargeable_days="1",
        status=status,
    )
    if with_steps:
        LeaveApprovalStep.objects.create(
            request=row,
            sequence=1,
            role_code="UNIT_HEAD",
            assigned_user_id=201,
        )
        if leave_type not in {"CL", "RH"}:
            LeaveApprovalStep.objects.create(
                request=row,
                sequence=2,
                role_code="SANCTIONING_AUTHORITY",
                assigned_user_id=202,
            )
    return row


def test_requester_withdraws_pending_request_and_audit_is_attributed():
    request = _request()

    result = withdraw_leave_request(request_id=request.pk, actor=_actor(101))

    result.refresh_from_db()
    action = result.workflow_actions.get()
    assert result.status == LeaveRequest.Status.WITHDRAWN
    assert action.from_status == LeaveRequest.Status.PENDING_UNIT_HEAD
    assert action.to_status == LeaveRequest.Status.WITHDRAWN
    assert action.action == LeaveWorkflowAction.Action.WITHDRAWN
    assert action.actor_user_id == 101
    assert action.at is not None


def test_other_employee_cannot_withdraw_request():
    request = _request()

    with pytest.raises(NotFoundError):
        withdraw_leave_request(request_id=request.pk, actor=_actor(202))

    request.refresh_from_db()
    assert request.status == LeaveRequest.Status.PENDING_UNIT_HEAD
    assert request.workflow_actions.count() == 0


@pytest.mark.parametrize(
    "status",
    (
        LeaveRequest.Status.DRAFT,
        LeaveRequest.Status.APPROVED,
        LeaveRequest.Status.REJECTED,
        LeaveRequest.Status.WITHDRAWN,
        LeaveRequest.Status.CANCELLED,
    ),
)
def test_nonpending_request_cannot_be_withdrawn(status):
    request = _request(status=status)

    with pytest.raises(ConflictError) as error:
        withdraw_leave_request(request_id=request.pk, actor=_actor(101))

    assert error.value.code == "request_not_withdrawable"
    assert request.workflow_actions.count() == 0


def test_duplicate_withdrawal_creates_one_successful_audit_action():
    request = _request()
    withdraw_leave_request(request_id=request.pk, actor=_actor(101))

    with pytest.raises(ConflictError):
        withdraw_leave_request(request_id=request.pk, actor=_actor(101))

    assert request.workflow_actions.filter(action=LeaveWorkflowAction.Action.WITHDRAWN).count() == 1


def test_recommendation_advances_without_final_rejection_or_balance_post():
    request = _request()

    result = decide_leave_request(
        request_id=request.pk,
        actor=_actor(201),
        decision="NOT_RECOMMENDED",
        reason="Insufficient coverage",
    )

    result.refresh_from_db()
    first = result.approval_steps.get(sequence=1)
    action = result.workflow_actions.get()
    assert first.status == LeaveApprovalStep.StepStatus.COMPLETED
    assert first.decision == LeaveApprovalStep.Decision.NOT_RECOMMENDED
    assert result.status == LeaveRequest.Status.PENDING_FINAL_DECISION
    assert result.status != LeaveRequest.Status.REJECTED
    assert action.action == LeaveWorkflowAction.Action.UNIT_HEAD_NOT_RECOMMENDED


def test_establishment_processing_advances_to_final_sanction():
    request = _request(with_steps=False)
    for sequence, role_code, assigned_user_id in (
        (1, "UNIT_HEAD", 201),
        (2, "ESTABLISHMENT", 202),
        (3, "SANCTIONING_AUTHORITY", 203),
    ):
        LeaveApprovalStep.objects.create(
            request=request,
            sequence=sequence,
            role_code=role_code,
            assigned_user_id=assigned_user_id,
        )

    recommended = decide_leave_request(
        request_id=request.pk,
        actor=_actor(201),
        decision="RECOMMENDED",
    )
    processed = decide_leave_request(
        request_id=request.pk,
        actor=_actor(202),
        decision="PROCESSED",
    )

    assert recommended.status == LeaveRequest.Status.PENDING_ESTABLISHMENT
    assert processed.status == LeaveRequest.Status.PENDING_FINAL_DECISION
    assert processed.workflow_actions.order_by("id").last().action == (
        LeaveWorkflowAction.Action.ESTABLISHMENT_PROCESSED
    )


def test_unassigned_actor_cannot_recommend():
    request = _request()

    with pytest.raises(PermissionDeniedError):
        decide_leave_request(request_id=request.pk, actor=_actor(203), decision="RECOMMENDED")

    request.refresh_from_db()
    assert request.status == LeaveRequest.Status.PENDING_UNIT_HEAD
    assert request.workflow_actions.count() == 0


def test_decision_after_withdrawal_is_rejected_without_another_action():
    request = _request()
    withdraw_leave_request(request_id=request.pk, actor=_actor(101))
    action_count = request.workflow_actions.count()

    with pytest.raises(ConflictError) as error:
        decide_leave_request(request_id=request.pk, actor=_actor(201), decision="RECOMMENDED")

    request.refresh_from_db()
    assert error.value.code == "request_not_actionable"
    assert request.status == LeaveRequest.Status.WITHDRAWN
    assert request.workflow_actions.count() == action_count


def test_final_approval_fails_closed_without_atomic_balance_posting():
    request = _request()
    request.status = LeaveRequest.Status.PENDING_FINAL_DECISION
    request.save(update_fields=["status"])
    first = request.approval_steps.get(sequence=1)
    first.status = LeaveApprovalStep.StepStatus.COMPLETED
    first.decision = LeaveApprovalStep.Decision.RECOMMENDED
    first.save(update_fields=["status", "decision"])
    step = request.approval_steps.get(sequence=2)

    with pytest.raises(ELMDependencyUnavailable):
        decide_leave_request(
            request_id=request.pk, actor=_actor(step.assigned_user_id), decision="APPROVED"
        )

    request.refresh_from_db()
    assert request.status == LeaveRequest.Status.PENDING_FINAL_DECISION
    assert request.workflow_actions.count() == 0
    assert request.approval_steps.get(sequence=2).status == LeaveApprovalStep.StepStatus.PENDING


def test_final_rejection_is_recorded_without_balance_mutation():
    request = _request()
    request.status = LeaveRequest.Status.PENDING_FINAL_DECISION
    request.save(update_fields=["status"])
    first = request.approval_steps.get(sequence=1)
    first.status = LeaveApprovalStep.StepStatus.COMPLETED
    first.decision = LeaveApprovalStep.Decision.RECOMMENDED
    first.save(update_fields=["status", "decision"])
    step = request.approval_steps.get(sequence=2)

    result = decide_leave_request(
        request_id=request.pk, actor=_actor(step.assigned_user_id), decision="REJECTED"
    )

    result.refresh_from_db()
    assert result.status == LeaveRequest.Status.REJECTED
    assert result.workflow_actions.get().action == LeaveWorkflowAction.Action.REJECTED


def test_substitute_acceptance_gates_approval_routing():
    request = _request(status=LeaveRequest.Status.PENDING_SUBSTITUTE)
    assignment = SubstituteAssignment.objects.create(
        request=request, sequence=1, nominee_user_id=303
    )

    result = respond_to_substitute_assignment(
        request_id=request.pk, actor=_actor(303), decision="ACCEPTED"
    )

    result.refresh_from_db()
    assignment.refresh_from_db()
    assert assignment.status == SubstituteAssignment.Status.ACCEPTED
    assert assignment.responded_at is not None
    assert result.status == LeaveRequest.Status.PENDING_UNIT_HEAD


def test_director_substitute_acceptance_routes_to_self_sanction():
    request = _request(status=LeaveRequest.Status.PENDING_SUBSTITUTE, with_steps=False)
    LeaveApprovalStep.objects.create(
        request=request,
        sequence=1,
        role_code="DIRECTOR_SELF_SANCTION",
        assigned_user_id=request.user_id,
    )
    SubstituteAssignment.objects.create(
        request=request,
        sequence=1,
        nominee_user_id=303,
    )

    result = respond_to_substitute_assignment(
        request_id=request.pk,
        actor=_actor(303),
        decision="ACCEPTED",
    )

    assert result.status == LeaveRequest.Status.PENDING_DIRECTOR_SANCTION


def test_substitute_decline_requires_applicant_action():
    request = _request(status=LeaveRequest.Status.PENDING_SUBSTITUTE)
    SubstituteAssignment.objects.create(request=request, sequence=1, nominee_user_id=303)

    result = respond_to_substitute_assignment(
        request_id=request.pk, actor=_actor(303), decision="DECLINED"
    )

    assert result.status == LeaveRequest.Status.APPLICANT_ACTION_REQUIRED
    with pytest.raises(ConflictError):
        decide_leave_request(request_id=request.pk, actor=_actor(201), decision="RECOMMENDED")


def test_replacement_substitute_is_allowed_only_after_decline(monkeypatch):
    request = _request(status=LeaveRequest.Status.APPLICANT_ACTION_REQUIRED)
    SubstituteAssignment.objects.create(
        request=request,
        sequence=1,
        nominee_user_id=303,
        status=SubstituteAssignment.Status.DECLINED,
    )
    monkeypatch.setattr("modules.elm.services.workflow._validate_nominee", lambda **kwargs: None)

    result = nominate_replacement_substitute(
        request_id=request.pk, actor=_actor(101), nominee_user_id=304
    )

    result.refresh_from_db()
    assert result.status == LeaveRequest.Status.PENDING_SUBSTITUTE
    assert list(
        result.substitute_assignments.order_by("sequence").values_list("nominee_user_id", "status")
    ) == [(303, "DECLINED"), (304, "PENDING")]


def test_second_substitute_decline_cannot_start_another_replacement_loop(monkeypatch):
    request = _request(status=LeaveRequest.Status.APPLICANT_ACTION_REQUIRED)
    SubstituteAssignment.objects.create(
        request=request,
        sequence=1,
        nominee_user_id=303,
        status=SubstituteAssignment.Status.DECLINED,
    )
    SubstituteAssignment.objects.create(
        request=request,
        sequence=2,
        nominee_user_id=304,
        status=SubstituteAssignment.Status.DECLINED,
    )
    monkeypatch.setattr("modules.elm.services.workflow._validate_nominee", lambda **kwargs: None)

    with pytest.raises(ConflictError) as error:
        nominate_replacement_substitute(
            request_id=request.pk,
            actor=_actor(101),
            nominee_user_id=305,
        )

    request.refresh_from_db()
    assert error.value.code == "replacement_not_allowed"
    assert request.status == LeaveRequest.Status.APPLICANT_ACTION_REQUIRED
    assert request.substitute_assignments.count() == 2
