from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from modules.elm.domain import rules
from modules.elm.models import (
    Account, Application, AttendanceOutbox, AuditEntry, EmployeeConfiguration,
    HolidayCalendar, LedgerEntry, Notification, Policy, WorkflowTask,
)


class SubmitSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=rules.CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=("full", "first", "second"), default="full")
    reason = serializers.CharField(max_length=5000)
    station_leave = serializers.BooleanField(default=False)
    station_details = serializers.CharField(max_length=2000, allow_blank=True, default="")
    medical_reference = serializers.CharField(max_length=300, allow_blank=True, default="")
    substitute_id = serializers.IntegerField(min_value=1, allow_null=True, default=None)


class ActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("accept", "decline", "recommend", "not_recommend",
                                             "forward", "approve", "reject", "review", "withdraw", "replace_substitute"))
    revision = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=5000, allow_blank=True, default="")
    substitute_id = serializers.IntegerField(min_value=1, required=False)


class LifecycleSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("cancellation", "extension", "resumption"))
    reason = serializers.CharField(max_length=5000)
    end_date = serializers.DateField(required=False)
    substitute_id = serializers.IntegerField(min_value=1, allow_null=True, default=None)


class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEntry
        fields = ("id", "action", "actor_id", "reason", "from_status", "to_status", "created_at")


@extend_schema_serializer(component_name="ElmApplication")
class ApplicationSerializer(serializers.ModelSerializer):
    history = HistorySerializer(many=True, read_only=True)
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ("id", "user_id", "kind", "parent_id", "category", "start_date", "end_date",
                  "effective_end_date", "half", "reason", "station_leave", "station_details",
                  "medical_reference", "substitute_id", "status", "days_by_year", "revision",
                  "resumption_reviewed", "created_at", "history", "allowed_actions")

    def get_allowed_actions(self, obj) -> list[str]:
        actor = self.context.get("actor")
        if actor is None:
            return []
        actions = []
        if actor.user_id == obj.user_id and actor.has_permission("elm.application.self"):
            if obj.status in rules.PENDING and obj.kind in ("leave", "extension"):
                actions.append("withdraw")
            if obj.status == "applicant_action":
                actions.append("replace_substitute")
        if actor.has_permission("elm.task.act"):
            for task in obj.tasks.all():
                if task.pending and task.user_id == actor.user_id and task.role == actor.active_role:
                    if actor.user_id != obj.user_id or (task.role == "Director" and task.stage == "sanction"):
                        actions.extend(rules.allowed_decisions(task.stage, obj.category, obj.kind))
        return actions


class TaskSerializer(serializers.ModelSerializer):
    application_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkflowTask
        fields = ("id", "application_id", "stage", "role", "created_at")


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("year", "cl", "rh", "scl", "el", "col", "vl", "year_end_processed")


class LedgerSerializer(serializers.ModelSerializer):
    year = serializers.IntegerField(source="account.year", read_only=True)

    class Meta:
        model = LedgerEntry
        fields = ("id", "year", "application_id", "category", "delta", "operation", "created_at")


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "application_id", "message", "read", "created_at")


class PolicySerializer(serializers.ModelSerializer):
    non_working_weekdays = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6))

    class Meta:
        model = Policy
        fields = ("non_working_weekdays", "require_col_evidence", "reminder_hours", "escalation_hours")


class RouteStepSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=("unit_head", "establishment", "sanction"))
    user_id = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(choices=("Unit Head", *rules.AUTHORITY_ROLES))
    escalation_user_id = serializers.IntegerField(min_value=1, required=False)
    escalation_role = serializers.ChoiceField(choices=("Unit Head", *rules.AUTHORITY_ROLES), required=False)
    reassign_on_escalation = serializers.BooleanField(default=False)


class EmployeeConfigurationSerializer(serializers.ModelSerializer):
    eligible_categories = serializers.ListField(child=serializers.ChoiceField(choices=rules.CATEGORIES))
    routes = serializers.DictField(child=RouteStepSerializer(many=True))

    class Meta:
        model = EmployeeConfiguration
        fields = ("user_id", "unit", "designation", "coverage_required", "eligible_categories", "routes")


class ConfigurationSerializer(serializers.Serializer):
    policy = PolicySerializer(required=False)
    employee = EmployeeConfigurationSerializer(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Supply a policy or employee configuration.")
        return attrs


class CalendarSerializer(serializers.ModelSerializer):
    holidays = serializers.ListField(child=serializers.DateField())
    restricted_holidays = serializers.ListField(child=serializers.DateField())
    year = serializers.IntegerField(min_value=1900, max_value=2200)

    class Meta:
        model = HolidayCalendar
        fields = ("id", "year", "holidays", "restricted_holidays", "published")
        read_only_fields = ("id",)
        validators = []


class OfflineSerializer(SubmitSerializer):
    user_id = serializers.IntegerField(min_value=1)
    offline_reference = serializers.CharField(max_length=300)
    unavailability_reason = serializers.CharField(max_length=2000)
    authority_id = serializers.IntegerField(min_value=1)
    authority_role = serializers.ChoiceField(choices=("Unit Head", *rules.AUTHORITY_ROLES))


class CorrectionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)
    reference = serializers.CharField(max_length=300)


class OutboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceOutbox
        fields = ("id", "application_id", "payload", "created_at")
