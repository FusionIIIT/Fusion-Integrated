import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models


# BR-DEPT-022 and BR-DEPT-010 held by the database itself, under a per-department advisory lock.
TENURE = """
CREATE FUNCTION department_tenure_no_overlap() RETURNS trigger AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('department_role_tenure'), NEW.department_id::integer);
    IF EXISTS (
        SELECT 1 FROM department_role_tenure t
        WHERE t.department_id = NEW.department_id AND t.role = NEW.role AND t.id <> NEW.id
          AND t.valid_from < NEW.valid_to AND NEW.valid_from < t.valid_to
    ) THEN
        RAISE EXCEPTION 'two % tenures overlap in department %', NEW.role, NEW.department_id
            USING ERRCODE = 'exclusion_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER department_tenure_no_overlap BEFORE INSERT OR UPDATE ON department_role_tenure
    FOR EACH ROW EXECUTE FUNCTION department_tenure_no_overlap();
"""

SLOT = """
CREATE FUNCTION department_slot_no_clash() RETURNS trigger AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('department_timetable_slot'), NEW.department_id::integer);
    IF EXISTS (
        SELECT 1 FROM department_timetable_slot s
        WHERE s.department_id = NEW.department_id AND s.id <> NEW.id
          AND s.day_of_week = NEW.day_of_week
          AND s.starts_at < NEW.ends_at AND NEW.starts_at < s.ends_at
          AND (
              (btrim(NEW.room) <> '' AND lower(btrim(s.room)) = lower(btrim(NEW.room)))
              OR (NEW.programme <> '' AND NEW.batch_year IS NOT NULL
                  AND s.programme = NEW.programme AND s.batch_year = NEW.batch_year)
          )
    ) THEN
        RAISE EXCEPTION 'timetable slots clash in department %', NEW.department_id
            USING ERRCODE = 'exclusion_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER department_slot_no_clash BEFORE INSERT OR UPDATE ON department_timetable_slot
    FOR EACH ROW EXECUTE FUNCTION department_slot_no_clash();
"""


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=12, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('core_policies', models.TextField(blank=True)),
                ('description', models.TextField(blank=True)),
                ('contact_email', models.EmailField(blank=True, max_length=254)),
                ('contact_phone', models.CharField(blank=True, max_length=30)),
                ('office_location', models.CharField(blank=True, max_length=120)),
                ('website', models.URLField(blank=True)),
            ],
            options={
                'db_table': 'department_department',
                'ordering': ['code'],
                'constraints': [models.CheckConstraint(condition=models.Q(('name', ''), _negated=True), name='dept_name_not_blank')],
            },
        ),
        migrations.CreateModel(
            name='DepartmentNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('topic', models.CharField(max_length=60)),
                ('dedupe_key', models.CharField(max_length=200, unique=True)),
                ('recipient_user_id', models.IntegerField()),
                ('subject', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sending', 'Sending'), ('sent', 'Sent'), ('failed', 'Failed')], default='pending', max_length=8)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('last_error', models.CharField(blank=True, max_length=300)),
                ('claimed_at', models.DateTimeField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'department_notification_outbox',
                'indexes': [models.Index(fields=['status', 'created_at'], name='dept_outbox_pending_idx'), models.Index(fields=['recipient_user_id', '-created_at'], name='dept_outbox_recipient_idx')],
            },
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('submitter_id', models.IntegerField()),
                ('submitter_kind', models.CharField(max_length=10)),
                ('subject', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('category', models.CharField(blank=True, choices=[('academic', 'academic'), ('infrastructure', 'infrastructure'), ('administrative', 'administrative'), ('facilities', 'facilities'), ('other', 'other')], max_length=20)),
                ('status', models.CharField(choices=[('new', 'New'), ('under_review', 'Under review'), ('resolved', 'Resolved'), ('closed', 'Closed')], default='new', max_length=14)),
                ('reviewed_by', models.IntegerField(blank=True, null=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('disposed_by', models.IntegerField(blank=True, null=True)),
                ('disposed_at', models.DateTimeField(blank=True, null=True)),
                ('resolution_note', models.TextField(blank=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='feedback', to='department.department')),
            ],
            options={
                'db_table': 'department_feedback',
            },
        ),
        migrations.CreateModel(
            name='FeedbackNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author_id', models.IntegerField()),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('feedback', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='department.feedback')),
            ],
            options={
                'db_table': 'department_feedback_note',
            },
        ),
        migrations.CreateModel(
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=120)),
                ('unit', models.CharField(default='unit', max_length=20)),
                ('current_quantity', models.PositiveIntegerField(default=0)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inventory_items', to='department.department')),
            ],
            options={
                'db_table': 'department_inventory_item',
            },
        ),
        migrations.CreateModel(
            name='LabResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=120)),
                ('location', models.CharField(blank=True, max_length=120)),
                ('equipment', models.TextField(blank=True)),
                ('capacity', models.PositiveIntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('available', 'Available'), ('maintenance', 'Under maintenance'), ('retired', 'Retired')], default='available', max_length=12)),
                ('updated_by', models.IntegerField()),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lab_resources', to='department.department')),
            ],
            options={
                'db_table': 'department_lab_resource',
            },
        ),
        migrations.CreateModel(
            name='OfficialChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('field', models.CharField(choices=[('name', 'name'), ('core_policies', 'core_policies')], max_length=20)),
                ('proposed_value', models.TextField()),
                ('previous_value', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'Pending HOD approval'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('proposed_by', models.IntegerField()),
                ('decided_by', models.IntegerField(blank=True, null=True)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('reason', models.CharField(blank=True, max_length=500)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='official_changes', to='department.department')),
            ],
            options={
                'db_table': 'department_official_change',
            },
        ),
        migrations.CreateModel(
            name='ProfileRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(blank=True, null=True)),
                ('kind', models.CharField(choices=[('faculty', 'Faculty'), ('student', 'Student'), ('alumni', 'Alumni')], max_length=8)),
                ('display_name', models.CharField(max_length=150)),
                ('office', models.CharField(blank=True, max_length=120)),
                ('research_interests', models.TextField(blank=True)),
                ('bio', models.TextField(blank=True)),
                ('graduation_year', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('current_position', models.CharField(blank=True, max_length=150)),
                ('is_active', models.BooleanField(default=True)),
                ('updated_by', models.IntegerField()),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='profiles', to='department.department')),
            ],
            options={
                'db_table': 'department_profile_record',
            },
        ),
        migrations.CreateModel(
            name='RoleTenure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('role', models.CharField(choices=[('hod', 'HOD'), ('dept_admin', 'Dept_Admin')], max_length=10)),
                ('user_id', models.IntegerField()),
                ('valid_from', models.DateTimeField()),
                ('valid_to', models.DateTimeField()),
                ('assigned_by', models.IntegerField()),
                ('transition_applied_at', models.DateTimeField(blank=True, null=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tenures', to='department.department')),
            ],
            options={
                'db_table': 'department_role_tenure',
            },
        ),
        migrations.CreateModel(
            name='StockRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('requester_id', models.IntegerField()),
                ('quantity', models.PositiveIntegerField()),
                ('purpose', models.CharField(blank=True, max_length=300)),
                ('status', models.CharField(choices=[('pending_hod', 'Pending HOD approval'), ('approved', 'Approved for issuance'), ('rejected', 'Rejected'), ('issued', 'Issued')], default='pending_hod', max_length=12)),
                ('decided_by', models.IntegerField(blank=True, null=True)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('reason', models.CharField(blank=True, max_length=500)),
                ('issued_by', models.IntegerField(blank=True, null=True)),
                ('issued_at', models.DateTimeField(blank=True, null=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stock_requests', to='department.department')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='requests', to='department.inventoryitem')),
            ],
            options={
                'db_table': 'department_stock_request',
            },
        ),
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('receipt', 'Receipt'), ('issue', 'Issue')], max_length=8)),
                ('quantity', models.PositiveIntegerField()),
                ('actor_id', models.IntegerField()),
                ('note', models.CharField(blank=True, max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movements', to='department.inventoryitem')),
                ('stock_request', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movement', to='department.stockrequest')),
            ],
            options={
                'db_table': 'department_stock_movement',
            },
        ),
        migrations.CreateModel(
            name='TimetableSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('kind', models.CharField(choices=[('class', 'Class'), ('lab', 'Lab')], max_length=5)),
                ('programme', models.CharField(blank=True, max_length=40)),
                ('batch_year', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('course_code', models.CharField(max_length=20)),
                ('day_of_week', models.PositiveSmallIntegerField()),
                ('starts_at', models.TimeField()),
                ('ends_at', models.TimeField()),
                ('room', models.CharField(blank=True, max_length=40)),
                ('updated_by', models.IntegerField()),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='timetable_slots', to='department.department')),
            ],
            options={
                'db_table': 'department_timetable_slot',
            },
        ),
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('audience_role', models.CharField(choices=[('student', 'student'), ('faculty', 'faculty'), ('dept_admin', 'dept_admin'), ('hod', 'hod'), ('all', 'all')], max_length=12)),
                ('programme', models.CharField(blank=True, max_length=40)),
                ('batch_year', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('hidden', 'Hidden'), ('deleted', 'Deleted')], default='active', max_length=8)),
                ('author_id', models.IntegerField()),
                ('published_at', models.DateTimeField()),
                ('edited_by', models.IntegerField(blank=True, null=True)),
                ('edited_at', models.DateTimeField(blank=True, null=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='announcements', to='department.department')),
            ],
            options={
                'db_table': 'department_announcement',
                'indexes': [models.Index(fields=['department', 'status', '-id'], name='dept_ann_feed_idx')],
                'constraints': [models.CheckConstraint(condition=models.Q(models.Q(('title', ''), _negated=True), models.Q(('body', ''), _negated=True)), name='dept_ann_has_content'), models.CheckConstraint(condition=models.Q(('audience_role__in', ('student', 'faculty', 'dept_admin', 'hod', 'all'))), name='dept_ann_audience_known')],
            },
        ),
        migrations.AddIndex(
            model_name='feedback',
            index=models.Index(fields=['department', 'status', '-id'], name='dept_fb_queue_idx'),
        ),
        migrations.AddIndex(
            model_name='feedback',
            index=models.Index(fields=['submitter_id', '-id'], name='dept_fb_mine_idx'),
        ),
        migrations.AddConstraint(
            model_name='feedback',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('reviewed_by__isnull', True), ('status', 'new')), models.Q(models.Q(('status', 'new'), _negated=True), ('reviewed_by__isnull', False)), _connector='OR'), name='dept_fb_reviewed_iff_not_new'),
        ),
        migrations.AddConstraint(
            model_name='feedback',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('disposed_by__isnull', False), ('status__in', ['resolved', 'closed'])), models.Q(models.Q(('status__in', ['resolved', 'closed']), _negated=True), ('disposed_by__isnull', True)), _connector='OR'), name='dept_fb_disposed_iff_terminal'),
        ),
        migrations.AddIndex(
            model_name='feedbacknote',
            index=models.Index(fields=['feedback', 'id'], name='dept_note_thread_idx'),
        ),
        migrations.AddConstraint(
            model_name='feedbacknote',
            constraint=models.CheckConstraint(condition=models.Q(('body', ''), _negated=True), name='dept_note_has_body'),
        ),
        migrations.AddIndex(
            model_name='inventoryitem',
            index=models.Index(fields=['department', '-id'], name='dept_item_list_idx'),
        ),
        migrations.AddConstraint(
            model_name='inventoryitem',
            constraint=models.CheckConstraint(condition=models.Q(('current_quantity__gte', 0)), name='dept_item_not_negative'),
        ),
        migrations.AddConstraint(
            model_name='inventoryitem',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('name'), models.F('department'), name='dept_item_unique_name'),
        ),
        migrations.AddIndex(
            model_name='labresource',
            index=models.Index(fields=['department', '-id'], name='dept_lab_list_idx'),
        ),
        migrations.AddConstraint(
            model_name='labresource',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('name'), models.F('department'), name='dept_lab_unique_name'),
        ),
        migrations.AddIndex(
            model_name='officialchange',
            index=models.Index(fields=['department', 'status', '-id'], name='dept_change_queue_idx'),
        ),
        migrations.AddConstraint(
            model_name='officialchange',
            constraint=models.CheckConstraint(condition=models.Q(('field__in', ('name', 'core_policies'))), name='dept_change_official_field'),
        ),
        migrations.AddConstraint(
            model_name='officialchange',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'pending')), fields=('department', 'field'), name='dept_change_one_pending_per_field'),
        ),
        migrations.AddConstraint(
            model_name='officialchange',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('decided_by__isnull', True), ('status', 'pending')), models.Q(models.Q(('status', 'pending'), _negated=True), ('decided_by__isnull', False)), _connector='OR'), name='dept_change_decided_iff_not_pending'),
        ),
        migrations.AddIndex(
            model_name='profilerecord',
            index=models.Index(fields=['department', 'kind', 'display_name'], name='dept_profile_list_idx'),
        ),
        migrations.AddConstraint(
            model_name='profilerecord',
            constraint=models.UniqueConstraint(condition=models.Q(('user_id__isnull', False)), fields=('department', 'user_id'), name='dept_profile_one_per_user'),
        ),
        migrations.AddConstraint(
            model_name='profilerecord',
            constraint=models.CheckConstraint(condition=models.Q(('kind', 'alumni'), ('user_id__isnull', False), _connector='OR'), name='dept_profile_login_unless_alumni'),
        ),
        migrations.AddConstraint(
            model_name='profilerecord',
            constraint=models.CheckConstraint(condition=models.Q(('display_name', ''), _negated=True), name='dept_profile_has_name'),
        ),
        migrations.AddIndex(
            model_name='roletenure',
            index=models.Index(fields=['department', 'role', 'valid_from'], name='dept_tenure_lookup_idx'),
        ),
        migrations.AddIndex(
            model_name='roletenure',
            index=models.Index(fields=['user_id', 'role'], name='dept_tenure_user_idx'),
        ),
        migrations.AddIndex(
            model_name='roletenure',
            index=models.Index(fields=['transition_applied_at', 'valid_from'], name='dept_tenure_pending_idx'),
        ),
        migrations.AddConstraint(
            model_name='roletenure',
            constraint=models.CheckConstraint(condition=models.Q(('valid_to__gt', models.F('valid_from'))), name='dept_tenure_interval'),
        ),
        migrations.AddConstraint(
            model_name='roletenure',
            constraint=models.CheckConstraint(condition=models.Q(('role__in', ['hod', 'dept_admin'])), name='dept_tenure_role_known'),
        ),
        migrations.AddIndex(
            model_name='stockrequest',
            index=models.Index(fields=['department', 'status', '-id'], name='dept_req_queue_idx'),
        ),
        migrations.AddIndex(
            model_name='stockrequest',
            index=models.Index(fields=['requester_id', '-id'], name='dept_req_mine_idx'),
        ),
        migrations.AddConstraint(
            model_name='stockrequest',
            constraint=models.CheckConstraint(condition=models.Q(('quantity__gt', 0)), name='dept_req_positive'),
        ),
        migrations.AddConstraint(
            model_name='stockrequest',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['pending_hod', 'approved', 'rejected', 'issued'])), name='dept_req_status_known'),
        ),
        migrations.AddConstraint(
            model_name='stockrequest',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('status', 'issued'), _negated=True), ('issued_by__isnull', False), _connector='OR'), name='dept_req_issued_has_issuer'),
        ),
        migrations.AddIndex(
            model_name='stockmovement',
            index=models.Index(fields=['item', '-id'], name='dept_move_item_idx'),
        ),
        migrations.AddConstraint(
            model_name='stockmovement',
            constraint=models.CheckConstraint(condition=models.Q(('quantity__gt', 0)), name='dept_move_positive'),
        ),
        migrations.AddConstraint(
            model_name='stockmovement',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('kind', 'issue'), ('stock_request__isnull', False)), models.Q(('kind', 'receipt'), ('stock_request__isnull', True)), _connector='OR'), name='dept_move_issue_has_request'),
        ),
        migrations.AddIndex(
            model_name='timetableslot',
            index=models.Index(fields=['department', 'day_of_week', 'starts_at'], name='dept_slot_week_idx'),
        ),
        migrations.AddConstraint(
            model_name='timetableslot',
            constraint=models.CheckConstraint(condition=models.Q(('ends_at__gt', models.F('starts_at'))), name='dept_slot_ends_after_start'),
        ),
        migrations.AddConstraint(
            model_name='timetableslot',
            constraint=models.CheckConstraint(condition=models.Q(('day_of_week__lte', 6)), name='dept_slot_day_known'),
        ),
        migrations.RunSQL(
            TENURE,
            reverse_sql="DROP TRIGGER IF EXISTS department_tenure_no_overlap ON department_role_tenure;"
            " DROP FUNCTION IF EXISTS department_tenure_no_overlap();",
        ),
        migrations.RunSQL(
            SLOT,
            reverse_sql="DROP TRIGGER IF EXISTS department_slot_no_clash ON department_timetable_slot;"
            " DROP FUNCTION IF EXISTS department_slot_no_clash();",
        ),
    ]
