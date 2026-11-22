"""Spec tests for strategy FR, module rspc: CFR-021 to CFR-029 (notifications, integration, roles, scope, updates, admin).

One test per design case in docs/09-rspc/spec-tests/FR_DESIGN.json. Each test names its
test_id and source_id. Cases the shipped RSPC interfaces cannot express are skipped with
reason "NOT_AUTOMATED: <reason>".
"""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import (
    Project,
    Proposal,
)
from modules.rspc.registry import ROLE_GRANTS
from modules.rspc.services import (
    finance as finance_services,
)
from modules.rspc.services import (
    project as project_services,
)
from modules.rspc.services import (
    proposal as proposal_services,
)

URL = "/api/v1/rspc"
TODAY = datetime.date.today()
F1, F2, HOD, DEAN = 101, 102, 50, 100


def _client_for(stub_iam, session):
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


def _as(stub_iam, user_id, role):
    """Client acting as `user_id` holding `role` (grants taken from the RSPC registry).

    The IAM stub serves one session at a time, so build the client right before use.
    """
    session = make_session(
        user_id=user_id,
        permissions=ROLE_GRANTS[role],
        modules=("rspc",),
        kind="faculty",
        roles=(role,),
        active_role=role,
    )
    return _client_for(stub_iam, session)


def _payload(**overrides):
    data = {
        "title": "Spec Proposal",
        "proposal_type": "sponsored_research",
        "department": "CSE",
        "funding_agency": "DST",
        "proposed_budget": "1000000.00",
        "summary": "Spec test proposal.",
    }
    data.update(overrides)
    return data


def _proposal(user_id, kind, title):
    return proposal_services.create_proposal(
        user_id=user_id,
        title=title,
        proposal_type=kind,
        department="CSE",
        funding_agency="DST",
        proposed_budget=Decimal("1000000.00"),
    )


def _submitted(user_id, kind, title):
    prop = _proposal(user_id, kind, title)
    return proposal_services.submit_proposal(proposal=prop, actor_user_id=user_id)


def _endorsed(user_id, kind, title, hod_id=HOD):
    prop = _submitted(user_id, kind, title)
    return proposal_services.endorse_proposal(proposal=prop, actor_user_id=hod_id)


def _project(user_id, code, status="active", kind="sponsored"):
    project = project_services.sanction_and_register_project(
        user_id=user_id,
        project_code=code,
        project_type=kind,
        title=f"Project {code}",
        department="CSE",
        funding_agency="DST",
        sanction_order_no=f"ORD/{code}",
        sanction_date=TODAY,
        start_date=TODAY,
        end_date=TODAY + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("3000000.00"),
    )
    if status != "sanctioned":
        Project.objects.filter(pk=project.pk).update(status=status)
        project.refresh_from_db()
    return project


