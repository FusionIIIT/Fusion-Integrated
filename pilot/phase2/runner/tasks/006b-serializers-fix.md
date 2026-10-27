TITLE: Fix the actions field in LeaveApplicationSerializer found in review of 006
FORMAT: diff
EDIT: modules/leave/api/serializers.py
READ: modules/leave/models.py
LIMIT: 600
POST: none
---
Review of task 006. LeaveApplicationSerializer declares `actions = LeaveActionSerializer(many=True)` but "actions" is missing from Meta.fields, so DRF raises AssertionError ("The field 'actions' was declared ... but has not been included in the 'fields' option") on the first response. The serializer is output-only. Fix only this, with SEARCH/REPLACE edits:

1. Change `actions = LeaveActionSerializer(many=True)` to `actions = LeaveActionSerializer(many=True, read_only=True)`.
2. Add "actions" as the last entry of LeaveApplicationSerializer.Meta.fields (after "created_at").
3. Add `read_only_fields = fields` inside that Meta, after the fields list, and remove LeaveApplicationSerializer's __init__ method (it is no longer needed).

Do not change anything else.
