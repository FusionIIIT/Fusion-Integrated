from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import VisitLog
from modules.vms.tests import factories as f

HOST, ADMIN, OTHER = 2001, 3002, 2999
HOST_PERMS = ("vms.request.decide",)
ADMIN_PERMS = ("vms.extension.decide",)


@pytest.fixture(autouse=True)
def _policy(db):
    f.make_published_policy(version=1, max_visit_hours=8)


@pytest.fixture
def host():
    return f.make_actor("faculty", permissions=HOST_PERMS, user_id=HOST)


@pytest.fixture
def other_host():
    return f.make_actor("faculty", permissions=HOST_PERMS, user_id=OTHER)


@pytest.fixture
def admin():
    now = timezone.now()
    f.make_role_assignment(user_id=ADMIN, role="admin", starts_at=now - timedelta(days=365),
                           ends_at=now + timedelta(days=365))
    return f.make_actor("staff", permissions=ADMIN_PERMS, user_id=ADMIN)


def on_site_pass(hours=2, on_site=True):
    """Approved request + active pass of `hours` from now (+ open check-in)."""
    now = timezone.now()
    vr = f.make_visit_request(status="approved", host_user_id=HOST, scheduled_start=now,
                              scheduled_end=now + timedelta(hours=hours))
    vp = f.make_visit_pass(visit_request=vr, valid_from=now,
                           valid_until=now + timedelta(hours=hours))
    if on_site:
        f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_IN)
    return vp