def _head(project, head_type, amount):
    return finance_services.allocate_budget_head(
        project=project,
        head_type=head_type,
        allocated_amount=Decimal(amount),
        actor_user_id=1,
    )


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_104():
    """TC-FR-104 | source RSPC-FR-026 (parent RSPC-CFR-021) | RSPC generates research-proposal review-stage notifications

    Action: Trigger the event: proposal reaches a review stage
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_105():
    """TC-FR-105 | source RSPC-FR-064 | RSPC generates pending progress report reminders

    Action: Trigger the event: progress report is pending
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_106():
    """TC-FR-106 | source RSPC-FR-065 | RSPC generates pending utilization report reminders

    Action: Trigger the event: utilization report is pending
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_107():
    """TC-FR-107 | source RSPC-FR-074 | RSPC generates proposal submission notifications

    Action: Trigger the event: proposal is submitted
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_108():
    """TC-FR-108 | source RSPC-FR-075 | RSPC generates proposal approval notifications

    Action: Trigger the event: proposal is approved
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_109():
    """TC-FR-109 | source RSPC-FR-076 | RSPC generates pending-action notifications

    Action: Trigger the event: an action is pending on a stakeholder
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_110():
    """TC-FR-110 | source RSPC-FR-077 | RSPC generates escalation notifications

    Action: Trigger the event: a request is escalated
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_111():
    """TC-FR-111 | source RSPC-FR-078 | RSPC generates reporting-deadline notifications

    Action: Trigger the event: a reporting deadline approaches
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_112():
    """TC-FR-112 | source RSPC-FR-079 | RSPC generates financial approval notifications

    Action: Trigger the event: a financial request is approved
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_113():
    """TC-FR-113 | source RSPC-FR-080 | RSPC generates compliance-requirement notifications

    Action: Trigger the event: a represented compliance requirement applies
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_114():
    """TC-FR-114 | source RSPC-FR-132 | RSPC generates proposal rejection notifications

    Action: Trigger the event: proposal is rejected
    Expected: A notification for the event is created for the relevant stakeholders
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_115():
    """TC-FR-115 | source RSPC-FR-081 | Notifications delivered via Fusion dashboard (BR-RSPC-061)

    Action: Trigger a supported event
    Expected: Notification appears on the recipient's Fusion dashboard
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_116():
    """TC-FR-116 | source RSPC-FR-082 | System-generated email notifications triggered (BR-RSPC-061)

    Action: Trigger a supported event
    Expected: An email notification event is handed to the email channel
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no notification creation or dashboard/email hand-off interface (no model, service, task or endpoint)')
def test_tc_fr_117():
    """TC-FR-117 | source RSPC-FR-099 | Notification delivery infrastructure is external

    Action: Trigger an event and inspect RSPC
    Expected: RSPC triggers the notification event only and offers no email delivery infrastructure itself
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no cross-module integration or external data-intake interface for this data')
def test_tc_fr_118():
    """TC-FR-118 | source RSPC-FR-083 (parent RSPC-CFR-022) | RSPC exchanges info with other Fusion modules where configured (BR-RSPC-045)

    Action: Trigger an RSPC workflow event
    Expected: Information is exchanged, referenced or recorded through the configured integration
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no cross-module integration or external data-intake interface for this data')
def test_tc_fr_119():
    """TC-FR-119 | source RSPC-FR-083 not configured | No exchange where integration not configured

    Action: Trigger the event
    Expected: No exchange occurs
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no cross-module integration or external data-intake interface for this data')
def test_tc_fr_120():
    """TC-FR-120 | source RSPC-FR-084 | Submission tracking from external funding agency recorded

    Action: Receive submission tracking data
    Expected: Recorded in RSPC
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no cross-module integration or external data-intake interface for this data')
def test_tc_fr_121():
    """TC-FR-121 | source RSPC-FR-085 | Disbursement tracking from external funding agency recorded

    Action: Receive disbursement data
    Expected: Recorded in RSPC
    """
    raise NotImplementedError


@pytest.mark.skip(reason="NOT_AUTOMATED: RSPC has no external funding-agency submission-tracking records, so 'tracking records remain available' cannot be set up")
def test_tc_fr_122():
    """TC-FR-122 | source RSPC-FR-100 | RSPC does not own external agency processes (BR-RSPC-062)

    Action: Look for functionality to submit or decide on behalf of the agency
    Expected: No such capability exists; tracking records remain available
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_123(stub_iam):
    """TC-FR-123 | source RSPC-FR-086 (parent RSPC-CFR-023) | RBAC enforced for project data (BR-RSPC-048)

    Action: Each requests project data
    Expected: Permitted role gets data; others denied
    """

    project = _project(F1, "RSPC/FR/123", status="active")
    owner = _as(stub_iam, F1, "faculty")
    assert owner.get(f"{URL}/projects/{project.id}/").status_code == 200
    other = _as(stub_iam, F2, "faculty")
    assert other.get(f"{URL}/projects/{project.id}/").status_code == 404
    session = make_session(
        user_id=F1, permissions=ROLE_GRANTS["faculty"], modules=("placement_cell",),
        kind="faculty", roles=("faculty",), active_role="faculty",
    )
    no_grant = _client_for(stub_iam, session)
    assert no_grant.get(f"{URL}/projects/{project.id}/").status_code == 403


