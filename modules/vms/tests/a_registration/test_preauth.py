"""Host pre-authorisation management (CFR-011)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.models import Alert, AuditLog, PreAuthorization
from modules.vms.services import preauth
from modules.vms.tests import factories as f
from modules.vms.tests.a_registration.conftest import HOST_ID

pytestmark = pytest.mark.django_db


def _data(**over):
    d = {"full_name": "Ravi Kumar", "phone": "9876543210", "email": "ravi@example.com",
         "id_doc_type": "passport", "id_doc_number": "P1234567",
         "valid_until": timezone.now() + timedelta(days=30), "max_visits": 3}
    d.update(over)
    return d


def test_create_audits_and_stores_grant(host):
    z = f.make_zone()
    pa = preauth.create(host_actor=host, data=_data(zones=[z]))
    assert (pa.host_user_id, pa.max_visits, pa.used_visits) == (HOST_ID, 3, 0)
    assert list(pa.zones.all()) == [z]
    assert AuditLog.objects.filter(action="vms.preauth.created").exists()


def test_valid_until_capped_at_one_year(host):
    with pytest.raises(BadRequestError) as e:
        preauth.create(host_actor=host,
                       data=_data(valid_until=timezone.now() + timedelta(days=400)))
    assert e.value.code == "validity_too_long"


def test_past_or_inverted_window_rejected(host):
    with pytest.raises(BadRequestError):
        preauth.create(host_actor=host, data=_data(valid_until=timezone.now()
                                                   - timedelta(days=1)))


def test_restricted_zone_cannot_be_preauthorised(host):
    z = f.make_zone(is_restricted=True)
    with pytest.raises(BadRequestError) as e:
        preauth.create(host_actor=host, data=_data(zones=[z]))
    assert e.value.code == "zone_not_allowed"


def test_blacklisted_visitor_cannot_be_preauthorised(host):
    v = f.make_blacklist_version(status="published", published_at=timezone.now())
    f.make_blacklist_entry(version=v, id_doc_number="P1234567")
    with pytest.raises(BadRequestError) as e:
        preauth.create(host_actor=host, data=_data())
    assert e.value.code == "visitor_blacklisted"
    assert not PreAuthorization.objects.exists() and Alert.objects.exists()


def test_bad_document_rejected(host):
    with pytest.raises(BadRequestError):
        preauth.create(host_actor=host, data=_data(id_doc_type="library_card"))


def test_non_host_cannot_create():
    with pytest.raises(PermissionDeniedError):
        preauth.create(host_actor=f.make_actor(kind="student"), data=_data())


def test_creation_does_not_overwrite_existing_visitor_master_data(host):
    person = f.make_visitor(id_doc_type="passport", id_doc_number="P1234567",
                            full_name="Original Name")
    preauth.create(host_actor=host, data=_data())
    person.refresh_from_db()
    assert person.full_name == "Original Name"


def test_revoke_owner_only_and_once(host):
    pa = f.make_pre_authorization(host_user_id=HOST_ID)
    other = f.make_pre_authorization(host_user_id=2002)
    with pytest.raises(NotFoundError):
        preauth.revoke(host_actor=host, preauth_id=other.pk)
    assert preauth.revoke(host_actor=host, preauth_id=pa.pk).revoked_at is not None
    with pytest.raises(ConflictError):
        preauth.revoke(host_actor=host, preauth_id=pa.pk)
