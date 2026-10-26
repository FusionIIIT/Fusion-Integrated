from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("elm", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="HolidayCalendar",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("year", models.PositiveSmallIntegerField(db_index=True, unique=True)),
                ("is_published", models.BooleanField(db_index=True, default=False)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("published_by", models.IntegerField(blank=True, null=True)),
            ],
            options={
                "db_table": "elm_holiday_calendar",
            },
        ),
        migrations.CreateModel(
            name="Holiday",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("date", models.DateField(db_index=True)),
                ("name", models.CharField(max_length=120)),
                ("is_rh", models.BooleanField(default=False)),
                ("is_closed", models.BooleanField(default=True)),
                (
                    "calendar",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="holidays",
                        to="elm.holidaycalendar",
                    ),
                ),
            ],
            options={
                "db_table": "elm_holiday",
            },
        ),
        migrations.AddConstraint(
            model_name="holiday",
            constraint=models.UniqueConstraint(
                fields=("calendar", "date", "name"),
                name="elm_holiday_cal_date_name_uniq",
            ),
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("cl", "Casual Leave"),
                            ("rh", "Restricted Holiday"),
                            ("scl", "Special Casual Leave"),
                            ("el", "Earned Leave"),
                            ("col", "Commuted Leave"),
                            ("vl", "Vacation Leave"),
                        ],
                        max_length=10,
                    ),
                ),
                ("year", models.PositiveSmallIntegerField(db_index=True)),
                (
                    "credited",
                    models.DecimalField(
                        decimal_places=1, default=Decimal("0.0"), max_digits=5
                    ),
                ),
                (
                    "carried_forward",
                    models.DecimalField(
                        decimal_places=1, default=Decimal("0.0"), max_digits=5
                    ),
                ),
                (
                    "converted_in",
                    models.DecimalField(
                        decimal_places=1, default=Decimal("0.0"), max_digits=5
                    ),
                ),
                (
                    "availed",
                    models.DecimalField(
                        decimal_places=1, default=Decimal("0.0"), max_digits=5
                    ),
                ),
                (
                    "pending",
                    models.DecimalField(
                        decimal_places=1, default=Decimal("0.0"), max_digits=5
                    ),
                ),
                (
                    "converted_out",
                    models.DecimalField(
                        decimal_places=1, default=Decimal("0.0"), max_digits=5
                    ),
                ),
            ],
            options={
                "db_table": "elm_leave_balance",
            },
        ),
        migrations.AddConstraint(
            model_name="leavebalance",
            constraint=models.UniqueConstraint(
                fields=("user_id", "category", "year"),
                name="elm_balance_user_cat_year_uniq",
            ),
        ),
        migrations.CreateModel(
            name="YearEndProcessingLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                ("year", models.PositiveSmallIntegerField(db_index=True)),
                ("process_type", models.CharField(max_length=30)),
                ("vl_converted", models.DecimalField(decimal_places=1, max_digits=5)),
                ("el_credited", models.DecimalField(decimal_places=1, max_digits=5)),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "elm_yearend_processing_log",
            },
        ),
        migrations.AddConstraint(
            model_name="yearendprocessinglog",
            constraint=models.UniqueConstraint(
                fields=("user_id", "year", "process_type"),
                name="elm_yearend_user_year_type_uniq",
            ),
        ),
        migrations.AlterModelTable(
            name="leaverequest",
            table="elm_leaverequest",
        ),
        migrations.AlterField(
            model_name="leaverequest",
            name="category",
            field=models.CharField(
                choices=[
                    ("cl", "Casual Leave"),
                    ("rh", "Restricted Holiday"),
                    ("scl", "Special Casual Leave"),
                    ("el", "Earned Leave"),
                    ("col", "Commuted Leave"),
                    ("vl", "Faculty Vacation Leave"),
                ],
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="leaverequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("submitted", "Submitted (Legacy)"),
                    ("pending_substitute", "Pending Substitute Response"),
                    ("substitute_declined", "Substitute Declined"),
                    ("pending_unit_head", "Pending Unit Head Review"),
                    ("pending_sanction", "Pending Final Sanction"),
                    (
                        "awaiting_director_self_sanction",
                        "Awaiting Director Self-Sanction",
                    ),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("withdrawn", "Withdrawn"),
                    (
                        "cancellation_pending_unit_head",
                        "Cancellation Pending Unit Head",
                    ),
                    (
                        "cancellation_pending_sanction",
                        "Cancellation Pending Final Sanction",
                    ),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="draft",
                max_length=35,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="half_day",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="half_day_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("first_half", "First Half"),
                    ("second_half", "Second Half"),
                ],
                max_length=16,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="leave_days",
            field=models.DecimalField(
                blank=True, decimal_places=1, max_digits=4, null=True
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="is_station_leave",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="station_address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="station_start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="station_end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="substitute_status",
            field=models.CharField(
                choices=[
                    ("none", "Not Required"),
                    ("pending", "Pending Consent"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                ],
                default="none",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="substitute_remarks",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="unit_head_recommendation",
            field=models.CharField(
                choices=[
                    ("none", "None"),
                    ("recommended", "Recommended"),
                    ("not_recommended", "Not Recommended"),
                ],
                default="none",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="unit_head_remarks",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="sanctioning_remarks",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(
                fields=["user_id", "status"], name="elm_req_user_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(
                fields=["substitute_id", "substitute_status"], name="elm_req_subst_idx"
            ),
        ),
        migrations.CreateModel(
            name="LeaveActionHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("actor_id", models.IntegerField(db_index=True)),
                ("action", models.CharField(max_length=35)),
                ("from_status", models.CharField(max_length=35)),
                ("to_status", models.CharField(max_length=35)),
                ("remarks", models.TextField(blank=True, default="")),
                (
                    "leave_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="actions",
                        to="elm.leaverequest",
                    ),
                ),
            ],
            options={
                "db_table": "elm_leave_action_history",
                "ordering": ["-created_at"],
            },
        ),
    ]