@pytest.mark.django_db
def test_tc_fr_124(stub_iam):
    """TC-FR-124 | source RSPC-FR-087 | Users restricted to actions permitted by RSPC roles (BR-RSPC-049)

    Action: Attempt an action reserved for Dean-RSPC
    Expected: Action denied
    """

    prop = _endorsed(F1, "sponsored_research", "Research proposal")
    client = _as(stub_iam, F2, "faculty")
    resp = client.post(f"{URL}/proposals/{prop.id}/approve/", data={}, format="json")
    assert resp.status_code == 403
    prop.refresh_from_db()
    assert prop.status == "endorsed_hod"
    assert prop.reviews.filter(action="approve").count() == 0


@pytest.mark.django_db
def test_tc_fr_125(stub_iam):
    """TC-FR-125 | source RSPC-FR-101 | RSPC does not own authentication or RBAC administration (BR-RSPC-063)

    Action: Look for RSPC functions for authentication or role administration
    Expected: None exist beyond RSPC role/action restrictions
    """

    from modules.rspc.api import urls as rspc_urls

    routes = [str(p.pattern).lower() for p in rspc_urls.urlpatterns]
    forbidden = ("login", "logout", "password", "token", "session", "signin", "role", "auth")
    offending = [r for r in routes if any(word in r for word in forbidden)]
    assert offending == []
    assert routes  # the module does expose its own (non-auth) endpoints


@pytest.mark.skip(reason='NOT_AUTOMATED: Role assignment is supplied by the external IAM service; RSPC has no interface that stores or exposes a role assignment')
def test_tc_fr_126():
    """TC-FR-126 | source RSPC-FR-091 (parent RSPC-CFR-024) | Role assignment info consumed (BR-RSPC-053)

    Action: Supply a role assignment for user U
    Expected: RSPC holds the role for U
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: Role assignment is supplied by the external IAM service; RSPC has no interface that stores or exposes a role assignment')
def test_tc_fr_127():
    """TC-FR-127 | source RSPC-FR-092 | Role reassignment info consumed (BR-RSPC-054)

    Action: Supply a reassignment
    Expected: RSPC holds the new role for U
    """
    raise NotImplementedError


@pytest.mark.django_db
def test_tc_fr_128(stub_iam):
    """TC-FR-128 | source RSPC-FR-093 | Role changes effective immediately (BR-RSPC-055)

    Action: Reassign role, U immediately retries actions
    Expected: New role permissions apply at once; old ones denied
    """

    prop = _endorsed(F2, "sponsored_research", "Research proposal", hod_id=HOD)
    user = 10
    # Before reassignment: the user is Faculty (may create, may not approve).
    old = _as(stub_iam, user, "faculty")
    assert old.post(f"{URL}/proposals/", data=_payload(), format="json").status_code == 201
    assert old.post(f"{URL}/proposals/{prop.id}/approve/", data={}, format="json").status_code == 403
    # Reassigned to Dean (RSPC): the very next requests use the new role.
    new = _as(stub_iam, user, "Dean (RSPC)")
    created = new.post(f"{URL}/proposals/", data=_payload(), format="json")
    assert created.status_code == 403
    assert Proposal.objects.filter(user_id=user).count() == 1
    approved = new.post(f"{URL}/proposals/{prop.id}/approve/", data={}, format="json")
    assert approved.status_code == 200
    assert approved.data["status"] == "approved_dean"


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no role-assignment log interface')
def test_tc_fr_129():
    """TC-FR-129 | source RSPC-FR-094 | Role assignments logged

    Action: Retrieve role log
    Expected: Assignment entry present
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no role-assignment log interface')
def test_tc_fr_130():
    """TC-FR-130 | source RSPC-FR-095 | Role reassignments logged

    Action: Retrieve role log
    Expected: Reassignment entry present
    """
    raise NotImplementedError


