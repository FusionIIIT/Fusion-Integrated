from rest_framework import serializers

from ..models import (
    AuthUser,
    Batch,
    Curriculum,
    Discipline,
    GlobalsDepartmentinfo,
    GlobalsDesignation,
    GlobalsExtrainfo,
    GlobalsFaculty,
    GlobalsHoldsdesignation,
    GlobalsModuleaccess,
    Programme,
    Staff,
    Student,
)


class GlobalExtraInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalsExtrainfo
        fields = '__all__'

class GlobalsDesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalsDesignation
        fields = '__all__'

class GlobalsDepartmentinfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalsDepartmentinfo
        fields = '__all__'
        
class GlobalsHoldsDesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalsHoldsdesignation
        fields = '__all__'
        
class AuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthUser
        fields = '__all__'
        
class GlobalsModuleaccessSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalsModuleaccess
        fields = '__all__'

    def validate_id(self, value):
        if GlobalsModuleaccess.objects.filter(id=value).exists():
            raise serializers.ValidationError("The ID must be unique.")
        return value

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'

class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = '__all__'

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = '__all__'

class CurriculumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curriculum
        fields = '__all__'


class DisciplineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discipline
        fields = '__all__'

class ProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programme
        fields = '__all__'

class GlobalsFacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalsFaculty
        fields = '__all__'
