TITLE: Fix the kind field length that stops Django from starting
FORMAT: diff
EDIT: modules/leave/models.py
LIMIT: 600
POST: none
---
Task 008's makemigrations and permission_manifest both failed with:
leave.LeaveApplication.kind: (fields.E009) 'max_length' is too small to fit the longest value in 'choices' (12 characters).
The longest RequestKind value is "cancellation" (12 characters). Fix only this, with one SEARCH/REPLACE edit: in LeaveApplication.kind change max_length=10 to max_length=12. Do not change anything else.
