"""policy, blacklist and passes services."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.vms.models import AuditLog, VisitPass
from modules.vms.services import blacklist, passes, policy
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


# --- policy --------------------------------------------------------------------------

def test_effective_with_nothing_published_uses_srs_defaults():
    p = policy.effective()
    assert (p.version, p.max_visit_hours, p.walk_in_pass_hours,
            p.approval_timeout_hours, p.advance_registration_hours) == (0, 8, 4, 24, 2)


def test_br_127_effective_is_latest_published_only():
    f.make_published_policy(version=1, max_visit_hours=6)
    f.make_published_policy(version=2, max_visit_hours=5)
    f.make_access_policy(version=3, max_visit_hours=1)   # draft
    p = policy.effective()
    assert (p.version, p.max_visit_hours) == (2, 5)


def test_effective_is_a_frozen_dataclass():
    f.make_published_policy(version=1)
    with pytest.raises(AttributeError):
        policy.effective().version = 9


def test_effective_at_returns_the_policy_then_current():
    now = timezone.now()
    f.make_published_policy(version=1, published_at=now - timedelta(days=10),
                            max_visit_hours=6)
    f.make_published_policy(version=2, published_at=now - timedelta(days=1),
                            max_visit_hours=5)
    assert policy.effective(at=now - timedelta(days=5)).version == 1
    assert policy.effective(at=now).version == 2


def test_effective_restricted_zones_include_flagged_zones():
    z = f.make_zone(is_restricted=True)
    z2 = f.make_zone()
    p = f.make_published_policy(version=1)
    p.restricted_zones.add(z2)
    assert policy.effective().restricted_zone_ids == {z.pk, z2.pk}


def test_br_129_snapshot_is_not_retroactive():
    now = timezone.now()
    f.make_published_policy(version=1, published_at=now - timedelta(days=10),
                            max_visit_hours=6)
    vr = f.make_visit_request()
    type(vr).objects.filter(pk=vr.pk).update(created_at=now - timedelta(days=5))
    vr.refresh_from_db()
    f.make_published_policy(version=2, published_at=now - timedelta(days=1),
                            max_visit_hours=2)
    assert policy.snapshot_for(vr).version == 1
    assert policy.effective().version == 2


def test_snapshot_for_request_older_than_any_policy_uses_oldest():
    f.make_published_policy(version=4, published_at=timezone.now() + timedelta(days=1))
    assert policy.snapshot_for(f.make_visit_request()).version == 4


def test_publish_marks_published_and_audits():
    draft = f.make_access_policy(version=7)
    out = policy.publish(policy_id=draft.pk, actor=f.make_actor(user_id=8))
    assert out.status == "published" and out.published_at
    assert AuditLog.objects.filter(action="vms.policy.published",
                                   entity_id=str(draft.pk)).exists()


def test_publish_twice_is_idempotent_and_unknown_is_none():
    draft = f.make_access_policy(version=8)
    first = policy.publish(policy_id=draft.pk, actor=None)
    again = policy.publish(policy_id=draft.pk, actor=None)
    assert again.published_at == first.published_at
    assert policy.publish(policy_id=999999, actor=None) is None


# --- blacklist -----------------------------------------------------------------------

@pytest.fixture
def live_version():
    return f.make_blacklist_version(version=1, status="published",
                                    published_at=timezone.now())


def test_check_without_published_version_is_clear():
    draft = f.make_blacklist_version()
    f.make_blacklist_entry(version=draft, id_doc_number="X1")
    assert blacklist.check(checkpoint="gate", id_doc_number="X1") is None


def test_br_120_only_published_version_counts(live_version):
    draft = f.make_blacklist_version()
    f.make_blacklist_entry(version=draft, id_doc_number="D1")
    f.make_blacklist_entry(version=live_version, id_doc_number="P1", severity="critical",
                           reason="Theft")
    assert blacklist.check(checkpoint="gate", id_doc_number="D1") is None
    hit = blacklist.check(checkpoint="walk_in", id_doc_number="p1")
    assert hit.severity == "critical" and hit.reason == "Theft"
    assert hit.matched_fields == ("id_doc_number",) and hit.checkpoint == "walk_in"


def test_entry_without_version_is_ignored(live_version):
    f.make_blacklist_entry(version=None, id_doc_number="N1")
    assert blacklist.check(checkpoint="gate", id_doc_number="N1") is None


def test_d2_id_is_normalised_phone_digits_email_case_insensitive(live_version):
    f.make_blacklist_entry(version=live_version, id_doc_number="ab 12", phone="",
                           email="Bad@Example.com")
    f.make_blacklist_entry(version=live_version, id_doc_number="", phone="+91 98765-43210")
    assert blacklist.check(checkpoint="gate", id_doc_number="AB12")
    assert blacklist.check(checkpoint="gate", email="bad@example.COM")
    assert blacklist.check(checkpoint="gate", phone="9876543210")
    assert blacklist.check(checkpoint="gate", phone="09876543210")


def test_d2_name_alone_never_matches(live_version):
    f.make_blacklist_entry(version=live_version, name="Same Name", id_doc_number="Z9")
    assert blacklist.check(checkpoint="gate", name="Same Name") is None


def test_blank_probe_never_matches(live_version):
    f.make_blacklist_entry(version=live_version, id_doc_number="", phone="", email="")
    assert blacklist.check(checkpoint="gate") is None


def test_inactive_and_expired_entries_are_ignored(live_version):
    f.make_blacklist_entry(version=live_version, id_doc_number="I1", is_active=False)
    f.make_blacklist_entry(version=live_version, id_doc_number="E1",
                           expiry_date=timezone.localdate() - timedelta(days=1))
    f.make_blacklist_entry(version=live_version, id_doc_number="F1",
                           expiry_date=timezone.localdate())
    assert blacklist.check(checkpoint="gate", id_doc_number="I1") is None
    assert blacklist.check(checkpoint="gate", id_doc_number="E1") is None
    assert blacklist.check(checkpoint="gate", id_doc_number="F1")


def test_worst_severity_wins(live_version):
    f.make_blacklist_entry(version=live_version, id_doc_number="S1", severity="low")
    f.make_blacklist_entry(version=live_version, phone="9000000001", id_doc_number="",
                           severity="high")
    hit = blacklist.check(checkpoint="gate", id_doc_number="S1", phone="9000000001")
    assert hit.severity == "high"


def test_br_118_safe_list_short_circuits(live_version):
    f.make_blacklist_entry(version=live_version, id_doc_number="SAFE1")
    f.make_safelist_entry(visitor_id_doc_number="safe1")
    assert blacklist.check(checkpoint="gate", id_doc_number="SAFE1") is None


def test_br_119_expired_or_revoked_safe_list_does_not_exempt(live_version):
    f.make_blacklist_entry(version=live_version, id_doc_number="SAFE2")
    entry = f.make_safelist_entry(visitor_id_doc_number="SAFE2",
                                  expires_at=timezone.now() - timedelta(minutes=1))
    assert blacklist.check(checkpoint="gate", id_doc_number="SAFE2")
    entry.expires_at = timezone.now() + timedelta(days=1)
    entry.revoked_at = timezone.now()
    entry.save()
    assert blacklist.check(checkpoint="gate", id_doc_number="SAFE2")


def test_unknown_checkpoint_is_rejected():
    with pytest.raises(ValueError):
        blacklist.check(checkpoint="lobby")


def test_add_entry_goes_into_the_published_version_and_takes_effect():
    actor = f.make_actor(user_id=3)
    entry = blacklist.add_entry(actor=actor, name="N", id_doc_number="ADD1", reason="r")
    assert entry.version.status == "published"
    assert blacklist.check(checkpoint="pre_registration", id_doc_number="ADD1")
    assert AuditLog.objects.filter(action="vms.blacklist.entry_added").exists()


# --- passes --------------------------------------------------------------------------

@pytest.fixture
def approved():
    f.make_published_policy(version=1, max_visit_hours=8, walk_in_pass_hours=4)
    start = timezone.now() + timedelta(hours=1)
    vr = f.make_visit_request(status="approved", scheduled_start=start,
                              scheduled_end=start + timedelta(hours=3))
    vr.requested_zones.add(f.make_zone(), f.make_zone())
    return vr


def test_issue_pass_sets_token_otp_window_zones_and_audit(approved):
    issuer = f.make_actor(user_id=123)
    vp = passes.issue_pass(request=approved, pass_type="PRE_REGISTERED", issued_by=issuer)
    assert len(vp.qr_token) >= 32 and len(vp.otp) == 6 and vp.otp.isdigit()
    assert (vp.valid_from, vp.valid_until) == (approved.scheduled_start, approved.scheduled_end)
    assert set(vp.allowed_zones.all()) == set(approved.requested_zones.all())
    assert vp.is_active and vp.issued_by_user_id == 123
    assert vp.issued_for_source == "pre_registered"
    row = AuditLog.objects.get(action="vms.pass.issued")
    assert row.entity_id == str(vp.pk) and row.actor_user_id == 123


def test_br_193_validity_is_capped_by_the_snapshot_policy(approved):
    approved.scheduled_end = approved.scheduled_start + timedelta(hours=20)
    approved.save()
    vp = passes.issue_pass(request=approved, pass_type="PRE_REGISTERED", issued_by=1)
    assert vp.valid_until == approved.scheduled_start + timedelta(hours=8)


def test_br_193_uses_the_policy_in_force_when_requested_not_the_latest(approved):
    type(approved).objects.filter(pk=approved.pk).update(
        created_at=timezone.now() - timedelta(days=3))
    old = policy.effective()
    assert old.version == 1
    f.make_published_policy(version=2, max_visit_hours=1)
    approved.refresh_from_db()
    approved.scheduled_end = approved.scheduled_start + timedelta(hours=20)
    approved.save()
    vp = passes.issue_pass(request=approved, pass_type="PRE_REGISTERED", issued_by=1)
    assert vp.valid_until == approved.scheduled_start + timedelta(hours=8)


def test_walk_in_pass_is_capped_by_walk_in_hours(approved):
    approved.scheduled_end = approved.scheduled_start + timedelta(hours=7)
    approved.save()
    vp = passes.issue_pass(request=approved, pass_type="WALK_IN", issued_by=1)
    assert vp.valid_until == approved.scheduled_start + timedelta(hours=4)


def test_explicit_window_and_zones_override_the_request(approved):
    z = f.make_zone()
    s = approved.scheduled_start
    vp = passes.issue_pass(request=approved, pass_type="VIP", issued_by=1,
                           valid_from=s, valid_until=s + timedelta(hours=1), zones=[z])
    assert vp.valid_until == s + timedelta(hours=1)
    assert list(vp.allowed_zones.all()) == [z]
    assert vp.pass_type == VisitPass.PassType.VIP


def test_pass_is_refused_for_unapproved_request(approved):
    approved.status = "pending"
    approved.save()
    with pytest.raises(ConflictError):
        passes.issue_pass(request=approved, pass_type="PRE_REGISTERED", issued_by=1)


def test_second_active_pass_for_one_request_is_refused(approved):
    passes.issue_pass(request=approved, pass_type="PRE_REGISTERED", issued_by=1)
    with pytest.raises(ConflictError):
        passes.issue_pass(request=approved, pass_type="PRE_REGISTERED", issued_by=1)


def test_otp_is_unique_among_active_passes(approved, monkeypatch):
    other = f.make_visit_pass(otp="111111", is_active=True)
    seq = iter([111111, 111111, 222222])
    monkeypatch.setattr(passes.secrets, "randbelow", lambda n: next(seq))
    vp = passes.issue_pass(request=approved, pass_type="PRE_REGISTERED", issued_by=1)
    assert vp.otp == "222222" and other.otp == "111111"


def test_otp_may_reuse_an_inactive_pass_value(approved, monkeypatch):
    f.make_visit_pass(otp="333333", is_active=False)
    monkeypatch.setattr(passes.secrets, "randbelow", lambda n: 333333)
    assert passes.issue_pass(request=approved, pass_type="PRE_REGISTERED",
                             issued_by=1).otp == "333333"


def test_qr_tokens_are_unique(approved):
    other = f.make_visit_request(status="approved")
    a = passes.issue_pass(request=approved, pass_type="PRE_REGISTERED", issued_by=1)
    b = passes.issue_pass(request=other, pass_type="PRE_REGISTERED", issued_by=1)
    assert a.qr_token != b.qr_token


def test_terminate_pass_is_a_stub_for_lane_d():
    with pytest.raises(NotImplementedError):
        passes.terminate_pass()
