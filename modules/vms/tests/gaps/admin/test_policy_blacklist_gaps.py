from datetime import time, timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vms.models import AccessPolicy, AuditLog
from modules.vms.services import blacklist, blacklist_admin, policy, policy_admin
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


def _publish_entry(admin_actor, **kw):
    d = blacklist_admin.create_version(actor=admin_actor)
    e = blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="A", reason="r", **kw)
    blacklist_admin.publish(actor=admin_actor, version_id=d.pk)
    return d, e


# --- policy ---------------------------------------------------------------------------

def test_uc_005_policy_publish_requires_all_fields_valid_visiting_hours(
        admin_actor, published_policy):
    """VMS-UC-005: invalid hours are rejected at publish and the draft stays a draft."""
    draft = policy_admin.create_draft(actor=admin_actor)
    AccessPolicy.objects.filter(pk=draft.pk).update(
        visiting_hours_start=time(18, 0), visiting_hours_end=time(9, 0))
    with pytest.raises(BadRequestError) as e:
        policy_admin.publish(actor=admin_actor, policy_id=draft.pk)
    assert e.value.code == "validation_error"
    draft.refresh_from_db()
    assert draft.status == "draft" and policy.effective().policy_id == published_policy.pk


def test_uc_005_policy_update_draft_rejects_inconsistent_values(admin_actor, published_policy):
    """VMS-UC-005: reminder must precede timeout; walk-in pass must fit max visit."""
    draft = policy_admin.create_draft(actor=admin_actor)
    with pytest.raises(BadRequestError):
        policy_admin.update_draft(actor=admin_actor, policy_id=draft.pk,
                                  changes={"reminder_after_hours": 99})
    with pytest.raises(BadRequestError):
        policy_admin.update_draft(actor=admin_actor, policy_id=draft.pk,
                                  changes={"max_visit_hours": 2, "walk_in_pass_hours": 5})
    with pytest.raises(BadRequestError):
        policy_admin.update_draft(actor=admin_actor, policy_id=draft.pk,
                                  changes={"nonsense": 1})


def test_uc_005_policy_draft_not_used_by_gate_or_registration(admin_actor, published_policy):
    """VMS-UC-005: edits to a draft never reach the runtime policy."""
    draft = policy_admin.create_draft(actor=admin_actor)
    policy_admin.update_draft(actor=admin_actor, policy_id=draft.pk,
                              changes={"max_visit_hours": 3, "walk_in_pass_hours": 3})
    assert policy.effective().policy_id == published_policy.pk
    assert policy.effective().max_visit_hours == published_policy.max_visit_hours


def test_uc_005_policy_list_includes_status_and_version_numbers_monotonic(
        admin_actor, published_policy):
    """VMS-UC-005: versions increase by one per new draft; list is newest first."""
    d2 = policy_admin.create_draft(actor=admin_actor)
    policy_admin.publish(actor=admin_actor, policy_id=d2.pk)
    d3 = policy_admin.create_draft(actor=admin_actor)
    assert (d2.version, d3.version) == (published_policy.version + 1, published_policy.version + 2)
    rows = list(policy_admin.list_policies(actor=admin_actor))
    assert [r.version for r in rows] == sorted((r.version for r in rows), reverse=True)
    assert {r.status for r in rows} == {"published", "draft"}


def test_br_126_publish_supersedes_prior_published_atomically(admin_actor, published_policy):
    """VMS-BR-126: after publish exactly one version is effective (the newest)."""
    d2 = policy_admin.create_draft(actor=admin_actor)
    policy_admin.publish(actor=admin_actor, policy_id=d2.pk)
    assert policy.effective().policy_id == d2.pk
    assert AccessPolicy.objects.filter(status="draft").count() == 0


def test_br_126_publish_stale_draft_conflicts(admin_actor, published_policy):
    """VMS-BR-126: a draft older than a published version cannot be published."""
    draft = policy_admin.create_draft(actor=admin_actor)
    f.make_published_policy(version=draft.version + 5)
    with pytest.raises(ConflictError) as e:
        policy_admin.publish(actor=admin_actor, policy_id=draft.pk)
    assert e.value.code == "stale_draft"
    draft.refresh_from_db()
    assert draft.status == "draft"


def test_br_125_policy_version_retained_after_supersede_and_readable(
        admin_actor, published_policy):
    """VMS-BR-125: history stays and can be diffed."""
    d2 = policy_admin.create_draft(actor=admin_actor)
    policy_admin.update_draft(actor=admin_actor, policy_id=d2.pk,
                              changes={"max_visit_hours": 5, "walk_in_pass_hours": 2})
    policy_admin.publish(actor=admin_actor, policy_id=d2.pk)
    assert AccessPolicy.objects.filter(pk=published_policy.pk).exists()
    out = policy_admin.diff(actor=admin_actor, a_id=published_policy.pk, b_id=d2.pk)
    assert out["changes"]["max_visit_hours"]["b"] == 5
    with pytest.raises(NotFoundError):
        policy_admin.get(0)


