from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("leave", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="leavetype",
            name="allows_half_day",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="is_half_day",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="half_day_slot",
            field=models.CharField(
                blank=True,
                choices=[("FORENOON", "Forenoon (First Half)"), ("AFTERNOON", "Afternoon (Second Half)")],
                max_length=15,
            ),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="is_station_leave",
            field=models.BooleanField(default=False),
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
            name="station_address",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="emergency_contact_no",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="attachment_path",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="recommender_user_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="recommendation_remarks",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="recommended_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="approval_remarks",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="leaverequest",
            name="rejection_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="leaverequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Draft"),
                    ("PENDING_APPROVAL", "Pending Approval"),
                    ("RECOMMENDED", "Recommended"),
                    ("APPROVED", "Approved"),
                    ("REJECTED", "Rejected"),
                    ("CANCELLED", "Cancelled"),
                ],
                default="PENDING_APPROVAL",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="LeaveLedger",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user_id", models.IntegerField(db_index=True)),
                (
                    "transaction_type",
                    models.CharField(
                        choices=[
                            ("CREDIT", "Credit"),
                            ("DEBIT", "Debit"),
                            ("RESTORE", "Restore"),
                            ("ADJUSTMENT", "Adjustment"),
                        ],
                        max_length=15,
                    ),
                ),
                ("days", models.DecimalField(decimal_places=1, max_digits=5)),
                ("balance_after", models.DecimalField(decimal_places=1, max_digits=5)),
                ("remarks", models.CharField(blank=True, max_length=255)),
                (
                    "leave_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ledger_entries",
                        to="leave.leavetype",
                    ),
                ),
                (
                    "reference_request",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ledger_entries",
                        to="leave.leaverequest",
                    ),
                ),
            ],
            options={
                "db_table": "leave_ledger",
            },
        ),
        migrations.AddIndex(
            model_name="leaverequest",
            index=models.Index(fields=["recommender_user_id", "status"], name="leave_req_recm_status_idx"),
        ),
        migrations.AddIndex(
            model_name="leaveledger",
            index=models.Index(fields=["user_id", "leave_type"], name="leave_ledger_user_type_idx"),
        ),
    ]
