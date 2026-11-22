# Initial schema for the patents module (Django 5.2.19, 2026-11-22 18:39)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AttorneyPanelMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True, unique=True)),
                ('firm_name', models.CharField(max_length=255)),
                ('expertise_domains', models.JSONField(default=list)),
                ('active_workload', models.PositiveIntegerField(default=0)),
                ('is_approved_panel', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'patents_attorney_panel',
            },
        ),
        migrations.CreateModel(
            name='CoInventor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('name', models.CharField(max_length=255)),
                ('email', models.EmailField(max_length=254)),
                ('share_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('consent_granted', models.BooleanField(default=False)),
                ('consent_timestamp', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'patents_coinventor',
            },
        ),
        migrations.CreateModel(
            name='CoInventorConsentToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('token_hash', models.CharField(max_length=64, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('co_inventor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consent_tokens', to='patents.coinventor')),
            ],
            options={
                'db_table': 'patents_coinventor_consent_token',
            },
        ),
        migrations.CreateModel(
            name='PatentApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('application_number', models.CharField(db_index=True, max_length=32, unique=True)),
                ('title', models.CharField(max_length=500)),
                ('abstract', models.TextField()),
                ('description', models.TextField()),
                ('claims', models.TextField()),
                ('status', models.CharField(db_index=True, default='draft', max_length=32)),
                ('domain_category', models.CharField(blank=True, default='', max_length=100)),
                ('assigned_director_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('assigned_attorney_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('external_filing_id', models.CharField(blank=True, default='', max_length=100)),
                ('filing_date', models.DateField(blank=True, null=True)),
                ('grant_date', models.DateField(blank=True, null=True)),
                ('renewal_due_date', models.DateField(blank=True, null=True)),
                ('renewal_decided_at', models.DateTimeField(blank=True, null=True)),
                ('jurisdiction', models.CharField(default='IN', max_length=50)),
                ('decision_date', models.DateTimeField(blank=True, null=True)),
                ('version', models.PositiveIntegerField(default=1)),
            ],
            options={
                'db_table': 'patents_application',
                'constraints': [models.CheckConstraint(condition=models.Q(('version__gte', 1)), name='patents_app_version_positive')],
            },
        ),
        migrations.CreateModel(
            name='OfficeActionRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('action_code', models.CharField(max_length=100)),
                ('issuing_authority', models.CharField(max_length=100)),
                ('issued_date', models.DateField()),
                ('response_deadline', models.DateField()),
                ('status', models.CharField(default='RECORDED', max_length=30)),
                ('requires_applicant_review', models.BooleanField(default=False)),
                ('response_summary', models.TextField(blank=True, default='')),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='office_actions', to='patents.patentapplication')),
            ],
            options={
                'db_table': 'patents_office_action',
            },
        ),
        migrations.AddField(
            model_name='coinventor',
            name='application',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='co_inventors', to='patents.patentapplication'),
        ),
        migrations.CreateModel(
            name='ApplicationDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document_type', models.CharField(max_length=50)),
                ('file_name', models.CharField(max_length=255)),
                ('file_format', models.CharField(default='pdf', max_length=10)),
                ('file_size_bytes', models.BigIntegerField()),
                ('storage_path', models.CharField(max_length=500)),
                ('sensitivity_level', models.CharField(default='confidential', max_length=30)),
                ('version', models.PositiveIntegerField(default=1)),
                ('uploaded_by_user_id', models.IntegerField(db_index=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='patents.patentapplication')),
            ],
            options={
                'db_table': 'patents_document',
            },
        ),
        migrations.CreateModel(
            name='AppealRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('applicant_user_id', models.IntegerField(db_index=True)),
                ('grounds', models.TextField()),
                ('status', models.CharField(default='SUBMITTED', max_length=30)),
                ('director_user_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('decision_notes', models.TextField(blank=True, default='')),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appeals', to='patents.patentapplication')),
            ],
            options={
                'db_table': 'patents_appeal_record',
            },
        ),
        migrations.CreateModel(
            name='PatentBudgetLedger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('entry_kind', models.CharField(choices=[('REQUEST', 'REQUEST'), ('APPROVAL', 'APPROVAL'), ('ESCALATION', 'ESCALATION'), ('REVERSAL', 'REVERSAL'), ('DISBURSEMENT', 'DISBURSEMENT')], default='REQUEST', max_length=20)),
                ('entry_type', models.CharField(max_length=30)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('category', models.CharField(max_length=50)),
                ('status', models.CharField(default='PENDING', max_length=30)),
                ('authorized_by_user_id', models.IntegerField(db_index=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budget_entries', to='patents.patentapplication')),
                ('replaces_entry', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='linked_entries', to='patents.patentbudgetledger')),
            ],
            options={
                'db_table': 'patents_budget_ledger',
            },
        ),
        migrations.CreateModel(
            name='PatentPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('director_review_days', models.PositiveIntegerField(default=15)),
                ('revision_resubmission_days', models.PositiveIntegerField(default=60)),
                ('cost_escalation_threshold', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('max_attorney_workload', models.PositiveIntegerField(blank=True, null=True)),
                ('max_document_size_bytes', models.BigIntegerField(default=52428800)),
                ('withdrawal_eligible_states', models.JSONField(default=list)),
                ('effective_from', models.DateTimeField(auto_now_add=True)),
                ('effective_to', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('superseded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supersedes', to='patents.patentpolicy')),
            ],
            options={
                'db_table': 'patents_policy',
            },
        ),
        migrations.CreateModel(
            name='ReviewDecision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('director_user_id', models.IntegerField(db_index=True)),
                ('decision', models.CharField(max_length=20)),
                ('justification', models.TextField()),
                ('assigned_at', models.DateTimeField(blank=True, null=True)),
                ('decided_at', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='patents.patentapplication')),
            ],
            options={
                'db_table': 'patents_review_decision',
            },
        ),
        migrations.CreateModel(
            name='TechnologyTransferRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('applicant_user_id', models.IntegerField(db_index=True)),
                ('request_type', models.CharField(max_length=50)),
                ('partner_name', models.CharField(max_length=255)),
                ('status', models.CharField(default='SUBMITTED', max_length=30)),
                ('confidentiality_level', models.CharField(default='confidential', max_length=30)),
                ('terms_summary', models.TextField(blank=True, default='')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='licensing_records', to='patents.patentapplication')),
            ],
            options={
                'db_table': 'patents_tech_transfer',
            },
        ),
        migrations.AddConstraint(
            model_name='coinventor',
            constraint=models.CheckConstraint(condition=models.Q(('share_percentage__gt', 0), ('share_percentage__lte', 100)), name='patents_coinventor_share_bounds'),
        ),
        migrations.AddConstraint(
            model_name='applicationdocument',
            constraint=models.CheckConstraint(condition=models.Q(('file_size_bytes__gt', 0), ('file_size_bytes__lte', 52428800)), name='patents_doc_size_bounds'),
        ),
    ]
