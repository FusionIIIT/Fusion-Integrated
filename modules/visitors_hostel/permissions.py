MODULE_CODE = "visitor_hostel"

PERMISSIONS = [
    ("visitor_hostel.booking.view_self", "View own booking requests"),
    ("visitor_hostel.booking.create", "Submit an online booking request"),
    ("visitor_hostel.booking.modify_self", "Request a booking modification"),
    ("visitor_hostel.booking.cancel_self", "Request booking cancellation"),
    ("visitor_hostel.booking.view", "View operational booking requests"),
    ("visitor_hostel.booking.record_offline", "Record an offline booking"),
    ("visitor_hostel.booking.review", "Review and route booking requests"),
    ("visitor_hostel.booking.decide", "Approve or reject forwarded requests"),
    ("visitor_hostel.room.manage", "Manage rooms and room allotments"),
    ("visitor_hostel.stay.manage", "Record guest check-in and check-out"),
    ("visitor_hostel.tariff.manage", "Manage visitor categories and tariffs"),
    ("visitor_hostel.meal.manage", "Manage guest meal bookings"),
    ("visitor_hostel.bill.manage", "Generate bills and record offline settlement"),
    ("visitor_hostel.inventory.manage", "Maintain Visitors Hostel inventory"),
    ("visitor_hostel.inventory.approve", "Review replenishment requirements"),
    ("visitor_hostel.report.view_caretaker", "View Caretaker operational reports"),
    ("visitor_hostel.report.view_in_charge", "View VH In-Charge reports"),
    ("visitor_hostel.role.view", "View VH operational role assignments"),
    ("visitor_hostel.notification.view_self", "View own VHMS notifications"),
]

SYSTEM_PERMISSIONS = [
    "visitor_hostel.notification.emit",
    "visitor_hostel.stay.alert",
    "visitor_hostel.inventory.alert",
]

_INDENTER = [
    "visitor_hostel.booking.view_self", "visitor_hostel.booking.create",
    "visitor_hostel.booking.modify_self", "visitor_hostel.booking.cancel_self",
    "visitor_hostel.notification.view_self",
]
_CARETAKER = [
    "visitor_hostel.booking.view", "visitor_hostel.booking.record_offline",
    "visitor_hostel.booking.review", "visitor_hostel.room.manage",
    "visitor_hostel.stay.manage", "visitor_hostel.meal.manage",
    "visitor_hostel.bill.manage", "visitor_hostel.inventory.manage",
    "visitor_hostel.role.view",
    "visitor_hostel.report.view_caretaker",
    "visitor_hostel.notification.view_self",
]
_IN_CHARGE = [
    "visitor_hostel.booking.view", "visitor_hostel.booking.decide",
    "visitor_hostel.tariff.manage",
    "visitor_hostel.inventory.approve",
    "visitor_hostel.report.view_in_charge",
    "visitor_hostel.role.view",
    "visitor_hostel.notification.view_self",
]

# IAM designation identifiers must be confirmed/configured by the platform.
# These grants declare intended capability sets; they do not create users or
# perform platform-level role assignment.
ROLE_GRANTS = {
    "indenter": _INDENTER,
    "caretaker": _CARETAKER,
    "vh_in_charge": _IN_CHARGE,
}
