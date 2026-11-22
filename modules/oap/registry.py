"""What the server tells the shell about this module (ADR-0010).

Every nav item has a client route of the same path in client/src/modules/oap/routes.tsx;
nav_matches_routes.py fails CI when they drift apart.
"""

MODULE = {
    "code": "oap",
    "label": "Other Academic Procedures",
    "icon": "Files",
    "base_path": "/oap",
    "nav_section": "Academics",
    "sort_order": 20,
    "status": "active",
}


def _nav(order, slug, label, icon, permission):
    return {
        "code": f"oap.{slug}",
        "label": label,
        "icon": icon,
        "to": f"/oap/{slug}",
        "required_permission": permission,
        "sort_order": order,
    }


NAV_ITEMS = [
    _nav(10, "leave", "Leave", "CalendarBlank", "oap.leave_application.view_self"),
    _nav(20, "leave-decisions", "Leave Decisions", "Checks", "oap.leave_application.approve"),
    _nav(30, "bonafide", "Bonafide", "Certificate", "oap.bonafide_request.view_self"),
    _nav(40, "bonafide-queue", "Bonafide Queue", "ClipboardText", "oap.bonafide_request.review"),
    _nav(50, "no-dues", "No-Dues", "ShieldCheck", "oap.no_dues_case.view_self"),
    _nav(60, "no-dues-queue", "No-Dues Queue", "Users", "oap.no_dues_case.view"),
    _nav(70, "claims", "Assistantship", "Wallet", "oap.assistantship_claim.view_self"),
    _nav(80, "claim-queue", "Claim Queue", "Briefcase", "oap.assistantship_claim.view"),
    _nav(
        90, "verifications", "Verifications", "Signature", "oap.assistantship_verification.review"
    ),
    _nav(100, "assignments", "Assignments", "UserCheck", "oap.thesis_supervisor_assignment.view"),
    _nav(110, "seminars", "Seminars", "GraduationCap", "oap.seminar_request.view_self"),
    _nav(120, "seminar-queue", "Seminar Queue", "Presentation", "oap.seminar_request.view"),
    _nav(
        130, "seminar-schedules", "Seminar Schedules", "CalendarBlank", "oap.seminar_schedule.view"
    ),
    _nav(140, "notifications", "Alerts", "Bell", "oap.notification.view_self"),
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("oap.leave_application.create", "Submit a leave application"),
    ("oap.leave_application.view_self", "See one's own leave applications"),
    ("oap.leave_application.view", "See leave applications routed to you"),
    ("oap.leave_application.approve", "Approve or reject a leave application"),
    ("oap.bonafide_request.create", "Request a bonafide certificate"),
    ("oap.bonafide_request.view_self", "See one's own bonafide requests"),
    ("oap.bonafide_request.view", "See bonafide requests routed to you"),
    ("oap.bonafide_request.review", "Verify a bonafide request"),
    ("oap.bonafide_request.approve", "Approve or reject a bonafide request"),
    ("oap.bonafide_certificate.view_self", "Download one's own approved bonafide certificate"),
    ("oap.no_dues_case.create", "Initiate no-dues clearance"),
    ("oap.no_dues_case.view_self", "Track one's own no-dues clearance"),
    ("oap.no_dues_case.view", "See no-dues cases for clearance"),
    ("oap.no_dues_case.approve", "Finalize no-dues clearance"),
    ("oap.no_dues_result.update", "Record one's own no-dues domain result"),
    ("oap.no_dues_certificate.view_self", "Download one's own no-dues certificate"),
    ("oap.assistantship_claim.create", "Submit an assistantship claim"),
    ("oap.assistantship_claim.view_self", "Track one's own assistantship claims"),
    ("oap.assistantship_claim.view", "See assistantship claims routed to you"),
    ("oap.assistantship_claim.review", "Review and forward an assistantship claim"),
    ("oap.assistantship_claim.approve", "Approve or reject an assistantship claim"),
    ("oap.assistantship_claim.update", "Record stipend processing"),
    ("oap.assistantship_verification.review", "Verify a claim in an assigned supervisor role"),
    ("oap.thesis_supervisor_assignment.assign", "Record a thesis-supervisor assignment"),
    ("oap.thesis_supervisor_assignment.view", "See thesis-supervisor assignments"),
    ("oap.ta_assignment.assign", "Record a TA assignment"),
    ("oap.ta_assignment.view", "See TA assignments"),
    ("oap.seminar_request.create", "Request graduate seminar scheduling"),
    ("oap.seminar_request.view_self", "See one's own seminar requests"),
    ("oap.seminar_request.view", "See seminar requests routed to you"),
    ("oap.seminar_schedule.update", "Schedule and log a graduate seminar"),
    ("oap.seminar_schedule.view", "View graduate seminar schedules"),
    ("oap.notification.view_self", "See one's own OAP alerts"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS: list[str] = []

_STUDENT = [
    "oap.leave_application.create",
    "oap.leave_application.view_self",
    "oap.bonafide_request.create",
    "oap.bonafide_request.view_self",
    "oap.bonafide_certificate.view_self",
    "oap.no_dues_case.create",
    "oap.no_dues_case.view_self",
    "oap.no_dues_certificate.view_self",
    "oap.notification.view_self",
]

_PG_STUDENT = [
    "oap.assistantship_claim.create",
    "oap.assistantship_claim.view_self",
    "oap.seminar_request.create",
    "oap.seminar_request.view_self",
    "oap.seminar_schedule.view",
]

_FACULTY = [
    "oap.assistantship_verification.review",
    "oap.seminar_schedule.view",
]

_HOD = [
    "oap.leave_application.view",
    "oap.leave_application.approve",
    "oap.assistantship_claim.view",
    "oap.assistantship_claim.approve",
]

_ACADEMIC_ADMIN = [
    "oap.bonafide_request.view",
    "oap.bonafide_request.review",
    "oap.bonafide_request.approve",
    "oap.no_dues_case.view",
    "oap.no_dues_case.approve",
    "oap.assistantship_claim.view",
    "oap.assistantship_claim.update",
]

_DEPARTMENT_ADMIN = [
    "oap.thesis_supervisor_assignment.assign",
    "oap.thesis_supervisor_assignment.view",
    "oap.ta_assignment.assign",
    "oap.ta_assignment.view",
    "oap.assistantship_claim.view",
    "oap.assistantship_claim.review",
    "oap.seminar_request.view",
    "oap.seminar_schedule.update",
    "oap.seminar_schedule.view",
]

_NO_DUES_AUTHORITY = [
    "oap.no_dues_result.update",
    "oap.no_dues_case.view",
]

#: Keyed by the designation name as it exists in globals_designation.
#: Names marked open in docs/09-oap/oap-blueprint.md (Gap G1, G2) must be confirmed.
ROLE_GRANTS = {
    "student": _STUDENT,
    "PG Student": _PG_STUDENT,
    "faculty": _FACULTY,
    "Head of Department": _HOD,
    "Academic Administrator": _ACADEMIC_ADMIN,
    "Department Administrator": _DEPARTMENT_ADMIN,
    "Librarian": _NO_DUES_AUTHORITY,
    "Hostel Warden": _NO_DUES_AUTHORITY,
    "Mess In-charge": _NO_DUES_AUTHORITY,
    "Lab Supervisor": _NO_DUES_AUTHORITY,
}
