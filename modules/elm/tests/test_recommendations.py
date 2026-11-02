
from datetime import date

import pytest

from core.api.exceptions import PermissionDeniedError
from modules.elm.domain.leave_rules import LeaveRuleError
from modules.elm.models import (
    LeaveApplication,
    LeaveApplicationStatus,
    LeaveType,
)
from modules.elm.services.recommendations import (
    NOT_RECOMMENDED,
    RECOMMENDED,
    recommend_leave_application,
)


UNIT_HEAD_ID = 902
FINAL_AUTHORITY_ID = 903
RECOMMEND_PERMISSION = "elm.leave_application.recommend"


class FakePrincipal:
    def __init__(self, user_id, permissions=()):
        self.user_id = user_id
        self.permissions = frozenset(permissions)

    def has_permission(self, code):
        return code in self.permissions


@pytest.fixture
def pending_el_request(db):
    return LeaveApplication.objects.create(
        user_id=801,
        leave_type=LeaveType.EL,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        requested_days=2,
        status=LeaveApplicationStatus.PENDING,
        assigned_unit_head_user_id=UNIT_HEAD_ID,
        assigned_final_authority_user_id=FINAL_AUTHORITY_ID,
        workflow_stage="awaiting_unit_head_review",
    )


@pytest.fixture
def unit_head():
    return FakePrincipal(
        UNIT_HEAD_ID,
        {RECOMMEND_PERMISSION},
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "recommendation",
    [RECOMMENDED, NOT_RECOMMENDED],
)
def test_recommendation_forwards_to_final_authority(
    pending_el_request,
    unit_head,
    recommendation,
):
    application = recommend_leave_application(
        actor=unit_head,
        application_id=pending_el_request.pk,
        recommendation=recommendation,
        remarks="Reviewed by Unit Head.",
    )

    assert application.status == LeaveApplicationStatus.PENDING
    assert application.unit_head_recommendation == recommendation
    assert application.unit_head_recommendation_remarks == (
        "Reviewed by Unit Head."
    )
    assert application.unit_head_recommended_by_user_id == UNIT_HEAD_ID
    assert application.workflow_stage == "awaiting_final_sanction"


@pytest.mark.django_db
def test_establishment_required_routes_to_establishment(
    pending_el_request,
    unit_head,
):
    pending_el_request.establishment_required = True
    pending_el_request.save(update_fields=["establishment_required"])

    application = recommend_leave_application(
        actor=unit_head,
        application_id=pending_el_request.pk,
        recommendation=RECOMMENDED,
    )

    assert application.workflow_stage == "awaiting_establishment"
    assert application.status == LeaveApplicationStatus.PENDING


@pytest.mark.django_db
def test_unassigned_user_cannot_recommend(
    pending_el_request,
):
    actor = FakePrincipal(
        904,
        {RECOMMEND_PERMISSION},
    )

    with pytest.raises(PermissionDeniedError):
        recommend_leave_application(
            actor=actor,
            application_id=pending_el_request.pk,
            recommendation=RECOMMENDED,
        )


@pytest.mark.django_db
def test_user_without_recommend_permission_is_denied(
    pending_el_request,
):
    actor = FakePrincipal(UNIT_HEAD_ID)

    with pytest.raises(PermissionDeniedError):
        recommend_leave_application(
            actor=actor,
            application_id=pending_el_request.pk,
            recommendation=RECOMMENDED,
        )


@pytest.mark.django_db
def test_cl_cannot_use_higher_sanction_recommendation(
    pending_el_request,
    unit_head,
):
    pending_el_request.leave_type = LeaveType.CL
    pending_el_request.save(update_fields=["leave_type"])

    with pytest.raises(
        LeaveRuleError,
        match="higher-sanction",
    ):
        recommend_leave_application(
            actor=unit_head,
            application_id=pending_el_request.pk,
            recommendation=RECOMMENDED,
        )


@pytest.mark.django_db
def test_invalid_recommendation_is_rejected(
    pending_el_request,
    unit_head,
):
    with pytest.raises(
        LeaveRuleError,
        match="Recommendation must be",
    ):
        recommend_leave_application(
            actor=unit_head,
            application_id=pending_el_request.pk,
            recommendation="approved",
        )
