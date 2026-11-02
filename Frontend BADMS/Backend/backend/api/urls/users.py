from django.urls import path

from ..views import users

urlpatterns = [
    path("users/add-staff/", users.add_individual_staff, name="add_individual_staff"),
    path("users/add-faculty/", users.add_individual_faculty, name="add_individual_faculty"),
    path("users/reset_password/", users.reset_password, name="reset-password"),
    path("users/import/", users.bulk_import_users, name="bulk-import-users"),
    path("users/export/", users.bulk_export_users, name="bulk-export-users"),
    path("users/mail-batch/", users.mail_to_whole_batch, name="mail-to-whole-batch"),
    path("download-sample-csv/", users.download_sample_csv, name="download_sample_csv"),
]
