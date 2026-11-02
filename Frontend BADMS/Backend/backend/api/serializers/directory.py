from rest_framework import serializers

from ..models import GlobalsFaculty, Staff, Student


class ViewStudentsWithFiltersSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='id.user.username')
    full_name = serializers.SerializerMethodField()
    programme = serializers.CharField()
    batch = serializers.IntegerField()
    discipline = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    category = serializers.CharField()
    gender = serializers.CharField(source='id.sex')

    class Meta:
        model = Student
        fields = ['id', 'username', 'full_name', 'user_type', 'programme', 'discipline', 'batch', 'curr_semester_no', 'category', 'gender']
    
    def get_full_name(self, obj):
        return f"{obj.id.user.first_name} {obj.id.user.last_name}".strip()

    def get_user_type(self, obj):
        return "student"

    def get_discipline(self, obj):
        if obj.batch_id and obj.batch_id.discipline:
            return obj.batch_id.discipline.name
        return None

class ViewStaffWithFiltersSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='id.user.username')
    full_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    gender = serializers.CharField(source='id.sex', default=None)
    designations = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = ['id', 'username', 'full_name', 'user_type', 'gender', 'designations']
    
    def get_full_name(self, obj):
        return f"{obj.id.user.first_name} {obj.id.user.last_name}".strip()

    def get_user_type(self, obj):
        return "staff"

    def get_designations(self, obj):
        return [
            d.designation.name
            for d in obj.id.user.holds_designations.all()
        ]

class ViewFacultyWithFiltersSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='id.user.username')
    full_name = serializers.SerializerMethodField()
    department = serializers.CharField(source='id.department.name', default=None)
    designations = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    gender = serializers.CharField(source='id.sex', default=None)

    class Meta:
        model = GlobalsFaculty
        fields = ['id', 'username', 'full_name', 'user_type', 'department', 'designations', 'gender']
    
    def get_full_name(self, obj):
        return f"{obj.id.user.first_name} {obj.id.user.last_name}".strip()

    def get_user_type(self, obj):
        return "faculty"
    
    def get_designations(self, obj):
        return [
            d.designation.name 
            for d in obj.id.user.holds_designations.all()
        ]