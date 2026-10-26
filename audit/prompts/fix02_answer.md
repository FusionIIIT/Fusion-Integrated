```diff
--- a/role_grants.py
+++ b/role_grants.py
@@ -10,7 +10,7 @@
     ("leave.resumption.review", "Review duty resumption declarations"),
     ("leave.substitute.review", "Accept or decline a nominated substitute responsibility"),
     ("leave.policy.manage", "Configure leave policy, hierarchy and SLA thresholds"),
-    ("leave.calendar.publish", "Maintain and publish the holiday and RH calendar"),
+    ("leave.calendar.publish", "Publish the holiday and RH calendar"),
     ("leave.record.manage", "Record already-sanctioned offline leave and maintain leave records"),
 ]

@@ -20,7 +20,7 @@
 _EMPLOYEE_BASE = [
     "leave.request.create", "leave.request.view_self", "leave.request.delete",
     "leave.resumption.create", "leave.substitute.review",
-]

+]

 _UNIT_HEAD_PERMS = [*_EMPLOYEE_BASE, "leave.request.review"]
 _ESTABLISHMENT_PERMS = [*_EMPLOYEE_BASE, "leave.request.assign", "leave.record.manage"]
 _SANCTION_PERMS = [*_EMPLOYEE_BASE, "leave.request.approve", "leave.resumption.review"]
@@ -30,7 +30,7 @@
     "leave.request.view_self", "leave.request.view", "leave.policy.manage",
     "leave.calendar.publish", "leave.record.manage"
 ]

-ROLE_GRANTS = {
+ROLE_GRANTS = {
     "faculty": _EMPLOYEE_BASE,
     "staff": _EMPLOYEE_BASE,
     "unit_head": _UNIT_HEAD_PERMS,
@@ -39,7 +39,7 @@
     "deputy_registrar": [*_ESTABLISHMENT_PERMS],
     "dean": _SANCTION_PERMS,
     "registrar": _SANCTION_PERMS,
-    "director": [*_SANCTION_PERMS, "leave.request.review"],
+    "director": [*_SANCTION_PERMS, "leave.request.review"],
     "leave_administrator": _ADMIN_PERMS,
 }
```