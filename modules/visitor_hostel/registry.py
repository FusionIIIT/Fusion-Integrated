"""What the server tells the shell about this module (ADR-0010), and who holds
which permission. Every nav item carries `required_permission`, so a role sees
only its own screens.

`status` stays "planned" until the client pages under
client/src/modules/visitor_hostel/ exist; seeding also holds it there while
`readiness()` reports anything unmet.
"""
MODULE = {
    "code": "visitor_hostel", "label": "Visitors Hostel", "icon": "House",
    "base_path": "/visitorhostel", "nav_section": "Campus", "sort_order": 20,
    "status": "planned",
}

NAV_ITEMS = [
    # -- Indenter ----------------------------------------------------------------
    {"code": "vh.book", "label": "Book a Room", "icon": "CalendarPlus",
     "to": "/visitorhostel/book",
     "required_permission": "visitor_hostel.booking.create", "sort_order": 10},
    {"code": "vh.mine", "label": "My Bookings", "icon": "ListChecks",
     "to": "/visitorhostel/mine",
     "required_permission": "visitor_hostel.booking.view_self", "sort_order": 20},

    # -- Caretaker ---------------------------------------------------------------
    {"code": "vh.queue", "label": "Booking Requests", "icon": "Tray",
     "to": "/visitorhostel/queue",
     "required_permission": "visitor_hostel.booking.review", "sort_order": 30},
    {"code": "vh.stays", "label": "Rooms & Stays", "icon": "Bed",
     "to": "/visitorhostel/stays",
     "required_permission": "visitor_hostel.stay.update", "sort_order": 40},
    {"code": "vh.billing", "label": "Billing", "icon": "Receipt",
     "to": "/visitorhostel/billing",
     "required_permission": "visitor_hostel.bill.manage", "sort_order": 50},
    {"code": "vh.inventory", "label": "Inventory", "icon": "Package",
     "to": "/visitorhostel/inventory",
     "required_permission": "visitor_hostel.inventory.manage", "sort_order": 60},
    {"code": "vh.operations", "label": "Daily Reports", "icon": "ClipboardText",
     "to": "/visitorhostel/operations",
     "required_permission": "visitor_hostel.operations_report.view",
     "sort_order": 70},

    # -- VH In-Charge ------------------------------------------------------------
    {"code": "vh.approvals", "label": "Approvals", "icon": "SealCheck",
     "to": "/visitorhostel/approvals",
     "required_permission": "visitor_hostel.booking.approve", "sort_order": 80},
    {"code": "vh.replenishment", "label": "Replenishment", "icon": "ShoppingCart",
     "to": "/visitorhostel/replenishment",
     "required_permission": "visitor_hostel.replenishment.approve",
     "sort_order": 90},
    {"code": "vh.reports", "label": "Reports", "icon": "ChartBar",
     "to": "/visitorhostel/reports",
     "required_permission": "visitor_hostel.report.view", "sort_order": 100},
]

#: Every permission this module recognises; ROLE_GRANTS says who holds each.
PERMISSIONS = [
    ("visitor_hostel.booking.create", "Submit a booking request for a visitor"),
    ("visitor_hostel.booking.view_self", "See one's own bookings"),
    ("visitor_hostel.modification.create", "Request a booking modification"),
    ("visitor_hostel.cancellation.create", "Request a booking cancellation"),
    ("visitor_hostel.booking.view", "See every booking, online and offline"),
    ("visitor_hostel.booking.review", "Review, forward or reject a booking"),
    ("visitor_hostel.offline_booking.create", "Record a telephonic or walk-in booking"),
    ("visitor_hostel.cancellation.approve", "Confirm a cancellation request"),
    ("visitor_hostel.room.manage", "Maintain rooms and allot them"),
    ("visitor_hostel.stay.update", "Record check-in and check-out"),
    ("visitor_hostel.meal.manage", "Record meal bookings for guests"),
    ("visitor_hostel.bill.manage", "Generate bills and record settlement"),
    ("visitor_hostel.inventory.manage", "Maintain VH inventory"),
    ("visitor_hostel.replenishment.create", "Record a replenishment requirement"),
    ("visitor_hostel.operations_report.view", "See the Caretaker's daily reports"),
    ("visitor_hostel.alert.view", "See no-show and overstay alerts"),
    ("visitor_hostel.booking.approve", "Approve or reject a forwarded booking"),
    ("visitor_hostel.bill.view", "Review finalized bills and meal records"),
    ("visitor_hostel.inventory.view", "Review VH inventory"),
    ("visitor_hostel.replenishment.approve", "Approve a replenishment requirement"),
    ("visitor_hostel.report.view", "See the VH In-Charge's reports"),
    ("visitor_hostel.tariff.view", "See visitor categories and tariffs"),
    ("visitor_hostel.duty.view", "See who is on duty"),
    ("visitor_hostel.tariff.manage", "Record a new tariff version"),
    ("visitor_hostel.duty.manage", "Reassign the Caretaker or VH In-Charge"),
    ("visitor_hostel.modification.approve", "Confirm a booking modification"),
]

