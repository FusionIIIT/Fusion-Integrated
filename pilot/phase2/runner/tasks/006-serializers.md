TITLE: Rewrite API serializers to match the new models
FORMAT: whole
EDIT: modules/leave/api/serializers.py
READ: kit:phase2/DESIGN.md modules/leave/models.py
LIMIT: 1200
POST: none
---
Review findings: the Phase-1 serializers import modules.directory.serializers, which does not exist (Django cannot even start), and describe fields that are not on the models.

Replace the whole content of modules/leave/api/serializers.py with DRF serializers for the models in modules/leave/models.py (read-only):
- LeaveActionSerializer (ModelSerializer: id, actor_id, action, remark, created_at)
- LeaveApplicationSerializer (ModelSerializer, all fields read-only: id, user_id, kind, parent, category, start_date, end_date, half_day, days, purpose, station_leave, station_address, substitute_id, substitute_status, unit_head_id, establishment_id, sanctioning_authority_id, unit_head_recommendation, stage, status, assignee_id, decided_at, created_at, and actions = LeaveActionSerializer(many=True))
- ApplySerializer (Serializer: category ChoiceField from LeaveCategory, start_date, end_date, half_day ChoiceField default "none", purpose CharField, station_leave BooleanField default False, station_address CharField allow_blank default "", substitute_id IntegerField required=False allow_null=True; validate() rejects end_date before start_date)
- DecisionSerializer (decision ChoiceField of approve, reject, recommended, not_recommended, verify; remark CharField allow_blank default "")
- SubstituteResponseSerializer (accept BooleanField)
- ReplaceSubstituteSerializer (substitute_id IntegerField)
- LeaveBalanceSerializer (ModelSerializer: category, year, entitled, used, and available as a read-only DecimalField(max_digits=5, decimal_places=1))
- ReportingLineSerializer (ModelSerializer: user_id read-only, unit_head_id, establishment_id, sanctioning_authority_id)

Import only from rest_framework and modules.leave.models. Write the whole file. Do not ask for more files.

Use exactly these imports at the top of serializers.py and nothing else:

from rest_framework import serializers

from modules.leave.models import HalfDay, LeaveAction, LeaveApplication, LeaveBalance, LeaveCategory, ReportingLine
