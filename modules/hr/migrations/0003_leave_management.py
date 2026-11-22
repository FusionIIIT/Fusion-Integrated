import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


LEAVE_TYPES = [
    ("casual", "Casual"),
    ("restricted", "Restricted"),
    ("medical", "Medical"),
    ("earned", "Earned"),
    ("vacation", "Vacation"),
    ("sabbatical", "Sabbatical"),
]
CLAIM_TYPES = [
    ("ltc_advance", "LTC advance"),
    ("ltc_reimbursement", "LTC reimbursement"),
    ("cpda_advance", "CPDA advance"),
    ("cpda_reimbursement", "CPDA reimbursement"),
]
ROUTE_TYPES = [
    *CLAIM_TYPES,
    ("leave_casual", "Casual leave"),
    ("leave_restricted", "Restricted leave"),
    ("leave_medical", "Medical leave"),
    ("leave_earned", "Earned leave"),
    ("leave_vacation", "Vacation leave"),
    ("leave_sabbatical", "Sabbatical leave"),
]


class Migration(migrations.Migration):
    dependencies = [("hr", "0002_audit_event_immutable")]

    operations = [
        migrations.AlterField(
            model_name="workflowroute",
            name="request_type",
            field=models.CharField(max_length=24, choices=ROUTE_TYPES),
        ),
        migrations.AlterField(
            model_name="claim",
            name="request_type",
            field=models.CharField(max_length=24, choices=CLAIM_TYPES),
        ),
        migrations.CreateModel(
            name="LeaveBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("leave_type", models.CharField(max_length=16, choices=LEAVE_TYPES)),
                ("available_days", models.DecimalField(max_digits=8, decimal_places=2)),
                ("is_eligible", models.BooleanField(default=True)),
                ("updated_by_user_id", models.IntegerField()),
                ("employee", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="leave_balances", to="hr.employeerecord")),
            ],
            options={
                "db_table": "hr_leave_balance",
                "indexes": [models.Index(fields=["leave_type", "is_eligible"],
                                         name="hr_leave_type_eligible_idx")],
                "constraints": [
                    models.UniqueConstraint(fields=("employee", "leave_type"),
                                            name="hr_leave_balance_employee_type_uniq"),
                    models.CheckConstraint(condition=Q(available_days__gte=0),
                                           name="hr_leave_balance_nonnegative"),
                ],
            },
        ),
        migrations.CreateModel(
            name="LeaveRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("leave_type", models.CharField(max_length=16, choices=LEAVE_TYPES)),
                ("duration_days", models.DecimalField(max_digits=7, decimal_places=2)),
                ("justification", models.CharField(max_length=1000)),
                ("status", models.CharField(max_length=28, default="pending_authority",
                                             choices=[
                                                 ("pending_authority", "Pending current authority"),
                                                 ("pending_next_authority", "Pending next authority"),
                                                 ("approved", "Approved"),
                                                 ("rejected", "Rejected"),
                                             ])),
                ("route_snapshot", models.JSONField(default=list)),
                ("authority_step", models.PositiveIntegerField(default=0)),
                ("current_authority_user_id", models.IntegerField(null=True, blank=True)),
                ("submitted_by_user_id", models.IntegerField()),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                                to="hr.employeerecord")),
            ],
            options={
                "db_table": "hr_leave_request",
                "indexes": [
                    models.Index(fields=["employee", "-created_at"],
                                 name="hr_leave_employee_recent_idx"),
                    models.Index(fields=["status", "current_authority_user_id"],
                                 name="hr_leave_authority_status_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(condition=Q(duration_days__gt=0),
                                           name="hr_leave_duration_positive"),
                    models.CheckConstraint(condition=Q(status__in=[
                        "pending_authority", "pending_next_authority", "approved", "rejected",
                    ]), name="hr_leave_status_valid"),
                ],
            },
        ),
        migrations.CreateModel(
            name="LeaveLedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("entry_type", models.CharField(max_length=24, choices=[
                    ("balance_configured", "Balance configured"),
                    ("leave_approved", "Leave approved"),
                ])),
                ("amount_delta", models.DecimalField(max_digits=8, decimal_places=2)),
                ("actor_user_id", models.IntegerField()),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("balance", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="entries", to="hr.leavebalance")),
                ("leave_request", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="ledger_entries", to="hr.leaverequest")),
            ],
            options={
                "db_table": "hr_leave_ledger_entry",
                "indexes": [
                    models.Index(fields=["balance", "created_at"],
                                 name="hr_leave_ledger_balance_idx"),
                    models.Index(fields=["leave_request", "created_at"],
                                 name="hr_leave_ledger_request_idx"),
                ],
            },
        ),
        migrations.RunPython(
            code=lambda apps, schema_editor: _install_ledger_immutability(schema_editor),
            reverse_code=lambda apps, schema_editor: _remove_ledger_immutability(schema_editor),
        ),
    ]


def _install_ledger_immutability(schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
        CREATE OR REPLACE FUNCTION hr_reject_leave_ledger_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'HR leave ledger entries are immutable';
        END;
        $$
    """)
    schema_editor.execute("""
        CREATE TRIGGER hr_leave_ledger_immutable
        BEFORE UPDATE OR DELETE ON hr_leave_ledger_entry
        FOR EACH ROW EXECUTE FUNCTION hr_reject_leave_ledger_mutation()
    """)


def _remove_ledger_immutability(schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS hr_leave_ledger_immutable ON hr_leave_ledger_entry")
    schema_editor.execute("DROP FUNCTION IF EXISTS hr_reject_leave_ledger_mutation()")
