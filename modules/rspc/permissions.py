"""RSPC module permissions and role grants.

Module code: rspc
Actors: Faculty, HoD, RSPC Admin, Dean-RSPC, Director
"""

MODULE_CODE = "rspc"

PERMISSIONS = [
    # Research project proposal
    ("rspc.proposal.create",           "Submit a research project proposal"),
    ("rspc.proposal.view_self",        "View own proposals"),
    ("rspc.proposal.view",             "View all proposals (within scope)"),
    ("rspc.proposal.review_hod",       "Review proposal as HoD"),
    ("rspc.proposal.verify_admin",     "Verify and forward proposals as RSPC Admin"),
    ("rspc.proposal.decide_dean",      "Approve/reject proposals as Dean-RSPC"),
    ("rspc.proposal.decide_director",  "Authorize proposals as Director"),

    # Consultancy project
    ("rspc.consultancy.create",        "Register a consultancy project"),
    ("rspc.consultancy.view_self",     "View own consultancy projects"),
    ("rspc.consultancy.view",          "View all consultancy projects"),
    ("rspc.consultancy.review_hod",    "Review consultancy as HoD"),
    ("rspc.consultancy.verify_admin",  "Verify consultancy as RSPC Admin"),
    ("rspc.consultancy.decide_dean",   "Decide consultancy as Dean-RSPC"),
    ("rspc.consultancy.decide_director", "Authorize consultancy as Director"),

    # Staff appointment
    ("rspc.appointment.create",        "Request project-based staff appointment"),
    ("rspc.appointment.view_self",     "View own appointment requests"),
    ("rspc.appointment.view",          "View all appointment requests"),
    ("rspc.appointment.manage_admin",  "Manage appointment records as RSPC Admin"),
    ("rspc.appointment.recommend",     "Record selection recommendation as Faculty"),
    ("rspc.appointment.decide_dean",   "Approve/forward appointment as Dean-RSPC"),
    ("rspc.appointment.decide_director", "Authorize appointment as Director"),

    # Financial / fund requests
    ("rspc.finance.create",            "Submit fund-utilization or expenditure request"),
    ("rspc.finance.view_self",         "View own financial requests"),
    ("rspc.finance.view",              "View all financial requests"),
    ("rspc.finance.verify_admin",      "Verify financial requests as RSPC Admin"),
    ("rspc.finance.decide_dean",       "Approve/forward financial requests as Dean-RSPC"),
    ("rspc.finance.decide_director",   "Authorize financial requests as Director"),

    # Procurement
    ("rspc.procurement.create",        "Request equipment or consumable procurement"),
    ("rspc.procurement.view_self",     "View own procurement requests"),
    ("rspc.procurement.view",          "View all procurement requests"),
    ("rspc.procurement.verify_admin",  "Verify procurement requests as RSPC Admin"),
    ("rspc.procurement.decide_dean",   "Approve/forward procurement as Dean-RSPC"),
    ("rspc.procurement.decide_director", "Authorize procurement as Director"),

    # Progress reports
    ("rspc.progress_report.submit",    "Submit periodic progress report"),
    ("rspc.progress_report.view_self", "View own progress reports"),
    ("rspc.progress_report.view",      "View all progress reports"),
    ("rspc.progress_report.manage",    "Manage/review progress reports as Admin/Dean"),

    # Project closure
    ("rspc.closure.submit",            "Submit project closure report"),
    ("rspc.closure.view_self",         "View own closure records"),
    ("rspc.closure.view",              "View all closure records"),
    ("rspc.closure.verify_admin",      "Verify closure records as RSPC Admin"),
    ("rspc.closure.decide_dean",       "Approve closure as Dean-RSPC"),

    # Reports / admin dashboard
    ("rspc.report.view",               "View RSPC operational reports and statistics"),
    ("rspc.report.manage",             "Manage all RSPC records (admin)"),
]

SYSTEM_PERMISSIONS: list[str] = []

_FACULTY = [
    "rspc.proposal.create",
    "rspc.proposal.view_self",
    "rspc.consultancy.create",
    "rspc.consultancy.view_self",
    "rspc.appointment.create",
    "rspc.appointment.view_self",
    "rspc.appointment.recommend",
    "rspc.finance.create",
    "rspc.finance.view_self",
    "rspc.procurement.create",
    "rspc.procurement.view_self",
    "rspc.progress_report.submit",
    "rspc.progress_report.view_self",
    "rspc.closure.submit",
    "rspc.closure.view_self",
]

_HOD = [
    *_FACULTY,
    "rspc.proposal.view",
    "rspc.proposal.review_hod",
    "rspc.consultancy.view",
    "rspc.consultancy.review_hod",
    "rspc.progress_report.view",
    "rspc.closure.view",
]

_RSPC_ADMIN = [
    "rspc.proposal.view",
    "rspc.proposal.verify_admin",
    "rspc.consultancy.view",
    "rspc.consultancy.verify_admin",
    "rspc.appointment.view",
    "rspc.appointment.manage_admin",
    "rspc.finance.view",
    "rspc.finance.verify_admin",
    "rspc.procurement.view",
    "rspc.procurement.verify_admin",
    "rspc.progress_report.view",
    "rspc.progress_report.manage",
    "rspc.closure.view",
    "rspc.closure.verify_admin",
    "rspc.report.view",
    "rspc.report.manage",
]

_DEAN_RSPC = [
    "rspc.proposal.view",
    "rspc.proposal.decide_dean",
    "rspc.consultancy.view",
    "rspc.consultancy.decide_dean",
    "rspc.appointment.view",
    "rspc.appointment.decide_dean",
    "rspc.finance.view",
    "rspc.finance.decide_dean",
    "rspc.procurement.view",
    "rspc.procurement.decide_dean",
    "rspc.progress_report.view",
    "rspc.closure.view",
    "rspc.closure.decide_dean",
    "rspc.report.view",
]

_DIRECTOR = [
    "rspc.proposal.view",
    "rspc.proposal.decide_director",
    "rspc.consultancy.view",
    "rspc.consultancy.decide_director",
    "rspc.appointment.view",
    "rspc.appointment.decide_director",
    "rspc.finance.view",
    "rspc.finance.decide_director",
    "rspc.procurement.view",
    "rspc.procurement.decide_director",
    "rspc.progress_report.view",
    "rspc.closure.view",
    "rspc.report.view",
]

ROLE_GRANTS = {
    "faculty":      _FACULTY,
    "hod":          _HOD,
    "rspc_admin":   _RSPC_ADMIN,
    "dean_rspc":    _DEAN_RSPC,
    "director":     _DIRECTOR,
    "Dean Academic": _DEAN_RSPC,
}
