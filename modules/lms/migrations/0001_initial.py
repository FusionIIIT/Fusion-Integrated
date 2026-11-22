# Initial migration for LMS module.

import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(db_index=True, max_length=32, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('syllabus', models.TextField(blank=True)),
                ('schedule', models.CharField(blank=True, max_length=200)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='published', max_length=16)),
            ],
            options={
                'db_table': 'lms_course',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='CourseAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=200)),
                ('instructions', models.TextField(blank=True)),
                ('submission_type', models.CharField(choices=[('file', 'File Upload'), ('text', 'Text Entry'), ('link', 'Website Link')], default='file', max_length=16)),
                ('points_possible', models.DecimalField(decimal_places=2, default=Decimal('100.00'), max_digits=6)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published'), ('scheduled', 'Scheduled')], default='draft', max_length=16)),
                ('due_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('release_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('closes_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('allow_late', models.BooleanField(default=False)),
                ('file', models.FileField(blank=True, null=True, upload_to='lms/assignments/%Y/%m/')),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('file_size', models.BigIntegerField(blank=True, null=True)),
                ('created_by_user_id', models.IntegerField(db_index=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='lms.course')),
            ],
            options={
                'db_table': 'lms_course_assignment',
                'ordering': ['due_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CourseAssignmentExtension',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('extended_due_at', models.DateTimeField(db_index=True)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('granted_by_user_id', models.IntegerField(db_index=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extensions', to='lms.courseassignment')),
            ],
            options={
                'db_table': 'lms_course_assignment_extension',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CourseMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('material_type', models.CharField(choices=[('file', 'File'), ('link', 'Link'), ('note', 'Note')], default='file', max_length=16)),
                ('section_type', models.CharField(choices=[('module', 'Module'), ('week', 'Weekly Section')], default='module', max_length=16)),
                ('section_title', models.CharField(db_index=True, max_length=100)),
                ('file', models.FileField(blank=True, null=True, upload_to='lms/materials/%Y/%m/')),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('file_size', models.BigIntegerField(blank=True, null=True)),
                ('link_url', models.CharField(blank=True, max_length=500)),
                ('content', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published'), ('scheduled', 'Scheduled')], default='published', max_length=16)),
                ('release_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('order', models.IntegerField(default=0)),
                ('created_by_user_id', models.IntegerField(db_index=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='materials', to='lms.course')),
            ],
            options={
                'db_table': 'lms_course_material',
                'ordering': ['section_title', 'order', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CourseMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('role', models.CharField(choices=[('faculty', 'Faculty'), ('student', 'Student'), ('ta', 'Teaching Assistant'), ('observer', 'Observer')], max_length=16)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='lms.course')),
            ],
            options={
                'db_table': 'lms_course_membership',
                'ordering': ['course', 'role', 'user_id'],
            },
        ),
        migrations.CreateModel(
            name='CourseSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_user_id', models.IntegerField(db_index=True)),
                ('submission_type', models.CharField(choices=[('file', 'File Upload'), ('text', 'Text Entry'), ('link', 'Website Link')], max_length=16)),
                ('status', models.CharField(choices=[('submitted', 'Submitted'), ('late', 'Late')], default='submitted', max_length=16)),
                ('submitted_at', models.DateTimeField(db_index=True)),
                ('file', models.FileField(blank=True, null=True, upload_to='lms/submissions/%Y/%m/')),
                ('file_name', models.CharField(blank=True, max_length=255)),
                ('file_size', models.BigIntegerField(blank=True, null=True)),
                ('content_text', models.TextField(blank=True)),
                ('link_url', models.CharField(blank=True, max_length=500)),
                ('attempt_number', models.PositiveIntegerField(default=1)),
                ('is_latest', models.BooleanField(db_index=True, default=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='lms.courseassignment')),
            ],
            options={
                'db_table': 'lms_course_submission',
                'ordering': ['-submitted_at'],
            },
        ),
        migrations.CreateModel(
            name='CourseSubmissionGrade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_user_id', models.IntegerField(db_index=True)),
                ('score', models.DecimalField(decimal_places=2, max_digits=6)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('released', 'Released')], db_index=True, default='draft', max_length=16)),
                ('graded_by_user_id', models.IntegerField(db_index=True)),
                ('graded_at', models.DateTimeField(db_index=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grades', to='lms.courseassignment')),
                ('submission', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='grade', to='lms.coursesubmission')),
            ],
            options={
                'db_table': 'lms_course_submission_grade',
                'ordering': ['-graded_at'],
            },
        ),
        migrations.CreateModel(
            name='GradeAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('old_score', models.DecimalField(decimal_places=2, max_digits=6)),
                ('new_score', models.DecimalField(decimal_places=2, max_digits=6)),
                ('actor_user_id', models.IntegerField(db_index=True)),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grade_audit_logs', to='lms.coursesubmission')),
            ],
            options={
                'db_table': 'lms_grade_audit_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CourseAnnouncement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('created_by_user_id', models.IntegerField(db_index=True)),
                ('author_role', models.CharField(default='faculty', max_length=16)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='announcements', to='lms.course')),
            ],
            options={
                'db_table': 'lms_course_announcement',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['course', '-created_at'], name='lms_ann_course_created_idx')],
            },
        ),
        migrations.AddIndex(
            model_name='courseassignment',
            index=models.Index(fields=['course', 'status'], name='lms_asg_course_status_idx'),
        ),
        migrations.AddIndex(
            model_name='courseassignment',
            index=models.Index(fields=['course', 'due_at'], name='lms_asg_course_due_idx'),
        ),
        migrations.AddIndex(
            model_name='courseassignment',
            index=models.Index(fields=['status', 'release_at'], name='lms_asg_status_rel_idx'),
        ),
        migrations.AddIndex(
            model_name='courseassignmentextension',
            index=models.Index(fields=['assignment', 'user_id'], name='lms_asg_ext_usr_idx'),
        ),
        migrations.AddIndex(
            model_name='courseassignmentextension',
            index=models.Index(fields=['user_id', 'extended_due_at'], name='lms_asg_ext_due_idx'),
        ),
        migrations.AddConstraint(
            model_name='courseassignmentextension',
            constraint=models.UniqueConstraint(fields=('assignment', 'user_id'), name='lms_asg_ext_unique'),
        ),
        migrations.AddIndex(
            model_name='coursematerial',
            index=models.Index(fields=['course', 'status'], name='lms_mat_course_status_idx'),
        ),
        migrations.AddIndex(
            model_name='coursematerial',
            index=models.Index(fields=['course', 'section_title'], name='lms_mat_course_sec_idx'),
        ),
        migrations.AddIndex(
            model_name='coursematerial',
            index=models.Index(fields=['status', 'release_at'], name='lms_mat_status_rel_idx'),
        ),
        migrations.AddIndex(
            model_name='coursemembership',
            index=models.Index(fields=['user_id', 'role'], name='lms_mem_user_role_idx'),
        ),
        migrations.AddIndex(
            model_name='coursemembership',
            index=models.Index(fields=['course', 'role'], name='lms_mem_course_role_idx'),
        ),
        migrations.AddConstraint(
            model_name='coursemembership',
            constraint=models.UniqueConstraint(fields=('course', 'user_id'), name='lms_membership_unique'),
        ),
        migrations.AddIndex(
            model_name='coursesubmission',
            index=models.Index(fields=['assignment', 'student_user_id', 'is_latest'], name='lms_sub_asg_std_lat_idx'),
        ),
        migrations.AddIndex(
            model_name='coursesubmission',
            index=models.Index(fields=['assignment', 'status'], name='lms_sub_asg_status_idx'),
        ),
        migrations.AddIndex(
            model_name='coursesubmission',
            index=models.Index(fields=['student_user_id', '-submitted_at'], name='lms_sub_std_date_idx'),
        ),
        migrations.AddIndex(
            model_name='coursesubmissiongrade',
            index=models.Index(fields=['assignment', 'student_user_id'], name='lms_grd_asg_std_idx'),
        ),
        migrations.AddIndex(
            model_name='coursesubmissiongrade',
            index=models.Index(fields=['assignment', 'status'], name='lms_grd_asg_status_idx'),
        ),
        migrations.AddIndex(
            model_name='coursesubmissiongrade',
            index=models.Index(fields=['graded_by_user_id', 'graded_at'], name='lms_grd_by_date_idx'),
        ),
    ]
