MODULE = {"code": "employee_leave", "label": "Employee Leave",
          "icon": "FaCalendarAlt", "base_path": "/leave",
          "nav_section": "Employee Leave", "sort_order": 30, "status": "active"}

PERMISSIONS = [
    ("employee_leave.application.view_self", "View own leave applications"),
    ("employee_leave.application.create", "Create leave applications"),
    ("employee_leave.application.withdraw", "Withdraw pending applications"),
    ("employee_leave.balance.view", "View leave balances"),
    ("employee_leave.calendar.view", "View the holiday calendar"),
]

NAV_ITEMS = [
    {"code": "employee_leave.dashboard", "label": "Leave Dashboard",
     "icon": "FaCalendarAlt", "to": "/leave", "required_permission":
     "employee_leave.application.view_self", "sort_order": 10},
    {"code": "employee_leave.apply", "label": "Apply for Leave",
     "icon": "FaPlus", "to": "/leave/apply", "required_permission":
     "employee_leave.application.create", "sort_order": 20},
    {"code": "employee_leave.calendar", "label": "Holiday Calendar",
     "icon": "FaRegCalendar", "to": "/leave/calendar", "required_permission":
     "employee_leave.calendar.view", "sort_order": 30},
]

_EMPLOYEE = [code for code, _label in PERMISSIONS]
ROLE_GRANTS = {"student": _EMPLOYEE, "faculty": _EMPLOYEE, "staff": _EMPLOYEE,
               "admin": _EMPLOYEE, "acadadmin": _EMPLOYEE}
