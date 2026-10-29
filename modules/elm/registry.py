MODULE = {"code": "elm", "label": "Employee Leave Management", "icon": "CalendarCheck", "base_path": "/elm", "nav_section": "Employee Services", "sort_order": 20, "status": "active"}
NAV_ITEMS = [
 {"code":"elm.my-leave","label":"My Leave","icon":"CalendarDays","to":"/elm/my-leave","required_permission":"elm.leave.view_self","sort_order":10},
 {"code":"elm.apply","label":"Apply for Leave","icon":"CalendarPlus","to":"/elm/apply","required_permission":"elm.leave.apply","sort_order":20},
 {"code":"elm.substitute","label":"Substitute Requests","icon":"Users","to":"/elm/substitute-requests","required_permission":"elm.substitute.respond","sort_order":30},
 {"code":"elm.approvals","label":"Leave Approvals","icon":"ClipboardCheck","to":"/elm/approvals","required_permission":"elm.leave.review","sort_order":40},
 {"code":"elm.admin","label":"ELM Administration","icon":"Settings","to":"/elm/admin","required_permission":"elm.leave.configure","sort_order":50},
]
PERMISSIONS = [("elm.leave.view_self","View own leave requests and balances"),("elm.leave.apply","Submit own leave requests"),("elm.substitute.respond","Respond to substitute requests"),("elm.leave.review","Review and sanction leave requests"),("elm.leave.configure","Configure ELM policies and calendars"),("elm.leave.view_all","View leave records for administration")]
SYSTEM_PERMISSIONS = []
ROLE_GRANTS = {
 "student": ["elm.leave.view_self","elm.leave.apply"],
 "faculty": ["elm.leave.view_self","elm.leave.apply","elm.substitute.respond"],
 "staff": ["elm.leave.view_self","elm.leave.apply","elm.substitute.respond"],
 "leave_administrator": ["elm.leave.view_self","elm.leave.view_all","elm.leave.configure"],
 "unit_head": ["elm.leave.view_self","elm.leave.apply","elm.substitute.respond","elm.leave.review"],
}
