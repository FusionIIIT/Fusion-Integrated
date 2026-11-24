# Migration for dept

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("code", models.CharField(max_length=32, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True, default="")),
                ("core_policies", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "dept_department",
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("item_code", models.CharField(max_length=64)),
                ("name", models.CharField(max_length=255)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("EQUIPMENT", "Equipment"),
                            ("CONSUMABLE", "Consumable"),
                            ("FURNITURE", "Furniture"),
                            ("OTHER", "Other"),
                        ],
                        default="CONSUMABLE",
                        max_length=64,
                    ),
                ),
                ("quantity", models.IntegerField(default=0)),
                ("unit", models.CharField(default="units", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inventory_items",
                        to="dept.department",
                    ),
                ),
            ],
            options={
                "db_table": "dept_inventory_item",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="LabResource",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("lab_name", models.CharField(max_length=150)),
                ("location", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True, default="")),
                ("equipment_details", models.JSONField(blank=True, default=list)),
                ("in_charge_id", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lab_resources",
                        to="dept.department",
                    ),
                ),
            ],
            options={
                "db_table": "dept_lab_resource",
                "ordering": ["lab_name"],
            },
        ),
        migrations.CreateModel(
            name="OfficialDetailChangeRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("proposed_by_id", models.CharField(max_length=64)),
                ("field_name", models.CharField(max_length=64)),
                ("old_value", models.TextField(blank=True, default="")),
                ("new_value", models.TextField()),
                ("justification", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("reviewed_by_id", models.CharField(blank=True, default="", max_length=64)),
                ("review_reason", models.TextField(blank=True, default="")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="official_changes",
                        to="dept.department",
                    ),
                ),
            ],
            options={
                "db_table": "dept_official_change_request",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="StockRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("requested_by_id", models.CharField(max_length=64)),
                ("requested_quantity", models.IntegerField()),
                ("purpose", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("SUBMITTED", "Submitted"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                            ("ISSUED", "Issued"),
                        ],
                        default="SUBMITTED",
                        max_length=16,
                    ),
                ),
                ("hod_decision_by_id", models.CharField(blank=True, default="", max_length=64)),
                ("hod_decision_at", models.DateTimeField(blank=True, null=True)),
                ("hod_remarks", models.TextField(blank=True, default="")),
                ("issued_by_id", models.CharField(blank=True, default="", max_length=64)),
                ("issued_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_requests",
                        to="dept.department",
                    ),
                ),
                (
                    "inventory_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requests",
                        to="dept.inventoryitem",
                    ),
                ),
            ],
            options={
                "db_table": "dept_stock_request",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="StockTransaction",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "transaction_type",
                    models.CharField(
                        choices=[
                            ("INSERTION", "Insertion"),
                            ("ISSUANCE", "Issuance"),
                            ("ADJUSTMENT", "Adjustment"),
                        ],
                        max_length=16,
                    ),
                ),
                ("quantity_delta", models.IntegerField()),
                ("balance_after", models.IntegerField()),
                ("performed_by_id", models.CharField(max_length=64)),
                ("related_request_id", models.UUIDField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "inventory_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transactions",
                        to="dept.inventoryitem",
                    ),
                ),
            ],
            options={
                "db_table": "dept_stock_transaction",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TimetableEntry",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("program", models.CharField(max_length=64)),
                ("academic_year", models.IntegerField()),
                ("semester", models.IntegerField()),
                (
                    "day_of_week",
                    models.IntegerField(
                        choices=[
                            (0, "Monday"),
                            (1, "Tuesday"),
                            (2, "Wednesday"),
                            (3, "Thursday"),
                            (4, "Friday"),
                            (5, "Saturday"),
                            (6, "Sunday"),
                        ]
                    ),
                ),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("course_code", models.CharField(max_length=32)),
                ("course_name", models.CharField(max_length=255)),
                ("instructor_id", models.CharField(max_length=64)),
                ("room_or_lab", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="timetables",
                        to="dept.department",
                    ),
                ),
            ],
            options={
                "db_table": "dept_timetable_entry",
                "ordering": ["day_of_week", "start_time"],
            },
        ),
        migrations.CreateModel(
            name="UserProfileExtension",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("user_id", models.CharField(max_length=64)),
                (
                    "profile_type",
                    models.CharField(
                        choices=[
                            ("STUDENT", "Student"),
                            ("FACULTY", "Faculty"),
                            ("ALUMNI", "Alumni"),
                        ],
                        max_length=32,
                    ),
                ),
                ("office_room", models.CharField(blank=True, default="", max_length=64)),
                ("research_interests", models.TextField(blank=True, default="")),
                ("contact_phone", models.CharField(blank=True, default="", max_length=32)),
                ("emergency_contact", models.CharField(blank=True, default="", max_length=128)),
                ("courses_taught", models.JSONField(blank=True, default=list)),
                ("batch_or_roll", models.CharField(blank=True, default="", max_length=32)),
                ("graduation_year", models.IntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile_extensions",
                        to="dept.department",
                    ),
                ),
            ],
            options={
                "db_table": "dept_user_profile_extension",
                "ordering": ["user_id"],
            },
        ),
        migrations.CreateModel(
            name="Announcement",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField()),
                ("author_id", models.CharField(max_length=64)),
                ("author_role", models.CharField(max_length=32)),
                ("target_role", models.CharField(default="ALL", max_length=32)),
                ("target_program", models.CharField(default="ALL", max_length=64)),
                ("target_academic_year", models.IntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("HIDDEN", "Hidden"),
                            ("DELETED", "Deleted"),
                        ],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="announcements",
                        to="dept.department",
                    ),
                ),
            ],
            options={
                "db_table": "dept_announcement",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["department", "status", "-created_at"],
                        name="dept_announ_departm_b2d1b3_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="DepartmentRoleAssignment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "role_name",
                    models.CharField(
                        choices=[
                            ("HOD", "Head of Department"),
                            ("DEPT_ADMIN", "Department Administrator"),
                        ],
                        max_length=32,
                    ),
                ),
                ("user_id", models.CharField(max_length=64)),
                ("start_date", models.DateTimeField()),
                ("end_date", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("SCHEDULED", "Scheduled"),
                            ("ACTIVE", "Active"),
                            ("REVOKED", "Revoked"),
                            ("EXPIRED", "Expired"),
                        ],
                        default="SCHEDULED",
                        max_length=16,
                    ),
                ),
                ("assigned_by_id", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_assignments",
                        to="dept.department",
                    ),
                ),
            ],
            options={
                "db_table": "dept_role_assignment",
                "ordering": ["-start_date"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("start_date__lt", models.F("end_date"))),
                        name="valid_role_tenure_range",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("status", "ACTIVE")),
                        fields=("department", "role_name"),
                        name="unique_active_role_per_department",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Feedback",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("submitted_by_id", models.CharField(max_length=64)),
                ("submitter_role", models.CharField(max_length=32)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("ACADEMIC", "Academic"),
                            ("INFRASTRUCTURE", "Infrastructure"),
                            ("ADMINISTRATIVE", "Administrative"),
                            ("OTHER", "Other"),
                        ],
                        default="ACADEMIC",
                        max_length=64,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("NEW", "New"),
                            ("UNDER_REVIEW", "Under Review"),
                            ("RESOLVED", "Resolved"),
                            ("CLOSED", "Closed"),
                        ],
                        default="NEW",
                        max_length=16,
                    ),
                ),
                ("admin_remarks", models.TextField(blank=True, default="")),
                ("reviewed_by_admin_id", models.CharField(blank=True, default="", max_length=64)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("terminal_by_id", models.CharField(blank=True, default="", max_length=64)),
                ("terminal_by_role", models.CharField(blank=True, default="", max_length=32)),
                ("terminal_remarks", models.TextField(blank=True, default="")),
                ("terminal_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedbacks",
                        to="dept.department",
                    ),
                ),
            ],
            options={
                "db_table": "dept_feedback",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["department", "status", "-created_at"],
                        name="dept_feedba_departm_637254_idx",
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.UniqueConstraint(
                fields=("department", "item_code"), name="unique_dept_inventory_item"
            ),
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.CheckConstraint(
                condition=models.Q(("quantity__gte", 0)), name="non_negative_inventory_quantity"
            ),
        ),
        migrations.AddConstraint(
            model_name="labresource",
            constraint=models.UniqueConstraint(
                fields=("department", "lab_name"), name="unique_dept_lab_name"
            ),
        ),
        migrations.AddIndex(
            model_name="stockrequest",
            index=models.Index(
                fields=["department", "status", "-created_at"],
                name="dept_stock__departm_7429ef_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockrequest",
            index=models.Index(
                fields=["requested_by_id", "status"], name="dept_stock__request_df96cb_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="stockrequest",
            constraint=models.CheckConstraint(
                condition=models.Q(("requested_quantity__gt", 0)),
                name="positive_stock_request_quantity",
            ),
        ),
        migrations.AddIndex(
            model_name="timetableentry",
            index=models.Index(
                fields=["department", "program", "academic_year", "semester"],
                name="dept_timeta_departm_538fd4_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="timetableentry",
            index=models.Index(
                fields=["day_of_week", "start_time", "end_time"],
                name="dept_timeta_day_of__b11f79_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="timetableentry",
            constraint=models.CheckConstraint(
                condition=models.Q(("start_time__lt", models.F("end_time"))),
                name="valid_timetable_time_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="userprofileextension",
            constraint=models.UniqueConstraint(
                fields=("department", "user_id"), name="unique_dept_user_profile"
            ),
        ),
    ]
