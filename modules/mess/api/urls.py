from django.urls import path
from . import views_student, views_caretaker, views_warden_admin

urlpatterns = [
    path('registration/submit/', views_student.submit_registration, name='registration_submit'),
    path('rebate/submit/', views_student.submit_rebate, name='rebate_submit'),
    path('rebate/<int:request_id>/review/', views_student.review_rebate, name='review_rebate'),
    path('bills/<int:bill_id>/publish/', views_student.publish_bill, name='publish_bill'),
    path('roles/assign/', views_caretaker.assign_role, name='assign_role'),
    path('roles/assign/', views_warden_admin.assign_role, name='assign_role'),
]
