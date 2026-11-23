import pytest

from modules.directory import contracts
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def test_get_active_student_ids_returns_sorted_active_students():
    UserRef.objects.create(user_id=202, username="21bcs002", display_name="Bob", kind="student", is_active=True)
    UserRef.objects.create(user_id=101, username="21bcs001", display_name="Alice", kind="student", is_active=True)
    UserRef.objects.create(user_id=303, username="21bcs003", display_name="Charlie", kind="student", is_active=False)
    UserRef.objects.create(user_id=404, username="fac001", display_name="Dr. Smith", kind="faculty", is_active=True)

    result = contracts.get_active_student_ids()
    assert result == [101, 202]
