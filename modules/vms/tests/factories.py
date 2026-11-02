"""Shared test factories for every vms model (plain functions).

Each `make_<model>(**overrides)` creates and returns a valid row, building
its required parents. Lanes use these instead of hand-rolled fixtures.
Needs DB access (use the `db` fixture / `django_db` mark).
"""
import itertools
import secrets
import uuid
from datetime import timedelta

from django.utils import timezone

from fusion_auth.client import IamSession
from fusion_auth.principal import Principal
from modules.vms import models as m

_seq = itertools.count(1)


def _n() -> int:
    return next(_seq)


def _now():
    return timezone.now()


def _create(model, defaults, overrides):
    return model.objects.create(**{**defaults, **overrides})


# --- actors -----------------------------------------------------------------

def make_actor(kind="staff", roles=(), permissions=(), user_id=None,
               modules=("vms",)) -> Principal:
    """A Principal built the way the root conftest `make_session` does."""
    uid = user_id if user_id is not None else 1000 + _n()
    roles = tuple(roles)
    return Principal.from_session(IamSession(
        user_id=uid, username=f"u{uid}", display_name=f"User {uid}",
        kind=kind, active_role=roles[0] if roles else kind,
        roles=roles or (kind,), permissions=frozenset(permissions),
        modules=tuple(modules),
    ))


# --- core -------------------------------------------------------------------

def make_zone(**kw):
    return _create(m.Zone, {"name": f"Zone {_n()}"}, kw)


def make_gate(**kw):
    kw.setdefault("zone", make_zone())
    return _create(m.Gate, {"name": f"Gate {_n()}", "device_id": f"dev-{_n()}"}, kw)


def make_visitor(**kw):
    n = _n()
    return _create(m.Visitor, {
        "full_name": f"Visitor {n}", "phone": f"9{n:09d}",
        "email": f"visitor{n}@example.com", "id_doc_type": "passport",
        "id_doc_number": f"ID{n:06d}"}, kw)


def make_visit_request(**kw):
    kw.setdefault("visitor", make_visitor())
    start = _now() + timedelta(days=1)
    return _create(m.VisitRequest, {
        "host_user_id": 2001, "purpose": "Meeting",
        "scheduled_start": start, "scheduled_end": start + timedelta(hours=2)}, kw)


def make_visit_pass(**kw):
    kw.setdefault("visit_request", make_visit_request(status="approved"))
    now = _now()
    return _create(m.VisitPass, {
        "pass_type": m.VisitPass.PassType.PRE_REGISTERED,
        "qr_token": secrets.token_hex(16), "otp": f"{_n() % 1000000:06d}",
        "valid_from": now, "valid_until": now + timedelta(hours=4),
        "issued_by_user_id": 2001}, kw)


def make_visit_log(**kw):
    kw.setdefault("visit_pass", make_visit_pass())
    return _create(m.VisitLog, {"event": m.VisitLog.Event.CHECK_IN,
                                "logged_by_user_id": 3001}, kw)


# --- people -----------------------------------------------------------------

def make_visitor_session(**kw):
    kw.setdefault("visitor", make_visitor())
    return _create(m.VisitorSession, {
        "token_hash": secrets.token_hex(32), "otp_hash": secrets.token_hex(32),
        "expires_at": _now() + timedelta(hours=12)}, kw)


def make_role_assignment(**kw):
    now = _now()
    return _create(m.RoleAssignment, {
        "user_id": 3001, "role": m.RoleAssignment.Role.SECURITY,
        "scope_type": m.RoleAssignment.ScopeType.CAMPUS,
        "starts_at": now - timedelta(hours=1), "ends_at": now + timedelta(days=30),
        "assigned_by_user_id": 1}, kw)


def make_vip_permission(**kw):
    kw.setdefault("visitor", make_visitor())
    now = _now()
    return _create(m.VipPermission, {
        "valid_from": now, "valid_until": now + timedelta(days=30),
        "granted_by_user_id": 1}, kw)


def make_pre_authorization(**kw):
    kw.setdefault("visitor", make_visitor())
    now = _now()
    return _create(m.PreAuthorization, {
        "host_user_id": 2001, "valid_from": now,
        "valid_until": now + timedelta(days=30), "max_visits": 3}, kw)


