import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveRequest, LeaveType


def _client(stub_iam, *, permissions=(), modules=("elm",), uid=1001, role="faculty"):
    stub_iam(
        make_session(
            user_id=uid,
            permissions=permissions,
            modules=modules,
            roles=(role,),
            active_role=role,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token elm-test-token")
    return client


def test_elm_endpoints_require_a_module_grant(stub_iam):
    client = _client(stub_iam, permissions=("elm.leave.view_self",), modules=())

    response = client.get("/api/v1/elm/leaves/")

    assert response.status_code == 403


def test_elm_endpoints_require_the_specific_permission(stub_iam):
    client = _client(stub_iam)

    response = client.get("/api/v1/elm/leaves/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_employee_list_is_scoped_to_the_authenticated_user(stub_iam):
    for user_id in ("1001", "2002"):
        LeaveRequest.objects.create(
            applicant_user_id=user_id,
            leave_type=LeaveType.CASUAL,
            start_date="2026-10-27",
            end_date="2026-10-27",
            duration_days="1.0",
            reason="Personal work",
        )
    client = _client(stub_iam, permissions=("elm.leave.view_self",))

    response = client.get("/api/v1/elm/leaves/")

    assert response.status_code == 200
    assert [row["applicant_user_id"] for row in response.data] == ["1001"]


@pytest.mark.django_db
def test_director_queue_only_contains_authority_stage_requests(stub_iam):
    from modules.elm.models import LeaveStatus

    unit_head_request = LeaveRequest.objects.create(
        applicant_user_id="1001",
        leave_type=LeaveType.CASUAL,
        start_date="2026-10-27",
        end_date="2026-10-27",
        duration_days="1.0",
        reason="Unit Head stage",
        status=LeaveStatus.PENDING_UNIT_HEAD,
        current_approver_role="unit_head",
    )
    authority_request = LeaveRequest.objects.create(
        applicant_user_id="1002",
        leave_type=LeaveType.CASUAL,
        start_date="2026-10-28",
        end_date="2026-10-28",
        duration_days="1.0",
        reason="Authority stage",
        status=LeaveStatus.PENDING_AUTHORITY,
        current_approver_role="director",
    )
    client = _client(
        stub_iam,
        permissions=("elm.leave.approve",),
        role="director",
    )

    response = client.get("/api/v1/elm/approvals/")

    assert response.status_code == 200
    assert [row["id"] for row in response.data] == [str(authority_request.id)]
    assert str(unit_head_request.id) not in [row["id"] for row in response.data]
