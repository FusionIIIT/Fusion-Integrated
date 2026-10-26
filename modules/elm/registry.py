"""Server-side module and navigation declaration for the ELM MVP."""

MODULE = {
    "code": "elm_leave",
    "label": "Employee Leave",
    "icon": "Calendar",
    "base_path": "/apply_leave",
    "nav_section": "People",
    "sort_order": 30,
    "status": "active",
}

# The two self-service pages are usable in the MVP. Approvals remains visible
# only so users can see the explicit not-yet-implemented notice.
NAV_ITEMS = [
    {
        "code": "elm_leave.apply",
        "label": "Apply Leave",
        "icon": "CalendarPlus",
        "to": "/apply_leave/apply",
        "required_permission": "",
        "sort_order": 10,
    },
    {
        "code": "elm_leave.my_leaves",
        "label": "My Leaves",
        "icon": "CalendarCheck",
        "to": "/apply_leave/my-leaves",
        "required_permission": "",
        "sort_order": 20,
    },
    {
        "code": "elm_leave.approvals",
        "label": "Approvals (coming soon)",
        "icon": "CalendarClock",
        "to": "/apply_leave/approvals",
        "required_permission": "",
        "sort_order": 30,
    },
]
