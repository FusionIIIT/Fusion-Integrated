import csv
import datetime
import logging
from django.http import HttpResponse
from django.db.models import Max, Q
from django.db.models.functions import Upper
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from rest_framework.views import APIView
from ..models import GlobalsDesignation, GlobalsHoldsdesignation, GlobalsModuleaccess, AuthUser, Batch, Student, GlobalsDepartmentinfo, Programme, GlobalsFaculty, Staff
from ..serializers import GlobalExtraInfoSerializer, GlobalsDesignationSerializer, GlobalsModuleaccessSerializer, AuthUserSerializer, GlobalsHoldsDesignationSerializer, StudentSerializer, GlobalsFacultySerializer, GlobalsDepartmentinfoSerializer, BatchSerializer, ProgrammeSerializer, StaffSerializer, ViewStudentsWithFiltersSerializer, ViewStaffWithFiltersSerializer, ViewFacultyWithFiltersSerializer
from io import StringIO
from ..services.users import create_password, generate_random_password, send_email, mail_to_user, configure_password_mail, add_user_extra_info, add_user_designation_info, add_student_info
from django.contrib.auth.hashers import make_password
from backend.settings import EMAIL_TEST_ARRAY
from django.conf import settings

logger = logging.getLogger(__name__)


@api_view(['GET'])
def get_all_departments(request):
    records = GlobalsDepartmentinfo.objects.all().order_by('id')
    serializer = GlobalsDepartmentinfoSerializer(records, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_all_batches(request):
    records = Batch.objects.distinct('year')
    serializer = BatchSerializer(records, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_all_programmes(request):
    records = Programme.objects.all().order_by('id')
    serializer = ProgrammeSerializer(records, many=True)
    return Response(serializer.data)


class UserListView(APIView):
    def get(self, request):
        user_type = request.GET.get('type')
        serializer = None

        if user_type == "student":
            students = Student.objects.select_related('id__user', 'id__department', 'batch_id')
            programme = request.GET.get("programme")
            batch = request.GET.get("batch")
            discipline = request.GET.get("discipline")
            category = request.GET.get("category")
            gender = request.GET.get("gender")

            if programme:
                students = students.filter(programme__iexact=programme)
            if batch:
                students = students.filter(batch=batch)
            if discipline:
                students = students.filter(batch_id__discipline__name__iexact=discipline)
            if category:
                students = students.filter(category__iexact=category)
            if gender:
                students = students.filter(id__sex__iexact=gender)

            serializer = ViewStudentsWithFiltersSerializer(students, many=True)

        elif user_type == "faculty":
            faculty = GlobalsFaculty.objects.select_related('id__user', 'id__department').prefetch_related('id__user__holds_designations__designation')
            designation = request.GET.get("designation")
            gender = request.GET.get("gender")

            if designation:
                faculty = faculty.filter(id__user__holds_designations__designation__name__iexact=designation).distinct()
            if gender:
                faculty = faculty.filter(id__sex__iexact=gender)

            serializer = ViewFacultyWithFiltersSerializer(faculty, many=True)

        elif user_type == "staff":
            staff = Staff.objects.select_related("id__user", "id__department").prefetch_related('id__user__holds_designations__designation')
            designation = request.GET.get("designation")
            gender = request.GET.get("gender")

            if designation:
                staff = staff.filter(id__user__holds_designations__designation__name__iexact=designation).distinct()
            if gender:
                staff = staff.filter(id__sex__iexact=gender)

            serializer = ViewStaffWithFiltersSerializer(staff, many=True)

        else:
            return Response({"error": "Invalid or missing user type."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data)
