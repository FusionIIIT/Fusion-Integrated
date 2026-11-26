from rest_framework import serializers

from modules.department.models.timetable import AcademicProgram, LabResource, TimetableSlot


class DeptTimetableSlotSerializer(serializers.ModelSerializer):
    """Serializes a TimetableSlot model instance, excluding created_at and updated_at."""
    class Meta:
        model = TimetableSlot
        fields = [
            "id",
            "slot_kind",
            "weekday",
            "start_time",
            "end_time",
            "room",
            "faculty_user_id",
            "programme",
            "batch_year",
            "title",
        ]


class DeptSlotWriteSerializer(serializers.Serializer):
    """Serializes data for creating/updating a TimetableSlot."""
    slot_kind = serializers.ChoiceField(choices=[('class', 'Class'), ('lab', 'Lab')])
    weekday = serializers.IntegerField(help_text="Weekday integer 0 to 6")
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    room = serializers.CharField()
    faculty_user_id = serializers.IntegerField(required=False, allow_null=True)
    programme = serializers.CharField(required=False, allow_blank=True)
    batch_year = serializers.IntegerField(required=False, allow_null=True)
    title = serializers.CharField()


class DeptSlotUploadSerializer(serializers.Serializer):
    """Serializes data for uploading multiple timetable slots."""
    department = serializers.IntegerField()
    slots = DeptSlotWriteSerializer(many=True)


class DeptLabSerializer(serializers.ModelSerializer):
    """Serializes a LabResource model instance (read and writable)."""
    class Meta:
        model = LabResource
        fields = [
            "id",
            "name",
            "equipment",
            "capacity",
            "location",
            "notes",
            "department",
        ]


class DeptProgramSerializer(serializers.ModelSerializer):
    """Serializes an AcademicProgram model instance (read and writable)."""
    class Meta:
        model = AcademicProgram
        fields = [
            "id",
            "name",
            "level",
            "description",
            "department",
        ]
