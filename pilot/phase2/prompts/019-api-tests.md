Phase 1 shipped no API tests. Write modules/leave/tests/test_api.py with pytest tests that call the real API through Fusion's permission gates. The repository's conftest.py (read-only) provides the `stub_iam` fixture (an in-memory fake of the IAM) and the function `make_session`. A test logs in as a person like this:

from rest_framework.test import APIClient
from conftest import make_session

def client_for(stub_iam, user_id, permissions, kind="staff"):
    stub_iam(make_session(user_id=user_id, permissions=permissions, modules=("leave",), kind=kind, roles=("employee",), active_role="employee"))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c

Use `pytestmark = pytest.mark.django_db`. Create reporting lines with ReportingLine.objects.create(user_id=..., unit_head_id=..., establishment_id=None, sanctioning_authority_id=...). Use dates in the future that start on a Monday: `start = date.today() + timedelta(days=21 - date.today().weekday())`. The base URL is "/api/v1/leave/". Employee permissions: ("leave.application.apply", "leave.application.view_own", "leave.substitute.respond"); Unit Head: ("leave.application.review",); Leave Administrator: ("leave.admin.manage",).

Write one small test function for each of these (named after the rule):
1. test_withdraw_pending_request (BR-EL-022): apply CL, POST applications/<id>/withdraw/ -> 200 and status "withdrawn"; withdrawing again -> 404.
2. test_cancellation_restores_balance (BR-EL-023): apply 2 days of CL, the unit head approves it (decision "approve"), the CL balance shows used "2.0"; the owner POSTs applications/<id>/cancel/ -> 200 with kind "cancellation"; the unit head approves that cancellation; the original application's status is "cancelled" and the CL balance's used is back to "0.0".
3. test_balances_for_staff_and_faculty (BR-EL-005/006): GET balances/ returns the categories CL, RH, SCL, EL, COL for kind "staff" and CL, RH, SCL, COL, VL for kind "faculty".
4. test_reporting_lines_admin_only (EL-UC-014): PUT reporting-lines/<user_id>/ {"unit_head_id": 201} as the Leave Administrator -> 200, then GET -> 200 with unit_head_id 201; the same PUT as an employee -> 403.
5. test_wrong_decision_for_stage_is_400 (BR-EL-016): for a pending CL at the unit head, decision "recommended" -> 400.
6. test_unknown_application_is_404: GET applications/999999/ -> 404.

Import only from datetime, pytest, rest_framework.test, conftest and modules.leave.models. Write the whole file. Do not ask for more files.
