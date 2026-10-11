"""DRF serializers for HR module."""
from rest_framework import serializers

from modules.hr.models import Department, EmploymentContract


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "code", "parent", "head_user_id", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class EmploymentContractSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    department_code = serializers.CharField(source="department.code", read_only=True)

    class Meta:
        model = EmploymentContract
        fields = [
            "id", "user_id", "department", "department_name", "department_code",
            "title", "kind", "status", "starts_on", "ends_on",
            "ended_by_user_id", "end_reason", "created_at",
        ]
        read_only_fields = ["id", "ended_by_user_id", "created_at"]


class CreateContractSerializer(serializers.Serializer):
    user_id       = serializers.IntegerField()
    department_id = serializers.IntegerField()
    title         = serializers.CharField(max_length=120)
    kind          = serializers.ChoiceField(choices=EmploymentContract.KIND, default="permanent")
    starts_on     = serializers.DateField()
    ends_on       = serializers.DateField(required=False, allow_null=True)


class EndContractSerializer(serializers.Serializer):
    ends_on = serializers.DateField()
    reason  = serializers.CharField(max_length=300, required=False, default="")