def test_br_127_registration_gate_and_checkout_use_same_published_policy(
        admin_actor, published_policy):
    """VMS-BR-127: one runtime source - effective() is the newest published, not a draft."""
    d2 = policy_admin.create_draft(actor=admin_actor)
    policy_admin.publish(actor=admin_actor, policy_id=d2.pk)
    policy_admin.create_draft(actor=admin_actor)
    first, second = policy.effective(), policy.effective()
    assert first.policy_id == second.policy_id == d2.pk


def test_br_128_edit_of_published_never_mutates_original_row(admin_actor, published_policy):
    """VMS-BR-128: editing a published row is refused and leaves it unchanged."""
    before = published_policy.max_visit_hours
    with pytest.raises(ConflictError) as e:
        policy_admin.update_draft(actor=admin_actor, policy_id=published_policy.pk,
                                  changes={"max_visit_hours": before + 1})
    assert e.value.code == "not_a_draft"
    published_policy.refresh_from_db()
    assert published_policy.max_visit_hours == before


def test_uc_005_policy_restricted_zone_flag_change_applies_next_validation(
        admin_actor, published_policy):
    """VMS-UC-005: restricted zones set on a draft become effective on publish."""
    zone = f.make_zone()
    d = policy_admin.create_draft(actor=admin_actor)
    policy_admin.update_draft(actor=admin_actor, policy_id=d.pk, changes={},
                              restricted_zone_ids=[zone.pk])
    assert zone.pk not in policy.effective().restricted_zone_ids
    policy_admin.publish(actor=admin_actor, policy_id=d.pk)
    assert zone.pk in policy.effective().restricted_zone_ids
    d2 = policy_admin.create_draft(actor=admin_actor)
    with pytest.raises(BadRequestError):
        policy_admin.update_draft(actor=admin_actor, policy_id=d2.pk, changes={},
                                  restricted_zone_ids=[zone.pk + 999])


# --- blacklist ------------------------------------------------------------------------

def test_uc_006_blacklist_entry_edit_creates_change_in_draft_only(admin_actor):
    """VMS-UC-006: editing a carried-forward entry touches the draft copy, not the live row."""
    v1, live = _publish_entry(admin_actor, id_doc_number="E1", severity="low")
    d2 = blacklist_admin.create_version(actor=admin_actor)
    copy = d2.entries.get()
    blacklist_admin.update_entry(actor=admin_actor, version_id=d2.pk, entry_id=copy.pk,
                                 severity="critical")
    live.refresh_from_db()
    assert live.severity == "low" and copy.pk != live.pk
    assert blacklist.check(checkpoint="gate", id_doc_number="E1").severity == "low"
    with pytest.raises(NotFoundError):          # live row is not addressable via the draft
        blacklist_admin.update_entry(actor=admin_actor, version_id=d2.pk,
                                     entry_id=live.pk, severity="high")


@pytest.mark.xfail(strict=True, reason="BUG: publishing a draft with no changes is accepted")
def test_uc_006_blacklist_publish_with_no_changes_rejected(admin_actor):
    """VMS-UC-006: an empty publish (identical to live) is refused."""
    _publish_entry(admin_actor, id_doc_number="E1")
    d2 = blacklist_admin.create_version(actor=admin_actor)
    with pytest.raises(BadRequestError):
        blacklist_admin.publish(actor=admin_actor, version_id=d2.pk)


@pytest.mark.xfail(strict=True, reason="BUG: add_entry accepts an expiry_date in the past")
def test_uc_006_blacklist_entry_expiry_before_now_rejected(admin_actor):
    """VMS-UC-006: an entry already expired at creation is a 400."""
    d = blacklist_admin.create_version(actor=admin_actor)
    with pytest.raises(BadRequestError):
        blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="A", reason="r",
                                  id_doc_number="E1",
                                  expiry_date=timezone.localdate() - timedelta(days=1))


def test_uc_006_blacklist_update_to_active_entry_without_identifier_rejected(admin_actor):
    """VMS-UC-006: stripping every identifier from an active entry is a 400."""
    d = blacklist_admin.create_version(actor=admin_actor)
    e = blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="A", reason="r",
                                  phone="9876543210")
    with pytest.raises(BadRequestError):
        blacklist_admin.update_entry(actor=admin_actor, version_id=d.pk, entry_id=e.pk,
                                     phone="")


