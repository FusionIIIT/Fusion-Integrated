# Initial IAA schema. Generated-style migration kept dependency-free from other apps.
import django.db.models.deletion
from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="IAAExpenseRequest", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("claimant_user_id", models.PositiveBigIntegerField(db_index=True)), ("department_id", models.CharField(blank=True,max_length=80)),
            ("request_type", models.CharField(choices=[("expense","Expense"),("voucher","Voucher")],max_length=16)),
            ("title",models.CharField(max_length=180)),("description",models.TextField(blank=True)),
            ("amount",models.DecimalField(decimal_places=2,max_digits=14)),("currency",models.CharField(default="INR",max_length=3)),
            ("financial_year",models.CharField(max_length=9)),("budget_code",models.CharField(blank=True,max_length=80)),
            ("attachments",models.JSONField(blank=True,default=list)),
            ("status",models.CharField(choices=[(x,x.replace("_"," ").title()) for x in ("draft","submitted","finance_review","clarification","pending_approval","approved","rejected","processed","cancelled")],db_index=True,default="draft",max_length=24)),
            ("submitted_at",models.DateTimeField(blank=True,null=True)),("locked_at",models.DateTimeField(blank=True,null=True)),
        ], options={"db_table":"iaa_expense_request","ordering":["-created_at"]}),
        migrations.CreateModel(name="IAAPolicy", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),
            ("financial_year",models.CharField(max_length=9,unique=True)),("parameters",models.JSONField(blank=True,default=dict)),("approval_rules",models.JSONField(blank=True,default=list)),("is_active",models.BooleanField(default=False)),("updated_by_user_id",models.PositiveBigIntegerField(blank=True,null=True)),
        ],options={"db_table":"iaa_policy"}),
        migrations.CreateModel(name="IAAAuditObservation", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),
            ("reference",models.CharField(max_length=100,unique=True)),("title",models.CharField(max_length=180)),("finding",models.TextField()),("owner_user_id",models.PositiveBigIntegerField(blank=True,null=True)),("response",models.TextField(blank=True)),("closure_evidence",models.TextField(blank=True)),
            ("status",models.CharField(choices=[("open","Open"),("responded","Responded"),("closed","Closed")],default="open",max_length=24)),("raised_by_user_id",models.PositiveBigIntegerField()),
        ],options={"db_table":"iaa_audit_observation","ordering":["-created_at"]}),
        migrations.CreateModel(name="IAAAnomaly", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),
            ("reference",models.CharField(blank=True,max_length=100)),("category",models.CharField(max_length=80)),("description",models.TextField()),("status",models.CharField(choices=[("open","Open"),("investigating","Investigating"),("resolved","Resolved"),("escalated","Escalated")],default="open",max_length=16)),("raised_by_user_id",models.PositiveBigIntegerField()),("resolution",models.TextField(blank=True)),("resolved_by_user_id",models.PositiveBigIntegerField(blank=True,null=True)),("resolved_at",models.DateTimeField(blank=True,null=True)),
            ("request",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="anomalies",to="iaa.iaaexpenserequest")),
        ],options={"db_table":"iaa_anomaly","ordering":["-created_at"]}),
        migrations.CreateModel(name="IATravelClaim", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),("claimant_user_id",models.PositiveBigIntegerField(db_index=True)),("trip_purpose",models.CharField(max_length=180)),("start_date",models.DateField()),("end_date",models.DateField()),("amount",models.DecimalField(decimal_places=2,max_digits=14)),("currency",models.CharField(default="INR",max_length=3)),("details",models.JSONField(blank=True,default=dict)),("status",models.CharField(choices=[(x,x.replace("_"," ").title()) for x in ("draft","submitted","verified","pending_approval","approved","rejected","processed")],db_index=True,default="draft",max_length=24)),("submitted_at",models.DateTimeField(blank=True,null=True)),
        ],options={"db_table":"iaa_travel_claim","ordering":["-created_at"]}),
        migrations.CreateModel(name="IAAAuditEvent", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("aggregate_type",models.CharField(max_length=40)),("aggregate_id",models.PositiveBigIntegerField()),("action",models.CharField(max_length=80)),("actor_user_id",models.PositiveBigIntegerField(blank=True,null=True)),("actor_role",models.CharField(blank=True,max_length=80)),("before",models.JSONField(blank=True,default=dict)),("after",models.JSONField(blank=True,default=dict)),("remarks",models.TextField(blank=True)),("occurred_at",models.DateTimeField(auto_now_add=True)),
        ],options={"db_table":"iaa_audit_event","ordering":["-occurred_at"],"indexes":[models.Index(fields=["aggregate_type","aggregate_id"],name="iaa_audit_aggregate_idx")]}),
        migrations.CreateModel(name="IAAApproval", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),("level",models.PositiveSmallIntegerField(default=1)),("approver_user_id",models.PositiveBigIntegerField(db_index=True)),("approver_role",models.CharField(max_length=80)),("decision",models.CharField(choices=[("approved","Approved"),("rejected","Rejected"),("escalated","Escalated")],max_length=16)),("remarks",models.TextField()),("decided_at",models.DateTimeField(default=django.utils.timezone.now)),
            ("request",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="approvals",to="iaa.iaaexpenserequest")),
        ],options={"db_table":"iaa_approval","ordering":["level","decided_at"],"constraints":[models.UniqueConstraint(fields=("request","level"),name="iaa_one_decision_per_level")]}),
    ]
