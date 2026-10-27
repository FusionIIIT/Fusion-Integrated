"""Permission declarations for the Employee Leave Management (ELM) module."""

MODULE_CODE = "elm"

PERMISSIONS = [
    ("elm.leave.apply", "Apply for personal leave and manage own requests"),
    ("elm.leave.view_self", "View own leave balances, history, and applications"),
    ("elm.leave.substitute", "Respond to substitute responsibility nominations"),
    ("elm.leave.unit_head_review", "Unit Head review, sanction CL/RH, recommend higher leave"),
    ("elm.leave.establishment_review", "Establishment section verification and routing"),
    ("elm.leave.sanction", "Final sanctioning authority for higher-level leave"),
    ("elm.leave.admin", "Maintain leave policies, calendars, hierarchies, and offline records"),
    ("elm.leave.report", "Access institutional leave reports and records"),
]