def test_br_112_blacklist_check_at_preauth_extension_walkin_event_checkpoints(admin_actor):
    """VMS-BR-112: every declared checkpoint blocks; an unknown one is a programming error."""
    _publish_entry(admin_actor, id_doc_number="E1")
    for cp in blacklist.CHECKPOINTS:
        assert blacklist.check(checkpoint=cp, id_doc_number="E1") is not None
    with pytest.raises(ValueError):
        blacklist.check(checkpoint="lobby", id_doc_number="E1")


def test_br_118_safelist_scope_limited_to_named_visitor_and_gate(admin_actor):
    """VMS-BR-118: a safe-list entry exempts only its named id document."""
    _publish_entry(admin_actor, id_doc_number="E1", phone="9876543210")
    blacklist_admin.add_safelist(actor=admin_actor, id_doc_number="E1", reason="ok",
                                 expires_at=timezone.now() + timedelta(days=3))
    assert blacklist.check(checkpoint="gate", id_doc_number="E1") is None
    assert blacklist.check(checkpoint="gate", id_doc_number="E2", phone="9876543210") is not None


def test_br_118_safelist_does_not_exempt_other_visitor_same_name(admin_actor):
    """VMS-BR-118: same display name, different id is still blocked."""
    d = blacklist_admin.create_version(actor=admin_actor)
    blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="Same Name",
                              id_doc_number="E1", reason="r")
    blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="Same Name",
                              id_doc_number="E2", reason="r")
    blacklist_admin.publish(actor=admin_actor, version_id=d.pk)
    blacklist_admin.add_safelist(actor=admin_actor, id_doc_number="E1", reason="ok",
                                 expires_at=timezone.now() + timedelta(days=3))
    assert blacklist.check(checkpoint="gate", name="Same Name", id_doc_number="E1") is None
    assert blacklist.check(checkpoint="gate", name="Same Name", id_doc_number="E2") is not None


def test_br_119_safelist_expiry_exact_boundary(admin_actor):
    """VMS-BR-119: at the expiry instant the safe-list no longer applies."""
    _publish_entry(admin_actor, id_doc_number="E1")
    exp = timezone.now() + timedelta(days=2)
    blacklist_admin.add_safelist(actor=admin_actor, id_doc_number="E1", reason="ok",
                                 expires_at=exp)
    assert blacklist.check(checkpoint="gate", id_doc_number="E1",
                           at=exp - timedelta(seconds=1)) is None
    assert blacklist.check(checkpoint="gate", id_doc_number="E1", at=exp) is not None


def test_br_119_safelist_revoke_twice_conflicts_and_unknown_not_found(admin_actor):
    """VMS-BR-119: revoke is one-way; unknown ids 404."""
    s = blacklist_admin.add_safelist(actor=admin_actor, id_doc_number="E1", reason="ok",
                                     expires_at=timezone.now() + timedelta(days=2))
    blacklist_admin.revoke_safelist(actor=admin_actor, entry_id=s.pk)
    with pytest.raises(ConflictError):
        blacklist_admin.revoke_safelist(actor=admin_actor, entry_id=s.pk)
    with pytest.raises(NotFoundError):
        blacklist_admin.revoke_safelist(actor=admin_actor, entry_id=0)
    assert AuditLog.objects.filter(action="vms.safelist.revoked", entity_id=str(s.pk)).exists()


def test_br_120_blacklist_publish_makes_new_entries_effective_immediately_for_gate(
        admin_actor):
    """VMS-BR-120: the next check after publish already sees the entry; a stale draft is refused."""
    _publish_entry(admin_actor, id_doc_number="E1")
    assert blacklist.check(checkpoint="gate", id_doc_number="N1") is None
    d2 = blacklist_admin.create_version(actor=admin_actor)
    blacklist_admin.add_entry(actor=admin_actor, version_id=d2.pk, name="N", reason="r",
                              id_doc_number="N1")
    blacklist_admin.publish(actor=admin_actor, version_id=d2.pk)
    assert blacklist.check(checkpoint="gate", id_doc_number="N1") is not None
    stale = f.make_blacklist_version(version=0, status="draft")
    with pytest.raises(ConflictError) as e:
        blacklist_admin.publish(actor=admin_actor, version_id=stale.pk)
    assert e.value.code == "stale_draft"


def test_br_117_alert_severity_matches_entry_severity(admin_actor):
    """VMS-BR-117: the worst matching severity is reported."""
    d = blacklist_admin.create_version(actor=admin_actor)
    blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="A", reason="r",
                              id_doc_number="E1", severity="low")
    blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="B", reason="r",
                              phone="9876543210", severity="critical")
    blacklist_admin.publish(actor=admin_actor, version_id=d.pk)
    hit = blacklist.check(checkpoint="gate", id_doc_number="E1", phone="9876543210")
    assert hit.severity == "critical"
    assert blacklist.check(checkpoint="gate", id_doc_number="E1").severity == "low"
