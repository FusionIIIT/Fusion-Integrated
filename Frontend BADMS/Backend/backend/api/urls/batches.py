from django.urls import path

from ..views import batches

urlpatterns = [
    path("upcoming-batches/disciplines/", batches.list_disciplines, name="list-disciplines"),
    path("upcoming-batches/curriculums/", batches.list_curriculums, name="list-curriculums"),
    path("upcoming-batches/sync/", batches.sync_batch_data, name="sync-batch-data"),
    path("upcoming-batches/create/", batches.create_batch, name="create-batch"),
    path("upcoming-batches/<int:batch_id>/delete/", batches.delete_batch, name="delete-batch"),
    path("upcoming-batches/<int:batch_id>/students/", batches.get_batch_students, name="get-batch-students"),
    path("upcoming-batches/save-students/", batches.save_students_batch, name="save-students-batch"),
    path("upcoming-batches/add-student/", batches.add_single_student, name="add-single-student"),
    path("upcoming-batches/student/<int:student_id>/", batches.get_student, name="get-student"),
    path("upcoming-batches/student/<int:student_id>/update/", batches.update_student, name="update-student"),
    path("upcoming-batches/student/<int:student_id>/delete/", batches.delete_student, name="delete-student"),
    path("upcoming-batches/student/<int:student_id>/status/", batches.update_student_status, name="update-student-status"),
]
