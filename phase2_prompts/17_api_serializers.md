# Task: write modules/leave/api/serializers.py (output the COMPLETE file)

Context:
Pattern to follow: `modules/placement/api/serializers.py`.
Models: `LeaveCategory`, `LeaveBalance`, `LeaveApplication`, `LeaveApplicationTransition` from `modules.leave.models`.

## Required Serializers

1. `LeaveCategorySerializer(serializers.ModelSerializer)`:
   - model = LeaveCategory
   - fields = ("code", "name", "description", "is_carry_forwardable")
   - read_only_fields = fields

2. `LeaveBalanceSerializer(serializers.ModelSerializer)`:
   - category = LeaveCategorySerializer(read_only=True)
   - category_code = serializers.CharField(source="category.code", read_only=True)
   - model = LeaveBalance
   - fields = ("id", "user_id", "category", "category_code", "year", "balance_days", "is_converted")
   - read_only_fields = fields

3. `LeaveApplicationTransitionSerializer(serializers.ModelSerializer)`:
   - model = LeaveApplicationTransition
   - fields = ("id", "from_status", "to_status", "actor_user_id", "actor_label", "reason", "at")
   - read_only_fields = fields

4. `LeaveApplicationSerializer(serializers.ModelSerializer)`:
   - category = LeaveCategorySerializer(read_only=True)
   - category_code = serializers.CharField(source="category.code", read_only=True)
   - allowed_transitions = serializers.SerializerMethodField()
   - model = LeaveApplication
   - fields = (
       "id", "user_id", "category", "category_code", "status", "start_date",
       "end_date", "half_day", "days_charged", "balance_deducted", "reason",
       "is_station_leave", "station_details", "substitute_user_id",
       "substitute_response", "recommendation", "applicant_is_director",
       "withdrawn_reason", "actual_resumption_date", "resumption_status",
       "allowed_transitions", "created_at", "updated_at",
     )
   - read_only_fields = fields
   - `get_allowed_transitions(self, obj) -> list[str]`:
     ```python
     from modules.leave.domain import state_machine as sm
     from modules.leave.services.applications import actor_kind
     actor = self.context.get("actor")
     return sm.allowed_targets(obj.status, actor_kind(actor, obj) if actor else None)
     ```

5. `LeaveApplicationCreateSerializer(serializers.Serializer)`:
   - category_code = serializers.CharField(max_length=3)
   - start_date = serializers.DateField()
   - end_date = serializers.DateField()
   - half_day = serializers.CharField(max_length=6, required=False, allow_blank=True, default="")
   - reason = serializers.CharField()
   - is_station_leave = serializers.BooleanField(required=False, default=False)
   - station_details = serializers.DictField(required=False, default=dict)
   - substitute_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)
   - applicant_is_director = serializers.BooleanField(required=False, default=False)
   - medical_evidence_ref = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")

6. `LeaveApplicationTransitionInputSerializer(serializers.Serializer)`:
   - to_status = serializers.CharField(max_length=40)
   - reason = serializers.CharField(required=False, allow_blank=True, default="")
   - recommendation = serializers.CharField(required=False, allow_blank=True, default="")
   - replacement_substitute_id = serializers.IntegerField(required=False, allow_null=True, default=None)

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs. Max line length 100.
