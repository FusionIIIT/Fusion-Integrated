import django
import os
# from django.conf import settings
# settings.configure()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()
import pandas as pd
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from api.models import AuthUser, GlobalsExtrainfo, GlobalsHoldsdesignation, GlobalsFaculty

file_path = r"faculty_info.csv"  # Use raw string
data = pd.read_csv(file_path)

def change_passwords():
    with transaction.atomic():
        professors = AuthUser.objects.filter(password="user@123")
        for professor in professors:
            professor.password = 'pbkdf2_sha256$600000$2pIest9Ou4GT5jM5S9aLRi$FEkwFQx9zN/lzP76ZB32YsqbkqjSlMDwXMmbIWX6wYU='
            professor.save()

def add_professors():
    # try:
        with transaction.atomic():  
            for _, row in data.iterrows():
                auth_user = AuthUser.objects.create(
                    password=row["password"],  
                    last_login=None,
                    is_superuser=row["is_superuser"],
                    username=row["username"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    email=row["email"],
                    is_staff=row["is_staff"],
                    is_active=row["is_active"],
                    date_joined=timezone.now(),
                )
                
                
                GlobalsExtrainfo.objects.create(
                    id=row["initials"], 
                    title=row["title"],
                    sex=row["sex"],
                    date_of_birth=datetime.strptime(row["date_of_birth"], "%d-%m-%Y"),
                    user_status=row["user_status"],
                    address=row["address"],
                    phone_no=row["phone_no"],
                    user_type=row["user_type"],
                    profile_picture=row.get("profile_picture"),
                    about_me=row["about_me"],
                    date_modified=datetime.now(),
                    department_id=row["department_id"], 
                    user=auth_user,
                )
                
                GlobalsFaculty.objects.create(
                    id_id=row["initials"]
                )
                
                GlobalsHoldsdesignation.objects.create(
                    designation_id=row["designation_id"],  
                    user=auth_user,
                    working=auth_user,
                )
        print("Professors added successfully!")
    # except Exception as e:
    #     print(f"Error: {e}")

if __name__ == "__main__":
    # add_professors()
    change_passwords()
