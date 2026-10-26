import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.elm.models import Employee, Unit


@pytest.fixture
def elm_people(db):
    users = [
        UserRef.objects.create(user_id=i, username=f"u{i}", display_name=f"User {i}", kind="staff")
        for i in range(1, 7)
    ]
    employees = [
        Employee.objects.create(user=u, eid=f"E{i}", name=u.display_name, is_faculty=i == 5)
        for i, u in zip(range(1, 7), users, strict=True)
    ]
    unit = Unit.objects.create(name="Unit", head=employees[1])
    employees[0].unit = unit
    employees[0].save(update_fields=["unit"])
    return employees


@pytest.fixture
def elm_client(stub_iam, elm_people):
    def make(employee, *, role="employee", modules=("elm_leave",)):
        stub_iam(
            make_session(
                user_id=employee.user_id,
                kind="staff",
                active_role=role,
                roles=(role,),
                modules=modules,
            )
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        return client

    return make
