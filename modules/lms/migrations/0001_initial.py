import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CourseWorkspace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('external_offering_key', models.CharField(max_length=68, unique=True)),
                ('syllabus', models.TextField(blank=True)),
                ('schedule', models.TextField(blank=True)),
                ('details_published_at', models.DateTimeField(blank=True, null=True)),
                ('created_by_user_id', models.IntegerField(null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Assignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(blank=True, max_length=200)),
                ('instructions', models.TextField()),
                ('due_at', models.DateTimeField()),
                ('submission_type', models.CharField(max_length=4)),
                ('points_possible', models.DecimalField(decimal_places=2, max_digits=10)),
                ('state', models.CharField(default='DRAFT', max_length=10)),
                ('release_at', models.DateTimeField(blank=True, null=True)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('author_user_id', models.IntegerField()),
                ('publisher_user_id', models.IntegerField(null=True)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lms.courseworkspace')),
            ],
        ),
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content', models.TextField()),
                ('author_user_id', models.IntegerField()),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lms.courseworkspace')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MaterialSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('kind', models.CharField(choices=[('MODULE', 'Module'), ('WEEK', 'Week')], max_length=6)),
                ('label', models.CharField(max_length=200)),
                ('order', models.PositiveIntegerField(default=0)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lms.courseworkspace')),
            ],
        ),
        migrations.CreateModel(
            name='StoredFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner_user_id', models.IntegerField()),
                ('storage_key', models.CharField(max_length=160, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('mime_type', models.CharField(max_length=120)),
                ('size', models.PositiveIntegerField()),
                ('sha256', models.CharField(max_length=64)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lms.courseworkspace')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Material',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(blank=True, max_length=200)),
                ('kind', models.CharField(max_length=4)),
                ('text', models.TextField(blank=True)),
                ('url', models.URLField(blank=True, max_length=2000)),
                ('order', models.PositiveIntegerField(default=0)),
                ('state', models.CharField(default='DRAFT', max_length=10)),
                ('release_at', models.DateTimeField(blank=True, null=True)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('author_user_id', models.IntegerField()),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lms.courseworkspace')),
                ('section', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='lms.materialsection')),
                ('stored_file', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='lms.storedfile')),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('kind', models.CharField(max_length=4)),
                ('text', models.TextField(blank=True)),
                ('url', models.URLField(blank=True, max_length=2000)),
                ('submitted_at', models.DateTimeField()),
                ('policy_version', models.CharField(default='A9-LMS-BP-0.2', max_length=32)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lms.assignment')),
                ('stored_file', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='lms.storedfile')),
            ],
        ),
        migrations.CreateModel(
            name='GradeAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor_user_id', models.IntegerField()),
                ('operation', models.CharField(max_length=16)),
                ('old_points', models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ('new_points', models.DecimalField(decimal_places=2, max_digits=10)),
                ('old_feedback', models.TextField(blank=True)),
                ('new_feedback', models.TextField(blank=True)),
                ('old_state', models.CharField(max_length=8)),
                ('new_state', models.CharField(max_length=8)),
                ('changed_at', models.DateTimeField()),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='grade_audit', to='lms.submission')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Grade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('points', models.DecimalField(decimal_places=2, max_digits=10)),
                ('feedback', models.TextField(blank=True)),
                ('state', models.CharField(default='DRAFT', max_length=8)),
                ('grader_user_id', models.IntegerField()),
                ('graded_at', models.DateTimeField()),
                ('released_by_user_id', models.IntegerField(null=True)),
                ('released_at', models.DateTimeField(null=True)),
                ('submission', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='grade', to='lms.submission')),
            ],
        ),
        migrations.CreateModel(
            name='CoursePolicyVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.PositiveIntegerField()),
                ('effective_from', models.DateTimeField()),
                ('can_ta_post_announcements', models.BooleanField(default=False)),
                ('decision_version', models.CharField(default='A9-LMS-BP-0.2', max_length=32)),
                ('author_user_id', models.IntegerField(null=True)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lms.courseworkspace')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('workspace', 'version'), name='lms_policy_version_uniq'), models.UniqueConstraint(fields=('workspace', 'effective_from'), name='lms_policy_time_uniq')],
            },
        ),
        migrations.AddIndex(
            model_name='assignment',
            index=models.Index(fields=['workspace', 'state'], name='lms_assignment_scope'),
        ),
        migrations.AddIndex(
            model_name='assignment',
            index=models.Index(fields=['state', 'release_at'], name='lms_assignment_due'),
        ),
        migrations.AddConstraint(
            model_name='assignment',
            constraint=models.CheckConstraint(condition=models.Q(('points_possible__gte', 0)), name='lms_assignment_points'),
        ),
        migrations.AddConstraint(
            model_name='assignment',
            constraint=models.CheckConstraint(condition=models.Q(('submission_type__in', ('FILE', 'TEXT', 'LINK'))), name='lms_assignment_kind_valid'),
        ),
        migrations.AddConstraint(
            model_name='assignment',
            constraint=models.CheckConstraint(condition=models.Q(('state__in', ('DRAFT', 'SCHEDULED', 'AVAILABLE'))), name='lms_assignment_state_valid'),
        ),
        migrations.AddConstraint(
            model_name='assignment',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('state', 'SCHEDULED'), _negated=True), ('release_at__isnull', False), _connector='OR'), name='lms_assignment_scheduled_time'),
        ),
        migrations.AddConstraint(
            model_name='materialsection',
            constraint=models.CheckConstraint(condition=models.Q(('kind__in', ('MODULE', 'WEEK'))), name='lms_section_kind_valid'),
        ),
        migrations.AddIndex(
            model_name='material',
            index=models.Index(fields=['workspace', 'state', 'order'], name='lms_material_scope'),
        ),
        migrations.AddIndex(
            model_name='material',
            index=models.Index(fields=['state', 'release_at'], name='lms_material_due'),
        ),
        migrations.AddConstraint(
            model_name='material',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('kind', 'NOTE'), ('stored_file__isnull', True), ('url', ''), models.Q(('text', ''), _negated=True)), models.Q(('kind', 'LINK'), ('stored_file__isnull', True), ('text', ''), models.Q(('url', ''), _negated=True)), models.Q(('kind', 'FILE'), ('stored_file__isnull', False), ('text', ''), ('url', '')), _connector='OR'), name='lms_material_payload'),
        ),
        migrations.AddConstraint(
            model_name='material',
            constraint=models.CheckConstraint(condition=models.Q(('state__in', ('DRAFT', 'SCHEDULED', 'PUBLISHED'))), name='lms_material_state_valid'),
        ),
        migrations.AddConstraint(
            model_name='material',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('state', 'SCHEDULED'), _negated=True), ('release_at__isnull', False), _connector='OR'), name='lms_material_scheduled_time'),
        ),
        migrations.AddConstraint(
            model_name='submission',
            constraint=models.UniqueConstraint(fields=('assignment', 'user_id'), name='lms_submission_assignment_user_uniq'),
        ),
        migrations.AddConstraint(
            model_name='submission',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('kind', 'TEXT'), ('stored_file__isnull', True), ('url', ''), models.Q(('text', ''), _negated=True)), models.Q(('kind', 'LINK'), ('stored_file__isnull', True), ('text', ''), models.Q(('url', ''), _negated=True)), models.Q(('kind', 'FILE'), ('stored_file__isnull', False), ('text', ''), ('url', '')), _connector='OR'), name='lms_submission_payload'),
        ),
        migrations.AddConstraint(
            model_name='grade',
            constraint=models.CheckConstraint(condition=models.Q(('points__gte', 0)), name='lms_grade_points_nonnegative'),
        ),
        migrations.AddConstraint(
            model_name='grade',
            constraint=models.CheckConstraint(condition=models.Q(('state__in', ('DRAFT', 'RELEASED'))), name='lms_grade_state'),
        ),
        migrations.AddConstraint(
            model_name='grade',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('state', 'RELEASED'), _negated=True), models.Q(('released_at__isnull', False), ('released_by_user_id__isnull', False)), _connector='OR'), name='lms_grade_release_attribution'),
        ),
    ]
