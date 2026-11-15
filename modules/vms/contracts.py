"""vms's public surface.

Other modules reach VMS through these functions and nothing else. Every
getter takes a sequence of ids: a singular get_x(id) is the thing that gets
called inside a loop, so the batched form is the only form available.
"""
from __future__ import annotations

from collections.abc import Sequence

from modules.vms.models import Pass, Visit, Visitor


def get_visitors(visitor_ids: Sequence[int]) -> dict[int, dict]:
    rows = Visitor.objects.filter(id__in=list(visitor_ids))
    return {
        r.id: {
            "id": r.id,
            "full_name": r.full_name,
            "phone": r.phone,
            "email": r.email,
            "is_disabled": r.is_disabled,
            "is_anonymous": r.is_anonymous,
        }
        for r in rows
    }


def get_visit_summaries(visit_ids: Sequence[int]) -> dict[int, dict]:
    rows = Visit.objects.filter(id__in=list(visit_ids))
    return {
        r.id: {
            "id": r.id,
            "visitor_id": r.visitor_id,
            "host_user_id": r.host_user_id,
            "status": r.status,
            "checked_in_at": r.checked_in_at,
            "checked_out_at": r.checked_out_at,
        }
        for r in rows
    }


def get_pass_states(pass_codes: Sequence[str]) -> dict[str, dict]:
    rows = Pass.objects.filter(pass_code__in=list(pass_codes))
    return {
        r.pass_code: {
            "pass_code": r.pass_code,
            "status": r.status,
            "visit_id": r.visit_id,
            "valid_from": r.valid_from,
            "valid_until": r.valid_until,
            "permitted_zones": list(r.permitted_zones),
        }
        for r in rows
    }


def search(*, q: str, limit: int = 25) -> list[dict]:
    """Quick visitor search by name, phone, email or id (VMS-CFR-020).

    Exact-prefix on the identifier fields, substring on the name — the
    blacklist matcher is the one that must never do this; see
    services.blacklist.find_matches.
    """
    from django.db.models import Q

    q = (q or "").strip()
    if not q:
        return []
    rows = (
        Visitor.objects.filter(
            Q(full_name__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
            | Q(id_doc_number__icontains=q)
        )
        .order_by("full_name")[:limit]
    )
    return [
        {"id": r.id, "full_name": r.full_name, "phone": r.phone,
         "email": r.email, "is_disabled": r.is_disabled}
        for r in rows
    ]


def on_site_roster(*, zone_code: str | None = None) -> list[dict]:
    """Live on-site roster (VMS-CFR-017), optionally narrowed to a zone."""
    rows = Visit.objects.filter(status="ON_SITE").order_by("checked_in_at")
    out = []
    for v in rows:
        if zone_code is not None:
            zones = set()
            active = Pass.objects.filter(visit_id=v.id, status="ACTIVE").first()
            if active:
                zones = set(active.permitted_zones)
            if zone_code not in zones:
                continue
        out.append({
            "visit_id": v.id,
            "visitor_id": v.visitor_id,
            "host_user_id": v.host_user_id,
            "checked_in_at": v.checked_in_at,
            "gate_code": v.gate_code,
        })
    return out
