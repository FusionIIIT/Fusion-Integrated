"""RSPC permission definitions and constants.
Follows <module>.<resource>.<action> format.
"""

MODULE_CODE = "rspc"

PERMISSIONS = [
    # Research Proposals (UC-002..006)
    ("rspc.proposal.create", "Submit research project proposals"),
    ("rspc.proposal.view_self", "View own submitted research proposals"),
    ("rspc.proposal.view", "View all research project proposals within scope"),
    ("rspc.proposal.recommend_dept", "Record HoD departmental recommendation on proposals"),
    ("rspc.proposal.verify", "Perform RSPC Admin verification on proposals"),
    ("rspc.proposal.approve_dean", "Dean-RSPC review and approval of proposals"),
    ("rspc.proposal.authorize_director", "Director authorization for high-value proposals"),
    # Consultancy Projects (UC-007, 008, 003..006)
    ("rspc.consultancy.create", "Register consultancy projects"),
    ("rspc.consultancy.view_self", "View own registered consultancy projects"),
    ("rspc.consultancy.view", "View all consultancy projects"),
    ("rspc.consultancy.recommend_dept", "Record HoD recommendation on consultancy"),
    ("rspc.consultancy.verify", "Verify consultancy project records"),
    ("rspc.consultancy.approve_dean", "Dean-RSPC review and approval of consultancy"),
    ("rspc.consultancy.authorize_director", "Director authorization for consultancy projects"),
    # Projects Portfolio (UC-001, UC-021)
    ("rspc.project.view_self", "View own active/completed RSPC projects portfolio"),
    ("rspc.project.view", "View institutional RSPC projects portfolio"),
    ("rspc.project.update", "Update project lifecycle details, milestones, and progress"),
    # Staff Appointments (UC-009, 010, 022, 023, 006)
    ("rspc.staff.request", "Submit project staff appointment request"),
    ("rspc.staff.view", "View project staff appointment requests"),
    ("rspc.staff.verify", "Verify staff appointment requests and operational records"),
    ("rspc.staff.recommend", "Record staff selection committee participation & recommendation"),
    ("rspc.staff.approve_dean", "Dean-RSPC decision on staff appointment"),
    ("rspc.staff.authorize_director", "Director decision on staff appointment"),
    # Financial & Fund Requests (UC-011, 012, 024, 006)
    ("rspc.finance.request", "Submit fund utilization or expenditure requests"),
    ("rspc.finance.view", "View project financial and fund requests"),
    ("rspc.finance.verify", "Verify financial and fund requests"),
    ("rspc.finance.approve_dean", "Dean-RSPC approval of financial requests"),
    ("rspc.finance.authorize_director", "Director authorization for high-value financial requests"),
    # Procurement Requests (UC-013, 025, 026, 006)
    ("rspc.procurement.request", "Submit project equipment or consumable procurement requests"),
    ("rspc.procurement.view", "View procurement requests and track status"),
    ("rspc.procurement.verify", "Verify procurement requests and validate project budget"),
    ("rspc.procurement.approve_dean", "Dean-RSPC approval of procurement requests"),
    ("rspc.procurement.authorize_director", "Director authorization for high-value procurement"),
    # Progress & Utilization Reporting (UC-014)
    ("rspc.report.submit", "Submit periodic progress and utilization reports"),
    ("rspc.report.view", "View historical progress and utilization reports"),
    # Project Closure (UC-015, 027, 028, 006)
    ("rspc.closure.submit", "Submit project closure and completion reports"),
    ("rspc.closure.verify", "Verify project closure, settlement, and asset declarations"),
    ("rspc.closure.approve_dean", "Dean-RSPC decision and archival of project closure"),
    ("rspc.closure.authorize_director", "Director decision on project closure"),
    # Notifications, Audit & Integrations (UC-016, 017, 018, 029, 030, 031)
    ("rspc.notification.view_self", "View received RSPC dashboard notifications"),
    ("rspc.audit.view", "View RSPC audit trails, logs, and compliance records"),
    ("rspc.integration.exchange", "Exchange RSPC integration records with Fusion modules"),
    ("rspc.agency.track", "Record and view external funding agency tracking updates"),
    ("rspc.role.sync", "Synchronize RSPC role assignments"),
]

SYSTEM_PERMISSIONS = [
    "rspc.notification.dispatch",
]
