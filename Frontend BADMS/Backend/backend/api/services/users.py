from rest_framework.response import Response
from rest_framework import status
import concurrent.futures
import logging
import secrets
import string
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime
from ..models import GlobalsDepartmentinfo, Batch, GlobalsDesignation, AuthUser
from ..serializers import GlobalExtraInfoSerializer, GlobalsHoldsDesignationSerializer, StudentSerializer
import os

logger = logging.getLogger(__name__)


def generate_random_password(length=12):
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c in string.ascii_uppercase for c in password)
                and any(c in string.ascii_lowercase for c in password)
                and any(c in string.digits for c in password)
                and any(c in string.punctuation for c in password)):
            return password

def create_password(data):
    # Return a strong, unpredictable password. Previously this derived the password
    # from the username plus three characters chosen with the non-cryptographic
    # `random` module, which is both guessable (username-based) and low-entropy.
    # Account credentials must never be predictable, so delegate to the CSPRNG-backed
    # generator. (`data` is accepted for backwards compatibility with callers.)
    return generate_random_password()



def save_password(student, hashed_password):
    student.password = hashed_password
    student.save()


def send_email(
    subject,
    message,
    from_email=settings.EMAIL_HOST_USER,
    recipient_list=None,
):
    if recipient_list is None:
        recipient_list = [settings.EMAIL_TEST_USER]
    if not from_email:
        return Response(
            {"error": "No sender email provided."}, status=status.HTTP_400_BAD_REQUEST
        )
    try:
        send_mail(subject, message, from_email, recipient_list)
    except Exception as e:
        logger.exception("Failed to send email to %s", recipient_list)
        raise

def configure_password_mail(students):
    count = len(students)
    if settings.EMAIL_TEST_MODE == 1:
        count = settings.EMAIL_TEST_COUNT
    
    try:
        for student in students[:count]:
            plain_password = generate_random_password()
            hashed_password = make_password(plain_password)
            save_password(student, hashed_password)
            try:
                mail_to_user_single(student, plain_password)
            except Exception as e:
                log_failed_email(student, plain_password, hashed_password, str(e))
                
        return Response(
            {"message": "Email sent successfully."}, status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.exception("Failed during configure_password_mail")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def log_failed_email(student, plain_password, hashed_password, error):
    log_dir = "failed_emails"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "failed_emails.txt")
    email = student.get('email', '') if isinstance(student, dict) else student.email
    username = student.get('username', '') if isinstance(student, dict) else student.username
    with open(log_file, "a") as f:
        f.write(f"Failed to send email to: {email}\n")
        f.write(f"Username: {username}\n")
        f.write(f"Error: {error}\n")
        f.write("\n")

def mail_to_user_single(student, password):
    # student is either a dict (bulk CSV import) or an AuthUser ORM object (batch mail)
    if isinstance(student, dict):
        username = student['username'].upper()
        email = student['email']
        first_name = (student.get('first_name') or '').capitalize()
    else:
        username = student.username.upper()
        email = student.email
        first_name = (student.first_name or '').capitalize()
    subject = "Your Fusion Portal Account Credentials"
    message = (
        f"Dear {first_name or 'Student'},\n\n"
        "Your account on the Fusion ERP Portal at PDPM IIITDM Jabalpur has been created.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  LOGIN CREDENTIALS\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Username : {username}\n"
        f"  Password : {password}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Portal Links:\n"
        "  • http://fusion.iiitdmj.ac.in/\n"
        "  • http://fusion.iiitdmj.ac.in:8000\n"
        "  • http://172.27.16.216:8000/ (On campus LAN only)\n\n"
        "Important:\n"
        "  1. Log in using the credentials above.\n"
        "  2. Change your password immediately after first login:\n"
        "       Log Out → Change Password → Set a strong new password.\n"
        "  3. Keep your password confidential.\n\n"
        "Need help? Contact us at fusion@iiitdmj.ac.in\n\n"
        "Regards,\n"
        "Fusion Development Team\n"
        "PDPM IIITDM Jabalpur"
    )
    recipient_list = [settings.EMAIL_TEST_USER] if settings.EMAIL_TEST_MODE == 1 else [email]
    send_email(subject=subject, message=message, from_email=settings.EMAIL_HOST_USER, recipient_list=recipient_list)
    
