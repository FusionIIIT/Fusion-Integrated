"""HR service tests."""
import datetime
import pytest

from core.api.exceptions import ConflictError
from modules.hr.models import Department, EmploymentContract
from modules.hr.services import hr as services


@pytest.fixture
def dept(db):
    return Department.objects.create(name="CSE", code="CSE")


@pytest.mark.django_db
def test_create_department(db):
    dept = services.create_department(
        name="ECE", code="ECE", actor_user_id=1,
    )
    assert dept.code == "ECE"
    assert dept.name == "ECE"


@pytest.mark.django_db
def test_create_contract(dept):
    c = services.create_contract(
        user_id=2001, department_id=dept.pk, title="Lecturer",
        kind="permanent", starts_on=datetime.date(2025, 1, 1),
        actor_user_id=1,
    )
    assert c.status == "active"
    assert c.user_id == 2001


@pytest.mark.django_db
def test_duplicate_active_contract_rejected(dept):
    services.create_contract(
        user_id=2002, department_id=dept.pk, title="Lecturer",
        kind="permanent", starts_on=datetime.date(2025, 1, 1),
        actor_user_id=1,
    )
    with pytest.raises(ConflictError, match="already has an active contract"):
        services.create_contract(
            user_id=2002, department_id=dept.pk, title="Prof",
            kind="permanent", starts_on=datetime.date(2025, 6, 1),
            actor_user_id=1,
        )


@pytest.mark.django_db
def test_end_contract(dept):
    c = services.create_contract(
        user_id=2003, department_id=dept.pk, title="Lecturer",
        kind="permanent", starts_on=datetime.date(2025, 1, 1),
        actor_user_id=1,
    )
    ended = services.end_contract(
        contract_id=c.pk, ends_on=datetime.date(2025, 12, 31),
        reason="Resignation", actor_user_id=1,
    )
    assert ended.status == "ended"
    assert ended.end_reason == "Resignation"
