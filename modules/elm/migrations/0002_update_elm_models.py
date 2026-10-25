from decimal import Decimal
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elm", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="leavecategory",
            name="annual_quota",
            field=models.DecimalField(
                decimal_places=1, default=Decimal("0.0"), max_digits=5
            ),
        ),
        migrations.AddField(
            model_name="leavecategory",
            name="carries_forward",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leavecategory",
            name="code",
            field=models.CharField(default="CL", max_length=20, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="leavecategory",
            name="continuous_counting",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leavecategory",
            name="faculty_only",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leavecategory",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.RemoveField(
            model_name="leaveapplication",
            name="employee",
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="user_id",
            field=models.IntegerField(db_index=True, default=1),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="leaveapplication",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="applications",
                to="elm.leavecategory",
            ),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="days_count",
            field=models.DecimalField(
                decimal_places=1, default=Decimal("1.0"), max_digits=5
            ),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="emergency_contact",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="half_day",
            field=models.CharField(
                choices=[
                    ("none", "Full Day"),
                    ("first_half", "First Half"),
                    ("second_half", "Second Half"),
                ],
                default="none",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="sanction_acted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="sanction_remarks",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="sanctioning_authority_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="station_address",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="station_end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="station_leave",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="station_start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="leaveapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_substitute", "Awaiting Substitute Consent"),
                    ("submitted", "Pending Unit Head Review"),
                    ("pending_sanction", "Pending Sanctioning Authority"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("withdrawn", "Withdrawn"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="submitted",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="substitute_acted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="substitute_id",
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="substitute_remarks",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="substitute_status",
            field=models.CharField(
                choices=[
                    ("none", "None"),
                    ("pending", "Pending"),
                    ("accepted", "Accepted"),
                    ("declined", "Declined"),
                ],
                default="none",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="unit_head_acted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="unit_head_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="unit_head_recommendation",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("recommended", "Recommended"),
                    ("not_recommended", "Not Recommended"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="leaveapplication",
            name="unit_head_remarks",
            field=models.TextField(blank=True),
        ),
        migrations.AddIndex(
            model_name="leaveapplication",
            index=models.Index(
                fields=["user_id", "status"], name="elm_app_user_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="leaveapplication",
            index=models.Index(
                fields=["status", "start_date"], name="elm_app_status_start_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="leaveapplication",
            index=models.Index(
                fields=["substitute_id", "substitute_status"],
                name="elm_app_sub_status_idx",
            ),
        ),
        migrations.RemoveField(
            model_name="leavebalance",
            name="employee",
        ),
        migrations.AddField(
            model_name="leavebalance",
            name="user_id",
            field=models.IntegerField(db_index=True, default=1),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="leavebalance",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="balances",
                to="elm.leavecategory",
            ),
        ),
        migrations.AddField(
            model_name="leavebalance",
            name="consumed",
            field=models.DecimalField(
                decimal_places=1, default=Decimal("0.0"), max_digits=5
            ),
        ),
        migrations.AddField(
            model_name="leavebalance",
            name="credited",
            field=models.DecimalField(
                decimal_places=1, default=Decimal("0.0"), max_digits=5
            ),
        ),
        migrations.AddField(
            model_name="leavebalance",
            name="year",
            field=models.IntegerField(default=2026),
        ),
        migrations.AlterField(
            model_name="leavebalance",
            name="balance",
            field=models.DecimalField(
                decimal_places=1, default=Decimal("0.0"), max_digits=5
            ),
        ),
        migrations.AlterUniqueTogether(
            name="leavebalance",
            unique_together={("user_id", "category", "year")},
        ),
        migrations.AddIndex(
            model_name="leavebalance",
            index=models.Index(
                fields=["user_id", "year"], name="elm_bal_user_year_idx"
            ),
        ),
        migrations.CreateModel(
            name="LeaveHistory",
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
                ("actor_id", models.IntegerField()),
                ("action", models.CharField(max_length=50)),
                ("from_status", models.CharField(max_length=30)),
                ("to_status", models.CharField(max_length=30)),
                ("remarks", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history",
                        to="elm.leaveapplication",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Leave History",
                "db_table": "elm_leave_history",
                "ordering": ["-created_at"],
            },
        ),
    ]
