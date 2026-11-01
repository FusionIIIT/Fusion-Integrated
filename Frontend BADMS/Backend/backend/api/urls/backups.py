from django.urls import path

from ..views import backups

urlpatterns = [
    path("backups/", backups.list_backups, name="list-backups"),
    path("backups/create/", backups.create_backup, name="create-backup"),
    path("backups/<uuid:backup_id>/", backups.get_backup, name="get-backup"),
    path("backups/<uuid:backup_id>/delete/", backups.delete_backup, name="delete-backup"),
    path("backups/<uuid:backup_id>/restore/", backups.restore_backup, name="restore-backup"),
    path("restores/", backups.list_restores, name="list-restores"),
    path("restores/<uuid:restore_id>/", backups.get_restore, name="get-restore"),
    path("schedules/", backups.list_schedules, name="list-schedules"),
    path("schedules/save/", backups.save_schedule, name="save-schedule"),
    path("schedules/preview/", backups.preview_next_runs, name="preview-next-runs"),
    path("schedules/<uuid:schedule_id>/toggle/", backups.toggle_schedule, name="toggle-schedule"),
    path("schedules/<uuid:schedule_id>/delete/", backups.delete_schedule, name="delete-schedule"),
    path("health-checks/", backups.list_health_checks, name="list-health-checks"),
    path("health-checks/run/", backups.run_health_check, name="run-health-check"),
    path("db-info/", backups.db_info, name="db-info"),
]
