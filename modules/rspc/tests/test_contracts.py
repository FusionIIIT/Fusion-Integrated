from decimal import Decimal

import pytest
from django.utils import timezone

from modules.rspc.contracts import get_faculty_project_summaries
from modules.rspc.models import Project


@pytest.mark.django_db
def test_faculty_project_summaries():
    today = timezone.now().date()
    # No user ids
    res = get_faculty_project_summaries([])
    assert res == {}

    # Create active and non-active projects
    Project.objects.create(
        user_id=101,
        project_code="PRJ-101-A",
        project_type="sponsored",
        title="Project A",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="DST/101/A",
        sanction_date=today,
        start_date=today,
        end_date=today,
        sanctioned_amount=Decimal("500000.00"),
        status="active",
    )
    Project.objects.create(
        user_id=101,
        project_code="PRJ-101-B",
        project_type="sponsored",
        title="Project B",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="DST/101/B",
        sanction_date=today,
        start_date=today,
        end_date=today,
        sanctioned_amount=Decimal("300000.00"),
        status="active",
    )
    Project.objects.create(
        user_id=101,
        project_code="PRJ-101-C",
        project_type="sponsored",
        title="Project C",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="DST/101/C",
        sanction_date=today,
        start_date=today,
        end_date=today,
        sanctioned_amount=Decimal("200000.00"),
        status="sanctioned",  # Not active
    )

    summaries = get_faculty_project_summaries([101, 102])
    assert 101 in summaries
    assert summaries[101].active_project_count == 2
    assert summaries[101].total_sanctioned_amount == Decimal("800000.00")

    assert 102 in summaries
    assert summaries[102].active_project_count == 0
    assert summaries[102].total_sanctioned_amount == Decimal("0.00")
