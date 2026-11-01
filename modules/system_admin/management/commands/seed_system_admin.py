"""Seed script for System Admin module.

Sets up default configurations, role definitions, initial basic users,
and baseline role assignments.
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from modules.system_admin.models import (
    AuditLog,
    BasicUser,
    RoleAssignment,
    RoleDefinition,
    SystemConfiguration,
)


class Command(BaseCommand):
    help = "Seed System Admin baseline data (configurations, roles, users)"

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. Permitted System Configurations (BR-SA-035)
        configs = [
            ("session_timeout_minutes", 15, "Super Admin idle session timeout in minutes (5-60)"),
            ("reversibility_window_days", 180, "Archived user reversibility period in days (30-365)"),
            ("role_reminder_intervals_days", [15, 7, 1], "Notice intervals for upcoming role expirations"),
            ("failed_login_alert_threshold", 5, "Consecutive failed login threshold triggering security alert"),
            ("purge_retention_years", 7, "Minimum archival retention before permanent purge eligibility"),
            ("password_history_count", 5, "Number of past passwords remembered for rotation policy"),
        ]
        for key, val, desc in configs:
            SystemConfiguration.objects.update_or_create(
                key=key,
                defaults={"value": val, "description": desc, "updated_by_user_id": 1},
            )
        self.stdout.write("  seeded system configurations")

        # 2. Standard Role Definitions
        roles_data = [
            {
                "code": "dean_academic",
                "name": "Dean of Academic Affairs",
                "description": "Oversees institute academic curriculum and examinations",
                "module_association": "academic",
                "allowed_user_types": ["faculty"],
                "is_singular": True,
                "default_validity_days": 730,
                "conflict_role_codes": ["hod_cse", "hod_ece", "hod_me"],
                "permissions": ["academic.curriculum.manage", "academic.grades.approve"],
            },
            {
                "code": "hod_cse",
                "name": "Head of Department (CSE)",
                "description": "Head of Computer Science & Engineering department",
                "module_association": "academic",
                "allowed_user_types": ["faculty"],
                "is_singular": True,
                "default_validity_days": 365,
                "conflict_role_codes": ["dean_academic"],
                "permissions": ["department.courses.assign", "department.leave.recommend"],
            },
            {
                "code": "hod_ece",
                "name": "Head of Department (ECE)",
                "description": "Head of Electronics & Communication Engineering department",
                "module_association": "academic",
                "allowed_user_types": ["faculty"],
                "is_singular": True,
                "default_validity_days": 365,
                "permissions": ["department.courses.assign", "department.leave.recommend"],
            },
            {
                "code": "placement_convener",
                "name": "Placement Cell Convener",
                "description": "Faculty lead for training and campus placements",
                "module_association": "placement_cell",
                "allowed_user_types": ["faculty"],
                "is_singular": True,
                "default_validity_days": 365,
                "permissions": ["placement_cell.policy.manage", "placement_cell.offer.approve"],
            },
            {
                "code": "placement_coordinator",
                "name": "Placement Student Coordinator",
                "description": "Student placement representative assisting recruiters",
                "module_association": "placement_cell",
                "allowed_user_types": ["student"],
                "is_singular": False,
                "default_validity_days": 180,
                "permissions": ["placement_cell.posting.view", "placement_cell.interview.coordinate"],
            },
            {
                "code": "warden_hall3",
                "name": "Hall 3 Warden",
                "description": "Chief administrator for student hostel residence Hall 3",
                "module_association": "hostel",
                "allowed_user_types": ["faculty", "staff"],
                "is_singular": True,
                "default_validity_days": 365,
                "permissions": ["hostel.room.allocate", "hostel.discipline.log"],
            },
            {
                "code": "it_head",
                "name": "IT Head",
                "description": "Institute Head of IT Infrastructure and Security",
                "module_association": "system_admin",
                "allowed_user_types": ["faculty", "staff"],
                "is_singular": True,
                "default_validity_days": 730,
                "permissions": ["system_admin.purge.authorize", "system_admin.audit.view"],
            },
        ]
        created_roles = {}
        for r_data in roles_data:
            role_obj, _ = RoleDefinition.objects.update_or_create(
                code=r_data["code"],
                defaults=r_data,
            )
            created_roles[r_data["code"]] = role_obj
        self.stdout.write(f"  seeded {len(created_roles)} role definitions")

        # 3. Sample Basic Users
        users_data = [
            {
                "institute_id": "2024CS01",
                "user_type": "student",
                "email": "aditya.v@iiitdmj.ac.in",
                "first_name": "Aditya",
                "last_name": "Verma",
                "contact_number": "+91 9876543210",
                "department": "Computer Science & Engineering",
                "programme": "B.Tech",
                "discipline": "CSE",
                "batch_year": 2024,
                "status": "active",
            },
            {
                "institute_id": "2024EC02",
                "user_type": "student",
                "email": "pooja.s@iiitdmj.ac.in",
                "first_name": "Pooja",
                "last_name": "Sharma",
                "contact_number": "+91 9876543211",
                "department": "Electronics & Communication Engineering",
                "programme": "B.Tech",
                "discipline": "ECE",
                "batch_year": 2024,
                "status": "active",
            },
            {
                "institute_id": "FAC101",
                "user_type": "faculty",
                "email": "rajesh.k@iiitdmj.ac.in",
                "first_name": "Dr. Rajesh",
                "last_name": "Kumar",
                "contact_number": "+91 9876543220",
                "department": "Computer Science & Engineering",
                "employee_id": "EMP101",
                "date_of_joining": date(2018, 7, 1),
                "status": "active",
            },
            {
                "institute_id": "FAC102",
                "user_type": "faculty",
                "email": "ananya.s@iiitdmj.ac.in",
                "first_name": "Dr. Ananya",
                "last_name": "Sen",
                "contact_number": "+91 9876543221",
                "department": "Electronics & Communication Engineering",
                "employee_id": "EMP102",
                "date_of_joining": date(2020, 1, 15),
                "status": "active",
            },
            {
                "institute_id": "STF201",
                "user_type": "staff",
                "email": "sunil.m@iiitdmj.ac.in",
                "first_name": "Sunil",
                "last_name": "Mishra",
                "contact_number": "+91 9876543230",
                "department": "Administration",
                "employee_id": "EMP201",
                "date_of_joining": date(2015, 3, 10),
                "status": "active",
            },
        ]
        created_users = {}
        for u_data in users_data:
            u_obj, _ = BasicUser.objects.update_or_create(
                institute_id=u_data["institute_id"],
                defaults=u_data,
            )
            created_users[u_data["institute_id"]] = u_obj
        self.stdout.write(f"  seeded {len(created_users)} basic users")

        # 4. Role Assignments
        today = date.today()
        assignments_data = [
            {
                "user_id": created_users["FAC101"].user_id,
                "role": created_roles["hod_cse"],
                "start_date": today - timedelta(days=60),
                "end_date": today + timedelta(days=305),
                "status": "active",
                "scope_type": "department",
                "scope_id": "CSE",
                "reason": "Appointed Head of Department by Director",
                "assigned_by_user_id": 1,
            },
            {
                "user_id": created_users["FAC102"].user_id,
                "role": created_roles["warden_hall3"],
                "start_date": today - timedelta(days=30),
                "end_date": today + timedelta(days=335),
                "status": "active",
                "scope_type": "hostel",
                "scope_id": "Hall 3",
                "reason": "Annual warden appointment",
                "assigned_by_user_id": 1,
            },
            {
                "user_id": created_users["2024CS01"].user_id,
                "role": created_roles["placement_coordinator"],
                "start_date": today,
                "end_date": today + timedelta(days=180),
                "status": "active",
                "scope_type": "institute",
                "scope_id": "",
                "reason": "Selected as placement student coordinator",
                "assigned_by_user_id": 1,
            },
        ]
        for a_data in assignments_data:
            RoleAssignment.objects.update_or_create(
                user_id=a_data["user_id"],
                role=a_data["role"],
                start_date=a_data["start_date"],
                defaults=a_data,
            )
        self.stdout.write(f"  seeded {len(assignments_data)} role assignments")

        # 5. Baseline Audit Entry
        AuditLog.objects.create(
            actor_user_id=1,
            actor_username="system_seed",
            action="system.seed",
            target_type="system",
            target_id="system_admin",
            result="success",
            reason="Initial environment setup and seed",
            details={"roles_seeded": len(created_roles), "users_seeded": len(created_users)},
        )
        self.stdout.write(self.style.SUCCESS("System Admin baseline seed complete."))
