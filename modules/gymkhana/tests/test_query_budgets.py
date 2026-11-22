import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.gymkhana.models.club import Club
from modules.gymkhana.selectors.clubs import list_clubs

pytestmark = pytest.mark.django_db


def test_club_list_query_count_does_not_grow_per_row(stub_iam):
    principal = type("Principal", (), {"id": 1, "is_admin": True, "is_staff": True})()
    Club.objects.bulk_create([
        Club(name=f"Small-{i}", category="Sports", faculty_councillor_id=200 + i)
        for i in range(3)
    ])
    with CaptureQueriesContext(connection) as small:
        list(list_clubs(principal))

    Club.objects.bulk_create([
        Club(name=f"Large-{i}", category="Sports", faculty_councillor_id=300 + i)
        for i in range(20)
    ])
    with CaptureQueriesContext(connection) as large:
        list(list_clubs(principal))

    assert len(large) <= len(small) + 2
