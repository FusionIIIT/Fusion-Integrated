# Migration to rename model indexes to explicit names

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0001_initial'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='assignment',
            new_name='idx_lms_asgn_crs_st_rel',
            old_name='lms_assignm_course__9668ad_idx',
        ),
        migrations.RenameIndex(
            model_name='assignmentsubmission',
            new_name='idx_lms_subm_asgn_std_sub',
            old_name='lms_assignm_assignm_a2bef2_idx',
        ),
        migrations.RenameIndex(
            model_name='coursematerial',
            new_name='idx_lms_mat_crs_st_rel',
            old_name='lms_course__course__e0a6de_idx',
        ),
        migrations.RenameIndex(
            model_name='submissiongrade',
            new_name='idx_lms_grade_status',
            old_name='lms_submiss_status_184c69_idx',
        ),
    ]