def mail_to_user(created_users):
    if not created_users:
        return

    # Generate a unique random password per user, save hash to DB, then email plaintext
    user_passwords = {}
    user_hashes = {}
    for user_data in created_users:
        password = generate_random_password()
        hashed = make_password(password)
        user_passwords[user_data['username']] = password
        user_hashes[user_data['username']] = hashed
        try:
            auth_user = AuthUser.objects.get(username=user_data['username'])
            auth_user.password = hashed
            auth_user.save()
        except Exception:
            logger.exception("Failed to set password for user %s", user_data['username'])

    try:
        max_threads = min(10, len(created_users))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [
                (executor.submit(mail_to_user_single, user, user_passwords[user['username']]), user)
                for user in created_users
            ]
            for future, user in futures:
                try:
                    future.result()
                except Exception as e:
                    uname = user['username']
                    log_failed_email(user, user_passwords[uname], user_hashes[uname], str(e))
        logger.info("Credential emails sent to %d users.", len(created_users))
    except Exception as e:
        logger.exception("Failed during bulk email send")

def convert_to_iso(date_str):
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            date = datetime.strptime(date_str, fmt)
            return date.strftime("%Y-%m-%d")
        except ValueError:
            continue
    dummy_date = datetime.strptime("01-01-2004", "%d-%m-%Y")
    return dummy_date.strftime("%Y-%m-%d")

def add_user_extra_info(row,user):
    department_name = row[13] if row[13] else 'CSE'
    department = GlobalsDepartmentinfo.objects.get(name=department_name).id
    extra_info_data = {
        'id': row[0].upper(),
        'title': row[9].capitalize() if row[9] else 'Mr.' if row[3] and row[3][0].upper() == 'M' else 'Ms.',
        'sex': row[3][0].upper(),
        'date_of_birth': convert_to_iso(row[10]),
        'user_status': "PRESENT",
        'address': row[11].lower().capitalize() if row[11] else 'NA',
        'phone_no': row[12] if row[12] else 9999999999,
        'user_type': 'student',
        'profile_picture': None,
        'about_me': 'NA',
        'date_modified': datetime.now().strftime("%Y-%m-%d"),
        'department': department,
        'user': user.id,
    }
    extra_info_serializer = GlobalExtraInfoSerializer(data=extra_info_data)
    if extra_info_serializer.is_valid():
        return extra_info_serializer
    return None

def add_user_designation_info(user_id, designation='student'):
    designation_id = GlobalsDesignation.objects.get(name=designation).id
    data = {
        'designation' : designation_id,
        'user' : user_id,
        'working' : user_id,
    }
    serializer = GlobalsHoldsDesignationSerializer(data=data)
    if serializer.is_valid():
        return serializer
    return None

def add_student_info(row, extrainfo):
    batch = int(row[7]) if row[7] else datetime.now().year
    batch_id = Batch.objects.filter(name = row[8], discipline__acronym = extrainfo.department.name, year = batch)
    data = {
        'id' : extrainfo.id,
        'programme' : row[8] if row[8] else 'B.Tech',
        'batch' : batch,
        'batch_id' : batch_id.first().id if batch_id else None,
        'cpi': 0.0,
        'category' : row[4].upper() if row[4].upper() else 'GEN',
        'father_name' : row[5].lower().capitalize() if row[5] else 'NA',
        'mother_name' : row[6].lower().capitalize() if row[6] else 'NA',
        'hall_no': 3,
        'room_no': None,
        'specialization': None,
        'curr_semester_no' : 2*(datetime.now().year - batch) + datetime.now().month // 7,
    }
    serializer = StudentSerializer(data=data)
    if serializer.is_valid():
        return serializer
    return None