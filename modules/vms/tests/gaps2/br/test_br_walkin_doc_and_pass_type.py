"""Gap tests: BR-187 (walk-in ID document types) and BR-211 (contingency pass type)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import VisitPass, VisitRequest
from modules.vms.services import walkin
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db

SEC, ADMIN, HOST = 3001, 3002, 2001


@pytest.fixture(autouse=True)
def _policy():
    f.make_published_policy(version=1)


@pytest.fixture
def security():
    f.make_role_assignment(user_id=SEC, role="security")
    return f.make_actor("staff", permissions=("vms.walkin.register", "vms.gate.operate"),
                        user_id=SEC)


@pytest.fixture
def admin():
    f.make_role_assignment(user_id=ADMIN, role="admin")
    return f.make_actor("staff", permissions=("vms.walkin.contingency_decide",),
                        user_id=ADMIN)


def _data(**over):
    d = {"full_name": "Wanda Walker", "phone": "9123456789", "id_doc_type": "passport",
         "id_doc_number": "WK123456", "purpose": "Delivery"}
    d.update(over)
    return d


@pytest.mark.parametrize("doc_type", ["passport", "aadhaar", "driving_licence", "voter_id"])
def test_br_187_walkin_every_supported_document_type_accepted(security, doc_type):
    """VMS-BR-187: walk-in registration accepts each supported ID document type."""
    vr = walkin.register(security_actor=security, data=_data(id_doc_type=doc_type),
                         host_user_id=HOST)
    assert vr.status == "pending" and vr.visitor.id_doc_type == doc_type


def test_br_211_contingency_approved_walkin_pass_is_walk_in_type(security, admin):
    """VMS-BR-211: a contingency-approved walk-in pass is classified WALK_IN."""
    vr = walkin.register(security_actor=security, data=_data(), host_user_id=HOST)
    VisitRequest.objects.filter(pk=vr.pk).update(
        created_at=timezone.now() - timedelta(hours=1))
    _, vp = walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="approve")
    assert vp.pass_type == VisitPass.PassType.WALK_IN
