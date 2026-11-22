import pytest
from django.http import Http404

from modules.pms.models.application import ApplicationStatus, PatentApplication
from modules.pms.selectors.scoping import get_application_scoped, visible_applications


@pytest.mark.django_db
def test_applicant_scoping():
    app1 = PatentApplication.objects.create(
        application_no="PMS-2026-0001",
        title="App by Student 1",
        abstract="Abs",
        applicant_user_id=101,
        status=ApplicationStatus.DRAFT,
    )
    app2 = PatentApplication.objects.create(
        application_no="PMS-2026-0002",
        title="App by Faculty 2",
        abstract="Abs",
        applicant_user_id=202,
        status=ApplicationStatus.DRAFT,
    )

    # User 101 acting as student can only see app1
    qs = visible_applications(user_id=101, roles=["student"])
    assert app1 in qs
    assert app2 not in qs

    # Accessing app2 raises Http404 (NEVER 403)
    with pytest.raises(Http404):
        get_application_scoped(app2.id, user_id=101, roles=["student"])

    # Coordinator can see both
    coord_qs = visible_applications(user_id=999, roles=["pms_coordinator"])
    assert app1 in coord_qs
    assert app2 in coord_qs
