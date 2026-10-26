from types import SimpleNamespace
from modules.leave.api.views import LeaveBalanceViewSet, LeaveRequestViewSet
from modules.leave.serializers import LeaveRequestSerializer


def test_employee_balance_queryset():
    principal = SimpleNamespace(username="alice", has_permission=lambda code: False)
    view = LeaveBalanceViewSet()
    view.request = SimpleNamespace(principal=principal)
    sql, params = view.get_queryset().query.sql_with_params()
    assert "alice" in params


def test_hr_request_queryset():
    principal = SimpleNamespace(username="hr", has_permission=lambda code: code == "leave_cell.requests.view_all")
    view = LeaveRequestViewSet()
    view.request = SimpleNamespace(principal=principal)
    assert view.get_queryset().query.where.children == []


def test_serializer_forged_fields():
    data = {
        "leave_type": "CL",
        "start_date": "2024-01-01",
        "end_date": "2024-01-05",
        "reason": "vacation",
        "employee_id": "alice",
        "status": "approved",
    }
    serializer = LeaveRequestSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    validated = serializer.validated_data
    assert "employee_id" not in validated
    assert "status" not in validated
    assert validated["leave_type"] == "CL"


def test_missing_username_balance_scope():
    # When principal has no username, queryset should be empty
    principal = SimpleNamespace(username=None, has_permission=lambda code: False)
    view = LeaveBalanceViewSet()
    view.request = SimpleNamespace(principal=principal)
    assert view.get_queryset().query.is_empty()


def test_http_method_names():
    # LeaveRequestViewSet should only allow GET and POST
    assert LeaveRequestViewSet.http_method_names == ["get", "post"]
