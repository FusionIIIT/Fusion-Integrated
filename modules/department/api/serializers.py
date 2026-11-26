from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.department import models
from modules.department.selectors import role_assignments
from modules.directory import contracts as directory


class DepartmentSerializer(serializers.ModelSerializer):
    headship = serializers.SerializerMethodField()

    class Meta:
        model = models.Department
        fields = ('id', 'code', 'name', 'core_policies', 'about', 'contact_email', 'location', 'website', 'headship')

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_headship(self, obj):
        holder = role_assignments.current_holder(obj, "hod")
        if holder is None:
            return None
        person = directory.get_users([holder.user_id]).get(holder.user_id)
        return {"user_id": holder.user_id, "display_name": person.display_name if person else ""}
