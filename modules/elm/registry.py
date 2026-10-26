MODULE = {
    "code": "employee_leave_management", "label": "Employee Leave Management",
    "icon": "Calendar", "base_path": "/elm", "nav_section": "Employee Services",
    "sort_order": 20, "status": "active",
}
NAV_ITEMS = [
    {"code":"elm.my-leave","label":"My Leave","icon":"Calendar","to":"/elm","required_permission":"elm.leave.view_self","sort_order":10},
    {"code":"elm.apply","label":"Apply Leave","icon":"Plus","to":"/elm/apply","required_permission":"elm.leave.create","sort_order":20},
    {"code":"elm.balances","label":"Balances & History","icon":"ChartBar","to":"/elm/balances","required_permission":"elm.leave.view_self","sort_order":30},
    {"code":"elm.pending","label":"Pending Reviews","icon":"Checks","to":"/elm/reviews","required_permission":"elm.leave.review","sort_order":40},
    {"code":"elm.admin","label":"ELM Administration","icon":"Settings","to":"/elm/admin","required_permission":"elm.admin.manage","sort_order":50},
]
PERMISSIONS = [
    ("elm.leave.view_self","View own leave requests and balances"),
    ("elm.leave.create","Create and submit leave requests"),
    ("elm.leave.withdraw","Withdraw pending requests"),
    ("elm.leave.review","Review and decide leave requests"),
    ("elm.leave.cancel","Review approved leave cancellation"),
    ("elm.leave.extension","Review leave extensions"),
    ("elm.leave.resumption","Review resumption"),
    ("elm.admin.manage","Maintain ELM policy, holiday and SLA configuration"),
    ("elm.admin.records","Maintain authorized leave records"),
    ("elm.admin.offline","Record already-sanctioned offline leave"),
]
_EMPLOYEE=["elm.leave.view_self","elm.leave.create","elm.leave.withdraw"]
_REVIEWER=["elm.leave.view_self","elm.leave.review","elm.leave.cancel","elm.leave.extension","elm.leave.resumption"]
_ADMIN=[*_REVIEWER,"elm.admin.manage","elm.admin.records","elm.admin.offline"]
ROLE_GRANTS={"student":_EMPLOYEE,"employee":_EMPLOYEE,"faculty":_EMPLOYEE,"unit_head":_REVIEWER,"leave_administrator":_ADMIN,"elm_administrator":_ADMIN,"Dean":_REVIEWER,"Registrar":_REVIEWER,"Director":_REVIEWER,"Deputy Registrar (Estt.)":_REVIEWER}