#: The spec names no holder for these (UC-VH-011, 019, 022). Operators act via
#: management commands until the institute decides, then they move to a role.
SYSTEM_PERMISSIONS = [
    "visitor_hostel.tariff.manage",
    "visitor_hostel.duty.manage",
    "visitor_hostel.modification.approve",
]

#: Holding one widens which bookings a role sees; scoping.py enforces it.
SCOPE_PERMISSIONS = [
    "visitor_hostel.booking.view",
]

_INDENTER = [
    "visitor_hostel.booking.create",
    "visitor_hostel.booking.view_self",
    "visitor_hostel.modification.create",
    "visitor_hostel.cancellation.create",
]

_CARETAKER = [
    "visitor_hostel.booking.view",
    "visitor_hostel.booking.review",
    "visitor_hostel.offline_booking.create",
    "visitor_hostel.cancellation.approve",
    "visitor_hostel.room.manage",
    "visitor_hostel.stay.update",
    "visitor_hostel.meal.manage",
    "visitor_hostel.bill.manage",
    "visitor_hostel.inventory.manage",
    "visitor_hostel.replenishment.create",
    "visitor_hostel.operations_report.view",
    "visitor_hostel.alert.view",
    "visitor_hostel.tariff.view",
    "visitor_hostel.duty.view",
]

_INCHARGE = [
    "visitor_hostel.booking.view",
    "visitor_hostel.booking.approve",
    "visitor_hostel.bill.view",
    "visitor_hostel.inventory.view",
    "visitor_hostel.replenishment.approve",
    "visitor_hostel.report.view",
    "visitor_hostel.tariff.view",
    "visitor_hostel.duty.view",
]

#: Keyed by designation name as globals_designation spells it. VhCaretaker and
#: VhIncharge are the legacy Fusion names; confirm them against the ERP.
ROLE_GRANTS = {
    "student": _INDENTER,
    "faculty": _INDENTER,
    "staff": _INDENTER,
    "VhCaretaker": _CARETAKER,
    "VhIncharge": _INCHARGE,
}


def readiness() -> list[str]:
    """What must exist before the module can take its first booking."""
    from django.db.utils import DatabaseError

    try:
        from modules.visitor_hostel.domain import duty, meals, tariffs
        from modules.visitor_hostel.models import MealTariff, Room, RoomTariff
        from modules.visitor_hostel.selectors import duty as duty_selectors

        unmet = []
        if not Room.objects.filter(is_active=True).exists():
            unmet.append("no active rooms are recorded")
        have = set(RoomTariff.objects.values_list("category", "occupancy"))
        missing = [f"{c}/{o}" for c in tariffs.CATEGORIES for o in tariffs.OCCUPANCIES
                   if (c, o) not in have]
        if missing:
            unmet.append(f"no room tariff for {', '.join(missing)} "
                         f"(manage.py vh_set_tariff)")
        priced = set(MealTariff.objects.values_list("item", flat=True))
        if set(meals.PRICED_ITEMS) - priced:
            unmet.append("no meal tariff for "
                         f"{', '.join(sorted(set(meals.PRICED_ITEMS) - priced))}")
        unmet.extend(f"no {duty.LABELS[role]} is on duty "
                     f"(manage.py vh_assign_duty --role {role})"
                     for role in duty.ROLES if duty_selectors.current(role) is None)
    except DatabaseError as exc:
        return [f"database not ready: {exc.__class__.__name__} — run migrate"]
    return unmet