# --- policy -----------------------------------------------------------------

def make_access_policy(**kw):
    return _create(m.AccessPolicy, {"version": _n() + 1000}, kw)


def make_published_policy(**kw):
    kw.setdefault("status", m.AccessPolicy.Status.PUBLISHED)
    kw.setdefault("published_at", _now())
    return make_access_policy(**kw)


def make_integration_setting(**kw):
    return _create(m.IntegrationSetting, {"key": f"setting_{_n()}", "value": {}}, kw)


def make_blacklist_version(**kw):
    return _create(m.BlacklistVersion, {"version": _n() + 1000}, kw)


def make_blacklist_entry(**kw):
    n = _n()
    return _create(m.BlacklistEntry, {
        "name": f"Barred {n}", "id_doc_number": f"BL{n:06d}",
        "reason": "Misconduct"}, kw)


def make_safelist_entry(**kw):
    return _create(m.SafeListEntry, {
        "visitor_id_doc_number": f"SL{_n():06d}", "reason": "Cleared",
        "expires_at": _now() + timedelta(days=30), "created_by_user_id": 1}, kw)


# --- access extras ----------------------------------------------------------

def make_zone_elevation(**kw):
    kw.setdefault("visit_pass", make_visit_pass())
    kw.setdefault("zone", make_zone())
    now = _now()
    return _create(m.ZoneElevation, {
        "starts_at": now, "ends_at": now + timedelta(hours=1),
        "granted_by_user_id": 1, "reason": "Escort"}, kw)


def make_gate_override(**kw):
    kw.setdefault("visit_log", make_visit_log(event=m.VisitLog.Event.DENIED))
    return _create(m.GateOverride, {"admin_user_id": 1, "justification": "ok"}, kw)


def make_escalation(**kw):
    kw.setdefault("visit_log", make_visit_log(event=m.VisitLog.Event.DENIED))
    return _create(m.Escalation, {"raised_by_user_id": 3001, "note": "check"}, kw)


# --- ops --------------------------------------------------------------------

def make_alert(**kw):
    return _create(m.Alert, {"kind": m.Alert.Kind.SUSPICIOUS}, kw)


def make_notification(**kw):
    return _create(m.Notification, {
        "topic": "request.submitted", "dedupe_key": f"dk-{uuid.uuid4()}",
        "recipient_user_id": 2001, "channel": m.Notification.Channel.INAPP,
        "subject": "Hello", "body": "Body"}, kw)


def make_audit_log(**kw):
    return _create(m.AuditLog, {
        "actor_user_id": 1, "actor_role": "admin", "action": "test.action",
        "entity_type": "VisitRequest", "entity_id": str(_n())}, kw)


def make_offline_sync_run(**kw):
    kw.setdefault("gate", make_gate())
    return _create(m.OfflineSyncRun, {"events_total": 0}, kw)


# --- events -----------------------------------------------------------------

def make_extension_request(**kw):
    kw.setdefault("visit_request", make_visit_request(status="approved"))
    return _create(m.ExtensionRequest, {
        "requested_end": _now() + timedelta(days=1), "reason": "Overran"}, kw)


def make_emergency_muster(**kw):
    return _create(m.EmergencyMuster, {"triggered_by_user_id": 3001,
                                       "trigger_role": "security"}, kw)


def make_muster_entry(**kw):
    kw.setdefault("muster", make_emergency_muster())
    kw.setdefault("visit_pass", make_visit_pass())
    return _create(m.MusterEntry, {}, kw)


def make_event_batch(**kw):
    now = _now()
    return _create(m.EventBatch, {
        "name": f"Event {_n()}", "organizer": "Dept",
        "valid_from": now, "valid_until": now + timedelta(days=1),
        "created_by_user_id": 1}, kw)


def make_event_attendee(**kw):
    kw.setdefault("batch", make_event_batch())
    n = _n()
    return _create(m.EventAttendee, {"name": f"Attendee {n}",
                                     "email": f"att{n}@example.com"}, kw)
