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


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reset_password(request):
    user_name = request.data.get('username')
    try:
        user = AuthUser.objects.annotate(username_upper=Upper('username')).get(username_upper=user_name.upper())
        new_password = generate_random_password()
        user.password = make_password(new_password)
        user.save()
        
        try:
            subject = "Your Fusion Portal Password Has Been Reset"
            message = (
                f"Dear {user.first_name.capitalize() or user.username},\n\n"
                "Your password on the Fusion ERP Portal has been reset by the System Administrator.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "  NEW CREDENTIALS\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  Username : {user.username.upper()}\n"
                f"  Password : {new_password}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Please log in and change your password immediately.\n\n"
                "Portal: http://fusion.iiitdmj.ac.in/\n\n"
                "If you did not request this reset, contact us at fusion@iiitdmj.ac.in\n\n"
                "Regards,\n"
                "System Administrator\n"
                "PDPM IIITDM Jabalpur"
            )
            send_email(subject=subject, message=message, from_email=settings.EMAIL_HOST_USER, recipient_list=[user.email])
        except Exception:
            logger.exception("Failed to send password reset email for user %s", user_name)

        # The plaintext password is delivered only to the user's registered
        # email, never in the response body. A failed email does not fail the
        # reset — the password has already been changed.
        return Response(
            {"message": "Password reset successfully. The new password has been emailed to the user."},
            status=status.HTTP_200_OK,
        )
    except AuthUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def add_individual_staff(request):
    required_fields = ["username", "first_name", "last_name", "sex", "designation"]
    data = request.data
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        return Response({
            "error": "Missing required fields.",
            "missing_fields": missing_fields
        }, status=status.HTTP_400_BAD_REQUEST)
    user_password = create_password(data)
    auth_user_data = {
        "password": make_password(user_password),
        "username": data['username'].lower(),
        "first_name": data['first_name'].lower().capitalize(),
        "last_name": data.get('last_name').lower().capitalize(),
        "email": f"{data['username'].lower()}@iiitdmj.ac.in",
        "is_staff": True,
        "is_superuser": False,
        "is_active": True,
        "date_joined": datetime.datetime.now().strftime("%Y-%m-%d"),
    }
    auth_serializer = AuthUserSerializer(data=auth_user_data)
    user = None
    if auth_serializer.is_valid():
        user = auth_serializer.save()
    else:
        return Response({
            "message": "Error in adding user to auth user table",
            "data": auth_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    default_department = GlobalsDepartmentinfo.objects.get(name='CSE').id
    extra_info_data = {
        'id': data['username'].lower(),
        'title': data.get('title') if data.get('title') else 'Mr.' if data['sex'][0].upper() == 'M' else 'Ms.',
        'sex': data['sex'][0].upper(),
        'date_of_birth': data.get("dob") if data.get("dob") else "2025-01-01",
        'user_status': "PRESENT",
        'address': data.get("address") if data.get("address") else "NA",
        'phone_no': data.get("phone") if data.get("phone") else 9999999999,
        'about_me': "NA",
        'user_type': 'staff',
        'profile_picture': None,
        'date_modified': datetime.datetime.now().strftime("%Y-%m-%d"),
        'department': data.get("department") if data.get("department") else default_department,
        'user': user.id,
    }
    extra_info_serializer = GlobalExtraInfoSerializer(data=extra_info_data)
    extra_info = None
    if extra_info_serializer.is_valid():
        extra_info = extra_info_serializer.save()
    else:
        return Response({
            "message": "Error in adding user to globals extra info table",
            "data": extra_info_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    holds_designation_data = {
        'designation' : data.get('designation'),
        'user' : user.id,
        'working' : user.id,
    }
    holds_designation_serializer = GlobalsHoldsDesignationSerializer(data=holds_designation_data)
    if holds_designation_serializer.is_valid():
        holds_designation_serializer.save()
    else:
        return Response({
            "message": "Error in adding user to globals holds designation table",
            "data": holds_designation_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    staff_id = extra_info.id
    staff_data = {
        'id' : staff_id,
    }

    staff_serializer = StaffSerializer(data=staff_data)
    if staff_serializer.is_valid():
        staff_serializer.save()
    else:
        return Response({
            "message": "Error in adding user to globals staff table",
            "data": staff_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    auth_user_data.pop("password", None)  # never expose the password hash in the response
    return Response({
        "message": "Staff added successfully",
        "auth_user_data": auth_user_data,
        "extra_info_user_data": extra_info_data,
        "holds_designation_user_data": holds_designation_data,
        "globals_staff_data": staff_data,
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def add_individual_faculty(request):
    required_fields = ["username", "first_name", "last_name", "sex", "designation"]
    data = request.data
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        return Response({
            "error": "Missing required fields.",
            "missing_fields": missing_fields
        }, status=status.HTTP_400_BAD_REQUEST)
    user_password = create_password(data)
    auth_user_data = {
        "password": make_password(user_password),
        "username": data['username'].lower(),
        "first_name": data['first_name'].lower().capitalize(),
        "last_name": data.get('last_name').lower().capitalize(),
        "email": f"{data['username'].lower()}@iiitdmj.ac.in",
        "is_staff": False,
        "is_superuser": False,
        "is_active": True,
        "date_joined": datetime.datetime.now().strftime("%Y-%m-%d"),
    }
    auth_serializer = AuthUserSerializer(data=auth_user_data)
    user = None
    if auth_serializer.is_valid():
        user = auth_serializer.save()
    else:
        return Response({
            "message": "Error in adding user to auth user table",
            "data": auth_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    default_department = GlobalsDepartmentinfo.objects.get(name='CSE').id
    extra_info_data = {
        'id': data['username'].lower(),
        'title': data.get('title') if data.get('title') else 'Mr.' if data['sex'][0].upper() == 'M' else 'Ms.',
        'sex': data['sex'][0].upper(),
        'date_of_birth': data.get("dob") if data.get("dob") else "2025-01-01",
        'user_status': "PRESENT",
        'address': data.get("address") if data.get("address") else "NA",
        'phone_no': data.get("phone") if data.get("phone") else 9999999999,
        'about_me': "NA",
        'user_type': 'faculty',
        'profile_picture': None,
        'date_modified': datetime.datetime.now().strftime("%Y-%m-%d"),
        'department': data.get("department") if data.get("department") else default_department,
        'user': user.id,
    }
    extra_info_serializer = GlobalExtraInfoSerializer(data=extra_info_data)
    extra_info = None
    if extra_info_serializer.is_valid():
        extra_info = extra_info_serializer.save()
    else:
        return Response({
            "message": "Error in adding user to globals extra info table",
            "data": extra_info_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    holds_designation_data = {
        'designation' : data.get('designation'),
        'user' : user.id,
        'working' : user.id,
    }
    holds_designation_serializer = GlobalsHoldsDesignationSerializer(data=holds_designation_data)
    if holds_designation_serializer.is_valid():
        holds_designation_serializer.save()
    else:
        return Response({
            "message": "Error in adding user to globals holds designation table",
            "data": holds_designation_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    faculty_id = extra_info.id
    faculty_data = {
        'id' : faculty_id,
    }

    faculty_serializer = GlobalsFacultySerializer(data=faculty_data)
    if faculty_serializer.is_valid():
        faculty_serializer.save()
    else:
        return Response({
            "message": "Error in adding user to globals faculty table",
            "data": faculty_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    auth_user_data.pop("password", None)  # never expose the password hash in the response
    return Response({
        "message": "Faculty added successfully",
        "auth_user_data": auth_user_data,
        "extra_info_user_data": extra_info_data,
        "holds_designation_user_data": holds_designation_data,
        "globals_faculty_data": faculty_data,
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_import_users(request):
    # CSV file headers:
    # 1 username
    # 2 first_name
    # 3 last_name
    # 4 sex
    # 5 category
    # 6 father_name
    # 7 mother_name
    # 8 batch
    # 9 programme
    # 10 title
    # 11 dob
    # 12 address
    # 13 phone_no
    # 14 department
    if 'file' not in request.FILES:
        return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
    
    file = request.FILES['file']
    if not file.name.endswith('.csv'):
        return Response({"error": "Please upload a valid CSV file."}, status=status.HTTP_400_BAD_REQUEST)

    file_data = file.read().decode('utf-8')
    csv_data = csv.reader(StringIO(file_data))
    
    headers = next(csv_data)
    created_users = []
    failed_users = []
    
    for row in csv_data:
        if len(row) < 9:
            failed_users.append(row)
            continue
        try:
            user_data = {
                'password': make_password(generate_random_password()),
                'username': row[0].upper(),
                'first_name': row[1].lower().capitalize() if len(row[1]) > 0 else 'NA',
                'last_name': row[2].lower().capitalize() if len(row[2]) > 0 else 'NA',
                'email': f"{row[0].lower()}@iiitdmj.ac.in",
                'is_staff': False,
                'is_superuser': False,
                'is_active': True,
                'date_joined': datetime.datetime.now().strftime("%Y-%m-%d"),
            }
            serializer = AuthUserSerializer(data=user_data)
            user = None
            if serializer.is_valid():
                user = serializer.save()
            extra_info_serializer = add_user_extra_info(row, user)
            extra_serializer = None
            if extra_info_serializer:
                extra_serializer = extra_info_serializer.save()
            role_serializer = add_user_designation_info(user.id)
            if role_serializer:
                role_serializer.save()
            student_serializer = add_student_info(row, extra_serializer)
            if student_serializer:
                student_serializer.save()
            if user and extra_info_serializer and role_serializer and student_serializer:
                created_users.append(serializer.data)
        except Exception as e:
            logger.exception("Failed to import user from row: %s", row)
            failed_users.append(row)

    if(len(created_users) > 0):
        mail_to_user(created_users)
        
    response_data = {
        "message": f"{len(created_users)} users created successfully.",
        "created_users": created_users,
        "skipped_users_count": len(failed_users),
    }

    if failed_users:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)

        for failed_user in failed_users:
            writer.writerow(failed_user)

        output.seek(0)
        response_data["skipped_users_csv"] = output.getvalue()

    return Response(response_data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def bulk_export_users(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_superuser'])
    users = AuthUser.objects.all()
    
    for user in users:
        writer.writerow([user.username, user.first_name, user.last_name, user.email, user.is_staff, user.is_superuser])
    
    return response

@api_view(['POST'])
@permission_classes([IsAdminUser])
def mail_to_whole_batch(request):
    emails = EMAIL_TEST_ARRAY
    email_list = emails.split(',')
    if(len(email_list) != 1):
        students = Student.objects.filter(batch=request.data.get('batch'), id__user__email__in=email_list)
    else:
        students = Student.objects.filter(batch=request.data.get('batch'))
        
    students_data = [student.id.user for student in students]
    try:
        configure_password_mail(students_data)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({"message": "Mail sent to whole batch successfully."}, status=status.HTTP_200_OK)

def download_sample_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "username", "first_name", "last_name", "sex", "category",
        "father_name", "mother_name", "batch", "programme", "title",
        "dob", "address", "phone_no", "department"
    ])
    return response
