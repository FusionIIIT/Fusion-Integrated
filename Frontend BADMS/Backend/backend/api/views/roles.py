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
def get_user_role_by_username(request):
    username = request.query_params.get('username')
    
    if not username:
        return Response({"error": "Username parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = AuthUser.objects.get(username__iexact=username)
        holds_designation_entries = GlobalsHoldsdesignation.objects.filter(user=user)
        
        if not holds_designation_entries.exists():
            return Response({"error": "User has no designations."}, status=status.HTTP_404_NOT_FOUND)
        
        designation_ids = list(
            holds_designation_entries.values_list("designation_id", flat=True)
        )
        
        roles = GlobalsDesignation.objects.filter(id__in=designation_ids)
        roles_serializer = GlobalsDesignationSerializer(roles, many=True)
        
        return Response({
            "user": AuthUserSerializer(user).data,
            "roles": roles_serializer.data,
        }, status=status.HTTP_200_OK)
        
    except AuthUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def update_user_roles(request):
    username = request.data.get('username')
    roles_to_add = request.data.get('roles')

    if not username or not roles_to_add:
        return Response({"error": "Username and roles are required."}, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(AuthUser, username__iexact=username)

    existing_roles = GlobalsHoldsdesignation.objects.filter(user=user)
    existing_role_names = set(existing_roles.values_list('designation__name', flat=True))

    processed_roles_to_add = set()

    for role in roles_to_add:
        if isinstance(role, dict):
            if 'name' in role:
                processed_roles_to_add.add(role['name'])
        elif isinstance(role, str):
            processed_roles_to_add.add(role)

    roles_to_remove = existing_role_names - processed_roles_to_add

    GlobalsHoldsdesignation.objects.filter(user=user, designation__name__in=roles_to_remove).delete()

    for role_name in processed_roles_to_add:
        if role_name not in existing_role_names:
            designation = get_object_or_404(GlobalsDesignation, name=role_name)
            GlobalsHoldsdesignation.objects.create(
                held_at=timezone.now(),
                designation=designation,
                user=user,
                working=user
            )

    return Response({"message": "User roles updated successfully."}, status=status.HTTP_200_OK)
        
@api_view(['GET'])
def global_designation_list(request):
    records = GlobalsDesignation.objects.all()
    serializer = GlobalsDesignationSerializer(records, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def get_category_designations(request):
    category = request.data.get('category', 'student')
    basic = request.data.get('basic', True)
    records = GlobalsDesignation.objects.all().filter(category=category, basic=basic)
    serializer = GlobalsDesignationSerializer(records, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def add_designation(request):
    serializer = GlobalsDesignationSerializer(data=request.data)
    if serializer.is_valid():
        role = serializer.save()
        max_id = GlobalsModuleaccess.objects.aggregate(Max('id'))['id__max']
        new_id = (max_id or 0) + 1
        data = {
            'id': new_id,
            'designation' : role.name,
            'program_and_curriculum' : False,
            'course_registration' : False,
            'thesis_research' : False,
            'course_management' : False,
            'other_academics' : False,
            'spacs' : False,
            'department' : False,
            'database' : False,
            'examinations' : False,
            'hr' : False,
            'iwd' : False,
            'complaint_management' : False,
            'fts' : False,
            'purchase_and_store' : False,
            'rspc' : False,
            'hostel_management' : False,
            'mess_management' : False,
            'gymkhana' : False,
            'placement_cell' : False,
            'visitor_hostel' : False,
            'phc' : False,
            'inventory_management': False,
        }
        module_serializer = GlobalsModuleaccessSerializer(data=data)
        if not module_serializer.is_valid():
            # The role itself was already created; say so, rather than a 201
            # that implies module access exists when the row never saved.
            return Response(
                {'role': serializer.data, 'modules_error': module_serializer.errors},
                status.HTTP_207_MULTI_STATUS)
        module_serializer.save()
        return Response({'role': serializer.data, 'modules': module_serializer.data}, status.HTTP_201_CREATED)
    else :
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
    
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])
def update_designation(request):
    name = request.data.get('name')
    
    if not name:
        return Response({"error": "No name provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        designation = GlobalsDesignation.objects.get(name=name)
    except GlobalsDesignation.DoesNotExist:
        return Response({"error": f"Designation with name '{name}' not found."}, status=status.HTTP_404_NOT_FOUND)
    
    partial = request.method == 'PATCH'
    serializer = GlobalsDesignationSerializer(designation, data=request.data, partial=partial)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_module_access(request):
    role_name = request.query_params.get('designation')
    
    if not role_name:
        return Response({"error": "No role provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        module_access = GlobalsModuleaccess.objects.get(designation=role_name)
    except GlobalsModuleaccess.DoesNotExist:
        return Response({"error": f"Module access for designation '{role_name}' not found."}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = GlobalsModuleaccessSerializer(module_access)
    return Response(serializer.data, status=status.HTTP_200_OK)
    
@api_view(['PUT'])
@permission_classes([IsAdminUser])
def modify_moduleaccess(request):
    role_name = request.data.get('designation')
    
    if not role_name:
        return Response({"error": "No role provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        designation = GlobalsModuleaccess.objects.get(designation=role_name)
    except GlobalsModuleaccess.DoesNotExist:
        return Response({"error": f"Designation with name '{role_name}' not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = GlobalsModuleaccessSerializer(designation, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
