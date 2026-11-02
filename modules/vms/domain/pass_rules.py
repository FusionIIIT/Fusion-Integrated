"""Gate validation rules (pure Python). BR-077, BR-082, BR-190, BR-191, BR-085 / D-14.

``validate_at_gate`` returns *all* failures in rule order; the caller decides which to log.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

PASS_INACTIVE = "pass_inactive"
OUTSIDE_VALIDITY = "outside_validity"
OUTSIDE_SLOT = "outside_slot"
BLACKLISTED = "blacklisted"
ZONE_NOT_PERMITTED = "zone_not_permitted"
ALREADY_INSIDE = "already_inside"
TERMINATED = "terminated"

#: Evaluation order (BR-077, 190, 112, 191, then state conflicts).
FAILURE_ORDER = (PASS_INACTIVE, OUTSIDE_VALIDITY, OUTSIDE_SLOT, BLACKLISTED,
                 ZONE_NOT_PERMITTED, ALREADY_INSIDE, TERMINATED)

#: Failures an Admin may override (BR-085, decision D-14). One-line edit to change the answer.
OVERRIDE_ELIGIBLE = frozenset({PASS_INACTIVE, OUTSIDE_VALIDITY, ZONE_NOT_PERMITTED, OUTSIDE_SLOT})

_RULE = {PASS_INACTIVE: "VMS-BR-077", OUTSIDE_VALIDITY: "VMS-BR-190", OUTSIDE_SLOT: "VMS-BR-190",
         BLACKLISTED: "VMS-BR-112", ZONE_NOT_PERMITTED: "VMS-BR-191",
         ALREADY_INSIDE: "VMS-BR-082", TERMINATED: "VMS-BR-077"}


@dataclass(frozen=True)
class Failure:
    code: str
    rule: str
    message: str


def _fail(code: str, message: str) -> Failure:
    return Failure(code, _RULE[code], message)


def validate_at_gate(pass_, now: datetime, zone_id, policy=None, blacklisted: bool = False,
                     open_checkin: bool = False) -> list[Failure]:
    """Check a presented pass. Duck-typed inputs:

    pass_   : is_active, terminated, valid_from, valid_until, allowed_zone_ids (pass zones plus
              active elevations; empty = every non-restricted zone), optional slot_start/slot_end
    policy  : optional, restricted_zone_ids (zones needing explicit permission)
    zone_id : target zone, or None for a plain gate entry with no zone check

    A terminated pass reports ``terminated`` only (not also ``pass_inactive``), so that
    ``pass_inactive`` stays overridable while ``terminated`` does not (D-14).
    """
    out: list[Failure] = []
    terminated = bool(getattr(pass_, "terminated", False))
    if not pass_.is_active and not terminated:
        out.append(_fail(PASS_INACTIVE, "Pass is not active."))
    if now < pass_.valid_from or now > pass_.valid_until:
        out.append(_fail(OUTSIDE_VALIDITY, "Outside the pass validity window."))
    slot_start = getattr(pass_, "slot_start", None)
    slot_end = getattr(pass_, "slot_end", None)
    if slot_start is not None and slot_end is not None and not (slot_start <= now <= slot_end):
        out.append(_fail(OUTSIDE_SLOT, "Outside the event slot."))
    if blacklisted:
        out.append(_fail(BLACKLISTED, "Visitor matches a published blacklist entry."))
    if zone_id is not None:
        allowed = set(getattr(pass_, "allowed_zone_ids", ()) or ())
        restricted = set(getattr(policy, "restricted_zone_ids", ()) or ()) if policy else set()
        permitted = zone_id in allowed or (not allowed and zone_id not in restricted)
        if not permitted:
            out.append(_fail(ZONE_NOT_PERMITTED, "Zone not permitted for this pass."))
    if open_checkin:
        out.append(_fail(ALREADY_INSIDE, "Visitor already has an open check-in."))
    if terminated:
        out.append(_fail(TERMINATED, "Pass was terminated."))
    return out


def is_overridable(failures: list[Failure]) -> bool:
    """True when there is at least one failure and every one is override-eligible."""
    return bool(failures) and all(f.code in OVERRIDE_ELIGIBLE for f in failures)
