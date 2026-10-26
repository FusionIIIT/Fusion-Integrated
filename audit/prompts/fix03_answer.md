```python
ROLE_GRANTS = {
    "faculty": ["leave.request.create", "leave.request.view_self", "leave.request.delete", "leave.resumption.create", "leave.substitute.review"],
    "staff": ["leave.request.create", "leave.request.view_self", "leave.request.delete", "leave.resumption.create", "leave.substitute.review"],
    "unit_head": ["leave.request.create", "leave.request.view_self", "leave.request.delete", "leave.resumption.create", "leave.substitute.review", "leave.request.review", "leave.request.view"],
    "hod": ["leave.request.create", "leave.request.view_self", "leave.request.delete", "leave.resumption.create", "leave.substitute.review", "leave.request.review", "leave.request.view"],
    "deputy_registrar": ["leave.request.create", "leave.request.view_self", "leave.request.delete", "leave.resumption.create", "leave.substitute.review", "leave.request.assign", "leave.request.view"],
    "dean": ["leave.request.create", "leave.request.view_self", "leave.request.delete", "leave.resumption.create", "leave.substitute.review", "leave.request.approve", "leave.resumption.review", "leave.request.view"],
    "registrar": ["leave.request.create", "leave.request.view_self", "leave.request.delete", "leave.resumption.create", "leave.substitute.review", "leave.request.approve", "leave.resumption.review", "leave.request.view"],
    "director": ["leave.request.create", "leave.request.view_self", "leave.request.delete", "leave.resumption.create", "leave.substitute.review", "leave.request.approve", "leave.resumption.review", "leave.request.view", "leave.request.review"],
    "leave_administrator": ["leave.request.view_self", "leave.request.view", "leave.policy.manage", "leave.calendar.publish", "leave.record.manage"]
}
```