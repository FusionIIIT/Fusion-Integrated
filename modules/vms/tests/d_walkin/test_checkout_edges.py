"""Check-out edge cases: bad credentials, unknown gate, invalid state, the notification
switch and the idempotent system/user completion helper (UC-021, BR-101, BR-105)."""
import pytest

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vms.models import Notification, VisitLog
from modules.vms.services import checkout
from modules.vms.tests import factories as f

from .conftest import HOST, on_site_pass

pytestmark = pytest.mark.django_db
E = VisitLog.Event


@pytest.mark.parametrize("credential", ["", "   ", None])
def test_gate_checkout_requires_a_credential(security, credential):
    with pytest.raises(BadRequestError) as e:
        checkout.gate_checkout(security_actor=security, credential=credential)
    assert e.value.code == "credential_required"


def test_gate_checkout_unknown_credential_is_not_found(security):
    with pytest.raises(NotFoundError):
        checkout.gate_checkout(security_actor=security, credential="no-such-pass")


def test_gate_checkout_unknown_gate_is_rejected_before_anything_is_written(security):
    vp = on_site_pass()
    with pytest.raises(BadRequestError) as e:
        checkout.gate_checkout(security_actor=security, credential=vp.qr_token, gate_id=987654)
    assert e.value.code == "unknown_gate"
    assert not VisitLog.objects.filter(event=E.CHECK_OUT).exists()


def test_gate_checkout_records_the_gate_it_happened_at(security):
    vp = on_site_pass()
    gate = f.make_gate()
    log = checkout.gate_checkout(security_actor=security, credential=vp.qr_token,
                                 gate_id=gate.pk)
    assert log.gate_id == gate.pk and log.logged_by_user_id == security.user_id


def test_checkout_from_a_state_that_cannot_complete_is_a_conflict(security):
    """A pass can be on site while its request is in a state the table will not complete."""
    vp = on_site_pass()
    type(vp.visit_request).objects.filter(pk=vp.visit_request_id).update(status="rejected")
    with pytest.raises(ConflictError) as e:
        checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    assert e.value.code == "invalid_state"
    assert not VisitLog.objects.filter(event=E.CHECK_OUT).exists()


def test_complete_visit_from_a_state_that_cannot_complete_is_a_quiet_noop():
    vp = on_site_pass()
    type(vp.visit_request).objects.filter(pk=vp.visit_request_id).update(status="rejected")
    assert checkout.complete_visit(vp.pk, "auto") is None
    assert not VisitLog.objects.filter(event=E.AUTO_CHECK_OUT).exists()


def test_checkout_notification_can_be_switched_off(security):
    f.make_integration_setting(key=checkout.NOTIFY_SETTING, value={"enabled": False})
    vp = on_site_pass()
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    assert not Notification.objects.filter(topic="visit.checked_out").exists()


def test_checkout_notification_is_sent_when_the_setting_is_a_plain_true(security):
    f.make_integration_setting(key=checkout.NOTIFY_SETTING, value=True)
    vp = on_site_pass()
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    assert Notification.objects.filter(topic="visit.checked_out",
                                       recipient_user_id=HOST).exists()


def test_complete_visit_unknown_pass_is_not_found():
    with pytest.raises(NotFoundError):
        checkout.complete_visit(987654, "auto")


def test_complete_visit_for_a_user_records_a_check_out_not_an_auto_check_out(security):
    vp = on_site_pass()
    log = checkout.complete_visit(vp.pk, "manual", actor=security)
    assert log.event == E.CHECK_OUT and log.logged_by_user_id == security.user_id
    assert checkout.complete_visit(vp.pk, "manual", actor=security) is None   # idempotent


def test_complete_visit_with_no_actor_records_an_auto_check_out():
    vp = on_site_pass()
    log = checkout.complete_visit(vp.pk, "auto")
    assert log.event == E.AUTO_CHECK_OUT and log.logged_by_user_id is None
