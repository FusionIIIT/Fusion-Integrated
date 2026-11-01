"""Management command to seed initial System Admin configuration, roles, conflicts, and basic users."""
from datetime import date
from django.core.management.base import BaseCommand
from modules.systemadmin.models.config import SystemAdminConfig
from modules.systemadmin.models.role_mgmt import RoleDefinition, RoleConflict
from modules.systemadmin.models.user_mgmt import BasicUserProfile
from modules.systemadmin.services.user_service import UserService
from modules.systemadmin.services.config_service import PERMITTED_CONFIG_KEYS, DEFAULT_CONFIG_VALUES


class Command(BaseCommand):
    help = "Seed initial configuration parameters, role definitions, conflicts, and demo basic users."

    def handle(self, *args, **options):
        self.stdout.write("Seeding System Admin default parameters...")
        for key, meta in PERMITTED_CONFIG_KEYS.items():
            SystemAdminConfig.objects.get_or_create(
                key=key,
                defaults={
                    "value": DEFAULT_CONFIG_VALUES.get(key),
                    "category": meta["category"],
                    "is_critical": meta.get("is_critical", False),
                    "description": f"Configurable parameter: {key}",
                    "updated_by": "system_seed",
                },
            )

        self.stdout.write("Seeding default Role Definitions...")
        roles_data = [
            {
                "code": "DIRECTOR",
                "name": "Director",
                "description": "Head of the Institute with executive oversight",
                "module_or_dept": "Administration",
                "allowed_user_types": ["faculty", "staff"],
                "is_singular": True,
                "is_time_bound": True,
                "default_validity_days": 1825,  # 5 years
            },
            {
                "code": "DEAN_ACAD",
                "name": "Dean Academic",
                "description": "Supervises institute academic affairs and curriculum policy",
                "module_or_dept": "Academic Office",
                "allowed_user_types": ["faculty"],
                "is_singular": True,
                "is_time_bound": True,
                "default_validity_days": 730,  # 2 years
            },
            {
                "code": "DEAN_SA",
                "name": "Dean Student Affairs",
                "description": "Supervises student affairs, hostel discipline and campus welfare",
                "module_or_dept": "Student Welfare",
                "allowed_user_types": ["faculty"],
                "is_singular": True,
                "is_time_bound": True,
                "default_validity_days": 730,
            },
            {
                "code": "HOD_CSE",
                "name": "Head of Department (CSE)",
                "description": "Head of Computer Science and Engineering Department",
                "module_or_dept": "Computer Science and Engineering",
                "allowed_user_types": ["faculty"],
                "is_singular": True,
                "is_time_bound": True,
                "default_validity_days": 730,
            },
            {
                "code": "HOD_ECE",
                "name": "Head of Department (ECE)",
                "description": "Head of Electronics and Communication Engineering Department",
                "module_or_dept": "Electronics and Communication Engineering",
                "allowed_user_types": ["faculty"],
                "is_singular": True,
                "is_time_bound": True,
                "default_validity_days": 730,
            },
            {
                "code": "FACULTY_ADVISOR",
                "name": "Faculty Advisor",
                "description": "Academic advisor for batch cohorts",
                "module_or_dept": "Academic Office",
                "allowed_user_types": ["faculty"],
                "is_singular": False,
                "is_time_bound": True,
                "default_validity_days": 365,
            },
            {
                "code": "WARDEN",
                "name": "Hostel Warden",
                "description": "Administrative caretaker and warden for residential halls",
                "module_or_dept": "Hostel Management",
                "allowed_user_types": ["faculty"],
                "is_singular": False,
                "is_time_bound": True,
                "default_validity_days": 365,
            },
            {
                "code": "STUDENT_SENATE",
                "name": "Student Senate Member",
                "description": "Elected student representative on campus governance senate",
                "module_or_dept": "Gymkhana",
                "allowed_user_types": ["student"],
                "is_singular": False,
                "is_time_bound": True,
                "default_validity_days": 365,
            },
            {
                "code": "PLACEMENT_COORD",
                "name": "Placement Coordinator",
                "description": "Student or faculty coordinator in training and placement cell",
                "module_or_dept": "Training and Placement Cell",
                "allowed_user_types": ["student", "faculty"],
                "is_singular": False,
                "is_time_bound": True,
                "default_validity_days": 365,
            },
        ]

        created_roles = {}
        for r_spec in roles_data:
            role_obj, _ = RoleDefinition.objects.get_or_create(
                code=r_spec["code"],
                defaults=r_spec,
            )
            created_roles[role_obj.code] = role_obj

        self.stdout.write("Configuring mutually exclusive Role Conflicts (SoD)...")
        if "DEAN_ACAD" in created_roles and "HOD_CSE" in created_roles:
            RoleConflict.objects.get_or_create(
                role_a=created_roles["DEAN_ACAD"],
                role_b=created_roles["HOD_CSE"],
                defaults={"reason": "Separation of institute-wide academic governance and departmental executive oversight (BR-SA-012)"},
            )

        if "DEAN_SA" in created_roles and "WARDEN" in created_roles:
            RoleConflict.objects.get_or_create(
                role_a=created_roles["DEAN_SA"],
                role_b=created_roles["WARDEN"],
                defaults={"reason": "Appellate authority cannot concurrently hold the primary hostel disciplinary role"},
            )

        self.stdout.write("Seeding Demo Basic Users...")
        demo_users = [
            {
                "institute_id": "2020FAC001",
                "full_name": "Dr. Rajesh Sharma",
                "institute_email": "dr.sharma@iiitdmj.ac.in",
                "user_type": "faculty",
                "department": "Computer Science and Engineering",
                "employee_id": "EMP-FAC-001",
                "contact_number": "+91-9876543210",
                "date_of_joining": date(2020, 7, 15),
            },
            {
                "institute_id": "2018FAC002",
                "full_name": "Dr. Sunita Gupta",
                "institute_email": "dr.gupta@iiitdmj.ac.in",
                "user_type": "faculty",
                "department": "Electronics and Communication Engineering",
                "employee_id": "EMP-FAC-002",
                "contact_number": "+91-9876543211",
                "date_of_joining": date(2018, 1, 10),
            },
            {
                "institute_id": "2019STF001",
                "full_name": "Amit Verma",
                "institute_email": "amit.verma@iiitdmj.ac.in",
                "user_type": "staff",
                "department": "Administration",
                "employee_id": "EMP-STF-001",
                "contact_number": "+91-9876543212",
                "date_of_joining": date(2019, 3, 1),
            },
            {
                "institute_id": "2024CS001",
                "full_name": "Rahul Kumar",
                "institute_email": "rahul.2024cs001@iiitdmj.ac.in",
                "user_type": "student",
                "department": "Computer Science and Engineering",
                "programme": "B.Tech",
                "discipline": "CSE",
                "batch_year": 2024,
                "contact_number": "+91-9876543213",
                "date_of_joining": date(2024, 8, 1),
            },
            {
                "institute_id": "2024EC001",
                "full_name": "Priya Patel",
                "institute_email": "priya.2024ec001@iiitdmj.ac.in",
                "user_type": "student",
                "department": "Electronics and Communication Engineering",
                "programme": "B.Tech",
                "discipline": "ECE",
                "batch_year": 2024,
                "contact_number": "+91-9876543214",
                "date_of_joining": date(2024, 8, 1),
            },
        ]

        for u in demo_users:
            if not BasicUserProfile.objects.filter(institute_id=u["institute_id"]).exists():
                UserService.create_basic_user(
                    institute_id=u["institute_id"],
                    user_type=u["user_type"],
                    full_name=u["full_name"],
                    institute_email=u["institute_email"],
                    date_of_joining=u["date_of_joining"],
                    contact_number=u.get("contact_number", ""),
                    department=u.get("department", ""),
                    programme=u.get("programme", ""),
                    discipline=u.get("discipline", ""),
                    batch_year=u.get("batch_year"),
                    employee_id=u.get("employee_id", ""),
                    actor_username="system_seed",
                )

        self.stdout.write(self.style.SUCCESS("Successfully seeded System Admin baseline data."))
