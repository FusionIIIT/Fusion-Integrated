"""Fixtures for the visit-lifecycle gap tests (patterns from d_walkin/ and i_duration/)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import VisitLog
from modules.vms.tests import factories as f

SEC, ADMIN, HOST = 3001, 3002, 2001
SEC_PERMS = ("vms.walkin.register", "vms.gate.operate", "vms.monitor.view")


@pytest.fixture(autouse=True)
def _policy(db):
    f.make_published_policy(version=1)


@pytest.fixture
def security():
    f.make_role_assignment(user_id=SEC, role="security")
    return f.make_actor("staff", permissions=SEC_PERMS, user_id=SEC)


@pytest.fixture
def admin():
    f.make_role_assignment(user_id=ADMIN, role="admin")
    return f.make_actor("staff", permissions=("vms.walkin.contingency_decide",
                                              "vms.pass.terminate"), user_id=ADMIN)


@pytest.fixture
def host():
    return f.make_actor("faculty", permissions=("vms.request.decide", "vms.pass.terminate"),
                        user_id=HOST)


def walkin_data(**over):
    d = {"full_name": "Wanda Walker", "phone": "9123456789", "id_doc_type": "passport",
         "id_doc_number": "WK123456", "purpose": "Delivery"}
    d.update(over)
    return d


def on_site_pass(host_id=HOST, hours=4, **req):
    """Approved request with an active pass and an open check-in."""
    vr = f.make_visit_request(status="approved", host_user_id=host_id, **req)
    vp = f.make_visit_pass(visit_request=vr, valid_until=timezone.now() + timedelta(hours=hours))
    f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_IN)
    return vp