@pytest.mark.skip(reason="NOT_AUTOMATED: RSPC has no appointment records or statuses, so the 'remain available' half of the expected result cannot be set up")
def test_tc_fr_131():
    """TC-FR-131 | source RSPC-FR-096 (parent RSPC-CFR-025) | No HR/payroll processing (BR-RSPC-058)

    Action: Look for payroll or HR master-data processing
    Expected: None exists; appointment records and statuses remain available
    """
    raise NotImplementedError


@pytest.mark.skip(reason="NOT_AUTOMATED: RSPC has no financial-request approval record/status (approve endpoint is a stub), so the 'remain available' half of the expected result cannot be set up")
def test_tc_fr_132():
    """TC-FR-132 | source RSPC-FR-097 (parent RSPC-CFR-026) | No accounts payment execution (BR-RSPC-059)

    Action: Look for payment execution
    Expected: None exists; request, approval, status and transaction records remain available
    """
    raise NotImplementedError


@pytest.mark.skip(reason="NOT_AUTOMATED: RSPC has no procurement request or status tracking, so the 'remain available' half of the expected result cannot be set up")
def test_tc_fr_133():
    """TC-FR-133 | source RSPC-FR-098 (parent RSPC-CFR-027) | No procurement execution or stock operations (BR-RSPC-060)

    Action: Look for purchase or stock operations
    Expected: None exist; request and status tracking remain available
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no update (PUT/PATCH) endpoint for project details, milestones, progress or utilization; a refusal test would only observe 405 for lack of the feature')
def test_tc_fr_134():
    """TC-FR-134 | source RSPC-FR-103 (parent RSPC-CFR-028) | Faculty can update project details when lifecycle permits (BR-RSPC-065)

    Action: Update details
    Expected: Update persisted
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no update (PUT/PATCH) endpoint for project details, milestones, progress or utilization; a refusal test would only observe 405 for lack of the feature')
def test_tc_fr_135():
    """TC-FR-135 | source RSPC-FR-104 | Faculty can update project milestones when lifecycle permits (BR-RSPC-065)

    Action: Update milestones
    Expected: Update persisted
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no update (PUT/PATCH) endpoint for project details, milestones, progress or utilization; a refusal test would only observe 405 for lack of the feature')
def test_tc_fr_136():
    """TC-FR-136 | source RSPC-FR-105 | Faculty can update project progress information when lifecycle permits (BR-RSPC-065)

    Action: Update progress information
    Expected: Update persisted
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no update (PUT/PATCH) endpoint for project details, milestones, progress or utilization; a refusal test would only observe 405 for lack of the feature')
def test_tc_fr_137():
    """TC-FR-137 | source RSPC-FR-106 | Faculty can update project utilization information when lifecycle permits (BR-RSPC-065)

    Action: Update utilization information
    Expected: Update persisted
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no update (PUT/PATCH) endpoint for project details, milestones, progress or utilization; a refusal test would only observe 405 for lack of the feature')
def test_tc_fr_138():
    """TC-FR-138 | source RSPC-FR-103 lifecycle not permitting | Faculty cannot update project details when lifecycle does not permit

    Action: Attempt update of details
    Expected: Update is rejected and stored data unchanged
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no update (PUT/PATCH) endpoint for project details, milestones, progress or utilization; a refusal test would only observe 405 for lack of the feature')
def test_tc_fr_139():
    """TC-FR-139 | source RSPC-FR-104 lifecycle not permitting | Faculty cannot update project milestones when lifecycle does not permit

    Action: Attempt update of milestones
    Expected: Update is rejected and stored data unchanged
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no update (PUT/PATCH) endpoint for project details, milestones, progress or utilization; a refusal test would only observe 405 for lack of the feature')
def test_tc_fr_140():
    """TC-FR-140 | source RSPC-FR-105 lifecycle not permitting | Faculty cannot update project progress information when lifecycle does not permit

    Action: Attempt update of progress information
    Expected: Update is rejected and stored data unchanged
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC exposes no update (PUT/PATCH) endpoint for project details, milestones, progress or utilization; a refusal test would only observe 405 for lack of the feature')
def test_tc_fr_141():
    """TC-FR-141 | source RSPC-FR-106 lifecycle not permitting | Faculty cannot update project utilization information when lifecycle does not permit

    Action: Attempt update of utilization information
    Expected: Update is rejected and stored data unchanged
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no RSPC-Admin completeness/requirements verification or forwarding interface (admin role only holds project/fund view and manage grants)')
def test_tc_fr_142():
    """TC-FR-142 | source RSPC-FR-110 (parent RSPC-CFR-029) | RSPC Admin verifies completeness of research-project proposals

    Action: Admin verifies completeness of research-project proposals
    Expected: Completeness result recorded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no RSPC-Admin completeness/requirements verification or forwarding interface (admin role only holds project/fund view and manage grants)')
