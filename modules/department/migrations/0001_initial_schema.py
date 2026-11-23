import django.contrib.postgres.fields
import django.contrib.postgres.operations
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('published_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('target_roles', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=80), blank=True, default=list, size=None)),
                ('target_programmes', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100), blank=True, default=list, size=None)),
                ('target_batch_years', django.contrib.postgres.fields.ArrayField(base_field=models.PositiveSmallIntegerField(), blank=True, default=list, size=None)),
            ],
            options={
                'indexes': [models.Index(condition=models.Q(('is_active', True)), fields=['department', '-id'], name='dept_announcement_active_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('department', ''), _negated=True), name='dept_announcement_has_scope'), models.CheckConstraint(condition=models.Q(('content', ''), _negated=True), name='dept_announcement_has_content')],
            },
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(db_index=True, max_length=200)),
                ('user_id', models.PositiveIntegerField()),
                ('content', models.TextField()),
                ('category', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(choices=[('new', 'New'), ('reviewed', 'Under review'), ('closed', 'Closed'), ('resolved', 'Resolved')], default='new', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(null=True)),
                ('reviewed_by_id', models.PositiveIntegerField(null=True)),
                ('disposed_at', models.DateTimeField(null=True)),
                ('disposed_by_id', models.PositiveIntegerField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='StockItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(max_length=200)),
                ('name', models.CharField(max_length=160)),
                ('quantity', models.PositiveIntegerField()),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('department', 'name'), name='dept_unique_stock_name')],
            },
        ),
        migrations.CreateModel(
            name='StockRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.PositiveIntegerField(db_index=True)),
                ('quantity', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('pending', 'Pending HOD approval'), ('approved', 'Approved for issuance'), ('rejected', 'Rejected'), ('issued', 'Issued')], default='pending', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='department.stockitem')),
            ],
        ),
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_id', models.PositiveIntegerField()),
                ('delta', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='department.stockitem')),
                ('request', models.OneToOneField(null=True, on_delete=django.db.models.deletion.PROTECT, to='department.stockrequest')),
            ],
        ),
        migrations.CreateModel(
            name='Notice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(db_index=True, max_length=200)),
                ('message', models.CharField(max_length=200)),
                ('user_id', models.PositiveIntegerField(null=True)),
                ('audience', models.CharField(blank=True, max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('announcement', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='department.announcement')),
            ],
            options={
                'constraints': [models.CheckConstraint(condition=models.Q(models.Q(('announcement__isnull', False), ('audience', ''), ('user_id__isnull', True)), models.Q(('announcement__isnull', True), ('audience', ''), ('user_id__isnull', False)), models.Q(('announcement__isnull', True), ('audience__in', ['hod', 'admin']), ('user_id__isnull', True)), _connector='OR'), name='dept_notice_one_audience')],
            },
        ),
        migrations.AddConstraint(
            model_name='stockrequest',
            constraint=models.CheckConstraint(condition=models.Q(('quantity__gt', 0)), name='dept_stock_request_positive'),
        ),
        migrations.AddConstraint(
            model_name='stockmovement',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('delta__gt', 0), ('request__isnull', True)), models.Q(('delta__lt', 0), ('request__isnull', False)), _connector='OR'), name='dept_stock_movement_direction'),
        ),
        migrations.AlterField(
            model_name='stockitem',
            name='quantity',
            field=models.PositiveBigIntegerField(),
        ),
        migrations.CreateModel(
            name='DepartmentDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(max_length=200, unique=True)),
                ('official_name', models.CharField(blank=True, max_length=200)),
                ('core_policies', models.TextField(blank=True)),
                ('general_information', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='LabResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(max_length=200)),
                ('name', models.CharField(max_length=160)),
                ('details', models.TextField()),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('department', 'name'), name='dept_unique_lab_name')],
            },
        ),
        migrations.CreateModel(
            name='TimetableSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(max_length=200)),
                ('term', models.CharField(max_length=40)),
                ('day', models.PositiveSmallIntegerField()),
                ('starts_at', models.TimeField()),
                ('ends_at', models.TimeField()),
                ('programme', models.CharField(max_length=100)),
                ('batch_year', models.PositiveSmallIntegerField()),
                ('room', models.CharField(max_length=100)),
                ('instructor_id', models.PositiveIntegerField()),
                ('title', models.CharField(max_length=160)),
                ('kind', models.CharField(choices=[('class', 'Class'), ('lab', 'Lab')], max_length=8)),
            ],
            options={
                'indexes': [models.Index(fields=['department', 'term', 'day'], name='dept_timetable_slots_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(('day__lte', 6)), name='dept_timetable_weekday'), models.CheckConstraint(condition=models.Q(('ends_at__gt', models.F('starts_at'))), name='dept_timetable_positive_duration')],
            },
        ),
        migrations.CreateModel(
            name='DepartmentProposal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(choices=[('official_name', 'Official name'), ('core_policies', 'Core policies')], max_length=20)),
                ('value', models.TextField()),
                ('status', models.CharField(default='pending', max_length=10)),
                ('proposed_by_id', models.PositiveIntegerField()),
                ('decided_by_id', models.PositiveIntegerField(null=True)),
                ('decided_at', models.DateTimeField(null=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='department.departmentdetails')),
            ],
            options={
                'constraints': [models.UniqueConstraint(condition=models.Q(('status', 'pending')), fields=('department', 'field'), name='dept_one_pending_field')],
            },
        ),
        django.contrib.postgres.operations.BtreeGistExtension(
        ),
        migrations.RunSQL(
            sql="\n                CREATE FUNCTION department_prevent_movement_change() RETURNS trigger\n                LANGUAGE plpgsql AS $$\n                BEGIN\n                    RAISE EXCEPTION 'Department stock movements are immutable'\n                        USING ERRCODE = 'integrity_constraint_violation';\n                END $$;\n                CREATE TRIGGER department_stock_movement_immutable\n                BEFORE UPDATE OR DELETE ON department_stockmovement\n                FOR EACH ROW EXECUTE FUNCTION department_prevent_movement_change();\n            ",
            reverse_sql='\n                DROP TRIGGER department_stock_movement_immutable ON department_stockmovement;\n                DROP FUNCTION department_prevent_movement_change();\n            ',
        ),
        migrations.RunSQL(
            sql="\n                ALTER TABLE department_timetableslot\n                ADD CONSTRAINT dept_timetable_room_overlap EXCLUDE USING gist (\n                    department WITH =, term WITH =, day WITH =, lower(room) WITH =,\n                    tsrange(DATE '2000-01-01' + starts_at, DATE '2000-01-01' + ends_at) WITH &&\n                ),\n                ADD CONSTRAINT dept_timetable_instructor_overlap EXCLUDE USING gist (\n                    department WITH =, term WITH =, day WITH =, instructor_id WITH =,\n                    tsrange(DATE '2000-01-01' + starts_at, DATE '2000-01-01' + ends_at) WITH &&\n                ),\n                ADD CONSTRAINT dept_timetable_cohort_overlap EXCLUDE USING gist (\n                    department WITH =, term WITH =, day WITH =, programme WITH =, batch_year WITH =,\n                    tsrange(DATE '2000-01-01' + starts_at, DATE '2000-01-01' + ends_at) WITH &&\n                );\n            ",
            reverse_sql='\n                ALTER TABLE department_timetableslot\n                DROP CONSTRAINT dept_timetable_room_overlap,\n                DROP CONSTRAINT dept_timetable_instructor_overlap,\n                DROP CONSTRAINT dept_timetable_cohort_overlap;\n            ',
        ),
    ]