def test_tc_fr_143():
    """TC-FR-143 | source RSPC-FR-111 | RSPC Admin verifies completeness of consultancy records

    Action: Admin verifies completeness of consultancy records
    Expected: Completeness result recorded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no RSPC-Admin completeness/requirements verification or forwarding interface (admin role only holds project/fund view and manage grants)')
def test_tc_fr_144():
    """TC-FR-144 | source RSPC-FR-112 | RSPC Admin verifies completeness of project-based staff-appointment requests

    Action: Admin verifies completeness of project-based staff-appointment requests
    Expected: Completeness result recorded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no RSPC-Admin completeness/requirements verification or forwarding interface (admin role only holds project/fund view and manage grants)')
def test_tc_fr_145():
    """TC-FR-145 | source RSPC-FR-113 | RSPC Admin verifies completeness of fund-utilization and expenditure requests

    Action: Admin verifies completeness of fund-utilization and expenditure requests
    Expected: Completeness result recorded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no RSPC-Admin completeness/requirements verification or forwarding interface (admin role only holds project/fund view and manage grants)')
def test_tc_fr_146():
    """TC-FR-146 | source RSPC-FR-114 | RSPC Admin verifies completeness of procurement requests

    Action: Admin verifies completeness of procurement requests
    Expected: Completeness result recorded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no RSPC-Admin completeness/requirements verification or forwarding interface (admin role only holds project/fund view and manage grants)')
def test_tc_fr_147():
    """TC-FR-147 | source RSPC-FR-115 | RSPC Admin verifies completeness of project-closure records

    Action: Admin verifies completeness of project-closure records
    Expected: Completeness result recorded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no RSPC-Admin completeness/requirements verification or forwarding interface (admin role only holds project/fund view and manage grants)')
def test_tc_fr_148():
    """TC-FR-148 | source RSPC-FR-116 | RSPC Admin checks records against institutional and funding-agency requirements

    Action: Admin runs the requirements check
    Expected: Result of the check recorded against the record
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no RSPC-Admin completeness/requirements verification or forwarding interface (admin role only holds project/fund view and manage grants)')
def test_tc_fr_149():
    """TC-FR-149 | source RSPC-FR-117 eligible | RSPC Admin forwards eligible requests along the approval path

    Action: Admin forwards the request
    Expected: Request moves to the applicable approving authority
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no RSPC-Admin completeness/requirements verification or forwarding interface (admin role only holds project/fund view and manage grants)')
def test_tc_fr_150():
    """TC-FR-150 | source RSPC-FR-117 ineligible | Ineligible requests are not forwarded

    Action: Admin attempts to forward
    Expected: Request is not forwarded
    """
    raise NotImplementedError


@pytest.mark.skip(reason='NOT_AUTOMATED: RSPC has no RSPC-Admin completeness/requirements verification or forwarding interface (admin role only holds project/fund view and manage grants)')
def test_tc_fr_151():
    """TC-FR-151 | source RSPC-CFR-029 forwarding by type | Eligible requests of each type reach the applicable authority

    Action: Admin forwards each
    Expected: Each reaches its represented approving authority only
    """
    raise NotImplementedError
